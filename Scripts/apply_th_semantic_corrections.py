#!/usr/bin/env python3
"""Apply the reviewed Thai semantic correction plan to authored text files."""

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from preserve_exact import check_value
from probe_assets import ROOT, require


DEFAULT_PLAN = ROOT / "Documentation/th-semantic-correction-plan-v2.json"
DEFAULT_RECEIPT = ROOT / "Documentation/th-semantic-correction-application-v1.json"
MANIFEST = ROOT / "Source/preserve-exactly-v4.json"
GUIDS = {
    "UI": "0cbd8a7a4f543344bb95659de87f67a5",
    "Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
    "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6",
}
BATCH = re.compile(r"(?:ui|dialogue|checks)-batch-\d{3}\.json")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load_plan(path):
    raw = path.read_bytes()
    plan = json.loads(raw)
    require(plan["status"] == "reviewed candidate correction batch; no translation files changed",
            "Expected the pinned reviewed plan")
    require(digest((ROOT / plan["auditProgressPath"]).read_bytes()) ==
            plan["auditProgressSha256"], "Semantic audit changed")
    require(digest((ROOT / plan["pairedPath"]).read_bytes()) ==
            plan["pairedSha256"], "Paired source/target input changed")
    if "inputReceiptPath" in plan:
        require(digest((ROOT / plan["inputReceiptPath"]).read_bytes()) ==
                plan["inputReceiptSha256"], "Previous correction receipt changed")
    if "diffAuditFindingsPath" in plan:
        require(digest((ROOT / plan["diffAuditFindingsPath"]).read_bytes()) ==
                plan["diffAuditFindingsSha256"], "Independent diff findings changed")
    audit = json.loads((ROOT / plan["auditProgressPath"]).read_text())
    require(audit["reviewedRows"] == audit["totalRows"] == 16538,
            "Complete first pass required")
    return plan, digest(raw)


def authored_entries():
    """Index only canonical Thai authored files and their mutable entry objects."""
    result = {}
    documents = {}
    for path in sorted((ROOT / "Translations/th").glob("*batch-*.json")):
        if not BATCH.fullmatch(path.name):
            continue
        document = json.loads(path.read_text())
        collection = document["collection"]
        require(collection in GUIDS and document["locale"] == "th",
                "Unexpected authored batch")
        documents[path] = document
        for entry in document["entries"]:
            stable_id = f"string:{GUIDS[collection]}:{entry['id']}"
            require(stable_id not in result, "Duplicate authored table ID")
            result[stable_id] = (path, entry)
    path = ROOT / "Translations/th/static-text-draft.json"
    document = json.loads(path.read_text())
    require(document["locale"] == "th", "Unexpected static draft")
    documents[path] = document
    for entry in document["entries"]:
        stable_id = entry["stableId"]
        require(stable_id not in result, "Duplicate authored static ID")
        result[stable_id] = (path, entry)
    return documents, result


def preflight(plan):
    documents, index = authored_entries()
    manifest = json.loads(MANIFEST.read_text())
    rules = {row["stableId"]: row for row in
             manifest["tableRows"] + manifest["staticRows"]}
    paired = {row["stableId"]: row for row in
              (json.loads(line) for line in (ROOT / plan["pairedPath"]).open())}
    changes = defaultdict(list)
    seen = set()
    for change in plan["changes"]:
        stable_id = change["stableId"]
        require(stable_id not in seen and stable_id in index and stable_id in paired,
                "Unknown or duplicate correction ID")
        seen.add(stable_id)
        row = paired[stable_id]
        require(row["ordinal"] == change["ordinal"] and
                row["source"] == change["source"],
                "Correction source identity changed")
        check_value(rules[stable_id], change["proposedTarget"])
        path, entry = index[stable_id]
        require(entry["target"] in (change["currentTarget"],
                                    change["proposedTarget"]),
                "Authored target has an ambiguous state: " + stable_id)
        changes[path].append((change, entry))
    require(len(seen) == len(plan["changes"]), "Correction count changed")

    pending = {}
    states = {}
    for path, entries in sorted(changes.items()):
        before = path.read_bytes()
        old = all(entry["target"] == change["currentTarget"]
                  for change, entry in entries)
        new = all(entry["target"] == change["proposedTarget"]
                  for change, entry in entries)
        require(old != new, "Mixed or ambiguous file state: " + str(path))
        state = "old" if old else "new"
        states[str(path.relative_to(ROOT))] = state
        if old:
            for change, entry in entries:
                entry["target"] = change["proposedTarget"]
            after = encoded(documents[path])
            pending[path] = (before, after, len(entries))
    return pending, states


def replace_pending(pending, stop_after=None):
    """Each file commits atomically; a retry reconciles old/new files."""
    for count, (path, (before, after, _)) in enumerate(sorted(pending.items()), 1):
        require(path.read_bytes() == before,
                "File changed after correction preflight: " + str(path))
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".th-correction-",
                                             delete=False) as stream:
                temp = Path(stream.name)
                stream.write(after)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp, path.stat().st_mode)
            os.replace(temp, path)
            if stop_after is not None and count == stop_after:
                raise RuntimeError("Simulated interruption after one atomic file replacement")
        finally:
            if temp is not None and temp.exists():
                temp.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--simulate-interruption-after", type=int)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    plan_path = args.plan.resolve()
    receipt_path = args.receipt.resolve()
    require(plan_path.is_relative_to(ROOT / "Documentation") and
            receipt_path.is_relative_to(ROOT / "Documentation"),
            "Plan and receipt must stay in canonical Documentation")
    require(args.simulate_interruption_after is None or
            (args.apply and args.simulate_interruption_after > 0),
            "Simulated interruption requires --apply and a positive file count")
    plan, plan_sha = load_plan(plan_path)
    pending, states = preflight(plan)
    summary = {"planSha256": plan_sha, "changes": len(plan["changes"]),
               "files": len(states), "oldFiles": sum(s == "old" for s in states.values()),
               "newFiles": sum(s == "new" for s in states.values())}
    if not args.apply:
        print(json.dumps(summary))
        return
    require(not receipt_path.exists(), "Correction receipt already exists")
    replace_pending(pending, args.simulate_interruption_after)
    remaining, final_states = preflight(plan)
    require(not remaining and all(s == "new" for s in final_states.values()),
            "Correction application is incomplete")
    files = []
    for name in sorted(states):
        path = ROOT / name
        before = pending.get(path)
        files.append({"path": name, "stateBefore": states[name],
                      "sha256After": digest(path.read_bytes()),
                      "sha256Before": digest(before[0]) if before else None})
    receipt = {"schemaVersion": 1,
               "status": "applied to authored Thai text; independent diff audit pending",
               "planPath": str(plan_path.relative_to(ROOT)), "planSha256": plan_sha,
               "changedRows": len(plan["changes"]), "changedFiles": len(files),
               "commitBoundary": "atomic replacement per file; retry reconciles old/new files",
               "files": files}
    receipt_path.write_bytes(encoded(receipt))
    print(json.dumps({**summary, "receipt": str(receipt_path.relative_to(ROOT)),
                      "finalNewFiles": len(final_states)}))


if __name__ == "__main__":
    main()
