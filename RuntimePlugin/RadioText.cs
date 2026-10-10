using System.Globalization;
using System.Text;
using System.Text.Json;

namespace NoHuman.TextRenderer;

// Logical text only. TMP/HarfBuzz/RTL processing happens after the noise operation.
internal static class RadioText
{
    internal sealed class Policy
    {
        public string Noise { get; init; }
        public bool Proportional { get; init; }
    }
    static readonly HashSet<string> Targets = new("th id cs hu nl fa ro hi fil el bg sr sw he".Split(' '));
    internal static Dictionary<string, Policy> ReadPolicies(Stream stream)
    {
        using var doc = JsonDocument.Parse(stream);
        if (doc.RootElement.GetProperty("schemaVersion").GetInt32() != 1)
            throw new InvalidDataException("Radio policy schema changed");
        var result = new Dictionary<string, Policy>();
        foreach (var row in doc.RootElement.GetProperty("locales").EnumerateObject())
        {
            var noise = row.Value.GetProperty("radioNoise").GetString();
            if (string.IsNullOrEmpty(noise) || noise.Any(c => char.IsControl(c) || char.IsWhiteSpace(c) || c == '<' || c == '>'))
                throw new InvalidDataException("Unsafe radio noise pool: " + row.Name);
            result.Add(row.Name, new Policy { Noise = noise, Proportional = row.Value.GetProperty("radioProportional").GetBoolean() });
        }
        if (!Targets.SetEquals(result.Keys)) throw new InvalidDataException("Incomplete radio locale policy");
        return result;
    }

    // .NET 6 predates the Indic-conjunct boundary rule. Merge its split virama
    // sequences explicitly, including join controls. Thai preposed vowels stay
    // with the following consonant rather than becoming isolated noise fragments.
    internal static string[] Elements(string text)
    {
        var result = new List<string>();
        var iterator = StringInfo.GetTextElementEnumerator(text);
        while (iterator.MoveNext())
        {
            var value = iterator.GetTextElement();
            if (result.Count > 0 && JoinsFollowing(result[^1], value)) result[^1] += value;
            else result.Add(value);
        }
        return result.ToArray();
    }
    static bool JoinsFollowing(string previous, string next)
    {
        if (previous.Length == 1 && previous[0] >= '\u0e40' && previous[0] <= '\u0e44' && next[0] >= '\u0e01' && next[0] <= '\u0e2e')
            return true;
        // Spacing vowel signs are separate Unicode graphemes but must not remain
        // visible after their consonant has been replaced by radio interference.
        if (previous.Any(c => c >= '\u0e01' && c <= '\u0e2e') &&
            (next[0] == '\u0e30' || next[0] == '\u0e32' || next[0] == '\u0e33' || next[0] == '\u0e45'))
            return true;
        var end = previous.Length - 1;
        while (end >= 0 && (previous[end] == '\u200c' || previous[end] == '\u200d')) end--;
        return end >= 0 && previous[end] == '\u094d' && next[0] >= '\u0915' && next[0] <= '\u0939';
    }
    const string Punctuation = "!\"#$%&'()*+, -./:;<=>?@[\\]^_`{|}~—“”«»¡‘’„…、。々《》「」！（），：？ｈ\n";
    internal static bool Preserve(string element) => element.All(c => char.IsWhiteSpace(c) || char.IsPunctuation(c) ||
        c == '\u200c' || c == '\u200d' || Punctuation.Contains(c));
    internal static string Display(string text, string[] elements, float[] thresholds, float quality, string noise, Func<int, int> choose)
    {
        if (elements.Length != thresholds.Length || string.Concat(elements) != text)
            throw new InvalidDataException("Radio threshold/text version mismatch");
        if (quality >= 1) return text; // Exact logical text, including authored outages.
        if (string.IsNullOrEmpty(noise)) throw new InvalidDataException("Empty radio noise pool");
        var result = new StringBuilder();
        for (var i = 0; i < elements.Length; i++)
            result.Append(quality >= thresholds[i] || Preserve(elements[i]) ? elements[i] : noise[choose(noise.Length)].ToString());
        return result.ToString();
    }
    internal static float Quality(float position, float target, float delta, float thresholdStart, bool correctBand, float wrongBandMultiplier)
    {
        var distance = Math.Abs(position - target);
        var quality = distance < delta ? 1f : thresholdStart <= 0 ? 0f : Math.Clamp(1f - (distance - delta) / thresholdStart, 0f, 1f);
        return correctBand ? quality : quality * wrongBandMultiplier;
    }
    internal static string RemoveMonospace(string text)
    {
        if (!text.StartsWith("<mspace=", StringComparison.Ordinal) || !text.EndsWith("</mspace>", StringComparison.Ordinal)) return text;
        var end = text.IndexOf('>');
        return end < 0 ? text : text.Substring(end + 1, text.Length - end - 1 - "</mspace>".Length);
    }
}
