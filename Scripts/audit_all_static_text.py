#!/usr/bin/env python3
"""Extract every serialized TMP text object from the pinned Unity data files."""

import argparse
import json
from collections import Counter
from pathlib import Path

import UnityPy

from probe_assets import DEFAULT_GAME, EXPECTED_UNITY, ROOT, digest, require
from unity_types import CheckedTypeTreeGenerator, generated_tree


FILES = (["globalgamemanagers.assets", "resources.assets"] +
         [f"sharedassets{index}.assets" for index in range(7)] +
         [f"level{index}" for index in range(7)])
SCRIPTS = {(1, 2981): "TextMeshProUGUI", (1, 2283): "RTLTextMeshPro"}
DEFAULT_OUTPUT = ROOT / "outputs/text-path-audit-v2/report.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "outputs"), "Output must be in outputs")
    require(not output.exists() and not output.parent.exists(),
            "Preserve the prior static text audit")
    state = json.loads((ROOT / "Documentation/localization-state.json").read_text())
    require(state["gameVersion"] == "1.3.19", "Supported game version changed")
    generator = CheckedTypeTreeGenerator(EXPECTED_UNITY)
    generator.load_local_dll_folder(str(DEFAULT_GAME /
        "NoImNotAHuman_BackUpThisFolder_ButDontShipItWithYourGame/Managed"))

    rows = []
    source_files = {}
    counts = Counter()
    for name in FILES:
        path = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        require(path.is_file(), "Missing source data file: " + name)
        relative = str(path.relative_to(DEFAULT_GAME))
        source_files[relative] = digest(path)
        if relative in state["sourceInputs"]:
            require(source_files[relative] == state["sourceInputs"][relative],
                    "Previously pinned source file changed: " + relative)
        env = UnityPy.load(str(path))
        env.typetree_generator = generator
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            head = obj.parse_monobehaviour_head()
            script = (head.m_Script.m_FileID, head.m_Script.m_PathID)
            if script not in SCRIPTS:
                continue
            tree, _ = generated_tree(obj)
            require(isinstance(tree.get("m_text"), str) and
                    "m_fontAsset" in tree and "m_fontSize" in tree,
                    "Known TMP script lacks text fields: " + name + ":" + str(obj.path_id))
            require(tree["m_GameObject"]["m_FileID"] == 0,
                    "TMP GameObject is external")
            rows.append({"file": name, "id": obj.path_id,
                         "class": SCRIPTS[script],
                         "scriptReference": {"fileId": script[0], "pathId": script[1]},
                         "gameObject": tree["m_GameObject"],
                         "fields": {"m_text": tree["m_text"],
                                    "originalText": tree.get("originalText"),
                                    "m_fontAsset": tree["m_fontAsset"],
                                    "m_isRichText": tree.get("m_isRichText")}})
            counts[(name, SCRIPTS[script])] += 1
    require(len(rows) == 244, "TMP object count changed")
    require(len({(row["file"], row["id"]) for row in rows}) == len(rows),
            "Duplicate TMP object identity")
    output.parent.mkdir(parents=True)
    result = {"schemaVersion": 2, "gameVersion": state["gameVersion"],
              "sourceFiles": source_files,
              "scriptReferences": {"TextMeshProUGUI": [1, 2981],
                                   "RTLTextMeshPro": [1, 2283]},
              "count": len(rows),
              "countsByFileAndClass": [
                  {"file": name, "class": class_name, "count": count}
                  for (name, class_name), count in sorted(counts.items())],
              "rows": rows}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)),
                      "objects": len(rows), "sourceFiles": len(source_files)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
