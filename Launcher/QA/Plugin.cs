using System.Text.Json;
using System.Runtime.InteropServices;
using BepInEx;
using BepInEx.Unity.IL2CPP;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.Localization.Settings;
using _Code.Infrastructure.Settings.Language;
using _Code.Infrastructure.CloseUps.Views.Radio;

namespace NoHuman.LauncherQA;

// A task-only, game-thread bridge. Never included in the player payload.
[BepInPlugin("fun.vnrevival.nohuman.launcher.qa", "No Human Launcher QA", "0.1.0")]
public sealed class Plugin : BasePlugin
{
    internal static string Root;
    public override void Load() {
        Root = Path.Combine(Paths.GameRootPath, "VNRevival-LauncherQA");
        if (!File.Exists(Path.Combine(Root,"enabled.txt")) || File.ReadAllText(Path.Combine(Root,"enabled.txt")) != "launcher-native-qa-v1\n")
            throw new InvalidDataException("Explicit task-only QA opt-in is absent");
        string request=Path.Combine(Root,"request.json");
        Driver.InitialId=File.Exists(request)?JsonDocument.Parse(File.ReadAllText(request)).RootElement.GetProperty("id").GetString():null;
        AddComponent<Driver>();
        Log.LogInfo("LAUNCHER_QA_READY: task-only game-thread bridge, no save writes");
    }
}
public sealed class Driver : MonoBehaviour
{
    public static string InitialId;
    public Driver(IntPtr ptr) : base(ptr) { last=InitialId; }
    string last; string pending; string pendingId; float next; object radioEvidence;
    static TextSettingsDropdownInstance Owner() {
        var list = Resources.FindObjectsOfTypeAll<TextSettingsDropdownInstance>().Where(x=>x.gameObject.activeInHierarchy).ToArray();
        if (list.Length != 1) throw new InvalidDataException("Expected one active language settings owner, found "+list.Length);
        return list[0];
    }
    static unsafe void Capture(string path) {
        IntPtr filename=Marshal.StringToHGlobalUni(path);
        try {
            var span=new UnityEngine.Bindings.ManagedSpanWrapper((void*)filename,path.Length);
            ScreenCapture.CaptureScreenshot_Injected(ref span,1,ScreenCapture.StereoScreenCaptureMode.LeftEye);
        } finally { Marshal.FreeHGlobal(filename); }
    }
    static string[] Labels(TMP_Dropdown dropdown) { var labels=new List<string>();foreach(var option in dropdown.options)labels.Add(option.text);return labels.ToArray(); }
    object Snapshot() {
        var locales=new List<string>();foreach(var l in LocalizationSettings.AvailableLocales.Locales)locales.Add(l.Identifier.Code);
        var buttons=Resources.FindObjectsOfTypeAll<Button>().Where(x=>x.gameObject.activeInHierarchy).Select(x=>new {name=x.gameObject.name,enabled=x.interactable}).ToArray();
        var texts=Resources.FindObjectsOfTypeAll<TMP_Text>().Where(x=>x.gameObject.activeInHierarchy).Select(x=>new{name=x.gameObject.name,text=x.text,raw=x.m_text,font=x.font?.name,overflow=x.isTextOverflowing}).ToArray();
        var pickers=Resources.FindObjectsOfTypeAll<TMP_Dropdown>().Where(x=>x.gameObject.activeInHierarchy).Select(x=>new{name=x.gameObject.name,count=x.options.Count,value=x.value,labels=Labels(x)}).ToArray();
        return new {locale=LocalizationSettings.SelectedLocale?.Identifier.Code,locales,buttons,texts,pickers,width=Screen.width,height=Screen.height,fullscreenMode=(int)Screen.fullScreenMode,radioEvidence};
    }
    void Record(string id,bool ok,string error=null) {
        var json=JsonSerializer.Serialize(new{id,ok,error,state=Snapshot()});
        string target=Path.Combine(Plugin.Root,"response.json"),temp=target+".new";File.WriteAllText(temp,json);File.Move(temp,target,true);
    }
    public void Update() {
        if(Time.realtimeSinceStartup<next)return;next=Time.realtimeSinceStartup+.1f;
        try {
            if(pending!=null){if(File.Exists(pending)&&new FileInfo(pending).Length>32){Record(pendingId,true);pending=null;}return;}
            string request=Path.Combine(Plugin.Root,"request.json");if(!File.Exists(request))return;
            using var doc=JsonDocument.Parse(File.ReadAllText(request));var r=doc.RootElement;string id=r.GetProperty("id").GetString();if(id==last)return;last=id;
            string action=r.GetProperty("action").GetString();
            if(action=="state") { }
            else if(action=="radio-probe") {
                // Task-owned native model: real IL2CPP methods and shipping hooks,
                // without invoking gameplay/save/input/timing dependencies.
                var table=LocalizationSettings.StringDatabase.GetTable("Dialogs");
                var ui=LocalizationSettings.StringDatabase.GetTable("UI");
                if(table==null||ui==null)throw new InvalidDataException("Localized tables unavailable");
                var model=new RadioModel(.05f,.2f,.1f,null,null,null);
                model._TargetPosition_k__BackingField=.5f;
                model._TargetState_k__BackingField=(ERadioState)0;
                model._CurrentState_k__BackingField=(ERadioState)0;
                model._noiseCharsLocalization=ui.GetEntry(56531188432228352L);
                var rows=new List<object>();
                foreach(var idValue in r.GetProperty("radioIds").EnumerateArray()) {
                    long key=idValue.GetInt64();var entry=table.GetEntry(key);
                    if(entry==null)throw new InvalidDataException("Radio table ID absent: "+key);
                    string message=entry.LocalizedValue;model._message=message;model.CalculateThresholdMap();
                    int nativeThresholds=model._thresholdMap.Length;
                    model._currentPosition=0;string weak=model.GetDisplayedMessage();float weakQuality=model.NormalisedDistance;
                    model._currentPosition=.375f;string intermediate=model.GetDisplayedMessage();float intermediateQuality=model.NormalisedDistance;
                    model._currentPosition=.5f;string perfect=model.GetDisplayedMessage();float perfectQuality=model.NormalisedDistance;
                    model._CurrentState_k__BackingField=(ERadioState)1;string wrongBand=model.GetDisplayedMessage();float wrongBandQuality=model.NormalisedDistance;
                    model._CurrentState_k__BackingField=(ERadioState)0;
                    if(perfect!=message||perfectQuality!=1||weakQuality!=0||Math.Abs(intermediateQuality-.625f)>.001f||Math.Abs(wrongBandQuality-.1f)>.001f||nativeThresholds!=message.Length)
                        throw new InvalidDataException("Native radio signal invariant failed: "+key);
                    rows.Add(new{id=key,message,weak,intermediate,perfect,wrongBand,weakQuality,intermediateQuality,perfectQuality,wrongBandQuality,nativeThresholds});
                }
                var speech=new List<object>();
                foreach(var idValue in r.GetProperty("speechIds").EnumerateArray()) {
                    long key=idValue.GetInt64();var entry=table.GetEntry(key);
                    if(entry==null)throw new InvalidDataException("Foreigner table ID absent: "+key);
                    speech.Add(new{id=key,text=entry.LocalizedValue});
                }
                radioEvidence=new{locale=LocalizationSettings.SelectedLocale.Identifier.Code,rows,speech,boundary="Actual native IL2CPP RadioModel and shipping Harmony hooks; task-owned state. Excludes gameplay timing/audio/input and radio TMP layout."};
            }
            else if(action=="click-button") {
                string name=r.GetProperty("name").GetString();if(name!="Settings"&&name!="Back"&&name!="Return")throw new InvalidDataException("Button outside menu-only QA scope");
                var buttons=Resources.FindObjectsOfTypeAll<Button>().Where(x=>x.gameObject.activeInHierarchy&&x.gameObject.name==name&&x.interactable).ToArray();
                if(buttons.Length!=1)throw new InvalidDataException("Ambiguous or unavailable menu button: "+name);buttons[0].onClick.Invoke();
            }
            else if(action=="open-picker") {var owner=Owner();if(owner._dropdown.Dropdown.options.Count!=32)throw new InvalidDataException("Expected all 32 native picker entries");owner._dropdown.Dropdown.Show();}
            else if(action=="scroll-picker-bottom"||action=="scroll-picker-position") {
                var list=Owner()._dropdown.Dropdown.m_Dropdown;if(list==null)throw new InvalidDataException("Language picker is not open");
                var scroll=list.GetComponentInChildren<ScrollRect>();if(scroll==null)throw new InvalidDataException("Picker scroll region missing");float position=action=="scroll-picker-bottom"?0:r.GetProperty("position").GetSingle();if(position<0||position>1)throw new InvalidDataException("Invalid scroll position");scroll.verticalNormalizedPosition=position;
            }
            else if(action=="close-picker") {Owner()._dropdown.Dropdown.Hide();}
            else if(action=="select-locale") {
                string code=r.GetProperty("locale").GetString();var owner=Owner();int index=-1;
                for(int i=0;i<owner._dropdown.Dropdown.options.Count;i++)if(owner._locales[i].Identifier.Code==code){if(index!=-1)throw new InvalidDataException("Duplicate picker locale");index=i;}
                if(index<0||owner._dropdown.Dropdown.options.Count!=32)throw new InvalidDataException("Native picker does not contain requested locale");owner._dropdown.Dropdown.value=index;
                if(LocalizationSettings.SelectedLocale.Identifier.Code!=code)throw new InvalidDataException("Native picker callback did not accept requested locale");
            }
            else if(action=="capture") {
                string name=r.GetProperty("name").GetString();if(Path.GetFileName(name)!=name||!name.EndsWith(".png"))throw new InvalidDataException("Unsafe capture name");
                pending=Path.Combine(Plugin.Root,name);if(File.Exists(pending))throw new InvalidDataException("Capture already exists");pendingId=id;Capture(pending);return;
            }
            else if(action=="set-capture-resolution") { Screen.SetResolution(960,600,false); }
            else if(action=="restore-capture-resolution") { Screen.SetResolution(1440,900,FullScreenMode.FullScreenWindow); }
            else if(action=="quit") {Record(id,true);Application.Quit();return;}
            else throw new InvalidDataException("Unknown QA command");
            Record(id,true);
        } catch(Exception ex) { if(last!=null)Record(last,false,ex.ToString());pending=null; }
    }
}
