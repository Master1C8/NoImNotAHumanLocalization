#!/usr/bin/env python3
"""Reproduce the Romanian review02 correction closure and next exact review delta.

The v2 independently read closure is retained. Review02 supplemental clean
reads are separately credited; proposed or changed units are invalidated.
Selectors use exact source repetitions and pinned compiled consumer topology.
"""

import hashlib
import importlib.util
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCALE = ROOT / "Translations/ro"
REVIEW = LOCALE / "independent-review-02"
PREVIOUS = LOCALE / "remedial-cycle-002-closure-v2"
OUT = LOCALE / "correction-cycle-003-closure"
PLAN = LOCALE / "correction-cycle-003-plan.json"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402

GUIDS = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load_ids(path):
    return set(path.read_text().splitlines())


def authored():
    files, values, locations = {}, {}, {}
    for path in sorted(LOCALE.glob("*-batch-???.json")) + [LOCALE / "static-text-draft.json"]:
        rel = str(path.relative_to(ROOT))
        data = read(path)
        files[rel] = sha(path)
        for index, entry in enumerate(data["entries"]):
            sid = entry.get("stableId") or f"string:{GUIDS[data['collection']]}:{entry['id']}"
            assert sid not in values
            values[sid] = entry["target"]
            locations[sid] = (rel, index)
    assert len(values) == 16538
    return files, values, locations


def evidence():
    plan = read(PLAN)
    assert plan["acceptedCorrections"] == 5 and plan["rejectedProposals"] == 0
    assert sha(REVIEW / "audit-manifest.json") == plan["reviewAuditManifestSha256"]
    assert sha(REVIEW / "consolidated-findings.json") == plan["reviewFindingsSha256"]
    assert sha(REVIEW / "input-pins.json") == plan["reviewInputPinsSha256"]
    audit = read(REVIEW / "audit-manifest.json")
    for desc in audit["files"]:
        assert sha(ROOT / desc["path"]) == desc["sha256"]
    assert sha(PREVIOUS / "manifest.json") == plan["previousClosureManifestSha256"]
    assert sha(ROOT / "Source/localization-inventory-v3/strings.jsonl") == plan["sourceInventorySha256"]
    assert sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl") == plan["staticInventorySha256"]
    assert sha(ROOT / "Documentation/glossary-translations/ro/layer.json") == plan["approvedGlossarySha256"]
    assert sha(ROOT / "Source/preserve-exactly-v4.json") == plan["preserveExactManifestSha256"]
    progress = read(LOCALE / "semantic-review-progress.json")
    assert progress["acceptedUnits"] == progress["reviewedUnits"] == 16538
    rows = []
    for desc in progress["reviewSegments"]:
        assert sha(ROOT / desc["path"]) == desc["sha256"]
        rows.extend(json.loads(line) for line in (ROOT / desc["path"]).read_text().splitlines())
    assert [row["ordinal"] for row in rows] == list(range(16538))
    byid = {row["stableId"]: row for row in rows}
    assert len(byid) == 16538
    before = {sid: row["target"] for sid, row in byid.items()}
    for d in read(LOCALE / "correction-cycle-001-plan.json")["corrections"]:
        assert before[d["stableId"]] == d["before"]
        before[d["stableId"]] = d["after"]
    for d in read(LOCALE / "remedial-cycle-002-plan.json")["decisions"]:
        assert before[d["stableId"]] == d["before"]
        before[d["stableId"]] = d["after"]
    files, values, locations = authored()
    assert set(values) == set(byid)
    changed = set()
    for d in plan["decisions"]:
        sid = d["stableId"]
        assert d["decision"] == "accepted"
        assert byid[sid]["source"] == d["source"] and before[sid] == d["before"]
        assert values[sid] == d["after"] != d["before"]
        assert locations[sid] == (d["authoredPath"], d["entryIndex"])
        changed.add(sid)
    assert len(changed) == 5
    for sid in set(byid) - changed:
        assert before[sid] == values[sid], sid
    rules = read(ROOT / "Source/preserve-exactly-v4.json")
    rules = {r["stableId"]: r for r in rules["tableRows"] + rules["staticRows"]}
    assert len(rules) == 16538
    for sid in byid:
        check_value(rules[sid], values[sid])
    pins = {"cycle003Plan": sha(PLAN), "review02Audit": sha(REVIEW / "audit-manifest.json"),
            "review02Findings": sha(REVIEW / "consolidated-findings.json"),
            "review02SupplementalReads": sha(REVIEW / "supplemental-context-decisions.jsonl"),
            "review02DeltaDecisions": sha(REVIEW / "per-id-decisions.jsonl"),
            "previousClosureManifest": sha(PREVIOUS / "manifest.json"),
            "firstPassProgress": sha(LOCALE / "semantic-review-progress.json"),
            "sourceInventory": plan["sourceInventorySha256"],
            "staticInventory": plan["staticInventorySha256"],
            "approvedGlossary": plan["approvedGlossarySha256"],
            "preserveExactManifest": plan["preserveExactManifestSha256"],
            "compiledDecoder": sha(LOCALE / "independent-review-01/compiled_context.py"),
            "compiledRuntimeBindings": sha(ROOT / "Source/glossary-corpus-v2/runtime-bindings.json"),
            "compiledScopePin": sha(ROOT / "Source/glossary-corpus-v2/current-dialogs-scope.json")}
    return plan, rows, byid, before, values, locations, files, changed, pins


def build():
    plan, rows, byid, before, values, locations, files, changed, pins = evidence()
    order = [r["stableId"] for r in rows]
    old = load_ids(PREVIOUS / "closure-ids.txt")
    assert len(old) == 4467
    supplemental = [json.loads(line) for line in
                    (REVIEW / "supplemental-context-decisions.jsonl").read_text().splitlines()]
    assert len(supplemental) == 41
    clean_supplemental = {r["stableId"] for r in supplemental
                          if r["decision"] == "no-objective-correction-in-context-unit"}
    proposed_supplemental = {r["stableId"] for r in supplemental
                             if r["decision"] == "objective-correction-proposed"}
    assert len(clean_supplemental) == 40 and len(proposed_supplemental) == 1
    assert proposed_supplemental <= changed
    independently_read = old | clean_supplemental
    clean_outside = clean_supplemental - old
    assert len(clean_outside) == 30
    # Retain the whole independently read prior closure, regardless of whether
    # an old reading found a correction. Changed old targets are invalidated.
    components = {"prior-reviewed-closure": old, "current-corrections": changed,
                  "clean-supplemental-context": clean_outside}
    sources = {byid[sid]["source"] for sid in changed}
    targets = {v for sid in changed for v in (before[sid], values[sid])}
    components["exact-source-and-target-repetitions"] = {
        r["stableId"] for r in rows if r["source"] in sources or
        before[r["stableId"]] in targets or values[r["stableId"]] in targets}
    decoder_path = LOCALE / "independent-review-01/compiled_context.py"
    spec = importlib.util.spec_from_file_location("ro_cycle3_full_program", decoder_path)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    nodes, program_sha = decoder.load()
    assert program_sha == plan["compiledAdjudication"]["programSha256"]
    key_to_ids = defaultdict(set)
    for r in rows:
        if r.get("key"):
            key_to_ids[r["key"]].add(r["stableId"])
    def resolved(name):
        return {op for ins in nodes[name] for op in ins["operands"]
                if isinstance(op, str) and op in key_to_ids}
    # The two call sites are discovered by actual call operands. Keep all
    # option/dialogue text in those nodes and the shared callback output.
    wash_callers = {name for name, instructions in nodes.items()
                    if any("selfchek_wash_armpits" in ins["operands"] for ins in instructions)}
    assert wash_callers == {"selfcheck_armpit_imposter", "selfcheck_hands"}
    wash_nodes = wash_callers | {"selfchek_wash_armpits"}
    wash_keys = set().union(*(resolved(name) for name in wash_nodes))
    components["wash-callback-family"] = {sid for key in wash_keys for sid in key_to_ids[key]}
    assert {d["stableId"] for d in plan["decisions"] if d["defectGroup"] == "washing-action-location"} \
        <= components["wash-callback-family"]
    # Follow the successful TryGiveItemFor branch to the actual two response
    # nodes, including the distinct Firefighter response. The six source lines
    # are selected by compiled response operands, not by hard-coded IDs.
    item = read(LOCALE / "independent-review-01/item-action-family.json")
    assert item["familyCount"] == 245 and item["programSha256"] == program_sha
    success_names = set()
    for name in item["consumerNodes"]:
        instructions = nodes[name]
        assert instructions == item["consumerNodes"][name]
        assert any("TryGiveItemFor" in ins["operands"] for ins in instructions)
        success_names.update(op for ins in instructions for op in ins["operands"]
                             if isinstance(op, str) and op.startswith("FEMA_GivingPostcard"))
    assert success_names == {"FEMA_GivingPostcard", "FEMA_GivingPostcard_Firefighter"}
    success_keys = set().union(*(resolved(name) for name in success_names))
    components["item-transfer-success-responses"] = {
        sid for key in success_keys for sid in key_to_ids[key]}
    assert len(components["item-transfer-success-responses"]) == 6
    assert {rows[o]["stableId"] for o in range(6757, 6763)} == \
        components["item-transfer-success-responses"]
    # Complete affected option/reply contexts are actual node operands.
    scene_names = set().union(*(plan["compiledAdjudication"][name]
                                for name in ("doctor", "couple", "washing", "transferSuccess")))
    scene_keys = set().union(*(resolved(name) for name in scene_names))
    components["affected-compiled-scenes"] = {sid for key in scene_keys for sid in key_to_ids[key]}
    previous_manifest = read(PREVIOUS / "manifest.json")
    catalog = {"v2-" + name: load_ids(ROOT / desc["path"])
               for name, desc in previous_manifest["currentRegressionCatalog"].items()}
    catalog.update({"wash-options-actual-callback": components["wash-callback-family"],
                    "successful-document-transfer-response": components["item-transfer-success-responses"],
                    "doctor-quarantine-chronology": {sid for name in plan["compiledAdjudication"]["doctor"]
                                                    for key in resolved(name) for sid in key_to_ids[key]},
                    "couple-past-night-context": {sid for name in plan["compiledAdjudication"]["couple"]
                                                  for key in resolved(name) for sid in key_to_ids[key]}})
    components["mandatory-regressions"] = set().union(*catalog.values())
    closure = set().union(*components.values())
    assert old <= closure <= set(order)
    retired = old - closure
    assert not retired
    invalidated_prior = changed & independently_read
    delta = changed | (closure - independently_read) | invalidated_prior
    assert changed <= delta <= closure
    assert {rows[o]["stableId"] for o in (11963, 12078, 12104)} <= closure
    assert components["item-transfer-success-responses"] <= closure
    return locals()


def emit():
    assert not OUT.exists(), "Closure is immutable"
    e = build()
    OUT.mkdir()
    order = e["order"]
    def id_file(name, members):
        path = OUT / name
        path.write_text("".join(sid + "\n" for sid in order if sid in members))
        return {"path": str(path.relative_to(ROOT)), "rows": len(members), "sha256": sha(path)}
    component_desc = {name: id_file("component-" + name + ".ids.txt", members)
                      for name, members in e["components"].items()}
    catalog_desc = {name: id_file("regression-" + name + ".ids.txt", members)
                    for name, members in e["catalog"].items()}
    changed = id_file("changed-ids.txt", e["changed"])
    closure = id_file("closure-ids.txt", e["closure"])
    delta = id_file("next-review-delta-ids.txt", e["delta"])
    reviewed = id_file("previous-independent-reads.ids.txt", e["independently_read"])
    clean_extra = id_file("clean-supplemental-reads.ids.txt", e["clean_outside"])
    invalidated = id_file("invalidated-prior-ids.txt", e["invalidated_prior"])
    retired = id_file("retired-prior-ids.txt", e["retired"])
    review_path = OUT / "review-rows.jsonl"
    with review_path.open("w") as stream:
        for row in e["rows"]:
            sid = row["stableId"]
            if sid not in e["closure"]:
                continue
            stream.write(json.dumps({"ordinal": row["ordinal"], "stableId": sid,
                                     "collection": row["collection"], "key": row["key"],
                                     "source": row["source"], "before": e["before"][sid],
                                     "after": e["values"][sid],
                                     "authoredPath": e["locations"][sid][0],
                                     "components": [name for name, members in e["components"].items() if sid in members],
                                     "mandatoryRegressions": [name for name, members in e["catalog"].items() if sid in members]},
                                    ensure_ascii=False, separators=(",", ":")) + "\n")
    review = {"path": str(review_path.relative_to(ROOT)), "rows": len(e["closure"]),
              "sha256": sha(review_path)}
    write(OUT / "compiled-consumer-context.json", {
        "programSha256": e["program_sha"],
        "washCallerNodes": sorted(e["wash_callers"]),
        "washCallbackNode": "selfchek_wash_armpits",
        "transferSuccessfulResponseNodes": sorted(e["success_names"]),
        "affectedSceneNodes": {name: e["nodes"][name] for name in sorted(e["scene_names"])},
        "washResolvedKeys": sorted(e["wash_keys"]),
        "transferSuccessResolvedKeys": sorted(e["success_keys"]),
        "sourcePeculiarity": e["plan"]["compiledAdjudication"]["sourcePeculiarity"],
        "limit": "Pinned compiled operands establish branch/callback relationships, not live gameplay reachability."})
    write(OUT / "retirement-and-invalidation.json", {
        "previousClosureIds": len(e["old"]), "review02CleanSupplementalOutsideClosure": len(e["clean_outside"]),
        "priorIndependentReadIds": len(e["independently_read"]),
        "retiredIds": 0,
        "retirementReason": "No ID from the previously independently reviewed closure was removed.",
        "correctedPriorReadIds": [sid for sid in order if sid in e["invalidated_prior"]],
        "proposedSupplementalIdWasNotCreditedClean": [sid for sid in order if sid in e["proposed_supplemental"]],
        "deltaFormula": "corrected IDs union (current closure minus previous independent reads) union explicitly invalidated prior IDs"})
    old_dynamic = PREVIOUS / "dynamic-consumer-context.json"
    dynamic = {"path": str(old_dynamic.relative_to(ROOT)), "sha256": sha(old_dynamic),
               "reusedBecause": "No occupied-room target or source/provider input changed in correction003."}
    other = {name: {"path": str((OUT / name).relative_to(ROOT)), "sha256": sha(OUT / name)}
             for name in ("compiled-consumer-context.json", "retirement-and-invalidation.json")}
    manifest = {"schemaVersion": 1, "locale": "ro", "cycle": 3,
                "status": "author correction003 closure; next independent review pending",
                "acceptedUnits": 16538, "firstPassReviewedUnits": 16538,
                "review02ExactDeltaReads": 1403, "review02SupplementalContextReads": 41,
                "pins": e["pins"], "recipeSha256": sha(pathlib.Path(__file__)),
                "previousComponents": e["previous_manifest"]["currentComponents"],
                "currentComponents": component_desc,
                "previousRegressionCatalog": e["previous_manifest"]["currentRegressionCatalog"],
                "currentRegressionCatalog": catalog_desc,
                "changedIds": changed, "closureIds": closure, "nextReviewDeltaIds": delta,
                "previousIndependentReads": reviewed, "cleanSupplementalReads": clean_extra,
                "invalidatedPriorIds": invalidated, "retiredPriorIds": retired,
                "reviewRows": review, "otherEvidence": other,
                "reusedDynamicConsumerContext": dynamic,
                "beforeAuthoredFiles": e["plan"]["beforeAuthoredFiles"],
                "afterAuthoredFiles": [{"path": path, "sha256": digest} for path, digest in sorted(e["files"].items())],
                "authoredMaps": e["plan"]["beforeAuthoredMaps"],
                "historicalPreimageLimit": e["plan"]["historicalPreimageLimit"],
                "independentReview": "pending distinct reviewer; author verification is not independent acceptance",
                "runtime": "not run"}
    write(OUT / "manifest.json", manifest)
    print(json.dumps({"manifestSha256": sha(OUT / "manifest.json"),
                      "closure": len(e["closure"]), "nextDelta": len(e["delta"]),
                      "corrected": len(e["changed"]), "cleanSupplementalOutside": len(e["clean_outside"]),
                      "retired": len(e["retired"])}))


def verify():
    manifest = read(OUT / "manifest.json")
    assert manifest["recipeSha256"] == sha(pathlib.Path(__file__))
    e = build()
    assert manifest["pins"] == e["pins"]
    for name, members in e["components"].items():
        desc = manifest["currentComponents"][name]
        assert sha(ROOT / desc["path"]) == desc["sha256"]
        assert load_ids(ROOT / desc["path"]) == members
    for name, members in e["catalog"].items():
        desc = manifest["currentRegressionCatalog"][name]
        assert sha(ROOT / desc["path"]) == desc["sha256"]
        assert load_ids(ROOT / desc["path"]) == members
    for name, members in (("changedIds", e["changed"]), ("closureIds", e["closure"]),
                          ("nextReviewDeltaIds", e["delta"]),
                          ("previousIndependentReads", e["independently_read"]),
                          ("cleanSupplementalReads", e["clean_outside"]),
                          ("invalidatedPriorIds", e["invalidated_prior"]),
                          ("retiredPriorIds", e["retired"])):
        desc = manifest[name]
        assert sha(ROOT / desc["path"]) == desc["sha256"]
        assert load_ids(ROOT / desc["path"]) == members
    for desc in ([manifest["reviewRows"], manifest["reusedDynamicConsumerContext"]] +
                 list(manifest["otherEvidence"].values()) + manifest["afterAuthoredFiles"] +
                 manifest["authoredMaps"]):
        assert sha(ROOT / desc["path"]) == desc["sha256"], desc["path"]
    print(json.dumps({"result": "verified", "manifestSha256": sha(OUT / "manifest.json"),
                      "closure": len(e["closure"]), "nextDelta": len(e["delta"])}))


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in {"emit", "verify"}
    {"emit": emit, "verify": verify}[sys.argv[1]]()
