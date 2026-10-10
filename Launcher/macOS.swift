import SwiftUI
import AppKit

// ContentView is adapted from StardewTranslationInstaller d4154ff.
@main
struct NoHumanLauncher: App {
    @StateObject private var state = AppState()
    var body: some Scene {
        WindowGroup("VN Revival — No, I’m not a Human") {
            ContentView(state: state).frame(width: 460, height: 350)
        }.windowResizability(.contentSize)
    }
}

enum Phase { case preparing, installing, ready, failed }
@MainActor
final class AppState: ObservableObject {
    @Published var phase: Phase = .preparing
    @Published var message = "Preparing installation…"
    private var gameApp: URL?
    private var explicitFolder: URL?
    private var started = false
    private var running = false
    private let defaults = UserDefaults.standard
    var phaseTitle: String {
        switch phase { case .preparing: "No, I’m not a Human"; case .installing: "Installing translations"; case .ready: "All translations installed"; case .failed: "Installation needs attention" }
    }
    init() {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "--game-app"), i + 1 < args.count { gameApp = URL(fileURLWithPath: args[i+1]) }
        if let i = args.firstIndex(of: "--game"), i + 1 < args.count { explicitFolder = URL(fileURLWithPath: args[i+1]) }
        if gameApp == nil, let saved = defaults.string(forKey: "gameApp") { gameApp = URL(fileURLWithPath: saved) }
    }
    func start() async { if started { return }; started = true; await install() }
    func retry() async { await install() }
    func chooseGameFolder() async {
        let panel = NSOpenPanel(); panel.canChooseDirectories = true; panel.canChooseFiles = true
        panel.allowsMultipleSelection = false; panel.title = "Choose No, I’m not a Human.app"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        gameApp = url; explicitFolder = nil; await install()
    }
    private func folder(in app: URL) throws -> URL {
        let drive = app.appendingPathComponent("Contents/SharedSupport/prefix/drive_c")
        guard let files = FileManager.default.enumerator(at: drive, includingPropertiesForKeys: [.isSymbolicLinkKey], options: [.skipsHiddenFiles]) else { throw error("Choose the installed game application.") }
        var matches: [URL] = []
        for case let item as URL in files {
            if item.lastPathComponent == "NoImNotAHuman.exe" { matches.append(item.deletingLastPathComponent()) }
        }
        guard matches.count == 1 else { throw error("This application must contain exactly one No, I’m not a Human installation.") }
        return matches[0]
    }
    private func discover() -> URL? {
        let candidates = ["/Applications/No Im not a Human.app", NSHomeDirectory()+"/Applications/No Im not a Human.app", "/Volumes/KINGSTONMAC/Applications/No Im not a Human.app"]
        return candidates.first(where: { FileManager.default.fileExists(atPath: $0) }).map { URL(fileURLWithPath: $0) }
    }
    func install() async {
        if running { return }; running = true; defer { running = false }
        phase = .installing; message = "Installing all 14 languages. Your saves are preserved."
        do {
            if gameApp == nil { gameApp = discover() }
            let game: URL
            if let explicitFolder { game = explicitFolder }
            else { guard let app = gameApp else { throw error("Game not found. Choose the installed game application.") }; game = try folder(in: app) }
            guard let resources = Bundle.main.resourceURL else { throw error("Application resources are missing.") }
            let helper = Bundle.main.bundleURL.appendingPathComponent("Contents/MacOS/nohuman-engine")
            let arguments = [resources.appendingPathComponent("Payload").path, game.path, "all"]
            let result = try await Task.detached(priority: .userInitiated) {
                let process = Process(); process.executableURL = helper; process.arguments = arguments
                let pipe = Pipe(); process.standardError = pipe; process.standardOutput = pipe
                try process.run()
                let data = pipe.fileHandleForReading.readDataToEndOfFile(); process.waitUntilExit()
                return (process.terminationStatus, String(data: data, encoding: .utf8) ?? "Installation failed.")
            }.value
            guard result.0 == 0 else { throw error(result.1) }
            if let gameApp { defaults.set(gameApp.path, forKey: "gameApp") }
            message = "Choose your language in the game settings."
            phase = .ready
        } catch { message = error.localizedDescription; phase = .failed }
    }
    func launchGame() {
        do {
            guard let app = gameApp else { throw error("Choose the installed game application to launch it.") }
            try configureLoader(in: app)
            NSWorkspace.shared.openApplication(at: app, configuration: NSWorkspace.OpenConfiguration()) { _, error in
                Task { @MainActor in
                    if let error { self.message = error.localizedDescription; self.phase = .failed }
                    else { NSApplication.shared.terminate(nil) }
                }
            }
        } catch { message = error.localizedDescription; phase = .failed }
    }
    private func configureLoader(in app: URL) throws {
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/bin/ps"); process.arguments = ["-axo", "command"]
        let pipe = Pipe(); process.standardOutput = pipe; try process.run()
        let processes = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        process.waitUntilExit()
        guard process.terminationStatus == 0, !processes.split(separator: "\n").contains(where: { $0.contains(app.path) && !$0.contains("No Human Launcher") }) else { throw error("Close the game before launching it through VN Revival.") }
        let reg = app.appendingPathComponent("Contents/SharedSupport/prefix/user.reg")
        let before = try Data(contentsOf: reg)
        guard let text = String(data: before, encoding: .utf8) else { throw error("Game settings could not be read.") }
        let section = "[Software\\\\Wine\\\\AppDefaults\\\\NoImNotAHuman.exe\\\\DllOverrides]"
        let ranges = text.ranges(of: section)
        guard ranges.count <= 1 else { throw error("Ambiguous game loader settings.") }
        var changed = text
        if let start = ranges.first {
            let end = text.range(of: "\n[", range: start.upperBound..<text.endIndex)?.lowerBound ?? text.endIndex
            let block = String(text[start.lowerBound..<end])
            let overrides = block.split(separator: "\n").filter { $0.hasPrefix("\"winhttp\"=") }
            guard overrides.count <= 1 else { throw error("Ambiguous winhttp loader setting.") }
            if let value = overrides.first {
                guard value == "\"winhttp\"=\"native,builtin\"" || value == "\"winhttp\"=\"native, builtin\"" else { throw error("The existing winhttp override is protected.") }
            } else { changed.insert(contentsOf: "\n\"winhttp\"=\"native,builtin\"\n", at: end) }
        } else { changed += "\n"+section+"\n\"winhttp\"=\"native,builtin\"\n" }
        guard try Data(contentsOf: reg) == before else { throw error("Game settings changed during launch. Retry.") }
        if changed != text { try Data(changed.utf8).write(to: reg, options: .atomic) }
    }
    private func error(_ message: String) -> NSError { NSError(domain: "VNRevival.NoHuman", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
}

extension String {
    func ranges(of pattern: String) -> [Range<String.Index>] {
        var result: [Range<String.Index>] = []; var start = startIndex
        while start < endIndex, let r = range(of: pattern, range: start..<endIndex) { result.append(r); start = r.upperBound }
        return result
    }
}

struct ContentView: View {
    @ObservedObject var state: AppState
    var body: some View {
        VStack(spacing: 22) {
            Spacer(minLength: 4)
            Image(systemName: state.phase == .ready ? "checkmark.circle.fill" : iconName)
                .font(.system(size: 60, weight: .semibold)).foregroundStyle(iconColor)
                .symbolEffect(.pulse, isActive: state.phase == .installing)
            VStack(spacing: 8) {
                Text(state.phaseTitle).font(.system(size: 27, weight: .bold, design: .rounded)).multilineTextAlignment(.center)
                if state.phase == .failed {
                    ScrollView { Text(state.message).foregroundStyle(Color.red).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }.frame(maxWidth: 380, maxHeight: 90)
                } else { Text(state.message).foregroundStyle(Color.secondary).multilineTextAlignment(.center).frame(maxWidth: 380) }
            }
            if state.phase == .preparing || state.phase == .installing { ProgressView().progressViewStyle(.linear).frame(width: 300) }
            Spacer()
            switch state.phase {
            case .ready: Button("Launch game", action: state.launchGame).buttonStyle(.borderedProminent).controlSize(.large).keyboardShortcut(.defaultAction)
            case .failed: HStack { Button("Choose game…") { Task { await state.chooseGameFolder() } }; Button("Retry") { Task { await state.retry() } }.buttonStyle(.borderedProminent) }
            case .preparing, .installing: Text("This may take a few minutes").font(.caption).foregroundStyle(.tertiary)
            }
        }.padding(30).task { await state.start() }
    }
    private var iconName: String { state.phase == .failed ? "exclamationmark.triangle.fill" : "arrow.down.circle.fill" }
    private var iconColor: Color { state.phase == .ready ? .green : state.phase == .failed ? .orange : .accentColor }
}
