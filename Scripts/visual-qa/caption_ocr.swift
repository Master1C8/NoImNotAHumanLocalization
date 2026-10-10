import Foundation
import ImageIO
import Vision

// Read only stored native frames. Never activate an application or synthesize input.
let list = URL(fileURLWithPath: CommandLine.arguments[1])
let options = try JSONSerialization.jsonObject(with: Data(contentsOf: list)) as! [String: Any]
let language = options["language"] as! String
var rows: [[String: Any]] = []
for path in options["files"] as! [String] {
    guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let full = CGImageSourceCreateImageAtIndex(source, 0, nil),
          full.width == 2880 && full.height == 1800,
          let cropped = full.cropping(to: CGRect(x: 0, y: 1500, width: 2880, height: 250)) else {
        throw NSError(domain: "CaptionOCR", code: 1, userInfo: [NSLocalizedDescriptionKey: "Native frame invalid: \(path)"])
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = [language]
    request.usesLanguageCorrection = false
    try VNImageRequestHandler(cgImage: cropped).perform([request])
    let observations = (request.results ?? []).sorted { $0.boundingBox.midY > $1.boundingBox.midY }
    rows.append(["file": path, "lines": observations.compactMap { $0.topCandidates(1).first?.string },
                 "confidence": observations.compactMap { $0.topCandidates(1).first?.confidence }])
}
let data = try JSONSerialization.data(withJSONObject: ["language": language, "rows": rows], options: [.prettyPrinted, .sortedKeys])
try data.write(to: URL(fileURLWithPath: CommandLine.arguments[2]), options: .atomic)
