// Independent CoreText shaping reference using the exact embedded game font.
// A diagnostic reference only; it never replaces native game evidence.
import AppKit
import CoreText
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
import Foundation

let args=Array(CommandLine.arguments.dropFirst())
guard args.count==3, let provider=CGDataProvider(url:URL(fileURLWithPath:args[0]) as CFURL),
      let graphicsFont=CGFont(provider),
      let context=CGContext(data:nil,width:1600,height:180,bitsPerComponent:8,bytesPerRow:0,
                            space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue)
else { fatalError("Expected font path, output path and exact sample text") }
let font=CTFontCreateWithGraphicsFont(graphicsFont,48,nil,nil)
context.setFillColor(CGColor(gray:0,alpha:1));context.fill(CGRect(x:0,y:0,width:1600,height:180))
let attrs:[NSAttributedString.Key:Any]=[
    NSAttributedString.Key(kCTFontAttributeName as String):font,
    NSAttributedString.Key(kCTForegroundColorAttributeName as String):CGColor(gray:1,alpha:1)]
let text=NSAttributedString(string:args[2],attributes:attrs)
let line=CTLineCreateWithAttributedString(text)
context.textPosition=CGPoint(x:40,y:70);CTLineDraw(line,context)
guard let image=context.makeImage(),
      let destination=CGImageDestinationCreateWithURL(URL(fileURLWithPath:args[1]) as CFURL,UTType.png.identifier as CFString,1,nil)
else { fatalError("Could not create reference image") }
CGImageDestinationAddImage(destination,image,nil)
guard CGImageDestinationFinalize(destination) else { fatalError("Could not save reference image") }
var runs:[[String:Any]]=[]
for run in CTLineGetGlyphRuns(line) as! [CTRun] {
    let count=CTRunGetGlyphCount(run)
    var glyphs=[CGGlyph](repeating:0,count:count)
    var indices=[CFIndex](repeating:0,count:count)
    var positions=[CGPoint](repeating:.zero,count:count)
    CTRunGetGlyphs(run,CFRange(location:0,length:0),&glyphs)
    CTRunGetStringIndices(run,CFRange(location:0,length:0),&indices)
    CTRunGetPositions(run,CFRange(location:0,length:0),&positions)
    runs.append(["glyphs":glyphs,"sourceUtf16Indices":indices,"positions":positions.map{[$0.x,$0.y]}])
}
let result:[String:Any]=["font":CTFontCopyPostScriptName(font),"sample":args[2],"backend":"macOS CoreText",
                        "glyphRuns":runs,"limits":"Independent reference, not in-game acceptance"]
let data=try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys])
try data.write(to:URL(fileURLWithPath:args[1]+".json"))
