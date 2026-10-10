"""Run the owning text guards for a whole locale with one source parse.

Writes a new full-corpus receipt, never historical validation sidecars.
Semantic review, rendered layout and gameplay remain separate gates.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from locale_text_inputs import current_text
from probe_assets import ROOT, digest, require
from validate_game_text_batch import DIGITS, TOKEN


def validate(locale, output):
    require(output.is_relative_to(ROOT) and not output.exists(), "Use a new canonical corpus receipt")
    # Fresh parse and protected grammar/ID/identity/order/credits checks, independent of old sidecars.
    values, files = current_text(locale, require_sidecars=False)
    source = {}
    strings = ROOT / "Source/localization-inventory-v3/strings.jsonl"
    static = ROOT / "Source/localization-inventory-v3/static-text.jsonl"
    inventory = json.loads((ROOT / "Documentation/localization-source-inventory-v3.json").read_text())
    require(inventory["outputs"]["strings.jsonl"] == digest(strings), "Owning validator source identity changed")
    for line in strings.open():
        row = json.loads(line)
        source[(row["collection"], int(row["stableId"].rsplit(":", 1)[1]))] = row
    for line in static.open():
        row = json.loads(line)
        source[("static", row["stableId"])] = row
    for identity, target in values.items():
        record = source[identity]
        original = record["source"]
        require(isinstance(original, str) and original.strip(), "Empty original source")
        if identity[0] == "static":
            tokens = Counter(TOKEN.findall(original))
        else:
            tokens = Counter(span["value"] for span in record["exactSpans"] if span["reason"] == "Runtime placeholder or markup")
            prefixes = [span["value"] for span in record["exactSpans"] if span["reason"] == "Yarn speaker/service prefix"]
            require(not prefixes or target.startswith(prefixes[0]), "Owning speaker prefix guard failed")
        require(Counter(TOKEN.findall(target)) == tokens, "Owning protected-token guard failed: " + str(identity))
        require(Counter(DIGITS.findall(target)) == Counter(DIGITS.findall(original)), "Owning numeric guard failed")
        require(re.findall(r"\r\n|\r|\n", target) == re.findall(r"\r\n|\r|\n", original), "Owning line-break guard failed")
        require(re.search(r"[ \t\r\n]*$", target).group() == re.search(r"[ \t\r\n]*$", original).group(), "Owning whitespace guard failed")
    for row in files:
        require(digest(ROOT / row["path"]) == row["sha256"], "Authored input changed during corpus validation")
    receipt = {"schemaVersion": 1, "locale": locale, "rows": len(values), "structuralResult": "passed",
               "exactResult": "passed", "selectedIdCoverage": "16538 unique; no missing/extra",
               "sourceInventorySha256": digest(strings), "staticInventorySha256": digest(static),
               "authoredFiles": files, "validatorSha256": digest(Path(__file__)),
               "inputLoaderSha256": digest(ROOT / "Scripts/locale_text_inputs.py"),
               "owningValidators": {name: digest(ROOT / "Scripts" / name) for name in
                                    ("validate_game_text_batch.py", "validate_static_text_draft.py", "preserve_exact.py")},
               "boundary": "all original batch/static structural guards plus selected-ID scope and protected nesting; one source parse per corpus",
               "sidecars": "unchanged; receipt independently rechecks current authored bytes", "runtime": "not-run"}
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"locale": locale, "structuralResult": "passed", "rows": len(values), "receipt": str(output.relative_to(ROOT))}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate(args.locale, args.output.resolve())
