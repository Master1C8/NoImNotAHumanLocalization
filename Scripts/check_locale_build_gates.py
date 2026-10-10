"""Exercise real incomplete/stale rejection boundaries before package output."""

import argparse
import json
from pathlib import Path

from build_locale_text import build
from locale_text_inputs import accepted_inputs, current_text, read
from probe_assets import ROOT, digest, require


def check(locale, acceptance_path, exact_path, base, output):
    require(output.is_relative_to(ROOT / "outputs") and not output.exists(), "Use a new canonical test output")
    output.mkdir(parents=True)
    results = []
    corpus = output / "incomplete-corpus"
    corpus.mkdir()
    directory = ROOT / "Translations" / locale
    # All unrelated identity/syntax/receipt guards pass. Only accepted coverage fails.
    for name in ("checks-batch-001.json", "checks-batch-001.validation.json",
                 "static-text-draft.json", "static-text-draft.validation.json"):
        (corpus / name).write_bytes((directory / name).read_bytes())
    try:
        current_text(locale, directory=corpus)
    except Exception as error:
        require(str(error) == "Incomplete accepted target coverage", "Incorrect negative-test boundary: " + str(error))
        results.append({"case": "incomplete actual corpus", "result": "rejected", "reason": str(error),
                        "dependencies": "real source/glossary/parser/exact rules; only corpus directory replaced"})
    else:
        raise RuntimeError("Incomplete corpus accepted")
    for mode in ("stale", "incomplete-report"):
        exact, acceptance = read(exact_path), read(acceptance_path)
        if mode == "stale":
            exact["inputFiles"][0]["sha256"] = "0" * 64
        else:
            exact["inputFiles"].pop()
        altered_exact = output / (mode + "-exact.json")
        altered_exact.write_text(json.dumps(exact) + "\n")
        acceptance["inputSha256"].pop(str(exact_path.relative_to(ROOT)))
        acceptance["inputSha256"][str(altered_exact.relative_to(ROOT))] = digest(altered_exact)
        altered_acceptance = output / (mode + "-acceptance.json")
        altered_acceptance.write_text(json.dumps(acceptance) + "\n")
        rejected_output = output / (mode + "-must-not-exist")
        try:
            build(locale, rejected_output, base, altered_acceptance, altered_exact)
        except Exception as error:
            reason = "Duplicate or stale pinned input" if mode == "stale" else "Authored input set changed after exact/semantic gate"
            require(str(error).startswith(reason) and not rejected_output.exists(), "Wrong rejection reason or output created")
            results.append({"case": mode, "result": "rejected before output creation", "reason": str(error),
                            "dependencies": "real acceptance/text loader; exact receipt altered with matching acceptance hash"})
        else:
            raise RuntimeError("Invalid accepted build allowed")
    _, _, files = accepted_inputs(locale, acceptance_path, exact_path)
    results.append({"case": "matching positive control", "result": "passed real acceptance preflight", "authoredFiles": len(files)})
    receipt = {"schemaVersion": 1, "locale": locale, "results": results, "checkerSha256": digest(Path(__file__)),
               "inputModuleSha256": digest(ROOT / "Scripts/locale_text_inputs.py"),
               "builderSha256": digest(ROOT / "Scripts/build_locale_text.py"), "runtime": "not-run"}
    (output / "verification.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale")
    for name in ("acceptance", "exact", "base", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    check(args.locale, args.acceptance.resolve(), args.exact.resolve(), args.base.resolve(), args.output.resolve())
