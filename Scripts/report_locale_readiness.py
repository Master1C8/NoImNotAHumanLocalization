#!/usr/bin/env python3
"""Report draft coverage for the shared 1.3.19 text inventory without touching drafts."""

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("id", "cs", "hu", "nl", "fa", "ro", "hi", "fil", "el", "bg", "sr", "sw", "he")
BATCH = re.compile(r"(?:ui|dialogue|checks)-batch-\d{3}\.json\Z")
DENOMINATOR = 16538


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_ids():
    acceptance = json.loads((ROOT / "Documentation/text-source-acceptance-v1.json").read_text())
    strings = ROOT / "Source/localization-inventory-v3/strings.jsonl"
    static = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
    if (acceptance["selectedTotalRows"] != DENOMINATOR or
        acceptance["sourceStringsSha256"] != sha256(strings) or
        acceptance["sourceStaticSha256"] != sha256(static)):
        raise ValueError("Accepted source inventory changed")
    selected = defaultdict(set)
    with strings.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row["collection"] in ("UI", "Dialogs"):
                selected[row["collection"]].add(int(row["stableId"].rsplit(":", 1)[1]))
    scope = json.loads((ROOT / "Documentation/text-source-scope-v7.json").read_text())
    for row in scope["selectedSupplementalStringRows"]:
        selected["ChecksDialogs"].add(int(row["stableId"].rsplit(":", 1)[1]))
    static_scope = json.loads((ROOT / "Documentation/static-text-scope-v2.json").read_text())
    selected["static"] = {row["stableId"] for row in static_scope["rows"]
                          if row["source"] and
                          (not row["localizedStringBindings"] or
                           any(link["sourceStableId"] is None
                               for link in row["localizedStringBindings"]))}
    if {key: len(value) for key, value in selected.items()} != {
        "UI": 259, "Dialogs": 16100, "ChecksDialogs": 1, "static": 178}:
        raise ValueError("Selected source-ID scope changed")
    return selected, sha256(strings), sha256(static)


def snapshot(exact=False):
    selected, strings_hash, static_hash = selected_ids()
    exact_rules = None
    if exact:
        from preserve_exact import MANIFEST, SCOPE, STATIC_SCOPE, check_value
        manifest = json.loads(MANIFEST.read_text())
        if (manifest["sourceInventorySha256"] != strings_hash or
            manifest["staticInventorySha256"] != static_hash or
            manifest["staticScopeSha256"] != sha256(STATIC_SCOPE) or
            manifest["sourceScopeReportSha256"] != sha256(SCOPE)):
            raise ValueError("Preserve-exact manifest changed")
        exact_rules = {(row.get("collection", "static"),
                        row["stableId"] if "collection" not in row else
                        int(row["stableId"].rsplit(":", 1)[1])): row
                       for row in manifest["tableRows"] + manifest["staticRows"]}
        if set(exact_rules) != {(collection, key) for collection, values in selected.items()
                                   for key in values}:
            raise ValueError("Preserve-exact manifest does not cover selected IDs")
    state = json.loads((ROOT / "Documentation/localization-state.json").read_text())
    roster = {row["locale"]: row for row in state["localeRows"]}
    result = {"schemaVersion": 1, "gameVersion": state["gameVersion"],
              "sourceInventorySha256": sha256(ROOT / "Documentation/text-source-acceptance-v1.json"),
              "denominatorPerLocale": DENOMINATOR,
              "preserveExactChecked": exact, "locales": []}
    for locale in LOCALES:
        seen = set()
        observed = set()
        validated = set()
        problems = []
        files = []
        directory = ROOT / "Translations" / locale
        candidates = sorted(p for p in directory.glob("*.json") if BATCH.fullmatch(p.name))
        static_path = directory / "static-text-draft.json"
        if static_path.exists():
            candidates.append(static_path)
        for path in candidates:
            try:
                raw = path.read_bytes()
                current_hash = hashlib.sha256(raw).hexdigest()
                data = json.loads(raw)
                collection = "static" if path == static_path else data["collection"]
                if collection in selected and isinstance(data.get("entries"), list):
                    for entry in data["entries"]:
                        if isinstance(entry, dict):
                            key = entry.get("stableId") if collection == "static" else entry.get("id")
                            if key in selected[collection] and isinstance(entry.get("target"), str) and entry["target"].strip():
                                observed.add((collection, key))
                source_hash = static_hash if collection == "static" else strings_hash
                hash_field = "sourceInventoryStaticSha256" if collection == "static" else "sourceInventorySha256"
                if (collection not in selected or data.get("locale") != locale or
                    data.get("gameVersion") != state["gameVersion"] or
                    data.get("sourceLocale") != "ru" or
                    data.get("glossaryFingerprint") != roster[locale]["glossaryFingerprint"] or
                    data.get(hash_field) != source_hash):
                    problems.append(str(path.relative_to(ROOT)) + ": identity mismatch")
                    continue
                keys = set()
                for entry in data["entries"]:
                    key = entry["stableId"] if collection == "static" else entry["id"]
                    if key not in selected[collection] or key in keys or not isinstance(entry["target"], str) or not entry["target"].strip():
                        raise ValueError("unknown, duplicate or empty row")
                    if exact_rules is not None:
                        check_value(exact_rules[(collection, key)], entry["target"])
                    keys.add(key)
                overlapping = len(seen & {(collection, key) for key in keys})
                if overlapping:
                    problems.append(str(path.relative_to(ROOT)) + f": {overlapping} overlapping IDs")
                own = {(collection, key) for key in keys}
                seen |= own
                sidecar = path.with_suffix(".validation.json")
                current_validation = False
                if sidecar.exists():
                    validation = json.loads(sidecar.read_text())
                    current_validation = (validation.get("structuralResult") == "passed" and
                                          validation.get("locale") == locale and
                                          validation.get("batchSha256", validation.get("draftSha256")) == current_hash)
                if current_validation:
                    validated |= own
                files.append({"path": str(path.relative_to(ROOT)), "sha256": current_hash,
                              "rows": len(keys), "currentStructuralValidation": current_validation})
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                problems.append(str(path.relative_to(ROOT)) + ": " + str(exc))
        authored = len(seen)
        result["locales"].append({"locale": locale,
                                  "observedInScopeRows": len(observed),
                                  "authoredRows": authored,
                                  "authoredPercent": round(100 * authored / DENOMINATOR, 3),
                                  "structurallyValidatedRows": len(validated),
                                  "editoriallyAcceptedRows": None,
                                  "editorial": "not assessed by draft scan",
                                  "runtime": "not tested on a final locale package",
                                  "files": files, "problems": problems})
    return result


def update_state(report):
    path = ROOT / "Documentation/localization-state.json"
    original = path.read_bytes()
    state = json.loads(original)
    if state["gameVersion"] != report["gameVersion"]:
        raise ValueError("Game version changed during readiness scan")
    by_locale = {row["locale"]: row for row in state["localeRows"]}
    recorded_at = datetime.now(timezone.utc).isoformat()
    for result in report["locales"]:
        row = by_locale[result["locale"]]
        row["translated"] = result["authoredRows"]
        row["total"] = DENOMINATOR
        row["sourceInventoryFingerprint"] = report["sourceInventorySha256"]
        if row["phase"] in ("probe", "translate-edit"):
            row["phase"] = "translate-edit"
        row["draftReadiness"] = {
            "recordedAt": recorded_at,
            "observedInScopeRows": result["observedInScopeRows"],
            "authoredRows": result["authoredRows"],
            "authoredPercent": result["authoredPercent"],
            "structurallyValidatedRows": result["structurallyValidatedRows"],
            "preserveExactChecked": report["preserveExactChecked"],
            "editoriallyAcceptedRows": None,
            "eligibleFileCount": len(result["files"]),
            "eligibleFileSetSha256": hashlib.sha256("".join(
                item["path"] + "\t" + item["sha256"] + "\n"
                for item in result["files"]).encode()).hexdigest(),
            "problems": result["problems"],
            "meaning": "Draft coverage only; final package/runtime status is separate"
        }
        if row["phase"] == "translate-edit":
            row["nextAction"] = "Complete selected text IDs, then full semantic and independent diff audits; offline package and exact-artifact runtime QA follow."
    state["updatedAt"] = recorded_at
    state["stageStatus"] = "Thai preview remains separate; 13 non-Thai locale drafts active; see per-locale draftReadiness for current observed coverage"
    state["nonThaiIntegration"] = {
        "scope": "13 non-Thai text-only locales; textures and images excluded",
        "guide": "Documentation/NON_THAI_INTEGRATION.md",
        "readinessCommand": "python3 Scripts/report_locale_readiness.py --compact",
        "sourceAcceptanceSha256": report["sourceInventorySha256"],
        "recordedAt": recorded_at,
        "draftCoverageIsEditorialAcceptance": False,
        "packageAndRuntime": "not assessed by this draft scan"
    }
    if path.read_bytes() != original:
        raise RuntimeError("Shared checkpoint changed during readiness scan")
    data = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".localization-state-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        if path.read_bytes() != original:
            raise RuntimeError("Shared checkpoint changed before replacement")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--exact", action="store_true",
                        help="Also run the pinned preserve-exact contract (use .venv/bin/python)")
    parser.add_argument("--update-state", action="store_true",
                        help="Record this bounded draft snapshot in the shared checkpoint")
    args = parser.parse_args()
    report = snapshot(exact=args.exact)
    if args.update_state:
        update_state(report)
    if args.compact:
        for row in report["locales"]:
            print(f"{row['locale']:3} {row['authoredRows']:5}/{DENOMINATOR} "
                  f"({row['authoredPercent']:6.3f}%) validated={row['structurallyValidatedRows']:5} "
                  f"observed={row['observedInScopeRows']:5} problems={len(row['problems'])}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
