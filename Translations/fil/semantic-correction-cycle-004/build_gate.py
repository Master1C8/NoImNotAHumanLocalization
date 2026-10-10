#!/usr/bin/env python3
"""Reproduce cycle004 fresh locale-only corpus and derived-input gate."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIL = ROOT / "Translations/fil"
CYCLE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write", action="store_true")
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    require(args.write != args.verify, "Choose write or verify")
    plan_path = CYCLE / "plan.json"
    plan = load(plan_path)
    for pin in plan["sourceAndGlossaryFingerprints"].values():
        require(sha(ROOT / pin["path"]) == pin["sha256"],
                "Source or glossary pin changed")
    require(sha(ROOT / "Source/preserve-exactly-v4.json") ==
            plan["preserveExactManifestSha256"], "Exact contract changed")
    for name, expected in plan["finalReviewEvidenceSha256"].items():
        require(sha(FIL / "independent-review-03" / name) == expected,
                "Independent final evidence changed: " + name)
    prior_path = FIL / "semantic-correction-cycle-003/closure.json"
    require(sha(prior_path) == plan["previousClosureSha256"],
            "Previous closure changed")
    require(sha(FIL / "semantic-correction-cycle-003/closure-paired.jsonl") ==
            plan["previousPairedSha256"], "Previous review pairs changed")
    receipt_path = CYCLE / "full-corpus-validation.json"
    receipt = load(receipt_path)
    require(receipt["locale"] == "fil" and receipt["rows"] == 16538 and
            receipt["structuralResult"] == receipt["exactResult"] == "passed" and
            len(receipt["authoredFiles"]) == 456,
            "Fresh locale-only corpus receipt incomplete")
    require(sha(ROOT / "Scripts/validate_locale_corpus.py") ==
            receipt["validatorSha256"] and
            sha(ROOT / "Scripts/locale_text_inputs.py") ==
            receipt["inputLoaderSha256"], "Fresh owning validator changed")
    for name, expected in receipt["owningValidators"].items():
        require(sha(ROOT / "Scripts" / name) == expected,
                "Fresh corpus dependency changed: " + name)
    for item in receipt["authoredFiles"]:
        require(sha(ROOT / item["path"]) == item["sha256"],
                "Current authored input differs from fresh guard")
    before = ROOT / plan["beforeAuthoredPath"]
    path = ROOT / plan["row"]["authoredPath"]
    old, new = load(before), load(path)
    require(sha(before) == plan["beforeAuthoredSha256"], "Before bytes changed")
    require({k: v for k, v in old.items() if k != "entries"} ==
            {k: v for k, v in new.items() if k != "entries"} and
            len(old["entries"]) == len(new["entries"]),
            "Authored metadata or entry count differs")
    diffs = []
    for a, b in zip(old["entries"], new["entries"]):
        require({k: v for k, v in a.items() if k != "target"} ==
                {k: v for k, v in b.items() if k != "target"},
                "Non-target authored field changed")
        if a["target"] != b["target"]:
            diffs.append((b["id"], a["target"], b["target"]))
    row = plan["row"]
    require(diffs == [(int(row["stableId"].rsplit(":", 1)[1]),
                       row["currentTarget"], row["acceptedFullTarget"])],
            "Full-unit target diff differs")
    prior_gate = load(FIL / "semantic-correction-cycle-003/full-structural-validation.json")
    prior_authored = {r["path"]: r["sha256"] for r in
                      prior_gate["batchReports"]}
    current_authored = {r["path"]: r["sha256"] for r in receipt["authoredFiles"]}
    require(len(prior_authored) == 455 and len(current_authored) == 456,
            "Authored set differs")
    require(all(current_authored[p] == h for p, h in prior_authored.items()
                if p != row["authoredPath"]),
            "Unrelated authored batch changed")
    require(current_authored["Translations/fil/static-text-draft.json"] ==
            prior_gate["staticDraftSha256"], "Static authored text changed")
    sidecar = path.with_suffix(".validation.json")
    validation = load(sidecar)
    require(validation["structuralResult"] == "passed" and
            validation["batchSha256"] == sha(path),
            "Affected batch validation receipt stale")
    for report in prior_gate["batchReports"]:
        if report["path"] != row["authoredPath"]:
            require(sha(ROOT / report["sidecarPath"]) ==
                    report["sidecarSha256"], "Unrelated sidecar changed")
    derived = {name: (FIL / filename, prior_gate[field]) for name, filename, field in
               (("commonOptions", "common-options-001.authored.json", "optionRecipeSha256"),
                ("staticPhrases", "static-phrases.authored.json", "staticPhraseRecipeSha256"),
                ("creditsRoles", "credits-role-map.json", "creditsRoleMapSha256"))}
    require(all(sha(p) == expected for p, expected in derived.values()),
            "Derived recipe changed")
    option_sources = {p["source"] for p in load(derived["commonOptions"][0])["phrases"]}
    require(row["source"] not in option_sources and
            not row["stableId"].startswith("tmp:"),
            "Correction unexpectedly affects derived recipe")
    output = {"schemaVersion": 1, "locale": "fil",
              "status": "fresh full corpus structure/exact and derived-input gate passed; independent semantics pending",
              "planSha256": sha(plan_path),
              "freshCorpusValidationPath": str(receipt_path.relative_to(ROOT)),
              "freshCorpusValidationSha256": sha(receipt_path),
              "checkedIds": 16538, "missingIds": 0, "extraIds": 0,
              "duplicateIds": 0, "authoredInputs": 456, "batches": 455,
              "changedTargets": 1, "unexpectedFieldOrEntryChanges": 0,
              "affectedBatchPath": row["authoredPath"],
              "affectedBatchSha256": sha(path),
              "affectedValidationPath": str(sidecar.relative_to(ROOT)),
              "affectedValidationSha256": sha(sidecar),
              "optionRecipeSha256": sha(derived["commonOptions"][0]),
              "optionExactSourceRows": prior_gate["optionExactSourceRows"],
              "staticPhraseRecipeSha256": sha(derived["staticPhrases"][0]),
              "staticPhraseRows": prior_gate["staticPhraseRows"],
              "creditsRoleMapSha256": sha(derived["creditsRoles"][0]),
              "creditsRegeneratedExact": prior_gate["creditsRegeneratedExact"],
              "derivedReuseRule": "One corrected dialogue source is absent from the option recipe; static draft and all three recipe hashes match cycle003, whose full expansion check passed. Fresh corpus guard independently checks credits assembly.",
              "staticDraftSha256": current_authored["Translations/fil/static-text-draft.json"],
              "sourceAndGlossaryFingerprints": plan["sourceAndGlossaryFingerprints"],
              "preserveExactManifestSha256": plan["preserveExactManifestSha256"],
              "authoredFiles": receipt["authoredFiles"]}
    raw = (json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode()
    dest = CYCLE / "full-structural-validation.json"
    if args.write:
        require(not dest.exists(), "Immutable gate already exists")
        dest.write_bytes(raw)
    else:
        require(dest.read_bytes() == raw, "Gate reproduction differs")
    print(json.dumps({"gateSha256": sha(dest), "checkedIds": 16538,
                      "authoredInputs": 456, "changedTargets": 1,
                      "options": output["optionExactSourceRows"],
                      "staticPhrases": output["staticPhraseRows"]}))


if __name__ == "__main__":
    main()
