#!/usr/bin/env python3
"""Make contact sheets for visual text classification of original game textures."""

import argparse
import json
from pathlib import Path

import UnityPy
from PIL import Image, ImageDraw, ImageOps

from probe_assets import DEFAULT_GAME, ROOT, digest, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "Source") and not output.exists(), "Use a new Source output directory")
    inventories = ROOT / "Source/glossary-textures"
    source_review = json.loads((ROOT / "Documentation/glossary-research/texture-review.json").read_text())
    output.mkdir(parents=True)
    rows = []
    for inventory in sorted(inventories.glob("*-inventory.json")):
        name = inventory.name.removesuffix("-inventory.json")
        expected = source_review["inventories"][inventory.name]
        require(digest(inventory) == expected["sha256"], "Texture inventory changed: " + name)
        declared = json.loads(inventory.read_text())
        require(len(declared) == expected["textureCount"], "Texture count changed: " + name)
        if not declared:
            continue
        asset = DEFAULT_GAME / "NoImNotAHuman_Data" / name
        env = UnityPy.load(str(asset))
        for item in declared:
            row = {"asset": name, "pathId": item["id"], "name": item["name"]}
            try:
                obj = env.file.objects[item["id"]]
                require(obj.type.name == "Texture2D", "Inventory object is not Texture2D")
                image = obj.read().image.convert("RGBA")
                row["size"] = list(image.size)
                thumb = ImageOps.contain(image, (172, 145), Image.Resampling.LANCZOS)
                row["thumb"] = thumb
                row["status"] = "decoded"
            except Exception as error:
                row["status"] = "decode-failed"
                row["error"] = str(error)[:300]
            rows.append(row)
        print(f"SCANNED {name}: {len(declared)} textures", flush=True)

    for start in range(0, len(rows), 96):
        sheet = Image.new("RGB", (12 * 190, 8 * 180), "#e8e8e8")
        pen = ImageDraw.Draw(sheet)
        for index, row in enumerate(rows[start:start + 96]):
            x, y = (index % 12) * 190, (index // 12) * 180
            if row["status"] == "decoded":
                thumb = row.pop("thumb")
                sheet.paste(thumb, (x + (190 - thumb.width) // 2, y), thumb)
            else:
                pen.rectangle((x + 5, y + 5, x + 180, y + 145), fill="#ffcccc")
            pen.text((x + 4, y + 147), f"{start + index} {row['asset'][:5]}:{row['pathId']}", fill="#111111")
            pen.text((x + 4, y + 161), row["name"][:27], fill="#111111")
        sheet.save(output / f"sheet-{start // 96 + 1:02d}.png")
    # Decode all thumbnails before writing the report; no PIL objects belong in JSON.
    for row in rows:
        row.pop("thumb", None)
    report = {
        "gameVersion": "1.3.19",
        "scope": "Original Texture2D contact sheets for visual text classification; no game launch",
        "sourceAssets": {name: digest(DEFAULT_GAME / "NoImNotAHuman_Data" / name) for name in sorted({r["asset"] for r in rows})},
        "rows": rows,
        "decoded": sum(r["status"] == "decoded" for r in rows),
        "failed": sum(r["status"] != "decoded" for r in rows),
        "sheets": sorted(p.name for p in output.glob("sheet-*.png")),
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"decoded": report["decoded"], "failed": report["failed"], "sheets": len(report["sheets"])}))


if __name__ == "__main__":
    main()
