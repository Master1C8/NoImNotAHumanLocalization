// Isolated-fixture instrumentation only. Disabled unless an explicit config exists.
using System.Text.Json;
using HarmonyLib;
using TMPro;
using Yarn.Unity;
using _Code.DialogSystem;

namespace NoHuman.TextRenderer;

internal static class DialogueProbe
{
    internal static bool Enabled;
    static string sample;
    static string root;
    static LineView view;
    static string lineId;
    static string logical;
    static int sequence;
    static int lastVisible=-1;
    static float lastPoll;
    static string lastCommand;
    static string lastPanel;
    internal static void Load()
    {
        root=Path.GetFullPath(Path.Combine(Path.GetDirectoryName(typeof(Plugin).Assembly.Location),"../../config"));
        var config=Path.Combine(root,"nohuman-dialogue-probe.json");
        if(!File.Exists(config))return;
        // The loader lives only in the copied fixture, and the config must opt in explicitly.
        using var doc=JsonDocument.Parse(File.ReadAllText(config));
        Enabled=doc.RootElement.GetProperty("enabled").GetBoolean();
        if(!Enabled)return;
        sample=doc.RootElement.TryGetProperty("sample",out var s)&&s.ValueKind==JsonValueKind.String?s.GetString():null;
        File.WriteAllText(Path.Combine(root,"nohuman-dialogue-evidence.jsonl"),"");
        Record("enabled",new{sample,assembly=typeof(Plugin).Assembly.Location});
    }
    static void Record(string kind,object data)=>File.AppendAllText(Path.Combine(root,"nohuman-dialogue-evidence.jsonl"),
        JsonSerializer.Serialize(new{kind,time=UnityEngine.Time.realtimeSinceStartup,data})+"\n");
    internal static void Begin(LineView component,LocalizedLine line)
    {
        if(!Enabled)return;
        view=component;lineId=line.TextID;sequence++;lastVisible=-1;
        logical=line.TextWithoutCharacterName.Text;
        Record("line",new{sequence,lineId,raw=line.RawText,logical,substitutions=line.Substitutions?.Length,
            component=component.lineText.GetInstanceID(),font=component.lineText.font?.name,
            typewriter=component.useTypewriterEffect,speed=component.typewriterEffectSpeed,autoAdvance=component.autoAdvance});
    }
    internal static void Prepare(LocalizedLine line)
    {
        if(!Enabled || sample==null || line.TextID!="line:entrance_neighbour_0_054308e")return;
        // Insert before Yarn parses markup and distributes the line to BOTH views.
        // Restrict the probe to one verified source line; speaker and substitutions stay exact.
        const string original="Neighbour: Привет, сосед. Давно не виделись. Как жизнь?";
        if(line.RawText!=original || line.Substitutions.Length!=0)
            throw new InvalidDataException("Bounded source line changed before probe insertion");
        line.RawText="Neighbour: "+sample;
        Record("sample",new{lineId=line.TextID,original,replacement=line.RawText,boundary="UnityLocalisedLineProvider before Yarn markup/substitution and view fan-out"});
    }
    internal static void Poll(FakeDialogRunner runner)
    {
        if(!Enabled || view==null || runner.lineView.GetInstanceID()!=view.GetInstanceID())return;
        var now=UnityEngine.Time.realtimeSinceStartup;
        if(now-lastPoll<.05f)return;lastPoll=now;
        var text=view.lineText;var visible=text.maxVisibleCharacters;
        var panel=runner.optionsView.lastLineText;
        if(panel!=null && panel.gameObject.activeInHierarchy && panel.text!=lastPanel) {
            lastPanel=panel.text;
            Record("answer-panel",new{sequence,lineId,text=panel.text,font=panel.font?.name,
                count=panel.textInfo.characterCount,visible=panel.maxVisibleCharacters,overflow=panel.isTextOverflowing});
        }
        if(visible!=lastVisible) {
            lastVisible=visible;
            Record("visibility",new{sequence,lineId,visible,count=text.textInfo.characterCount,logical=text.text,
                font=text.font?.name,active=text.gameObject.activeInHierarchy,overflow=text.isTextOverflowing,
                continueActive=view.continueButton!=null&&view.continueButton.activeInHierarchy,
                canInterrupt=view.currentStopToken?.CanInterrupt,interrupted=view.currentStopToken?.WasInterrupted});
        }
        var commandPath=Path.Combine(root,"nohuman-dialogue-command.json");
        if(!File.Exists(commandPath))return;
        var content=File.ReadAllText(commandPath);if(content==lastCommand)return;lastCommand=content;
        try {
            using var command=JsonDocument.Parse(content);var obj=command.RootElement;
            if(obj.GetProperty("lineId").GetString()!=lineId || obj.GetProperty("sequence").GetInt32()!=sequence ||
               obj.GetProperty("action").GetString()!="skip" || !text.gameObject.activeInHierarchy)
                throw new InvalidDataException("Command does not match the current active dialogue line");
            Record("skip-request",new{sequence,lineId,visible,count=text.textInfo.characterCount});
            runner.SkipLine();
            Record("skip-return",new{sequence,lineId,visible=text.maxVisibleCharacters,count=text.textInfo.characterCount});
        }catch(Exception ex){Record("command-rejected",new{message=ex.Message});}
    }
}

[HarmonyPatch(typeof(OptionsListView),"RunLine")]
internal static class DialogueAnswerLineEvidence
{
    static void Prefix(LocalizedLine __0) {
        if(DialogueProbe.Enabled)Plugin.Instance.Log.LogInfo("PROBE_ANSWER_LINE: "+__0.TextID+" "+__0.TextWithoutCharacterName.Text);
    }
}

[HarmonyPatch(typeof(Yarn.Unity.UnityLocalization.UnityLocalisedLineProvider),"GetLocalizedLine")]
internal static class DialogueSampleInput
{
    static void Postfix(LocalizedLine __result)=>DialogueProbe.Prepare(__result);
}

[HarmonyPatch(typeof(LineView),"RunLine")]
internal static class DialogueLineEvidence
{
    static void Prefix(LineView __instance,LocalizedLine __0)=>DialogueProbe.Begin(__instance,__0);
}
[HarmonyPatch(typeof(FakeDialogRunner),"Update")]
internal static class DialogueStateEvidence
{
    static void Postfix(FakeDialogRunner __instance)=>DialogueProbe.Poll(__instance);
}
