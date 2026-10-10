#!/usr/bin/env python3
"""Check the repaired photo selector against actual compiled Yarn photo branches."""

import hashlib
import json
import pathlib
import re
import struct

ROOT = pathlib.Path(__file__).resolve().parents[3]
CYCLE = pathlib.Path(__file__).resolve().parent


def varint(data, position):
    value = shift = 0
    while True:
        byte = data[position]
        position += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, position
        shift += 7


def fields(data):
    position = 0
    while position < len(data):
        tag, position = varint(data, position)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, position = varint(data, position)
        elif wire == 2:
            length, position = varint(data, position)
            value = data[position:position + length]
            position += length
        elif wire == 5:
            value = struct.unpack("<f", data[position:position + 4])[0]
            position += 4
        elif wire == 1:
            value = struct.unpack("<d", data[position:position + 8])[0]
            position += 8
        else:
            raise ValueError((number, wire, position))
        yield number, wire, value


def main():
    asset = ROOT / "Source/glossary-corpus-v1/sharedassets0.assets-2743.json"
    raw = bytes(json.loads(asset.read_text())["compiledYarnProgram"])
    names, edges, line_references = set(), {}, set()
    for number, _, value in fields(raw):
        if number != 2:
            continue
        entry = list(fields(value))
        name = next(item.decode() for key, _, item in entry if key == 1)
        node = next(item for key, _, item in entry if key == 2)
        assert name not in names
        names.add(name)
        edges[name] = set()
        for key, _, instruction in fields(node):
            if key != 2:
                continue
            fields_i = list(fields(instruction))
            opcode = next((item for number, _, item in fields_i if number == 1), None)
            for number, _, operand in fields_i:
                if number != 2:
                    continue
                for key, _, item in fields(operand):
                    if key == 1 and isinstance(item, bytes):
                        value = item.decode()
                        if value.startswith("line:"):
                            line_references.add(value)
                        if opcode == 6:
                            edges[name].add(value)
    source = {}
    for filename in ("strings.jsonl", "static-text.jsonl"):
        for line in (ROOT / "Source/localization-inventory-v3" / filename).open():
            row = json.loads(line)
            source[row["stableId"]] = row
    manifest = json.loads((ROOT / "Source/preserve-exactly-v4.json").read_text())
    accepted = {row["stableId"] for row in manifest["tableRows"] + manifest["staticRows"]}
    closure = set((CYCLE / "closure-ids.txt").read_text().splitlines())
    pattern = re.compile(r"фото|фотк|сним(?:ок|к)", re.IGNORECASE)
    seed_ids = {sid for sid in accepted if pattern.search(source[sid]["source"])}
    seed_nodes = {node for sid in seed_ids for node in source[sid].get("nodeNames", [])}
    unbound = sorted(sid for sid in seed_ids if not source[sid].get("nodeNames"))
    assert len(unbound) == 31
    assert all(source[sid]["key"] not in line_references for sid in unbound)
    assert any(source[sid]["key"] in line_references for sid in seed_ids - set(unbound))
    families = sorted({node.split("_Photo")[0] for node in seed_nodes if "_Photo" in node})
    assert seed_nodes <= names
    rows = []
    for family in families:
        prefix = family + "_Photo"
        compiled_family = {node for node in names if node.startswith(prefix)}
        assert compiled_family
        accepted_family_ids = {sid for sid in accepted if
                               compiled_family.intersection(source[sid].get("nodeNames", []))}
        missing = accepted_family_ids - closure
        assert not missing, (family, sorted(missing))
        family_edges = sorted((node, destination) for node in compiled_family
                              for destination in edges[node] if destination in compiled_family)
        rows.append({"family": family, "compiledNodes": sorted(compiled_family),
                     "acceptedTextUnits": len(accepted_family_ids),
                     "internalBranchEdges": [{"from": node, "to": destination}
                                             for node, destination in family_edges],
                     "missingAcceptedIds": []})
    result = {"schemaVersion": 1, "locale": "fa", "cycle": 2,
              "compiledAssetSha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
              "compiledProgramSha256": hashlib.sha256(raw).hexdigest(),
              "compiledNodeCount": len(names), "sourceMatchedIds": len(seed_ids),
              "sourceSeedNodes": len(seed_nodes), "photoFamilies": len(families),
              "compiledPhotoFamilyNodes": sum(len(row["compiledNodes"]) for row in rows),
              "internalPhotoBranchEdges": sum(len(row["internalBranchEdges"]) for row in rows),
              "missingAcceptedIds": [], "rows": rows}
    path = CYCLE / "photo-topology.json"
    data = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    unbound_result = {
        "schemaVersion": 1, "locale": "fa", "cycle": 2,
        "compiledProgramSha256": hashlib.sha256(raw).hexdigest(),
        "compiledLineKeyCount": len(line_references),
        "acceptedPhotoMatchesWithoutNodeNames": len(unbound),
        "compiledReferencesForTheseKeys": 0,
        "interpretation": "These accepted strings are translated and selected directly. Their line keys have no reference in the pinned compiled Yarn program; other serialized consumers or runtime reachability are not inferred.",
        "rows": [{"stableId": sid, "key": source[sid]["key"],
                  "source": source[sid]["source"], "compiledLineReferences": 0}
                 for sid in unbound],
    }
    unbound_path = CYCLE / "unbound-photo-binding.json"
    unbound_data = (json.dumps(unbound_result, ensure_ascii=False, indent=2) + "\n").encode()
    if unbound_path.exists():
        assert unbound_path.read_bytes() == unbound_data
    else:
        unbound_path.write_bytes(unbound_data)
    print(json.dumps({key: result[key] for key in
                      ("compiledNodeCount", "sourceMatchedIds", "sourceSeedNodes",
                       "photoFamilies", "compiledPhotoFamilyNodes",
                       "internalPhotoBranchEdges", "missingAcceptedIds")}))


if __name__ == "__main__":
    main()
