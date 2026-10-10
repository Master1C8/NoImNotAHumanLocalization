using NoHuman.TextRenderer;
using System.Text;
using System.Text.Json;

static void Equal<T>(T actual, T expected, string why)
{
    if (!EqualityComparer<T>.Default.Equals(actual, expected)) throw new Exception(why + ": " + actual + " != " + expected);
}
using var stream = typeof(RadioText).Assembly.GetManifestResourceStream("NoHuman.Mechanics.v1.json");
var policies = RadioText.ReadPolicies(stream);
Equal(policies.Count, 14, "Complete policy roster");
var segmentation = new Dictionary<string, string[]> {
    ["कि क्ष क्‍ष क्‌ष"] = new[] {"कि", " ", "क्ष", " ", "क्‍ष", " ", "क्‌ष"},
    ["เก้า กิ กุ"] = new[] {"เก้า", " ", "กิ", " ", "กุ"},
    ["a\u0301 👩‍💻"] = new[] {"a\u0301", " ", "👩‍💻"},
    ["שָׁלוֹם"] = new[] {"שָׁ", "ל", "וֹ", "ם"}
};
foreach (var (text, expected) in segmentation) {
    var elements = RadioText.Elements(text);
    Equal(string.Join("|", elements), string.Join("|", expected), "Complete text-element boundaries");
    var thresholds = Enumerable.Repeat(.5f, elements.Length).ToArray();
    var hidden = RadioText.Display(text, elements, thresholds, 0, "#", _ => 0);
    Equal(hidden, string.Concat(elements.Select(e => RadioText.Preserve(e) ? e : "#")), "Whole-element noise");
    Equal(RadioText.Display(text, elements, thresholds, 1, "#", _ => 0), text, "Exact full-signal recovery");
}
const string message = "18-8: код 451 от…меняется.\n";
var parts = RadioText.Elements(message);
var map = Enumerable.Range(1, parts.Length).Select(n => n / (float)parts.Length).ToArray();
var weakest = RadioText.Display(message, parts, map, 0, "#", _ => 0);
if (weakest.Contains("18") || weakest.Contains("451")) throw new Exception("Numbers must share normal signal masking");
if (!weakest.Contains("-") || !weakest.EndsWith(".\n") || !weakest.Contains("…")) throw new Exception("Original punctuation lost");
Equal(RadioText.Display(message, parts, map, 1, "#", _ => 0), message, "Authored outage survives perfect tuning");
var middle = RadioText.Display("ABCD", new[]{"A","B","C","D"}, new[]{.25f,.5f,.75f,1f}, .5f, "#", _=>0);
Equal(middle, "AB##", "Intermediate signal control");
try { RadioText.Display("ABCD", new[]{"A","B","C","D"}, new[]{.5f}, .5f, "#", _=>0); throw new Exception("Stale threshold map accepted"); }
catch (InvalidDataException ex) { Equal(ex.Message, "Radio threshold/text version mismatch", "Intended negative boundary"); }
Equal(RadioText.Quality(.5f,.5f,.05f,.1f,true,.2f),1f,"Tuned signal");
Equal(RadioText.Quality(0,.5f,.05f,.1f,true,.2f),0f,"Distant signal");
Equal(RadioText.Quality(.5f,.5f,.05f,.1f,false,.2f),.2f,"Wrong-band signal");
Equal(RadioText.RemoveMonospace("<mspace=1em>שלום 18-8</mspace>"),"שלום 18-8","Logical RTL text");
Equal(RadioText.RemoveMonospace("<b>ABCD</b>"),"<b>ABCD</b>","Unrelated formatting unchanged");
foreach (var punctuation in new[]{"।", "؟", "؛", "־"})
    Equal(RadioText.Display(punctuation, RadioText.Elements(punctuation), new[]{1f}, 0, "#", _=>0), punctuation, "Native punctuation retained");
foreach (var (locale, policy) in policies) {
    foreach (var quality in new[]{0f,.5f,1f}) {
        var output=RadioText.Display(message,parts,map,quality,policy.Noise,_=>0);
        if(quality==1) Equal(output,message,"Full-signal locale "+locale);
    }
    Console.WriteLine(JsonSerializer.Serialize(new{locale,policy.Noise,policy.Proportional,result="passed"}));
}
var fixtureLocales = new HashSet<string>();
var realMessages = 0;
foreach(var name in typeof(RadioText).Assembly.GetManifestResourceNames().Where(n => n.Contains("radio-mechanics-v1"))) {
    using var input=typeof(RadioText).Assembly.GetManifestResourceStream(name);
    using var fixture=JsonDocument.Parse(input);
    var locale=fixture.RootElement.GetProperty("locale").GetString();
    if(!fixtureLocales.Add(locale)) throw new Exception("Duplicate authored radio locale");
    var policy=policies[locale];
    Equal(fixture.RootElement.GetProperty("entries").GetArrayLength(),52,"Actual radio workload");
    foreach(var row in fixture.RootElement.GetProperty("entries").EnumerateArray()) {
        var logical=row.GetProperty("target").GetString();
        var elements=RadioText.Elements(logical);
        var thresholds=Enumerable.Range(1,elements.Length).Select(n=>n/(float)elements.Length).ToArray();
        Equal(RadioText.Display(logical,elements,thresholds,1,policy.Noise,_=>0),logical,"Actual perfect-signal message");
        var hidden=RadioText.Display(logical,elements,thresholds,0,policy.Noise,_=>0);
        if(hidden.Any(char.IsDigit)) throw new Exception("Actual code digits exposed at weakest signal");
        var partial=RadioText.Display(logical,elements,thresholds,.5f,policy.Noise,_=>0);
        if(string.IsNullOrEmpty(hidden) || string.IsNullOrEmpty(partial)) throw new Exception("Empty actual radio workload");
        realMessages++;
    }
}
Equal(fixtureLocales.SetEquals(policies.Keys),true,"All actual target-language fixtures ran");
Equal(realMessages,728,"14 locales times 52 real authored radio messages");
Console.WriteLine("ACTUAL_RADIO_MESSAGES_PASS: "+realMessages);
Console.WriteLine("RADIO_TESTS_PASS: actual logical noise implementation; excludes IL2CPP hooks, TMP layout, game timing, sound and input");
