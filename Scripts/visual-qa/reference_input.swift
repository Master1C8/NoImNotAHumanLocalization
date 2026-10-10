// Adapted from StardewTranslationInstaller's guarded CoreGraphics QA helper.
// Accepts only a current window belonging to this project's isolated fixture.
import AppKit
import CoreGraphics
import Foundation
import ApplicationServices

func reject(_ message: String) -> Never { fputs(message + "\n", stderr); exit(1) }
let args = Array(CommandLine.arguments.dropFirst())
guard args.count >= 3, let pid = Int32(args[1]), let window = Int(args[2]) else { reject("Invalid action/PID/window") }
let fixture = "/Users/antonkrutov/Desktop/no I'm not a human/runtime/No Human Probe.app/"
guard let app = NSRunningApplication(processIdentifier: pid),
      (app.bundleURL?.path ?? "").hasPrefix(fixture) else { reject("Process is not the fixture") }
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]] ?? []
guard let info = windows.first(where: {
    ($0[kCGWindowNumber as String] as? Int) == window && ($0[kCGWindowOwnerPID as String] as? Int) == Int(pid)
}), let bounds = info[kCGWindowBounds as String] as? [String: Double],
    let x = bounds["X"], let y = bounds["Y"], let w = bounds["Width"], let h = bounds["Height"] else { reject("Owned window disappeared") }
if args[0] == "focus" {
    guard AXIsProcessTrusted() else { reject("Accessibility access unavailable; no input sent") }
    let element = AXUIElementCreateApplication(pid)
    guard AXUIElementSetAttributeValue(element, kAXFrontmostAttribute as CFString, kCFBooleanTrue) == .success else {
        reject("Could not focus exact fixture through Accessibility")
    }
} else if args[0] == "click", args.count == 5, let px = Double(args[3]), let py = Double(args[4]) {
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { reject("Fixture lost focus; no input sent") }
    guard px > x && px < x+w && py > y && py < y+h else { reject("Click outside owned window") }
    let source = CGEventSource(stateID: .hidSystemState)
    let point = CGPoint(x: px, y: py)
    for kind in [CGEventType.mouseMoved, .leftMouseDown, .leftMouseUp] {
        guard let event = CGEvent(mouseEventSource: source, mouseType: kind, mouseCursorPosition: point, mouseButton: .left) else { reject("Cannot create event") }
        event.post(tap: .cghidEventTap)
        usleep(60_000)
    }
} else if args[0] == "move", args.count == 5, let px = Double(args[3]), let py = Double(args[4]) {
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { reject("Fixture lost focus") }
    guard px > x && px < x+w && py > y && py < y+h else { reject("Move outside owned window") }
    let point = CGPoint(x: px, y: py)
    guard let event = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left) else { reject("Cannot create move") }
    event.post(tap: .cghidEventTap)
} else if args[0] == "scroll", args.count == 4, let amount = Int32(args[3]) {
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { reject("Fixture lost focus") }
    guard let event = CGEvent(scrollWheelEvent2Source: nil, units: .pixel, wheelCount: 1, wheel1: amount, wheel2: 0, wheel3: 0) else { reject("Cannot create scroll") }
    event.post(tap: .cghidEventTap)
} else if ["hold-space", "tap-space", "hold-w"].contains(args[0]), args.count == 3 {
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid else { reject("Fixture lost focus; no input sent") }
    let source = CGEventSource(stateID: .hidSystemState)
    let key: CGKeyCode = args[0] == "hold-w" ? 13 : 49
    guard let down = CGEvent(keyboardEventSource: source, virtualKey: key, keyDown: true),
          let up = CGEvent(keyboardEventSource: source, virtualKey: key, keyDown: false) else { reject("Cannot create key event") }
    down.post(tap: .cghidEventTap)
    for _ in 0..<(args[0] == "hold-space" ? 40 : (args[0] == "hold-w" ? 10 : 1)) {
        usleep(100_000)
        if NSWorkspace.shared.frontmostApplication?.processIdentifier != pid {
            up.post(tap: .cghidEventTap)
            reject("Fixture lost focus during hold; key released")
        }
    }
    up.post(tap: .cghidEventTap)
} else { reject("Unsupported action") }
