using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;
using BepInEx;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using RTLTMPro;
using TMPro;
using UnityEngine.Localization;
using UnityEngine.Localization.Settings;

namespace NoHuman.NativeLanguages;

[BepInPlugin("fun.vnrevival.nohuman.native.languages", "No Human Native Languages", "0.2.1")]
public sealed class Plugin : BasePlugin
{
    internal static Plugin Instance;
    internal static Dictionary<string, Entry> Entries;
    internal static readonly Dictionary<int, Binding> Bound = new();
    [ThreadStatic] internal static bool Applying;
    [ThreadStatic] internal static int RtlDepth;
    const string Prefix = "VNREVIVAL_STATIC[";
    public sealed class Entry {
        [JsonPropertyName("fallback")] public string Fallback { get; set; }
        [JsonPropertyName("values")] public Dictionary<string, string> Values { get; set; }
    }
    internal sealed class Binding { public TMP_Text Text; public string Id; public string Last; }
    public override void Load()
    {
        Instance = this;
        Entries = JsonSerializer.Deserialize<Dictionary<string, Entry>>(File.ReadAllText(Path.Combine(Path.GetDirectoryName(typeof(Plugin).Assembly.Location), "static-text.json")));
        string[] codes = { "th","id","cs","hu","nl","fa","ro","hi","fil","el","bg","sr","sw","he" };
        if (Entries.Count != 178 || Entries.Values.Any(e => e.Fallback == null || e.Values.Count != 14 || codes.Any(c => !e.Values.ContainsKey(c))))
            throw new InvalidDataException("The native static text matrix is incomplete");
        new Harmony("fun.vnrevival.nohuman.native.languages").PatchAll(typeof(Plugin).Assembly);
        Log.LogInfo("NATIVE_LANGUAGES_READY: 14 languages, 178 static entries; locale selection belongs to the game");
    }
    internal static string Current() => LocalizationSettings.SelectedLocale?.Identifier.Code ?? "";
    internal static string Value(string id) {
        var e = Entries[id]; return e.Values.TryGetValue(Current(), out var value) ? value : e.Fallback;
    }
    internal static bool Resolve(TMP_Text text, ref string raw)
    {
        if (raw == null || !raw.StartsWith(Prefix, StringComparison.Ordinal) || !raw.EndsWith("]", StringComparison.Ordinal)) return false;
        string id = raw.Substring(Prefix.Length, raw.Length - Prefix.Length - 1);
        if (!Entries.ContainsKey(id)) throw new InvalidDataException("Unknown serialized static text identity: " + id);
        raw = Value(id); Bound[text.GetInstanceID()] = new Binding { Text = text, Id = id, Last = raw };
        return true;
    }
    internal static void Rebind()
    {
        Applying = true;
        try {
            foreach (var item in Bound.ToArray()) {
                var b = item.Value;
                if (!b.Text) { Bound.Remove(item.Key); continue; }
                b.Last = Value(b.Id);
                var rtl = b.Text.TryCast<RTLTextMeshPro>();
                if (rtl != null) rtl.text = b.Last; else b.Text.text = b.Last;
            }
            Instance.Log.LogInfo($"NATIVE_LOCALE_CHANGED: {Current()}; static bound={Bound.Count}");
        } finally { Applying = false; }
    }
}

[HarmonyPatch]
internal static class SerializedSetter
{
    static IEnumerable<MethodBase> TargetMethods() {
        yield return AccessTools.Method(typeof(TMP_Text), "set_text");
        yield return AccessTools.Method(typeof(RTLTextMeshPro), "set_text");
    }
    [HarmonyPriority(Priority.First)]
    static void Prefix(TMP_Text __instance, MethodBase __originalMethod, ref string __0, out bool __state)
    {
        __state = false;
        bool rtl = __originalMethod.DeclaringType == typeof(RTLTextMeshPro);
        bool marker = Plugin.Resolve(__instance, ref __0);
        NativePickerFont.Bind(__instance, __0);
        if (!marker && !Plugin.Applying && Plugin.RtlDepth == 0 && Plugin.Bound.TryGetValue(__instance.GetInstanceID(), out var previous) && __0 != previous.Last)
            Plugin.Bound.Remove(__instance.GetInstanceID()); // Respect gameplay's dynamic replacement.
        if (rtl) { Plugin.RtlDepth++; __state = true; }
    }
    static Exception Finalizer(bool __state, Exception __exception) {
        if (__state) Plugin.RtlDepth--;
        return __exception;
    }
}

[HarmonyPatch(typeof(RTLTextMeshPro), "UpdateText")]
internal static class SerializedRtlText
{
    [HarmonyPriority(Priority.First)]
    static void Prefix(RTLTextMeshPro __instance) {
        string raw = __instance.originalText;
        if (Plugin.Resolve(__instance, ref raw)) __instance.originalText = raw;
    }
}

[HarmonyPatch(typeof(TMP_Text), "ParseInputText")]
internal static class SerializedPlainText
{
    [HarmonyPriority(Priority.First)]
    static void Prefix(TMP_Text __instance) {
        string raw = __instance.m_text;
        if (Plugin.Resolve(__instance, ref raw)) __instance.m_text = raw;
    }
}

internal static class NativePickerFont
{
    [ThreadStatic] static bool binding;
    // A multilingual picker must use each label's script, independently of
    // the selected locale. Font and material must agree: a reused caption can
    // otherwise sample the preceding language's atlas despite a correct font.
    internal static void Bind(TMP_Text text, string raw) {
        if (binding || string.IsNullOrEmpty(raw)) return;
        var picker = text.GetComponentInParent<TMP_Dropdown>();
        if (picker == null || picker.gameObject.name != "Languages") return;
        string name = raw.Any(c => c >= '\u0590' && c <= '\u05ff') ? "VN Probe LiberationSans Dynamic"
            : raw.Any(c => (c >= '\u0600' && c <= '\u08ff') || (c >= '\ufb50' && c <= '\ufeff')) ? "NotoNaskhArabic-Regular SDF"
            : raw.Any(c => (c >= '\u0900' && c <= '\u097f') || (c >= '\ue001' && c <= '\uf19f')) ? "VN Probe Hindi Shaped Dynamic"
            : raw.Any(c => c >= '\u0e00' && c <= '\u0e7f') ? "ChakraPetch-SemiBold SDF"
            : "NotoSans-SemiBold SDF";
        var fonts = UnityEngine.Resources.FindObjectsOfTypeAll<TMP_FontAsset>().Where(f => f.name == name).ToArray();
        if (fonts.Length != 1) throw new InvalidDataException("Expected one verified picker font: " + name);
        var font = fonts[0];
        binding = true;
        try {
            if (text.font != font) text.font = font;
            if (text.fontSharedMaterial != font.material) text.fontSharedMaterial = font.material;
        } finally { binding = false; }
    }
}

[HarmonyPatch(typeof(TMP_Text), "set_font")]
internal static class PickerFontChange
{
    static void Postfix(TMP_Text __instance) { NativePickerFont.Bind(__instance, __instance.m_text); }
}

[HarmonyPatch(typeof(LocalizationSettings), "set_SelectedLocale")]
internal static class NativeLocaleSelection
{
    static void Postfix(Locale __0) { Plugin.Rebind(); }
}

[HarmonyPatch]

internal static class DestroyedText
{
    static IEnumerable<MethodBase> TargetMethods() {
        yield return AccessTools.Method(typeof(TextMeshProUGUI), "OnDestroy");
        yield return AccessTools.Method(typeof(TextMeshPro), "OnDestroy");
    }
    static void Prefix(TMP_Text __instance) { Plugin.Bound.Remove(__instance.GetInstanceID()); }
}
