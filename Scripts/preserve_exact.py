#!/usr/bin/env python3
"""Build and check the mixed-text preserve-exact contract for selected game text."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from probe_assets import ROOT, digest, require


INVENTORY = ROOT / "Source/localization-inventory-v3/strings.jsonl"
STATIC = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
STATIC_SCOPE = ROOT / "Documentation/static-text-scope-v2.json"
SCOPE = ROOT / "Documentation/text-source-scope-v7.json"
MANIFEST = ROOT / "Source/preserve-exactly-v4.json"
TOKEN = re.compile(r"\{([0-9]+)\}|<([^<>]+)>")
NUMBER = re.compile(r"\d+")
BREAK = re.compile(r"\r\n|\r|\n")
BATCH_NAME = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")
STATIC_WHOLE_EXACT = {"1", "0", "100", "0/10", "1.0", "1920x1080 (60 Hz)",
                      "Space", "help", "VSync", "ver. 0.1", "\u200b"}


def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def grammar(value, allow_source_malformed=False):
    """Parse the Unity format slots and TMP tag stack inside an extracted display cell."""
    require(isinstance(value, str), "Display cell must be text")
    slots, tags, stack, styled, nesting = [], [], [], [], []
    for match in TOKEN.finditer(value):
        if match.group(1) is not None:
            slots.append("{" + match.group(1) + "}")
            continue
        tag = match.group(2)
        tags.append("<" + tag + ">")
        if tag.startswith("sprite="):
            require(NUMBER.fullmatch(tag[7:]) is not None, "Unsupported TMP sprite tag")
            nesting.append(["<" + tag + ">", [entry[2] for entry in stack]])
        elif tag.startswith("/"):
            name = tag[1:].split("=", 1)[0]
            if not stack or stack[-1][0] != name:
                require(allow_source_malformed, "Unbalanced TMP tag")
                continue
            _, end, _ = stack.pop()
            styled.append(value[end:match.start()])
        else:
            name = tag.split("=", 1)[0]
            require(name in {"b", "color", "size", "align", "line-height", "mspace"},
                    "Unknown TMP markup tag")
            nesting.append(["<" + tag + ">", [entry[2] for entry in stack]])
            stack.append((name, match.end(), "<" + tag + ">"))
    require(allow_source_malformed or not stack, "Unclosed TMP tag")
    residue = TOKEN.sub("", value)
    require(value == ">>" or not any(ch in residue for ch in "{}<>"),
            "Malformed format slot or TMP tag")
    return {"formatSlots": slots, "tmpTags": tags, "tmpNesting": nesting,
            "styledSpans": styled, "numbers": NUMBER.findall(value),
            "lineBreaks": BREAK.findall(value),
            "trailingWhitespace": re.search(r"[ \t\r\n]*$", value).group()}


def contract(stable_id, source, prefix, whole_exact=False, exact_substrings=None):
    malformed_credits = stable_id == "tmp:level5:59:m_text"
    parsed = grammar(source, malformed_credits)
    require(all(span.strip() for span in parsed["styledSpans"]),
            "Empty styled span in source: " + stable_id)
    return {"stableId": stable_id, "sourceSha256": sha_text(source),
            "speakerPrefix": prefix, "formatSlots": parsed["formatSlots"],
            "tmpTags": parsed["tmpTags"], "tmpNesting": parsed["tmpNesting"],
            "sourceMalformedMarkup": malformed_credits,
            "numbers": parsed["numbers"],
            "lineBreaks": parsed["lineBreaks"],
            "trailingWhitespace": parsed["trailingWhitespace"],
            "wholeTextExact": whole_exact,
            "exactSubstrings": exact_substrings or []}


def build():
    require(not MANIFEST.exists(), "Preserve the previous manifest")
    static_scope = json.loads(STATIC_SCOPE.read_text())
    require(static_scope["staticInventorySha256"] == digest(STATIC),
            "Static scope source changed")
    scope = json.loads(SCOPE.read_text())
    supplemental = {row["stableId"]: row for row in scope["selectedSupplementalStringRows"]}
    require(len(supplemental) == 1, "Supplemental source scope changed")
    rows = []
    table_counts = Counter()
    for line in INVENTORY.open():
        row = json.loads(line)
        if row["collection"] not in ("Dialogs", "UI") and row["stableId"] not in supplemental:
            continue
        if row["stableId"] in supplemental:
            require(row["source"] == supplemental[row["stableId"]]["source"] and
                    row["key"] == supplemental[row["stableId"]]["key"],
                    "Supplemental source text changed")
        prefixes = [span["value"] for span in row["exactSpans"]
                    if span["reason"] == "Yarn speaker/service prefix"]
        require(len(prefixes) <= 1, "Ambiguous Yarn speaker prefix")
        prefix = prefixes[0] if prefixes else None
        require(prefix is None or row["source"].startswith(prefix),
                "Inventory speaker prefix changed")
        exact = (row["key"] or "").startswith("language_") or row["source"] in ("???", ">>")
        item = contract(row["stableId"], row["source"], prefix, exact)
        item["collection"] = row["collection"]
        item["key"] = row["key"]
        item["tablePathId"] = row["tablePathId"]
        rows.append(item)
        table_counts[row["collection"]] += 1
    require(table_counts == {"Dialogs": 16100, "UI": 259, "ChecksDialogs": 1},
            "Selected table counts changed")
    static_source = {row["stableId"]: row["source"] for row in
                     (json.loads(line) for line in STATIC.open())}
    static_rows = []
    for row in static_scope["rows"]:
        require(static_source[row["stableId"]] == row["source"],
                "Static role triage text changed")
        if not row["source"] or (row["localizedStringBindings"] and
                all(link["sourceStableId"] is not None
                    for link in row["localizedStringBindings"])):
            continue
        source = row["source"]
        item = contract(row["stableId"], source, None,
                        source in STATIC_WHOLE_EXACT,
                        ["Debug.Log"] if source == "Debug.Log summary" else [])
        item["roleGroup"] = "supplementalStatic"
        static_rows.append(item)
    require(len(static_rows) == 178, "Nonempty unbound static count changed")
    result = {"schemaVersion": 1, "gameVersion": "1.3.19",
              "status": "selected-source candidate; runtime scope remains unaccepted",
              "sourceInventorySha256": digest(INVENTORY),
              "staticInventorySha256": digest(STATIC),
              "staticScopeSha256": digest(STATIC_SCOPE),
              "sourceScopeReportSha256": digest(SCOPE),
              "tableCounts": dict(table_counts), "staticNonemptyUnboundCount": len(static_rows),
              "rules": ["Preserve stable identity, table collection, key and source fingerprint.",
                        "Preserve service/speaker prefix verbatim.",
                        "Preserve each numbered format slot and TMP tag; only the pinned source credits may retain their existing malformed nesting.",
                        "Preserve ordered numeric tokens, line break sequence and trailing whitespace.",
                        "Preserve explicitly technical whole texts and exact substrings."],
              "tableRows": rows, "staticRows": static_rows}
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"manifest": str(MANIFEST.relative_to(ROOT)),
                      "sha256": digest(MANIFEST), "tableRows": len(rows),
                      "staticRows": len(static_rows)}, ensure_ascii=False))


def check_value(rule, target):
    key = rule["stableId"]
    require(isinstance(target, str) and target.strip(), "Empty target: " + key)
    require(rule["speakerPrefix"] is None or target.startswith(rule["speakerPrefix"]),
            "Speaker/service prefix mismatch: " + key)
    parsed = grammar(target, rule.get("sourceMalformedMarkup", False))
    require(Counter(parsed["formatSlots"]) == Counter(rule["formatSlots"]),
            "Format slot mismatch: " + key)
    require(Counter(parsed["tmpTags"]) == Counter(rule["tmpTags"]),
            "TMP tag mismatch: " + key)
    if rule.get("sourceMalformedMarkup"):
        require(parsed["tmpTags"] == rule["tmpTags"],
                "Pinned source markup order mismatch: " + key)
    require(Counter((tag, tuple(parents)) for tag, parents in parsed["tmpNesting"]) ==
            Counter((tag, tuple(parents)) for tag, parents in rule["tmpNesting"]),
            "TMP tag nesting mismatch: " + key)
    require(all(span.strip() for span in parsed["styledSpans"]),
            "Empty TMP styled span: " + key)
    require(parsed["numbers"] == rule["numbers"], "Numeric order mismatch: " + key)
    require(parsed["lineBreaks"] == rule["lineBreaks"],
            "Line break mismatch: " + key)
    require(parsed["trailingWhitespace"] == rule["trailingWhitespace"],
            "Trailing whitespace mismatch: " + key)
    if rule["wholeTextExact"]:
        require(sha_text(target) == rule["sourceSha256"],
                "Whole-text exact value mismatch: " + key)
    for substring in rule["exactSubstrings"]:
        require(target.count(substring) == 1, "Exact substring mismatch: " + key)


def validate(locale, output):
    require(MANIFEST.exists(), "Missing preserve-exact manifest")
    manifest = json.loads(MANIFEST.read_text())
    require(manifest["sourceInventorySha256"] == digest(INVENTORY) and
            manifest["staticInventorySha256"] == digest(STATIC) and
            manifest["staticScopeSha256"] == digest(STATIC_SCOPE) and
            manifest["sourceScopeReportSha256"] == digest(SCOPE),
            "Manifest source changed")
    expected = {row["stableId"]: row for row in
                manifest["tableRows"] + manifest["staticRows"]}
    require(len(expected) == 16538, "Duplicate preserve-exact stable IDs")
    target = {}
    files = []
    root = ROOT / "Translations" / locale
    for path in sorted(root.glob("*batch-*.json")):
        if not BATCH_NAME.fullmatch(path.name):
            continue
        batch = json.loads(path.read_text())
        require(batch["locale"] == locale and
                batch["sourceInventorySha256"] == manifest["sourceInventorySha256"],
                "Batch source or locale differs")
        collection = batch["collection"]
        for entry in batch["entries"]:
            guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
                     "UI": "0cbd8a7a4f543344bb95659de87f67a5",
                     "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
            require(collection in guids, "Unknown target collection")
            stable_id = "string:" + guids[collection] + ":" + str(entry["id"])
            require(stable_id in expected and stable_id not in target,
                    "Unknown or duplicate table target: " + stable_id)
            target[stable_id] = entry["target"]
        files.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path)})
    static_path = root / "static-text-draft.json"
    static = json.loads(static_path.read_text())
    require(static["locale"] == locale and
            static["sourceInventoryStaticSha256"] == manifest["staticInventorySha256"],
            "Static source or locale differs")
    for entry in static["entries"]:
        stable_id = entry["stableId"]
        require(stable_id in expected and stable_id not in target,
                "Unknown or duplicate static target: " + stable_id)
        target[stable_id] = entry["target"]
    files.append({"path": str(static_path.relative_to(ROOT)), "sha256": digest(static_path)})
    require(set(target) == set(expected), "Incomplete preserve-exact target coverage")
    for stable_id, rule in expected.items():
        check_value(rule, target[stable_id])
    require(not output.exists(), "Preserve the previous validation report")
    result = {"schemaVersion": 1, "locale": locale, "gameVersion": manifest["gameVersion"],
              "manifestSha256": digest(MANIFEST), "sourceInventorySha256": digest(INVENTORY),
              "staticInventorySha256": digest(STATIC), "inputFiles": files,
              "checkedRows": len(target), "exactResult": "passed",
              "semanticReview": "pending", "runtime": "not-run"}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report": str(output.relative_to(ROOT)),
                      "checkedRows": len(target), "exactResult": "passed"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    checker = sub.add_parser("validate")
    checker.add_argument("locale")
    checker.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        output = (args.output or ROOT / f"Documentation/{args.locale}-preserve-exact-v4.json").resolve()
        require(output.is_relative_to(ROOT / "Documentation"), "Output must be in Documentation")
        validate(args.locale, output)


if __name__ == "__main__":
    main()
