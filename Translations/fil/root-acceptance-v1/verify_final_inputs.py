"""Check final Filipino decisions against current authored/source/consumer inputs."""
import argparse
import hashlib
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
LOCALE = ROOT / "Translations/fil"
sys.path.insert(0, str(ROOT / "Scripts"))
from locale_text_inputs import current_text
from verify_author_chain import verify as author_chain
from verify_decision_chain import CLEAN, verify as decision_chain

EXTERNAL_INPUTS = {
    "/Users/antonkrutov/.codex/instructions/game-localization-audit-workflow.md": "d48c07764d092293837d679bf9ccdba082c5d7b665b7db43d0e23e080e3af4b6",
    "/Users/antonkrutov/.codex/instructions/game-localization-prompt.md": "d579cb5e2fbf5acf97e35b39cc1f4de2696b1e28fe5a1a0723d7dfedeab433ea",
    "/Users/antonkrutov/.codex/instructions/sitefor-mods.md": "7d6b91f1fb14cfc07c3daf351e0ee8a31286e9df4b489af538be062551c1a3a1",
    "/Users/antonkrutov/.codex/skills/vn-game-localize/SKILL.md": "a04e9c8ec76677838f33e753067a444d9ccf99c551124a9a9d0e2f14885c2d5b",
    "/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/Assembly-CSharp.dll": "c674f171c61b644e6e746e0ced079ffa365abee2336d04ea9e67cbbc93e88213",
    "/Volumes/KINGSTONMAC/Applications/No Im not a Human.app/Contents/SharedSupport/prefix/drive_c/KS Games/No Im not a Human/NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed/YarnSpinner.dll": "c2b0db889611e842198ab82cad90cf2745cafc10ae0f8de448ab3a5bcedb66f2",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def rows(path):
    values = [json.loads(line) for line in path.read_text().splitlines()]
    result = {r["stableId"]: r for r in values}
    assert len(result) == len(values), path
    return result


def verify(cycle, review):
    c = LOCALE / f"semantic-correction-cycle-{cycle:03}"
    r = LOCALE / f"independent-review-{review:02}"
    manifest = load(r / "completion-manifest.json")
    external = {}
    for record in manifest["files"] + manifest["currentInputPins"]:
        path = (ROOT / record["path"]).resolve()
        if not path.is_relative_to(ROOT):
            assert EXTERNAL_INPUTS.get(str(path)) == record["sha256"], (path, "unapproved external input")
            external[str(path)] = record["sha256"]
        assert sha(path.read_bytes()) == record["sha256"], record["path"]
    verdict = load(r / "final-verdict.json")
    assert verdict["locale"] == "fil" and verdict["objectiveFindings"] == 0
    assert verdict["status"] == "clean" and verdict["cleanIndependentAcceptance"] is True
    values, authored = current_text("fil")
    source = rows(ROOT / "Source/localization-inventory-v3/strings.jsonl")
    source.update(rows(ROOT / "Source/localization-inventory-v3/static-text.jsonl"))
    targets = {}
    for stable_id, item in source.items():
        identity = (item["collection"], int(stable_id.rsplit(":", 1)[1])) if "collection" in item else ("static", stable_id)
        if identity in values:
            targets[stable_id] = values[identity]
    assert len(targets) == len(values) == 16538
    selected = {stable_id: source[stable_id] for stable_id in targets}
    pairs = rows(c / "closure-paired.jsonl")
    delta = rows(c / "next-delta-paired.jsonl")
    decisions = rows(r / "closure-decision-applicability.jsonl")
    fresh = rows(r / "fresh-decisions.jsonl")
    mandatory = rows(c / "mandatory-regression-catalog.jsonl")
    mandatory_decisions = rows(r / "mandatory-regression-applicability.jsonl")
    assert set(decisions) == set(pairs)
    assert set(fresh) == set(delta)
    assert set(mandatory_decisions) == set(mandatory) <= set(pairs)
    decoder_path = LOCALE / "independent-review-04/bytecode_decoder.py"
    spec = importlib.util.spec_from_file_location("fil_root_final_decoder", decoder_path)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    program_hash = sha(decoder.raw)
    assert program_hash == "33de1e80e55e4eb8ec2093078028aa83fc45ac8b77acc05c5a4f9477ebe92827"
    binding_path = ROOT / "Source/glossary-corpus-v2/runtime-bindings.json"
    bindings = load(binding_path)
    runners = [(name, item) for name, item in bindings.items()
               if "lineProvider" in item and "yarnProject" in item]
    assert len(runners) == 1
    runner_name, runner = runners[0]
    assert runner["lineProvider"]["m_FileID"] == 0
    provider_name = runner_name.rsplit(":", 1)[0] + ":" + str(runner["lineProvider"]["m_PathID"])
    provider = bindings[provider_name]
    collection_reference = provider["stringsTable"]["m_TableReference"]["m_TableCollectionName"]
    assert collection_reference.startswith("GUID:")
    dialogue_guid = collection_reference[5:]
    expected_dialogue_guids = {stable_id.split(":")[1] for stable_id, item in selected.items()
                              if item.get("collection") == "Dialogs"}
    assert expected_dialogue_guids == {dialogue_guid}
    keyed = defaultdict(list)
    for stable_id, item in selected.items():
        # RunLine/AddOption uses the runner's serialized line provider. A
        # same-named ChecksDialogs row has a distinct serialized consumer.
        if stable_id.startswith("string:" + dialogue_guid + ":") and item.get("key") is not None:
            keyed[item["key"]].append((stable_id, item))
    sites = defaultdict(list)
    for node_name, node in decoder.actual.items():
        for instruction in node["instructions"]:
            if instruction["op"] not in {"RunLine", "AddOption"}:
                continue
            key = instruction["operands"][0]
            candidates = [(stable_id, item) for stable_id, item in keyed.get(key, [])
                          if node_name in item.get("nodeNames", [])]
            assert key not in keyed or candidates, (node_name, key, "selected source owner missing")
            if not candidates:
                continue
            assert len(candidates) == 1, (node_name, key, "ambiguous selected source owner")
            stable_id, _ = candidates[0]
            sites[stable_id].append({"node": node_name, "instruction": instruction["index"],
                                     "opcode": instruction["op"], "operands": instruction["operands"]})
    comparable = ("stableId", "acceptedOrdinal", "sourceSha256", "targetSha256", "key", "nodeNames", "consumerIdentitySha256")
    for stable_id, pair in pairs.items():
        item = selected[stable_id]
        assert pair["source"] == item["source"] and pair["target"] == targets[stable_id]
        assert sha(pair["source"].encode()) == pair["sourceSha256"]
        assert sha(pair["target"].encode()) == pair["targetSha256"]
        identity = {"compiledProgramSha256": program_hash, "key": item.get("key"),
                    "nodeNames": item.get("nodeNames", []), "sites": sites.get(stable_id, [])}
        assert pair["consumerIdentity"] == identity, stable_id
        assert sha(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":")).encode()) == pair["consumerIdentitySha256"]
        for mapping in (decisions, delta, fresh, mandatory, mandatory_decisions):
            if stable_id not in mapping:
                continue
            record = mapping[stable_id]
            for field in comparable:
                assert record[field] == pair[field], (stable_id, field)
        for mapping in (decisions, fresh, mandatory_decisions):
            if stable_id in mapping:
                assert mapping[stable_id]["decision"] in CLEAN
                assert mapping[stable_id].get("findingId") is None
    assert verdict["currentClosure"] == verdict["closureAccepted"] == len(pairs)
    assert verdict["freshFullPairsRead"] == verdict["freshAccepted"] == len(delta)
    assert verdict["exactPriorDecisionReuse"] == len(pairs) - len(delta)
    regression = verdict["mandatoryRegression"]
    assert regression["total"] == len(mandatory)
    assert regression["fresh"] == len(set(mandatory) & set(delta))
    assert regression["reuse"] == len(mandatory) - regression["fresh"]
    assert regression["objectiveFindings"] == 0 and regression["status"] == "clean"
    first = author_chain(cycle)
    ancestry = decision_chain(review)
    assert not ancestry["unresolvedFindings"] and ancestry["cleanDecisions"] == len(pairs)
    return {"locale": "fil", "result": "passed", "cycle": cycle, "review": review,
            "authoredFiles": authored, "acceptedUnits": len(values), "currentClosure": len(pairs),
            "freshIndependentPairs": len(delta), "priorIndependentPairs": len(pairs) - len(delta),
            "mandatoryRegression": regression, "compiledProgramSha256": program_hash,
            "currentSourceTargetConsumerIdentity": "passed for every current closure and mandatory row",
            "authorChain": first, "decisionAncestry": ancestry,
            "currentManifestSha256": sha((r / "completion-manifest.json").read_bytes()),
            "currentVerdictSha256": sha((r / "final-verdict.json").read_bytes()),
            "verifiedExternalInputPins": [{"path": p, "sha256": h} for p, h in sorted(external.items())],
            "serializedProgramTableBinding": {"path": str(binding_path.relative_to(ROOT)),
                                               "sha256": sha(binding_path.read_bytes()),
                                               "runner": runner_name, "lineProvider": provider_name,
                                               "tableGuid": dialogue_guid,
                                               "rule": "Actual runner lineProvider stringsTable GUID owns RunLine/AddOption rows; duplicate bare keys in other collections retain their separate consumers."},
            "boundary": "Exact current 16538 text/metadata/exact/credits contract, recorded first-pass provenance, independent decision ancestry, actual compiled consumers and mandatory coverage; no new semantic reading or runtime acceptance.",
            "runtime": "not-run", "fontRenderingLayout": "not-run", "installation": "not-run"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--review", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.cycle, args.review), ensure_ascii=False, indent=2))
