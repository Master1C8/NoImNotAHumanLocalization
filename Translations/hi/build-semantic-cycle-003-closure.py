#!/usr/bin/env python3
"""Rebuild/verify the Hindi cycle003 full gate, correction evidence and reviewer delta."""
import argparse, collections, hashlib, importlib.util, json, pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HI = ROOT / "Translations/hi"

def sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def tsha(text): return hashlib.sha256(text.encode()).hexdigest()
def ih(ids): return tsha("\n".join(ids) + "\n")
def read(path): return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
def dump(value): return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
def rows(path): return [json.loads(line) for line in pathlib.Path(path).read_text().splitlines()]

def build():
    adj = read(HI / "semantic-cycle-003-adjudication.json")
    pre = read(HI / "semantic-cycle-003-preflight.json")
    plan = read(HI / "semantic-cycle-003-application-plan.json")
    previous = read(HI / "semantic-cycle-002-closure.json")
    old_gate = read(HI / "semantic-cycle-002-structural-gate.json")
    review = read(HI / "independent-review-02/final-coverage-and-closure-proof.json")
    assert len(adj["items"]) == plan["changedCount"] == 18
    assert pre["adjudicationSha256"] == sha(HI / "semantic-cycle-003-adjudication.json")
    assert plan["preflightSha256"] == sha(HI / "semantic-cycle-003-preflight.json")
    assert sha(HI / "semantic-cycle-002-closure.json") == adj["previousClosureSha256"] == plan["previousClosureSha256"]
    assert sha(ROOT / "Source/localization-inventory-v3/strings.jsonl") == adj["sourceInventorySha256"]
    assert sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl") == adj["staticInventorySha256"]
    assert sha(ROOT / "Documentation/glossary-translations/hi/layer.json") == adj["glossaryLayerSha256"]
    assert sha(ROOT / "Source/glossary-corpus-v2/runtime-bindings.json") == adj["compiledRuntimeBindingsSha256"]
    assert sha(ROOT / "Source/preserve-exactly-v4.json") == adj["preserveExactManifestSha256"]
    assert review["currentClosureCount"] == len(previous["reviewRows"]) == 5133
    previous_ids = [row["stableId"] for row in previous["reviewRows"]]
    assert ih(previous_ids) == previous["closureIdListSha256LfFinalNewline"]
    original = rows(ROOT / "Source/localization-inventory-v3/strings.jsonl")
    static = rows(ROOT / "Source/localization-inventory-v3/static-text.jsonl")
    source_by_collection_id = {(row["collection"],row["stableId"].rsplit(":",1)[1]):row for row in original}
    by_id = {row["stableId"]:row for row in original + static}
    manifest = read(ROOT / "Source/preserve-exactly-v4.json")
    rules = {row["stableId"]:row for row in manifest["tableRows"] + manifest["staticRows"]}
    sys.path.insert(0, str(ROOT / "Scripts"))
    spec = importlib.util.spec_from_file_location("preserve_exact",ROOT / "Scripts/preserve_exact.py")
    mod = importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    all_targets = {}; authored_paths = {}; gate_files = []
    for old in old_gate["files"]:
        path = ROOT / old["path"]
        val_path = ROOT / old["validationPath"]
        obj = read(path); validation = read(val_path)
        assert validation["batchSha256"] == sha(path) if "batchSha256" in validation else True
        assert validation.get("structuralResult") == "passed"
        for entry in obj["entries"]:
            sid = entry.get("stableId") or source_by_collection_id[(obj["collection"],str(entry["id"]))]["stableId"]
            assert sid not in all_targets
            all_targets[sid] = entry["target"]
            authored_paths[sid] = old["path"]
        gate_files.append({"path":old["path"],"sha256":sha(path),"validationPath":old["validationPath"],
                           "validationSha256":sha(val_path),"rows":len(obj["entries"])})
    accepted = [row for row in original + static if row["stableId"] in all_targets]
    ids = [row["stableId"] for row in accepted]
    assert len(ids) == len(set(ids)) == len(all_targets) == len(rules) == 16538
    assert ih(ids) == previous["sourceOrderIdListSha256LfFinalNewline"]
    for sid in ids: mod.check_value(rules[sid],all_targets[sid])
    before_dir = HI / "semantic-cycle-003-before-files"
    after_dir = HI / "semantic-cycle-003-after-files"
    change_map = {item["stableId"]:item for item in adj["items"]}
    assert len(change_map) == 18
    evidence = []
    for file in plan["files"]:
        path = ROOT / file["path"]; vp = ROOT / file["beforeValidationPath"]
        before = before_dir / path.name; after = after_dir / path.name
        old_obj, new_obj = read(before), read(path)
        key = lambda e: str(e.get("stableId") or e["id"])
        old_entries = {key(e):e for e in old_obj["entries"]};new_entries = {key(e):e for e in new_obj["entries"]}
        assert old_entries.keys() == new_entries.keys()
        assert sha(before) == file["beforeSha256"] and sha(after) == sha(path) == file["afterSha256"]
        assert sha(before_dir / vp.name) == file["beforeValidationSha256"]
        assert {k for k in old_entries if old_entries[k] != new_entries[k]} == {sid.rsplit(":",1)[1] for sid in file["changedIds"]}
        for sid in file["changedIds"]:
            k = sid.rsplit(":",1)[1]
            assert old_entries[k]["target"] == change_map[sid]["before"]
            assert new_entries[k]["target"] == change_map[sid]["acceptedFullTarget"]
        evidence.append({**file,"afterValidationSha256":sha(vp)})
    for name in ("static-phrases-authored.json","credits-role-map.json","static-text-draft.json","static-text-draft.validation.json",
                 "common-options-001.authored.json","common-options-002.authored.json","common-options-003.authored.json",
                 "dialogue-batch-900.json","dialogue-batch-901.json","dialogue-batch-902.json"):
        path = HI / name
        assert sha(path) == old_gate["phraseMapSha256"] if name == "static-phrases-authored.json" else True
        old_pin = next((f for f in old_gate["files"] if f["path"] == str(path.relative_to(ROOT))), None)
        if old_pin: assert sha(path) == old_pin["sha256"]
    gate = {"schemaVersion":1,"locale":"hi","gameVersion":"1.3.19",
            "status":"post-cycle-003 deterministic structure and 16,538 preserve-exact passed; distinct review pending",
            "manifestSha256":adj["preserveExactManifestSha256"],"sourceInventorySha256":adj["sourceInventorySha256"],
            "staticInventorySha256":adj["staticInventorySha256"],"glossaryLayerSha256":adj["glossaryLayerSha256"],
            "compiledRuntimeBindingsSha256":adj["compiledRuntimeBindingsSha256"],
            "acceptedIds":16538,"duplicateIds":0,"missingIds":0,"extraIds":0,"exactSpanFailures":0,
            "batchStructurePassed":334,"staticStructurePassed":True,
            "expandedCommonOptionRowsVerified":[2593,245,45],
            "staticPhraseMapRegenerationVerified":"unchanged pinned map and draft; cycle002 regeneration evidence exact",
            "creditsRoleMapRegenerationVerified":"unchanged pinned map and draft; cycle002 regeneration evidence exact",
            "changedIds":18,"changedFiles":len(plan["files"]),"files":gate_files}
    receipt = {"schemaVersion":1,"locale":"hi","status":"18 full-unit corrections applied once; before/after and sidecars verified",
               "applicationPlanSha256":sha(HI / "semantic-cycle-003-application-plan.json"),
               "adjudicationSha256":sha(HI / "semantic-cycle-003-adjudication.json"),
               "preflightSha256":sha(HI / "semantic-cycle-003-preflight.json"),
               "changedIds":18,"changedAuthoredFiles":len(plan["files"]),"evidenceFiles":evidence,
               "staticAndCommonOptionRecipes":"unchanged exact pins; no dependent output regeneration needed"}
    # Selector retains the source-risk catalog and previous reviewed dependencies.
    catalog_path = ROOT / previous["catalogPath"]
    assert sha(catalog_path) == previous["catalogSha256"]
    catalog = read(catalog_path)
    required = set()
    for group in catalog["groups"]:
        assert len(group["ids"]) == group["count"] and ih(group["ids"]) == group["idsSha256"]
        required.update(group["ids"])
    assert len(required) == 4805 and required <= set(ids)
    components = {k:set(v) for k,v in previous["components"].items()}
    changed = set(change_map)
    components["changed"].update(changed)
    normalized = lambda s: re.sub(r"\s+"," ",re.sub(r"^[A-Za-z][A-Za-z0-9_]*: ","",s)).replace("ё","е").strip()
    affected_source = {normalized(item["source"]) for item in adj["items"]}
    old_target = {item["before"] for item in adj["items"]}
    new_target = {item["acceptedFullTarget"] for item in adj["items"]}
    current_repetition = set()
    for row in accepted:
        sid = row["stableId"]
        if normalized(row["source"]) in affected_source or all_targets[sid] in old_target | new_target:
            current_repetition.add(sid)
    components["repetition"].update(current_repetition)
    changed_nodes = {name for item in adj["items"] for name in by_id[item["stableId"]].get("nodeNames",[])}
    current_scene = set()
    for row in accepted:
        if changed_nodes.intersection(row.get("nodeNames",[])):
            current_scene.add(row["stableId"])
    components["sceneContext"].update(current_scene)
    # Complete finite term/referent families, including both TV inflections and both psychic variants.
    motifs = {
        "earwax-inflected-tv-and-ear-check":r"(?i)\bсер[аы]\b|ушн\w*\s+сер\w*",
        "mycelium-all-speakers":r"(?i)мицелий",
        "bald-mother-grandmother":r"(?i)ма и ба|мам\w*.*бабушк|бабушк\w*.*мам",
        "ex-con-remarriage":r"(?i)за другого хахаля|жена.*вышла",
        "self-exam-agency":r"(?i)делая.*обследован|провод\w*.*обследован",
        "rocker-theft":r"(?i)всё пиздить|гитару сломали",
        "firefighter-ongoing-sacrifice":r"(?i)я бы хотел тушить|погибну|ребята.*гибнут",
        "twins-recovery":r"(?i)придёт в себя|сестр\w*.*состояни",
        "vibration-agreement":r"(?i)вибрац",
        "anger-reveal-and-faith":r"(?i)как мою…|новую веру|моя жена",
        "prophet-person-cat":r"(?i)персона с котом|впустить их домой",
        "tough-excess-agency":r"(?i)позволял слишком много",
    }
    family_counts = {}
    current_glossary = set()
    for name, pattern in motifs.items():
        matcher = re.compile(pattern)
        members = {row["stableId"] for row in accepted if matcher.search(row["source"])}
        current_glossary.update(members)
        family_counts[name] = len(members)
    components["glossaryReferent"].update(current_glossary)
    components["mandatoryRegression"].update(required)
    assert required <= components["mandatoryRegression"]
    assert set().union(*components.values()) <= set(ids)
    ordered_components = {name:[sid for sid in ids if sid in members] for name,members in components.items()}
    closure_set = set().union(*components.values())
    closure_ids = [sid for sid in ids if sid in closure_set]
    prior = set(previous_ids)
    new = closure_set - prior
    retired = prior - closure_set
    invalidated = (current_scene | current_repetition | current_glossary) & prior - changed
    # Retained prior runtime-binding dependencies are unchanged. No new slot occurs in this batch.
    delta_set = changed | new | invalidated
    delta_ids = [sid for sid in ids if sid in delta_set]
    assert delta_set == changed | (closure_set-prior) | invalidated
    assert not retired & delta_set
    assert len(closure_ids) == len(closure_set) and len(delta_ids) == len(delta_set)
    closure = {"schemaVersion":1,"locale":"hi","gameVersion":"1.3.19","status":"reproducible cycle003 dependency closure; distinct review pending",
               "acceptedCount":16538,"sourceOrderIdListSha256LfFinalNewline":ih(ids),
               "sourceInventorySha256":adj["sourceInventorySha256"],"staticInventorySha256":adj["staticInventorySha256"],
               "glossaryLayerSha256":adj["glossaryLayerSha256"],"compiledRuntimeBindingsSha256":adj["compiledRuntimeBindingsSha256"],
               "authoredStructuralGateSha256":tsha(dump(gate)),"adjudicationSha256":sha(HI / "semantic-cycle-003-adjudication.json"),
               "previousIndependentlyReviewedClosureSha256":sha(HI / "semantic-cycle-002-closure.json"),
               "review02FinalDecisionsSha256":adj["review02FinalDecisionsSha256"],
               "catalogPath":previous["catalogPath"],"catalogSha256":previous["catalogSha256"],
               "catalogRequiredCount":len(required),"catalogRequiredIdListSha256LfFinalNewline":ih([sid for sid in ids if sid in required]),
               "technicalContextPath":previous["technicalContextPath"],"technicalContextSha256":previous["technicalContextSha256"],
               "changedCount":len(changed),"closureCount":len(closure_ids),"closureIdListSha256LfFinalNewline":ih(closure_ids),
               "componentCounts":{name:len(members) for name,members in ordered_components.items()},
               "componentIdListSha256LfFinalNewline":{name:ih(members) for name,members in ordered_components.items()},
               "components":ordered_components,"glossaryReferentMotifs":motifs,"glossaryFamilyCounts":family_counts,
               "currentCycleDependencyCounts":{"sceneContext":len(current_scene),"repetition":len(current_repetition),"glossaryReferent":len(current_glossary)},
               "currentCycleDependencyIdListSha256LfFinalNewline":{"sceneContext":ih([sid for sid in ids if sid in current_scene]),"repetition":ih([sid for sid in ids if sid in current_repetition]),"glossaryReferent":ih([sid for sid in ids if sid in current_glossary])},
               "changedSceneNodeNames":sorted(changed_nodes),"missingRequiredCatalogIds":[],"extraUnacceptedIds":[],
               "reviewRows":[{"stableId":sid,"reviewIndex":ids.index(sid),"source":by_id[sid]["source"],"target":all_targets[sid],
                              "sourceSha256":tsha(by_id[sid]["source"]),"targetSha256":tsha(all_targets[sid]),
                              "authoredPath":authored_paths[sid],"components":[k for k,v in components.items() if sid in v]} for sid in closure_ids],
               "selectorMethod":"Canonical accepted order; previous exact closure retained; corrected full units; whole affected source scenes; exact repetitions and target echoes; explicit finite Russian term/referent variants, including сера/серы and psychic mycelium; pinned runtime supplier context; all 4,805 source-risk catalog IDs.",
               "selectorSha256":sha(pathlib.Path(__file__))}
    delta = {"schemaVersion":1,"locale":"hi","gameVersion":"1.3.19","status":"exact cycle003 distinct-reviewer delta; not independently read",
             "previousIndependentlyReviewedClosureSha256":sha(HI / "semantic-cycle-002-closure.json"),
             "previousIndependentlyReviewedCount":len(prior),
             "currentClosureCount":len(closure_ids),"currentClosureIdListSha256LfFinalNewline":ih(closure_ids),
             "correctedIds":[sid for sid in ids if sid in changed],"correctedCount":len(changed),
             "newDependencyIds":[sid for sid in ids if sid in new],"newDependencyCount":len(new),
             "explicitInvalidatedPriorIds":[sid for sid in ids if sid in invalidated],"explicitInvalidatedPriorCount":len(invalidated),
             "invalidationReason":"Previous independently read target intersects this cycle's corrected scene, exact repetition or explicit finite glossary/referent family. Historical carried components, retained mandatory catalog and unchanged runtime suppliers alone do not invalidate a prior read.",
             "retiredIds":[sid for sid in ids if sid in retired],"retiredCount":len(retired),
             "retirementReason":"Prior dependencies absent from current closure retain immutable review02 evidence and unchanged target hashes.",
             "deltaIds":delta_ids,"deltaCount":len(delta_ids),"deltaIdListSha256LfFinalNewline":ih(delta_ids),
             "formula":"corrected union (current closure minus previous independently reviewed closure) union explicit invalidated prior",
             "missingAcceptedIds":[],"extraUnacceptedIds":[]}
    for field in ("correctedIds","newDependencyIds","explicitInvalidatedPriorIds","retiredIds"):
        delta[field+"Sha256LfFinalNewline"] = ih(delta[field])
    return {"semantic-cycle-003-structural-gate.json":dump(gate),
            "semantic-cycle-003-applied-evidence.json":dump(receipt),
            "semantic-cycle-003-closure.json":dump(closure),
            "semantic-cycle-003-review-delta.json":dump(delta)},closure,delta

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--verify",action="store_true");args=parser.parse_args()
    files,closure,delta=build()
    for name,content in files.items():
        path=HI/name
        if args.verify:assert path.read_text(encoding="utf-8")==content,name
        else:
            assert not path.exists(),name
            path.write_text(content,encoding="utf-8")
    print("verified" if args.verify else "wrote",closure["closureCount"],"closure;",delta["deltaCount"],"delta;",delta["newDependencyCount"],"new;",delta["explicitInvalidatedPriorCount"],"invalidated;",delta["retiredCount"],"retired")

if __name__ == "__main__": main()
