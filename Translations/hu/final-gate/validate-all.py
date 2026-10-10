#!/usr/bin/env python3
"""Run the owning structural validators over every current Hungarian batch."""

import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HU = ROOT / "Translations/hu"
OUT = Path(__file__).resolve().parent
PATTERN = re.compile(r"(?:dialogue|ui|checks)-batch-\d{3}\.json$")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(path):
    sidecar = path.with_suffix(".validation.json")
    before = digest(sidecar)
    previous = json.loads(sidecar.read_text())
    assert previous["structuralResult"] == "passed"
    assert previous["batchSha256"] == digest(path)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    command = [sys.executable, str(ROOT / "Scripts/validate_game_text_batch.py"), str(path)]
    result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                            capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"{path.name}: {result.stderr or result.stdout}")
    current = json.loads(sidecar.read_text())
    assert current["structuralResult"] == "passed" and current["batchSha256"] == digest(path)
    assert digest(sidecar) == before, "Validator changed a current sidecar: " + path.name
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path),
            "rows": current["authoredRows"], "sidecarSha256": before,
            "validatorResult": "passed; byte-identical current sidecar"}


def main():
    output = OUT / "structural-validators.json"
    assert not output.exists(), "Immutable structural report already exists"
    paths = sorted(p for p in HU.glob("*-batch-*.json") if PATTERN.fullmatch(p.name))
    assert len(paths) == 473
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        rows = list(executor.map(run, paths))
    static = HU / "static-text-draft.json"
    static_sidecar = static.with_suffix(".validation.json")
    before = digest(static_sidecar)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    command = [sys.executable, str(ROOT / "Scripts/validate_static_text_draft.py"), str(static)]
    result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                            capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    static_report = json.loads(static_sidecar.read_text())
    assert static_report["rows"] == static_report["candidateRows"] == 178
    assert static_report["draftSha256"] == digest(static) and digest(static_sidecar) == before
    assert sum(row["rows"] for row in rows) == 16360
    report = {"schemaVersion": 1, "locale": "hu", "result": "passed",
              "tableBatchCount": len(rows), "tableRows": 16360,
              "staticRows": 178, "totalRows": 16538,
              "validatorScriptSha256": digest(ROOT / "Scripts/validate_game_text_batch.py"),
              "staticValidatorScriptSha256": digest(ROOT / "Scripts/validate_static_text_draft.py"),
              "tableBatches": rows,
              "staticDraft": {"path": str(static.relative_to(ROOT)), "sha256": digest(static),
                              "rows": 178, "sidecarSha256": before,
                              "validatorResult": "passed; byte-identical current sidecar"}}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"result": report["result"], "tableBatchCount": len(rows),
                      "tableRows": 16360, "staticRows": 178,
                      "reportSha256": digest(output)}))


if __name__ == "__main__":
    main()
