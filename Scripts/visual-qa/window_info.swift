// Read-only window discovery for the exact isolated Wine fixture.
import AppKit
import CoreGraphics
import ApplicationServices
import Foundation

let fixture = "/Users/antonkrutov/Desktop/no I'm not a human/runtime/No Human Probe.app/"
let apps = NSWorkspace.shared.runningApplications.filter {
    ($0.bundleURL?.path ?? "").hasPrefix(fixture)
}
let pids = Set(apps.map { Int($0.processIdentifier) })
let windows = (CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []).filter {
    pids.contains($0[kCGWindowOwnerPID as String] as? Int ?? -1)
}
let record: [String: Any] = [
    "screenRecordingAllowed": CGPreflightScreenCaptureAccess(),
    "accessibilityAllowed": AXIsProcessTrusted(),
    "applications": apps.map { ["pid": Int($0.processIdentifier), "path": $0.bundleURL?.path ?? "", "name": $0.localizedName ?? ""] },
    "windows": windows
]
let bytes = try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys])
FileHandle.standardOutput.write(bytes)
