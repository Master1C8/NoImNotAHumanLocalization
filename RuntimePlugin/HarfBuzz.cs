using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

namespace NoHuman.TextRenderer;

// This adapter shapes Devanagari runs only. It does not implement paragraph bidi.
internal sealed class HarfBuzz : IDisposable
{
    const string Native = "libHarfBuzzSharp";
    [StructLayout(LayoutKind.Sequential)] struct Info { public uint Glyph, Mask, Cluster, Var1, Var2; }
    [StructLayout(LayoutKind.Sequential)] struct Position { public int AdvanceX, AdvanceY, OffsetX, OffsetY; public uint Var; }
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr hb_blob_create(byte[] data, uint length, int mode, IntPtr user, IntPtr destroy);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_blob_destroy(IntPtr blob);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr hb_face_create(IntPtr blob, uint index);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern uint hb_face_get_upem(IntPtr face);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr hb_font_create(IntPtr face);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_ot_font_set_funcs(IntPtr font);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_font_set_scale(IntPtr font, int x, int y);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern int hb_font_get_glyph_h_advance(IntPtr font, uint glyph);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr hb_buffer_create();
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_buffer_add_utf16(IntPtr buffer, ushort[] text, int length, uint offset, int count);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_buffer_guess_segment_properties(IntPtr buffer);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_shape(IntPtr font, IntPtr buffer, IntPtr features, uint count);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr hb_buffer_get_glyph_infos(IntPtr buffer, out uint count);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern IntPtr hb_buffer_get_glyph_positions(IntPtr buffer, out uint count);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_buffer_destroy(IntPtr buffer);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_font_destroy(IntPtr font);
    [DllImport(Native, CallingConvention=CallingConvention.Cdecl)] static extern void hb_face_destroy(IntPtr face);
    readonly IntPtr face, font;
    readonly double upem;
    readonly Dictionary<string,string> cache = new();
    public HarfBuzz(string path)
    {
        byte[] data=File.ReadAllBytes(path);
        // DUPLICATE means HarfBuzz owns its copy after this call.
        var blob=hb_blob_create(data,checked((uint)data.Length),0,IntPtr.Zero,IntPtr.Zero);
        try { face=hb_face_create(blob,0); } finally { hb_blob_destroy(blob); }
        upem=hb_face_get_upem(face);
        if(face==IntPtr.Zero || upem==0) throw new InvalidDataException("Invalid shaping font");
        font=hb_font_create(face);hb_ot_font_set_funcs(font);hb_font_set_scale(font,(int)upem,(int)upem);
    }
    public static bool ContainsHindi(string text) => text!=null && text.Any(c=>c >= '\u0900' && c <= '\u097f');
    static string Em(double number)=>number.ToString("0.########",CultureInfo.InvariantCulture)+"em";
    string ShapeRun(string run)
    {
        if(cache.TryGetValue(run,out var previous))return previous;
        var buffer=hb_buffer_create();
        try {
            hb_buffer_add_utf16(buffer,run.Select(c=>(ushort)c).ToArray(),run.Length,0,run.Length);
            hb_buffer_guess_segment_properties(buffer);hb_shape(font,buffer,IntPtr.Zero,0);
            var infos=hb_buffer_get_glyph_infos(buffer,out var count);
            var positions=hb_buffer_get_glyph_positions(buffer,out var positionCount);
            if(count!=positionCount || count==0)throw new InvalidDataException("Invalid shape result");
            var result=new StringBuilder("<nobr>");
            for(int i=0;i<count;i++) {
                var glyph=Marshal.PtrToStructure<Info>(IntPtr.Add(infos,i*20));
                var p=Marshal.PtrToStructure<Position>(IntPtr.Add(positions,i*20));
                if(glyph.Glyph==0 || glyph.Glyph>=6400)throw new InvalidDataException("Unmapped shaping glyph");
                if(p.OffsetX!=0)result.Append("<space=").Append(Em(p.OffsetX/upem)).Append('>');
                if(p.OffsetY!=0)result.Append("<voffset=").Append(Em(p.OffsetY/upem)).Append('>');
                result.Append((char)(0xe000+glyph.Glyph));
                if(p.OffsetY!=0)result.Append("</voffset>");
                var trailing=p.AdvanceX-hb_font_get_glyph_h_advance(font,glyph.Glyph)-p.OffsetX;
                if(trailing!=0)result.Append("<space=").Append(Em(trailing/upem)).Append('>');
            }
            result.Append("</nobr>");var shaped=result.ToString();
            if(cache.Count>=2048)cache.Clear();cache[run]=shaped;return shaped;
        } finally { hb_buffer_destroy(buffer); }
    }
    // Only actual TMP tags are protected; visible angle-bracket text remains visible.
    static readonly Regex Tag=new(@"\G</?(?:b|i|u|s|color|size|br|gradient|link|nobr|voffset|space|align|alpha|cspace|mspace|indent|line-height|line-indent|margin|mark|page|pos|rotate|strikethrough|sub|sup|uppercase|lowercase|allcaps|smallcaps|width)(?:=[^<>]*|\s+[^<>]*)?>|\G<#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?>",RegexOptions.CultureInvariant|RegexOptions.IgnoreCase);
    static readonly Regex FontChange=new(@"</?(?:font|font-weight|style|material|sprite|noparse)(?:=|\s|>)",RegexOptions.CultureInvariant|RegexOptions.IgnoreCase);
    public string Shape(string text)
    {
        // Font-changing tags require a separately bound prepared face. Retain them.
        if(FontChange.IsMatch(text))return text;
        var result=new StringBuilder();
        for(int i=0;i<text.Length;) {
            var tag=Tag.Match(text,i);
            if(tag.Success) {result.Append(tag.Value);i+=tag.Length;continue;}
            if(text[i] >= '\u0900' && text[i] <= '\u097f') {
                int end=i+1;
                while(end<text.Length && ((text[end]>='\u0900' && text[end]<='\u097f') || text[end]=='\u200c' || text[end]=='\u200d'))end++;
                result.Append(ShapeRun(text[i..end]));i=end;
            } else result.Append(text[i++]);
        }
        return result.ToString();
    }
    public void Dispose(){hb_font_destroy(font);hb_face_destroy(face);}
}
