"""Bind a coordinator-reviewed final text handoff to current offline build inputs.

The handoff is the editorial decision input. This tool checks its recorded
evidence and final deterministic receipts; it does not perform semantic review.
"""

import argparse
import json
from pathlib import Path

from locale_text_inputs import accepted_inputs, checked_files, current_text, project_path, read
from probe_assets import ROOT, digest, require


def accept(handoff_path, output):
    require(handoff_path.is_relative_to(ROOT / "Translations") and output.is_relative_to(ROOT / "Documentation") and
            not output.exists(), "Use a canonical handoff and new acceptance receipt")
    handoff = read(handoff_path)
    locale = handoff["locale"]
    require(handoff["acceptedUnits"] == handoff["firstSemanticPassUnits"] == 16538 and
            handoff["unresolvedObjectiveFindings"] == 0 and handoff["independentClean"] is True and
            handoff["currentHashesUnchanged"] is True and handoff["independentReviewer"].startswith("/root/") and
            handoff["structural"] == {"rows": 16538, "result": "passed"} and
            handoff["derivedStatic"] == {"rows": 178, "result": "passed"}, "Editorial handoff incomplete")
    regression = handoff["mandatoryRegression"]
    require(regression["result"] == "passed" and regression["count"] > 0 and
            regression["count"] == regression["freshReads"] + regression["reusedUnchangedIndependentDecisions"],
            "Mandatory independent catalog incomplete")
    evidence = checked_files(handoff["evidenceFiles"])
    authored = checked_files(handoff["authoredFiles"])
    _, current = current_text(locale)
    require(authored == {row["path"]: row["sha256"] for row in current}, "Current authored set differs from final handoff")
    exact_path = project_path(handoff["preserveExactReport"]["path"])
    require(digest(exact_path) == handoff["preserveExactReport"]["sha256"], "Final exact report changed")
    exact = read(exact_path)
    require(exact["locale"] == locale and exact["exactResult"] == "passed" and exact["checkedRows"] == 16538 and
            checked_files(exact["inputFiles"]) == authored, "Exact report does not cover current authored set")
    inputs = {str(handoff_path.relative_to(ROOT)): digest(handoff_path), **evidence, **authored,
              str(exact_path.relative_to(ROOT)): digest(exact_path)}
    result = {"schemaVersion": 1, "gameVersion": "1.3.19", "sourceLocale": "ru", "locale": locale,
              "status": "text editorially accepted offline", "acceptedUnits": 16538,
              "firstSemanticPassUnits": 16538, "unresolvedObjectiveFindings": 0,
              "independentClean": True, "independentReviewer": handoff["independentReviewer"],
              "mandatoryRegression": regression, "structuralRows": 16538, "derivedStaticRows": 178,
              "inputSha256": inputs, "acceptanceToolSha256": digest(Path(__file__)),
              "runtime": "not-run", "fontRenderingLayout": "not-run", "imagesTextures": "excluded",
              "remainingLimits": handoff.get("remainingLimits", [])}
    # Validate the exact same contract the builder will consume before writing.
    # The temporary receipt is never used as an accepted build input.
    temporary = output.with_suffix(".pending.json")
    require(not temporary.exists(), "Acceptance pending receipt already exists")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    try:
        accepted_inputs(locale, temporary, exact_path)
        require(not output.exists(), "Acceptance appeared during validation")
        temporary.rename(output)
    except Exception:
        # Preserve a failed receipt for diagnosis; it is not editorial acceptance.
        raise
    print(json.dumps({"locale": locale, "acceptedUnits": 16538, "report": str(output.relative_to(ROOT)), "sha256": digest(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    accept(args.handoff.resolve(), args.output.resolve())
