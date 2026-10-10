#!/usr/bin/env python3
"""Reproduce the Romanian author correction dependency closure from pinned evidence.

The reviewed v3 set remains in scope. Additional selectors are locale-owned and
derive from source text, reviewer witnesses, compiled node operands and the
adjudicated correction batch; no diagnostic character-domain dump is an input.
"""

import hashlib
import importlib.util
import json
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCALE = ROOT / "Translations/ro"
REVIEW = LOCALE / "independent-review-01"
OUT = LOCALE / "remedial-cycle-002-closure-v2"
PLAN = LOCALE / "remedial-cycle-002-plan.json"
PREVIOUS = LOCALE / "correction-cycle-001-closure-v3"
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402

GUIDS = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
         "UI": "0cbd8a7a4f543344bb95659de87f67a5",
         "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def ids(path):
    return set(path.read_text().splitlines())


def authored():
    values, locations, files = {}, {}, {}
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
    return values, locations, files


def evidence():
    plan = read(PLAN)
    progress = read(LOCALE / "semantic-review-progress.json")
    assert progress["acceptedUnits"] == progress["reviewedUnits"] == 16538
    assert plan["acceptedChanges"] == 278 and plan["rejectedProposals"] == 1
    pins = {"plan": sha(PLAN), "firstPassProgress": sha(LOCALE / "semantic-review-progress.json"),
            "reviewResult": sha(REVIEW / "review-result.json"),
            "reviewLedger": sha(REVIEW / "per-id-decisions-final.jsonl"),
            "reviewFindings": sha(REVIEW / "consolidated-findings.json"),
            "reviewWitnesses": sha(REVIEW / "catalog-completeness-witnesses.json"),
            "compiledContext": sha(REVIEW / "compiled-context.json"),
            "itemActionFamily": sha(REVIEW / "item-action-family.json"),
            "itemTransferContract": sha(REVIEW / "item-transfer-contract-verification.json"),
            "occupiedRoomInputs": sha(REVIEW / "occupied-room-inputs.json"),
            "managedConsumers": sha(REVIEW / "managed-consumers.json"),
            "compiledDecoder": sha(REVIEW / "compiled_context.py"),
            "compiledRuntimeBindings": sha(ROOT / "Source/glossary-corpus-v2/runtime-bindings.json"),
            "compiledScopePin": sha(ROOT / "Source/glossary-corpus-v2/current-dialogs-scope.json"),
            "previousManifest": sha(PREVIOUS / "manifest.json"),
            "sourceInventory": sha(ROOT / "Source/localization-inventory-v3/strings.jsonl"),
            "staticInventory": sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl"),
            "preserveExactManifest": sha(ROOT / "Source/preserve-exactly-v4.json"),
            "approvedGlossary": sha(ROOT / "Documentation/glossary-translations/ro/layer.json")}
    assert pins["plan"] and pins["sourceInventory"] == plan["sourceInventorySha256"]
    assert pins["staticInventory"] == plan["staticInventorySha256"]
    assert pins["preserveExactManifest"] == plan["preserveExactManifestSha256"]
    assert pins["approvedGlossary"] == plan["approvedGlossarySha256"]
    assert pins["previousManifest"] == plan["previousClosureManifestSha256"]
    assert pins["reviewResult"] == plan["reviewResultSha256"]
    assert pins["reviewLedger"] == plan["perIdLedgerSha256"]
    assert pins["reviewFindings"] == plan["consolidatedFindingsSha256"]
    for desc in progress["reviewSegments"]:
        assert sha(ROOT / desc["path"]) == desc["sha256"]
    rows = [json.loads(line) for desc in progress["reviewSegments"]
            for line in (ROOT / desc["path"]).read_text().splitlines()]
    assert [r["ordinal"] for r in rows] == list(range(16538))
    byid = {r["stableId"]: r for r in rows}
    assert len(byid) == 16538
    values, locations, files = authored()
    assert set(values) == set(byid)
    before = {sid: r["target"] for sid, r in byid.items()}
    for c in read(LOCALE / "correction-cycle-001-plan.json")["corrections"]:
        assert before[c["stableId"]] == c["before"]
        before[c["stableId"]] = c["after"]
    changed = set()
    for d in plan["decisions"]:
        sid = d["stableId"]
        assert byid[sid]["source"] == d["source"] and before[sid] == d["before"]
        assert locations[sid] == (d["authoredPath"], d["entryIndex"])
        if d["decision"].startswith("accepted"):
            assert values[sid] == d["after"] != d["before"]
            changed.add(sid)
        else:
            assert values[sid] == d["before"] == d["after"]
    assert len(changed) == 278
    for sid in set(byid) - changed:
        assert values[sid] == before[sid], sid
    rules = read(ROOT / "Source/preserve-exactly-v4.json")
    rules = {r["stableId"]: r for r in rules["tableRows"] + rules["staticRows"]}
    assert len(rules) == 16538
    for sid in byid:
        check_value(rules[sid], values[sid])
    # Pin the generated repeat map and batch relation to the author plan.
    phrase = next(x for x in read(LOCALE / "dialogue-repeats-001.authored.json")["phrases"]
                  if x["source"] == "Выдать явку в КЧС")
    assert phrase["expectedRows"] == 245
    assert phrase["target"] == "Înmânează ordinul de prezentare la Comitet"
    return plan, rows, byid, before, values, locations, files, pins, changed


def build():
    plan, rows, byid, before, values, locations, files, pins, changed = evidence()
    order = [r["stableId"] for r in rows]
    previous = ids(PREVIOUS / "closure-ids.txt")
    assert len(previous) == 3090
    components = {"previous-independently-reviewed": previous,
                  "corrected-units": changed}
    # Exact source repeats, including 245 document-transfer options, are
    # selected without speaker restrictions. Retain before/after target repeats.
    sources = {byid[s]["source"] for s in changed}
    targets = {v for s in changed for v in (before[s], values[s])}
    components["source-and-target-repetitions"] = {
        r["stableId"] for r in rows if r["source"] in sources or
        before[r["stableId"]] in targets or values[r["stableId"]] in targets}
    witness = read(REVIEW / "catalog-completeness-witnesses.json")["surfaces"]
    # These fixed source surfaces repair the previous speaker-restricted
    # violence selector and noun-only dog selector. Body checks are selected
    # through affected compiled branches below; the global 4,839-row body
    # diagnostic is not itself a review dependency.
    for label in ("dog-branch-context", "violent-actions-unrestricted",
                  "kinship-and-referents", "hidden-role-ui",
                  "placeholder-callback-context"):
        surface = witness[label]
        selected = {r["stableId"] for r in surface["outsideClosure"]}
        assert len(selected) == surface["outsideClosureCount"]
        components["witness-" + label] = selected
    # Connect every corrected line to actual compiled node operands. The
    # item-action supplement contains the 245 callback nodes omitted by v3.
    compiled = read(REVIEW / "compiled-context.json")
    item = read(REVIEW / "item-action-family.json")
    assert compiled["programSha256"] == item["programSha256"]
    decoder_path = REVIEW / "compiled_context.py"
    spec = importlib.util.spec_from_file_location("ro_compiled_decoder", decoder_path)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    nodes, program_sha = decoder.load()
    assert program_sha == compiled["programSha256"]
    for name, value in compiled["nodes"].items():
        assert nodes[name] == value["instructions"]
    for name, instructions in item["consumerNodes"].items():
        assert nodes[name] == instructions
    key_to_ids = defaultdict(set)
    for r in rows:
        if r.get("key"):
            key_to_ids[r["key"]].add(r["stableId"])
    node_keys, node_for_changed = {}, defaultdict(set)
    for name, instructions in nodes.items():
        found = {op for ins in instructions for op in ins["operands"]
                 if isinstance(op, str) and op in key_to_ids}
        node_keys[name] = found
        for d in plan["decisions"]:
            if d["stableId"] in changed and d["key"] in found:
                node_for_changed[d["stableId"]].add(name)
    selected_nodes = set().union(*node_for_changed.values()) if node_for_changed else set()
    selected_nodes.update(item["consumerNodes"])
    compiled_ids = {sid for name in selected_nodes for key in node_keys[name]
                    for sid in key_to_ids[key]}
    components["compiled-scene-and-transfer-callbacks"] = compiled_ids
    # Two corrected dialogue lines are absent even from the pinned complete
    # compiled program. Use their complete key stem families and record the
    # source/program discrepancy instead of inventing edges.
    unmapped = [d for d in plan["decisions"] if d["stableId"] in changed and
                d["key"].startswith("line:") and d["stableId"] not in node_for_changed]
    stems = {d["key"].rsplit("_", 1)[0] for d in unmapped}
    components["unmapped-line-stem-context"] = {
        r["stableId"] for r in rows if r.get("key") and
        r["key"].rsplit("_", 1)[0] in stems}
    assert len(unmapped) == 2, [(d["ordinal"], d["key"]) for d in unmapped]
    # Preserve every v3 mandatory catalog class and add named remediations.
    previous_manifest = read(PREVIOUS / "manifest.json")
    catalog = {"v3-" + name: ids(ROOT / desc["path"])
               for name, desc in previous_manifest["mandatoryRegressionCatalog"].items()}
    catalog.update({"document-transfer-guard-and-callback": {
                        r["stableId"] for r in read(REVIEW / "item-transfer-contract-verification.json")["rows"]},
                    "dog-pronoun-branch": components["witness-dog-branch-context"],
                    "violent-action-unrestricted": components["witness-violent-actions-unrestricted"],
                    "kinship-and-referral": components["witness-kinship-and-referents"],
                    "hidden-character-label": components["witness-hidden-role-ui"],
                    "placeholder-callback": components["witness-placeholder-callback-context"]})
    assert len(catalog["document-transfer-guard-and-callback"]) == 245
    components["mandatory-regressions"] = set().union(*catalog.values())
    closure = set().union(*components.values())
    assert previous | changed <= closure <= set(order)
    retired = previous - closure
    assert not retired
    invalidated_prior = changed & previous
    delta = changed | (closure - previous) | invalidated_prior
    assert delta <= closure
    dynamic = read(REVIEW / "occupied-room-inputs.json")
    assert dynamic["sourceDomainCount"] == 13
    occupied = next(r for r in rows if r["ordinal"] == 2586)
    template = values[occupied["stableId"]]
    domain = []
    for itemrow in dynamic["samePlaceSourceDomain"]:
        sid = itemrow["stableId"]
        target = values[sid] if sid else None
        domain.append({"objectId": itemrow["objectId"], "sourceName": itemrow["name"],
                       "stableId": sid, "target": target,
                       "assembled": template.replace("{0}", target) if target else None})
    assert domain == plan["dynamicSamePlaceSourceCases"]
    return locals()


def emit():
    assert not OUT.exists(), "Closure is immutable; verify the existing evidence"
    e = build()
    OUT.mkdir()
    order = e["order"]
    descriptors = {}
    def list_file(name, members):
        path = OUT / name
        path.write_text("".join(sid + "\n" for sid in order if sid in members))
        descriptor = {"path": str(path.relative_to(ROOT)), "rows": len(members), "sha256": sha(path)}
        descriptors[name] = descriptor
        return descriptor
    for name, members in e["components"].items():
        list_file("component-" + name + ".ids.txt", members)
    for name, members in e["catalog"].items():
        list_file("regression-" + name + ".ids.txt", members)
    changed = list_file("changed-ids.txt", e["changed"])
    closure = list_file("closure-ids.txt", e["closure"])
    delta = list_file("next-review-delta-ids.txt", e["delta"])
    invalidated = list_file("invalidated-prior-ids.txt", e["invalidated_prior"])
    retired = list_file("retired-prior-ids.txt", e["retired"])
    review = OUT / "review-rows.jsonl"
    with review.open("w") as stream:
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
    review_desc = {"path": str(review.relative_to(ROOT)), "rows": len(e["closure"]), "sha256": sha(review)}
    write(OUT / "consumer-topology.json", {
        "programSha256": e["compiled"]["programSha256"],
        "selectedNodeCount": len(e["selected_nodes"]),
        "nodes": {name: {"instructions": e["nodes"][name],
                         "resolvedKeys": sorted(e["node_keys"][name]),
                         "resolvedStableIds": [sid for sid in order if any(sid in e["key_to_ids"][key] for key in e["node_keys"][name])]}
                  for name in sorted(e["selected_nodes"])},
        "correctedDialogueLinesWithoutSuppliedCompiledNode": [
            {"ordinal": d["ordinal"], "stableId": d["stableId"], "key": d["key"]} for d in e["unmapped"]],
        "fallback": "Complete source key-stem families for two corrected source lines absent from the pinned compiled program; no invented runtime edge."})
    write(OUT / "dynamic-consumer-context.json", {
        "callback": e["dynamic"]["callback"], "sourceDomainCount": 13,
        "samePlaceSourceDomain": e["domain"], "limit": e["dynamic"]["limit"],
        "occupiedLineStableId": e["occupied"]["stableId"],
        "occupiedLineTarget": e["template"]})
    write(OUT / "retirement-and-invalidation.json", {
        "previousClosureCount": len(e["previous"]), "retiredCount": 0,
        "retirementReason": "No previous independently reviewed ID was removed; the v3 set is retained as a conservative baseline.",
        "explicitlyInvalidatedPriorIds": [sid for sid in order if sid in e["invalidated_prior"]],
        "invalidationReason": "These previously reviewed targets changed in the author remedial batch.",
        "nextDeltaFormula": "corrected IDs union (current closure minus previous independent closure) union explicitly invalidated prior IDs"})
    other = {name: {"path": str((OUT / name).relative_to(ROOT)), "sha256": sha(OUT / name)}
             for name in ("consumer-topology.json", "dynamic-consumer-context.json",
                          "retirement-and-invalidation.json")}
    manifest = {"schemaVersion": 1, "locale": "ro", "cycle": 2,
                "status": "author remedial handoff; independent review pending",
                "supersedesClosure": "remedial-cycle-002-closure: bounded reviewer excerpt omitted five actual compiled nodes; v2 decodes the complete pinned program",
                "acceptedUnits": 16538, "firstPassReviewedUnits": 16538,
                "previousIndependentReviewedUnits": 3090,
                "reviewedByAuthorNow": "278 corrected values and bounded dependency closure preflight; author reading is not independent acceptance",
                "pins": e["pins"], "recipeSha256": sha(pathlib.Path(__file__)),
                "previousComponents": e["previous_manifest"]["components"],
                "currentComponents": {name: descriptors["component-" + name + ".ids.txt"] for name in e["components"]},
                "previousRegressionCatalog": e["previous_manifest"]["mandatoryRegressionCatalog"],
                "currentRegressionCatalog": {name: descriptors["regression-" + name + ".ids.txt"] for name in e["catalog"]},
                "changedIds": changed, "closureIds": closure, "nextReviewDeltaIds": delta,
                "invalidatedPriorIds": invalidated, "retiredPriorIds": retired,
                "reviewRows": review_desc, "otherEvidence": other,
                "afterAuthoredFiles": [{"path": path, "sha256": digest} for path, digest in sorted(e["files"].items())],
                "repeatMapSha256": sha(LOCALE / "dialogue-repeats-001.authored.json"),
                "generatedRepeatBatchSha256": sha(LOCALE / "dialogue-batch-001.json"),
                "nonTargetPreimageLimit": e["plan"]["preimageBoundary"],
                "catalogApplicability": "v3 mandatory catalog retained; new document-transfer, dog branch, unrestricted violence, kinship/referral, hidden label and callback witnesses selected. Global body-check diagnostic is bounded by affected compiled branches, not treated as a full semantic restart. Complete pinned compiled program is decoded for actual consumer nodes.",
                "runtime": "not run", "independentReview": "pending"}
    write(OUT / "manifest.json", manifest)
    print(json.dumps({"manifestSha256": sha(OUT / "manifest.json"),
                      "closure": len(e["closure"]), "delta": len(e["delta"]),
                      "changed": len(e["changed"]), "nodes": len(e["selected_nodes"]),
                      "retired": len(e["retired"])}))


def verify():
    manifest = read(OUT / "manifest.json")
    assert manifest["recipeSha256"] == sha(pathlib.Path(__file__))
    e = build()
    assert manifest["pins"] == e["pins"]
    for name, members in e["components"].items():
        assert ids(OUT / ("component-" + name + ".ids.txt")) == members
    for name, members in e["catalog"].items():
        assert ids(OUT / ("regression-" + name + ".ids.txt")) == members
    for name, members in (("changed", e["changed"]), ("closure", e["closure"]),
                          ("nextReviewDelta", e["delta"]),
                          ("invalidatedPrior", e["invalidated_prior"]),
                          ("retiredPrior", e["retired"])):
        key = name + "Ids"
        descriptor = manifest[key]
        assert sha(ROOT / descriptor["path"]) == descriptor["sha256"]
        assert ids(ROOT / descriptor["path"]) == members
    for descriptor in ([manifest["reviewRows"]] + list(manifest["otherEvidence"].values()) +
                       list(manifest["currentComponents"].values()) +
                       list(manifest["currentRegressionCatalog"].values()) +
                       manifest["afterAuthoredFiles"]):
        assert sha(ROOT / descriptor["path"]) == descriptor["sha256"], descriptor["path"]
    assert manifest["repeatMapSha256"] == sha(LOCALE / "dialogue-repeats-001.authored.json")
    assert manifest["generatedRepeatBatchSha256"] == sha(LOCALE / "dialogue-batch-001.json")
    print(json.dumps({"result": "verified", "manifestSha256": sha(OUT / "manifest.json"),
                      "closure": len(e["closure"]), "delta": len(e["delta"])}))


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in {"emit", "verify"}
    {"emit": emit, "verify": verify}[sys.argv[1]]()
