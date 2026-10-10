#!/usr/bin/env python3
"""Reproduce Romanian correction cycle 001 from pinned first-pass evidence.

Modes: plan builds and preflights an immutable adjudication; apply checks it again
and changes only authored values. Derived closure evidence is built separately.
"""

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts"))
from preserve_exact import check_value  # noqa: E402

LOCALE = ROOT / "Translations/ro"
PROGRESS = LOCALE / "semantic-review-progress.json"
PLAN = LOCALE / "correction-cycle-001-plan.json"
MANIFEST = ROOT / "Source/preserve-exactly-v4.json"
CLOSURE = LOCALE / "correction-cycle-001-closure-v2"

# These are author-adjudicated replacements, changing the first-pass proposal
# only where the full scene showed a semantic or Romanian-idiom problem.
OVERRIDES = {
    2585: "BigLebowski: Dacă te-ai hotărât să mă primești, un locșor pentru mine să golești.",
    10383: "Anxiety: TOȚI SUNT UN TOT ÎN FAȚA MORȚII.",
    14705: "Buddy: Iar apoi… Ha, mi i-au scos din gură cu lovituri în aceeași noapte. Doar pentru că am zâmbit. Amuzant, nu?",
    15699: "Widow: (Mortul a apărut în cadru, iar asta vă pune pe gânduri)",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def collect():
    p = load(PROGRESS)
    assert p["acceptedUnits"] == p["reviewedUnits"] == 16538
    assert p["nextId"] is None and p["nextOrdinal"] == 16538
    for item in p["reviewedFiles"] + p["reviewSegments"] + p["findingsBatches"]:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    assert sha(ROOT / "Source/localization-inventory-v3/strings.jsonl") == p["sourceInventorySha256"]
    assert sha(ROOT / "Source/localization-inventory-v3/static-text.jsonl") == p["staticInventorySha256"]
    assert sha(ROOT / "Documentation/glossary-translations/ro/layer.json") == p["approvedGlossarySha256"]
    assert sha(MANIFEST) == p["sourceManifestSha256"]
    rows = {}
    for seg in p["reviewSegments"]:
        for line in (ROOT / seg["path"]).read_text().splitlines():
            row = json.loads(line)
            assert row["ordinal"] not in rows
            rows[row["ordinal"]] = row
    assert set(rows) == set(range(16538))
    findings = []
    for batch in p["findingsBatches"]:
        part = load(ROOT / batch["path"])
        assert len(part["findings"]) == batch["findingCount"]
        findings += part["findings"]
    assert len(findings) == p["totalProposedFindings"] == 71
    assert len({f["stableId"] for f in findings}) == 71
    manifest = load(MANIFEST)
    rules = {r["stableId"]: r for r in manifest["tableRows"] + manifest["staticRows"]}
    assert len(rules) == 16538
    return p, rows, findings, rules


def authored():
    files, values, locations = {}, {}, {}
    guids = {"Dialogs": "444ff14f1967f5a4c8eb9e4cf4c913f1",
             "UI": "0cbd8a7a4f543344bb95659de87f67a5",
             "ChecksDialogs": "389c6d80595013c41b85a7197838c4b6"}
    for path in sorted(LOCALE.glob("*-batch-???.json")) + [LOCALE / "static-text-draft.json"]:
        data = load(path)
        files[str(path.relative_to(ROOT))] = data
        for i, entry in enumerate(data["entries"]):
            sid = (entry["stableId"] if "stableId" in entry else
                   f"string:{guids[data['collection']]}:{entry['id']}")
            assert sid not in values
            values[sid] = entry["target"]
            locations[sid] = (str(path.relative_to(ROOT)), i)
    assert len(values) == 16538
    return files, values, locations


def prepare():
    p, rows, findings, rules = collect()
    files, values, locations = authored()
    assert set(values) == set(rules)
    items = []
    for finding in findings:
        ordinal, sid = finding["ordinal"], finding["stableId"]
        row = rows[ordinal]
        before = finding["currentTarget"]
        after = OVERRIDES.get(ordinal, finding["proposedTarget"])
        assert row["stableId"] == sid and row["source"] == finding["source"]
        assert row["target"] == before and values[sid] == before
        assert row["batchPath"] == locations[sid][0]
        assert after != before and after.strip()
        check_value(rules[sid], after)
        items.append({"ordinal": ordinal, "stableId": sid, "key": finding["key"],
                      "source": finding["source"], "before": before, "after": after,
                      "reason": finding["reason"],
                      "adjudication": "accepted with revised wording" if ordinal in OVERRIDES else "accepted",
                      "authoredPath": locations[sid][0], "entryIndex": locations[sid][1]})
        values[sid] = after
    assert len(items) == 71
    for sid, rule in rules.items():
        check_value(rule, values[sid])
    return p, items, files, locations


def plan():
    assert not PLAN.exists(), "The adjudicated plan is immutable"
    p, items, files, _ = prepare()
    result = {
        "schemaVersion": 1, "locale": "ro", "cycle": 1,
        "status": "one complete first-pass correction batch preflighted; not yet applied",
        "firstPassProgressSha256": sha(PROGRESS),
        "sourceInventorySha256": p["sourceInventorySha256"],
        "staticInventorySha256": p["staticInventorySha256"],
        "sourceManifestSha256": p["sourceManifestSha256"],
        "approvedGlossarySha256": p["approvedGlossarySha256"],
        "acceptedUnits": 16538, "firstPassFindings": 71,
        "acceptedCorrections": 71, "rejectedFindings": 0,
        "preflight": "all 16538 projected values pass Source/preserve-exactly-v4.json with Scripts/preserve_exact.py check_value; all source IDs, authored paths, entry indices and original values aligned",
        "staticRoleDecision": {
            "stableId": "tmp:level0:2016:m_text",
            "role": "unbound supplemental developer-menu control",
            "assetEvidence": "Documentation/static-text-scope-v2.json: InGameDevMenu > Panel (initialActive=false) > PlayerTab > SuperSpeed > Label; localizedStringBindings=[]",
            "releaseReachability": "unverified; static asset ancestry alone does not establish a player-visible release surface"
        },
        "beforeAuthoredFiles": [{"path": path, "sha256": sha(ROOT / path)} for path in files],
        "corrections": items,
    }
    PLAN.write_text(canonical_json(result))
    print(json.dumps({"plan": str(PLAN.relative_to(ROOT)), "sha256": sha(PLAN),
                      "corrections": len(items), "projectedExactRows": 16538}))


def apply():
    saved = load(PLAN)
    assert saved["status"] == "one complete first-pass correction batch preflighted; not yet applied"
    assert saved["firstPassProgressSha256"] == sha(PROGRESS)
    p, items, files, _ = prepare()
    assert items == saved["corrections"]
    assert saved["sourceInventorySha256"] == p["sourceInventorySha256"]
    assert all(sha(ROOT / a["path"]) == a["sha256"] for a in saved["beforeAuthoredFiles"])
    touched = set()
    for item in items:
        file = files[item["authoredPath"]]
        entry = file["entries"][item["entryIndex"]]
        assert entry["target"] == item["before"]
        entry["target"] = item["after"]
        touched.add(item["authoredPath"])
    # Each replacement is atomic. The set of files is not a filesystem transaction;
    # an interruption is detected by comparing every pinned before/after value.
    for rel in sorted(touched):
        path = ROOT / rel
        temporary = path.with_suffix(path.suffix + ".cycle-001-tmp")
        temporary.write_text(canonical_json(files[rel]))
        temporary.replace(path)
    print(json.dumps({"applied": len(items), "files": len(touched), "planSha256": sha(PLAN)}))


def closure():
    """Construct exact canonical-order invalidation sets after the correction batch."""
    assert not CLOSURE.exists(), "Closure cycle 001 is immutable"
    saved = load(PLAN)
    progress = load(PROGRESS)
    assert saved["firstPassProgressSha256"] == sha(PROGRESS)
    assert progress["acceptedUnits"] == progress["reviewedUnits"] == 16538
    for descriptor in progress["reviewSegments"] + progress["findingsBatches"]:
        assert sha(ROOT / descriptor["path"]) == descriptor["sha256"]
    assert sha(MANIFEST) == saved["sourceManifestSha256"]
    assert sha(ROOT / "Documentation/glossary-translations/ro/layer.json") == saved["approvedGlossarySha256"]
    rows = []
    for descriptor in progress["reviewSegments"]:
        rows += [json.loads(line) for line in (ROOT / descriptor["path"]).read_text().splitlines()]
    assert [r["ordinal"] for r in rows] == list(range(16538))
    order = [r["stableId"] for r in rows]
    assert len(set(order)) == 16538
    byid = {r["stableId"]: r for r in rows}
    corrections = saved["corrections"]
    changed = {c["stableId"] for c in corrections}
    assert len(changed) == saved["acceptedCorrections"] == 71
    files, values, locations = authored()
    assert set(values) == set(order)
    for c in corrections:
        assert values[c["stableId"]] == c["after"]
        assert byid[c["stableId"]]["target"] == c["before"]
        assert locations[c["stableId"]] == (c["authoredPath"], c["entryIndex"])
    for sid in set(order) - changed:
        assert values[sid] == byid[sid]["target"], sid
    # Reconstruct each pre-correction authored file to prove no unrelated field
    # or entry changed. This also detects an interrupted multi-file application.
    before = {f["path"]: f["sha256"] for f in saved["beforeAuthoredFiles"]}
    touched = {c["authoredPath"] for c in corrections}
    byte_reconstruction_mismatches = []
    for rel, data in files.items():
        if rel in touched:
            reverse = json.loads(canonical_json(data))
            for c in corrections:
                if c["authoredPath"] == rel:
                    entry = reverse["entries"][c["entryIndex"]]
                    assert entry["target"] == c["after"]
                    entry["target"] = c["before"]
            if hashlib.sha256(canonical_json(reverse).encode()).hexdigest() != before[rel]:
                # Some first-pass batches used a different JSON byte layout.
                # Exact field values are checked against all immutable review
                # rows above; retain the original hash as historical evidence.
                byte_reconstruction_mismatches.append(rel)
        else:
            assert sha(ROOT / rel) == before[rel], rel

    components = {name: set() for name in
                  ("changed", "scene-branch-context", "exact-repetitions",
                   "glossary-referent-occurrences", "runtime-bindings",
                   "mandatory-regressions")}
    components["changed"] = changed
    changed_rows = [byid[sid] for sid in changed]
    stems = {(c["key"] or "").rsplit("_", 1)[0] for c in corrections if c["key"] and "_" in c["key"]}
    source_repeats = {c["source"] for c in corrections}
    before_after_repeats = {v for c in corrections for v in (c["before"], c["after"])}
    for r in rows:
        sid, key = r["stableId"], r.get("key") or ""
        if key and key.rsplit("_", 1)[0] in stems:
            components["scene-branch-context"].add(sid)
        if r["source"] in source_repeats or r["target"] in before_after_repeats or values[sid] in before_after_repeats:
            components["exact-repetitions"].add(sid)
    # The following selectors enumerate the actual concepts touched by the 71
    # edits, including Russian inflections and related Romanian referent forms.
    # Character-scoped patterns prevent a generic pronoun from pulling in all
    # unrelated dialogue. Review the specification before later regeneration.
    concept_spec = {
        "cucumber-calendar": {"source": r"огурц", "key": r"^calendar_day_"},
        "mushroom-potato": {"source": r"гриб|картош", "key": r"mushroom|potato|festival"},
        "dog-referent": {"source": r"собак|дворняг|пёс|щен", "target": r"câin|cățea"},
        "unidentified-blind-creature": {"source": r"\bОНО\b|\bНЕГО\b|\bОН\b|\bЭТО\b|твар|существ", "key": r"Blind_"},
        "teeth": {"source": r"зуб|зубн", "target": r"dinț|dinţi|dinții"},
        "hands": {"source": r"рук|ладон|ногт", "target": r"mâin|unghi"},
        "ears": {"source": r"\b(?:ухо|уши|ушей|ушам|ушах|ушами)\b", "target": r"urech"},
        "armpits": {"source": r"подмыш", "target": r"axil"},
        "photograph": {"source": r"фото|сним|кадр", "target": r"fotograf|cadru"},
        "drug-stash": {"source": r"закладк|наркот", "target": r"drog|ascunzătoare"},
        "violent-death-verbs": {"source": r"переб[ьи]|зарез|подых|выби[лть]|уби[лть]", "key": r"Wolfhound_|Esenin_|Couple_|Buddy_|Scammer_"},
        "cult-unity": {"source": r"един|одно целое", "key": r"Anxiety_|Cultist"},
        "affected-coarse-register": {"source": r"ёб|хуй|нихуя|нихера|пизд|бля", "key": r"Esenin_|Scammer_|Jacket_"},
        "super-speed": {"source": r"[Ss]uper speed|скорост", "target": r"[Ss]upervitez|vitez"},
    }
    concept_members = {}
    for name, spec in concept_spec.items():
        selectors = [(field, re.compile(expr, re.I)) for field, expr in spec.items() if field != "key"]
        key_selector = re.compile(spec["key"], re.I) if "key" in spec else None
        selected = set()
        for r in rows:
            term_match = any(regex.search((r.get(field) or "") if field != "target" else values[r["stableId"]])
                             for field, regex in selectors)
            key_match = bool(key_selector and key_selector.search(r.get("key") or ""))
            # Calendar and mushroom context includes all named UI/scene-family
            # bindings; character-scoped pronoun, violence, and register concepts
            # require both the source pattern and the affected speaker family.
            match = ((term_match or key_match) if name in {"cucumber-calendar", "mushroom-potato"}
                     else term_match and (key_selector is None or key_match))
            if match:
                selected.add(r["stableId"])
        assert selected, name
        concept_members[name] = selected
        components["glossary-referent-occurrences"].update(selected)

    static_scope = load(ROOT / "Documentation/static-text-scope-v2.json")
    static_dev_ids = {r["stableId"] for r in static_scope["rows"]
                      if r["stableId"] in byid and
                      any(a["name"] == "InGameDevMenu" for a in r["sceneAncestry"])}
    branch_dynamic = {r["stableId"] for r in rows
                      if (r.get("key") or "").startswith("line:BigLebowski_Entrance_Occupied_")}
    assert any("{0}" in byid[sid]["source"] for sid in branch_dynamic)
    components["runtime-bindings"].update(static_dev_ids | branch_dynamic)
    # Fixed project-specific regression catalog, independent of finding count.
    catalog = {
        "character-agreement-and-referents": concept_members["dog-referent"] |
            concept_members["unidentified-blind-creature"] | concept_members["teeth"] |
            concept_members["hands"] | concept_members["ears"] | concept_members["armpits"],
        "interface-menu-hud-save-locale": {r["stableId"] for r in rows if r.get("collection") == "UI"} |
            {r["stableId"] for r in rows if r["stableId"].startswith("tmp:")},
        "placeholders-and-markup": {r["stableId"] for r in rows
                                     if "{" in r["source"] or "<" in r["source"]},
        "branching-and-speaker-prefix": components["scene-branch-context"] | changed,
        "credits": {"tmp:level5:59:m_text"},
        "developer-menu-static": static_dev_ids,
    }
    for ids in catalog.values():
        assert ids <= set(order)
        components["mandatory-regressions"].update(ids)
    closure_ids = set().union(*components.values())
    assert changed <= closure_ids <= set(order)

    CLOSURE.mkdir()
    artifacts = []
    def write_ids(filename, ids):
        path = CLOSURE / filename
        path.write_text("".join(sid + "\n" for sid in order if sid in ids))
        descriptor = {"path": str(path.relative_to(ROOT)), "rows": len(ids),
                      "sha256": sha(path), "newline": "UTF-8 LF, including final LF"}
        artifacts.append(descriptor)
        return descriptor
    changed_descriptor = write_ids("changed-ids.txt", changed)
    closure_descriptor = write_ids("closure-ids.txt", closure_ids)
    component_descriptors = {name: write_ids(name + ".ids.txt", ids)
                             for name, ids in components.items()}
    concept_descriptors = {name: write_ids("concept-" + name + ".ids.txt", ids)
                           for name, ids in concept_members.items()}
    regression_descriptors = {name: write_ids("regression-" + name + ".ids.txt", ids)
                              for name, ids in catalog.items()}

    review = CLOSURE / "review-rows.jsonl"
    with review.open("w") as stream:
        for r in rows:
            sid = r["stableId"]
            if sid not in closure_ids:
                continue
            stream.write(json.dumps({"ordinal": r["ordinal"], "stableId": sid,
                                     "collection": r.get("collection"), "key": r.get("key"),
                                     "source": r["source"], "before": r["target"],
                                     "after": values[sid], "authoredPath": locations[sid][0],
                                     "components": [name for name, ids in components.items() if sid in ids]},
                                    ensure_ascii=False, separators=(",", ":")) + "\n")
    review_descriptor = {"path": str(review.relative_to(ROOT)), "rows": len(closure_ids),
                         "sha256": sha(review), "newline": "UTF-8 JSONL LF, including final LF"}
    artifacts.append(review_descriptor)

    # Bounded assembled text context for the one affected dialogue family with
    # a neighboring dynamic occupancy slot. The real executable order is not
    # proven by flattened table order; this is a format substitution witness.
    dynamic_rows = [r for r in rows if r["stableId"] in branch_dynamic]
    dynamic_context = {
        "sourceRole": "BigLebowski occupied-room branch; one neighboring line uses {0} occupant name",
        "consumerTopology": "same Yarn key family line:BigLebowski_Entrance_Occupied_*; flattened table order is not execution order",
        "placeholder": "{0}",
        "sampleInputs": ["Vecinul", "Fiica vecinului"],
        "rows": [{"stableId": r["stableId"], "key": r["key"], "source": r["source"],
                  "target": values[r["stableId"]],
                  "assembledSamples": [values[r["stableId"]].replace("{0}", name)
                                       for name in ("Vecinul", "Fiica vecinului")]}
                 for r in dynamic_rows],
        "limit": "Actual Yarn branch graph and live item/occupant substitutions remain runtime-unverified."
    }
    runtime_path = CLOSURE / "dynamic-consumer-context.json"
    runtime_path.write_text(canonical_json(dynamic_context))
    runtime_descriptor = {"path": str(runtime_path.relative_to(ROOT)), "rows": len(dynamic_rows),
                          "sha256": sha(runtime_path)}
    artifacts.append(runtime_descriptor)

    after_files = [{"path": rel, "sha256": sha(ROOT / rel)} for rel in sorted(files)]
    validations = [{"path": str((ROOT / rel).with_suffix(".validation.json").relative_to(ROOT)),
                    "sha256": sha((ROOT / rel).with_suffix(".validation.json"))}
                   for rel in sorted(touched)]
    manifest = {
        "schemaVersion": 1, "locale": "ro", "cycle": 1,
        "status": "author correction closure ready for independent review; not independently reviewed",
        "acceptedUnits": 16538, "firstPassReviewedUnits": 16538,
        "firstPassProgressSha256": sha(PROGRESS), "correctionPlanPath": str(PLAN.relative_to(ROOT)),
        "correctionPlanSha256": sha(PLAN),
        "recipeSha256": sha(pathlib.Path(__file__)),
        "supersedesClosureDraft": "Translations/ro/correction-cycle-001-closure/manifest.json; draft selector treated character keys as alternatives, overbroadly pulling unrelated dialogue. Draft remains immutable and is not the reviewer set.",
        "sourceInventorySha256": saved["sourceInventorySha256"],
        "staticInventorySha256": saved["staticInventorySha256"],
        "sourceManifestSha256": saved["sourceManifestSha256"],
        "approvedGlossarySha256": saved["approvedGlossarySha256"],
        "beforeAuthoredFiles": saved["beforeAuthoredFiles"],
        "afterAuthoredFiles": after_files,
        "beforeByteReconstruction": {"matchingFiles": len(touched) - len(byte_reconstruction_mismatches),
                                     "formattingUnreconstructableFiles": byte_reconstruction_mismatches,
                                     "semanticFieldParity": "all 16538 original target values and stable IDs checked against immutable first-pass rows; batch metadata retained by apply recipe"},
        "affectedValidationSidecars": validations,
        "changedIds": changed_descriptor, "closureIds": closure_descriptor,
        "components": component_descriptors, "concepts": concept_descriptors,
        "mandatoryRegressionCatalog": regression_descriptors,
        "reviewRows": review_descriptor, "dynamicConsumerContext": runtime_descriptor,
        "sourceRoleDecision": saved["staticRoleDecision"],
        "imageTextPlans": "not applicable: owner excluded translated textures and images",
        "independentReview": "pending; reviewer must be identifiable and verify closure, scene/branch semantics and regression catalog",
        "runtime": "not run",
        "evidenceRecipe": "Run .venv/bin/python Translations/ro/correction-cycle-001-recipe.py verify-closure; this recomputes sets from immutable first-pass rows, pinned plan, authored targets and selector specification. Validate modified authored files with Scripts/validate_game_text_batch.py or Scripts/validate_static_text_draft.py, then run .venv/bin/python Scripts/report_locale_readiness.py --exact --compact without --update-state.",
    }
    result = CLOSURE / "manifest.json"
    result.write_text(canonical_json(manifest))
    print(json.dumps({"closure": str(result.relative_to(ROOT)), "sha256": sha(result),
                      "changedIds": len(changed), "closureIds": len(closure_ids),
                      "components": {k: len(v) for k, v in components.items()},
                      "artifacts": len(artifacts)}))


def verify_closure():
    """Verify pinned immutable components and exact corrected target values."""
    manifest = load(CLOSURE / "manifest.json")
    assert manifest["correctionPlanSha256"] == sha(PLAN)
    assert manifest["recipeSha256"] == sha(pathlib.Path(__file__))
    assert manifest["firstPassProgressSha256"] == sha(PROGRESS)
    assert manifest["sourceManifestSha256"] == sha(MANIFEST)
    for descriptor in ([manifest["changedIds"], manifest["closureIds"], manifest["reviewRows"],
                        manifest["dynamicConsumerContext"]] +
                       list(manifest["components"].values()) +
                       list(manifest["concepts"].values()) +
                       list(manifest["mandatoryRegressionCatalog"].values()) +
                       manifest["afterAuthoredFiles"] + manifest["affectedValidationSidecars"]):
        assert sha(ROOT / descriptor["path"]) == descriptor["sha256"], descriptor["path"]
    _, values, _ = authored()
    for correction in load(PLAN)["corrections"]:
        assert values[correction["stableId"]] == correction["after"]
    print(json.dumps({"result": "verified", "manifestSha256": sha(CLOSURE / "manifest.json"),
                      "changedIds": manifest["changedIds"]["rows"],
                      "closureIds": manifest["closureIds"]["rows"]}))


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in {"plan", "apply", "closure", "verify-closure"}
    {"plan": plan, "apply": apply, "closure": closure,
     "verify-closure": verify_closure}[sys.argv[1]]()
