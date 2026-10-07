using BepInEx;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using RTLTMPro;
using TMPro;
using System.Runtime.InteropServices;

namespace NoHuman.TextRenderer;

[BepInPlugin("fun.vnrevival.nohuman.renderer", "No Human Text Renderer Probe", "0.3.0")]
public sealed class Plugin : BasePlugin
{
    internal static Plugin Instance=null!;
    internal static HarfBuzz Shaper=null!;
    [ThreadStatic] internal static int RtlSetterDepth;
    static readonly HashSet<string> reports=new();
    public override void Load()
    {
        Instance=this;
        var root=Path.GetDirectoryName(typeof(Plugin).Assembly.Location)!;
        string fontPath=Path.Combine(root,"hi-source.ttf");
        if(Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(fontPath))).ToLowerInvariant()!="e691fe27813ec6ed11d0a5be4c6c1f6739996ed682462eaa3244a6185217dd6c")
            throw new InvalidDataException("Shaping font version changed");
        NativeLibrary.Load(Path.Combine(root,"libHarfBuzzSharp.dll"));
        Shaper=new HarfBuzz(Path.Combine(root,"hi-source.ttf"));
        DialogueProbe.Load();
        new Harmony("fun.vnrevival.nohuman.renderer").PatchAll();
        Log.LogInfo("RENDERER_READY v0.3.0: Devanagari shaping + RTL setter routing + opt-in dialogue evidence");
    }
    internal static void Report(string kind,TMP_Text component,string original,string prepared)
    {
        var key=kind+":"+component.GetInstanceID()+":"+original;
        if(reports.Add(key))Instance.Log.LogInfo($"RENDERER_{kind}: id={component.GetInstanceID()} object={component.gameObject.name} font={component.font?.name} logical={original} rendered={prepared}");
    }
}

[HarmonyPatch]
internal static class RtlSetterScope
{
    static IEnumerable<System.Reflection.MethodBase> TargetMethods()
    {
        yield return AccessTools.Method(typeof(RTLTextMeshPro),"set_text");
        yield return AccessTools.Method(typeof(RTLTextMeshPro),"UpdateText");
    }
    static void Prefix()=>Plugin.RtlSetterDepth++;
    static Exception Finalizer(Exception __exception){Plugin.RtlSetterDepth--;return __exception;}
}

[HarmonyPatch(typeof(TMP_Text),"set_text")]
internal static class TextSetter
{
    static bool Prefix(TMP_Text __instance, ref string __0)
    {
        if(string.IsNullOrEmpty(__0))return true;
        try {
            // The existing RTL component already shapes menu inputs through its derived setter.
            // Dropdowns invoke the base setter; route only that bypass through the same component.
            if(Plugin.RtlSetterDepth==0 && __0.Any(c=>(c>='\u0590' && c<='\u08ff'))) {
                var rtl=__instance.TryCast<RTLTextMeshPro>();
                if(rtl!=null) {var original=__0;rtl.text=original;Plugin.Report("RTL_ROUTE",__instance,original,rtl.text);return false;}
            }
        } catch(Exception ex) {Plugin.Instance.Log.LogError("RENDERER_FAILED: "+ex);}
        return true;
    }
}

// Transform only the renderer's temporary input. Public/logical m_text is restored,
// including the exceptional path; the prepared processing array belongs to TMP.
[HarmonyPatch(typeof(TMP_Text),"ParseInputText")]
internal static class RenderInput
{
    static void Prefix(TMP_Text __instance, out string __state)
    {
        __state=null;
        var original=__instance.m_text;
        if(!HarfBuzz.ContainsHindi(original))return;
        try {
            if(__instance.font?.name!="VN Probe Hindi Shaped Dynamic" || !__instance.richText) {
                Plugin.Report("HI_UNBOUND",__instance,original,original);return;
            }
            var prepared=Plugin.Shaper.Shape(original);
            if(prepared==original){Plugin.Report("HI_SKIPPED",__instance,original,original);return;}
            __state=original;__instance.m_text=prepared;
            __instance.m_IsTextBackingStringDirty=false;
            Plugin.Report("HI",__instance,original,prepared);
        } catch(Exception ex) {Plugin.Instance.Log.LogError("RENDERER_FAILED: "+ex);}
    }
    static Exception Finalizer(TMP_Text __instance,string __state,Exception __exception)
    {
        if(__state!=null) {
            __instance.m_text=__state;
            // TMP's public getter otherwise reconstructs text from the shaped backing
            // array. Its dirty flag must agree with the restored logical m_text.
            __instance.m_IsTextBackingStringDirty=false;
            Plugin.Report("LOGICAL_RESTORED",__instance,__state,__instance.m_text);
        }
        return __exception;
    }
}
