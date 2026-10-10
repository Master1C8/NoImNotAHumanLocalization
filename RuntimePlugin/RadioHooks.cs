using HarmonyLib;
using TMPro;
using UnityEngine.Localization.Settings;
using _Code.Infrastructure.CloseUps.Views.Radio;

namespace NoHuman.TextRenderer;

internal static class RadioSupport
{
    static Dictionary<string, RadioText.Policy> policies;
    internal sealed class MessageState
    {
        internal string Message;
        internal string[] Elements;
        internal float[] Thresholds;
    }
    static readonly Dictionary<IntPtr, MessageState> messages = new();
    internal static void Load()
    {
        using var stream = typeof(RadioSupport).Assembly.GetManifestResourceStream("NoHuman.Mechanics.v1.json")
            ?? throw new InvalidDataException("Missing embedded mechanics policy");
        policies = RadioText.ReadPolicies(stream);
    }
    internal static bool TryPolicy(out RadioText.Policy policy)
    {
        var locale = LocalizationSettings.SelectedLocale;
        policy = null;
        return locale != null && policies.TryGetValue(locale.Identifier.Code, out policy);
    }
    internal static bool IsRadioText(TMP_Text text)
    {
        // Inspect the owning component and exact field, never object-name heuristics.
        var view = text.GetComponentInParent<RadioCloseUpView>();
        return view != null && view._messageBox != null && view._messageBox.GetInstanceID() == text.GetInstanceID();
    }
    internal static void Prepare(TMP_Text text, ref string value)
    {
        if (string.IsNullOrEmpty(value)) return;
        if (TryPolicy(out var policy) && policy.Proportional && IsRadioText(text)) value = RadioText.RemoveMonospace(value);
    }
    internal static void Forget(RadioModel model) => messages.Remove(model.Pointer);
    internal static MessageState Message(RadioModel model)
    {
        var text = model._message ?? "";
        if (messages.TryGetValue(model.Pointer, out var existing) && existing.Message == text) return existing;
        var elements = RadioText.Elements(text);
        var thresholds = new float[elements.Length];
        for (var i = 0; i < elements.Length; i++) thresholds[i] = (i + 1f) / elements.Length;
        for (var i = elements.Length - 1; i > 0; i--)
        {
            var j = UnityEngine.Random.Range(0, i + 1);
            (thresholds[i], thresholds[j]) = (thresholds[j], thresholds[i]);
        }
        var state = new MessageState { Message = text, Elements = elements, Thresholds = thresholds };
        messages[model.Pointer] = state;
        return state;
    }
}

[HarmonyPatch(typeof(RadioModel), "CalculateThresholdMap")]
internal static class RadioClusterThresholds
{
    static void Postfix(RadioModel __instance)
    {
        // Keep the native UTF-16 map intact so switching to an official locale
        // cannot feed the original implementation a shorter cluster array.
        RadioSupport.Forget(__instance);
        if (RadioSupport.TryPolicy(out _)) RadioSupport.Message(__instance);
    }
}

[HarmonyPatch(typeof(RadioModel), "GetDisplayedMessage")]
internal static class RadioClusterNoise
{
    static bool Prefix(RadioModel __instance, ref string __result)
    {
        if (!RadioSupport.TryPolicy(out var policy)) return true;
        var message = __instance._message;
        if (string.IsNullOrEmpty(message) || __instance._thresholdMap == null) { __result = ""; return false; }
        var state = RadioSupport.Message(__instance);
        var quality = RadioText.Quality(__instance.CurrentPosition, __instance.TargetPosition,
            __instance._delta, __instance._thresholdStart, __instance.CurrentState == __instance.TargetState, __instance._wrongStateMultiplier);
        __instance.NormalisedDistance = quality;
        __result = RadioText.Display(message, state.Elements, state.Thresholds, quality, policy.Noise, n => UnityEngine.Random.Range(0, n));
        return false;
    }
}

[HarmonyPatch(typeof(RTLTMPro.RTLTextMeshPro), "set_text")]
internal static class RadioRtlLogicalInput
{
    // Remove spacing before the derived setter stores originalText and shapes it.
    static void Prefix(RTLTMPro.RTLTextMeshPro __instance, ref string __0) => RadioSupport.Prepare(__instance, ref __0);
}
