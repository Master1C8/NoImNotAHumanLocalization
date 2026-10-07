using System.Runtime.InteropServices;
using NoHuman.TextRenderer;
NativeLibrary.SetDllImportResolver(typeof(HarfBuzz).Assembly,(name,a,path)=>name=="libHarfBuzzSharp"?NativeLibrary.Load("/opt/homebrew/lib/libharfbuzz.dylib"):IntPtr.Zero);
using var shaper=new HarfBuzz(args.Length==1 ? args[0] : throw new ArgumentException("Pass the exact shaping font path"));
var cases=new[]{"क्ष कि की कु कू प्र ज्ञ हिंदी ABC 123","हिन्दी","शक्ति","कर्म","क्‍ष","क्‌ष","<b>हिन्दी</b>","Latin 12 русский", ""};
foreach(var input in cases){var output=shaper.Shape(input);if(output!=shaper.Shape(input))throw new Exception("Unstable cache");if(output!=shaper.Shape(output))throw new Exception("Repeated shaping");Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(new{input,output}));}
if(shaper.Shape("कि").Count(c=>c>=0xe000&&c<=0xf8ff)!=2)throw new Exception("Prebase vowel expected two glyphs");
if(shaper.Shape("क्ष").Count(c=>c>=0xe000&&c<=0xf8ff)!=1)throw new Exception("Conjunct expected one glyph");
var formatted=shaper.Shape("<b>हिन्दी</b>");
if(!formatted.StartsWith("<b><nobr>") || !formatted.EndsWith("</nobr></b>"))throw new Exception("Supported tags must remain exact around shaped text");
if(shaper.Shape("<style=Hindi>हिन्दी</style>")!="<style=Hindi>हिन्दी</style>")throw new Exception("Font-changing style must remain unprocessed");
if(shaper.Shape("<ABC>हिन्दी")=="<ABC>हिन्दी")throw new Exception("Visible angle brackets must not disable shaping");
var linked=shaper.Shape("<link=\"हिन्दी\">क्ष</link>");
if(!linked.StartsWith("<link=\"हिन्दी\"><nobr>") || !linked.EndsWith("</nobr></link>"))throw new Exception("Link ID must remain exact");
if(shaper.Shape("<noparse>हिन्दी <b></noparse>")!="<noparse>हिन्दी <b></noparse>")throw new Exception("Noparse must remain unprocessed");
if(shaper.Shape("Latin 12 русский")!="Latin 12 русский")throw new Exception("Neighbor text changed");
Console.WriteLine("SHAPER_TESTS_PASS; native macOS HarfBuzz only; excludes Wine DLL, IL2CPP hooks, TMP rendering and gameplay");
