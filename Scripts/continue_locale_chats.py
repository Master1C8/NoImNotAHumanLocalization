#!/usr/bin/env python3
"""Continue existing locale chats after successful finite turns.

This coordinator never creates a chat, edits translation files, or uses Git.
It leaves interrupted/failed turns for human diagnosis instead of retrying them.
"""

import argparse
import fcntl
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from report_locale_readiness import DENOMINATOR, snapshot


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "outputs/locale-chat-runs"
STATE = RUNS / "supervisor-state.json"
SESSIONS = {
    "id": "01a11d89-3ba2-7823-8634-e8992885e032",
    "cs": "01a11d88-d63c-7a93-8ebe-eccabad4cd8e",
    "hu": "01a11d8a-9b09-7e12-8c53-216d514911f0",
    "nl": "01a11d89-3de3-7f32-ab4c-75b28baafb17",
    "fa": "01a11d89-bfe5-7572-a484-aceeff9ddcd4",
    "ro": "01a11d89-d1fb-7371-b3f8-941b4d0320ca",
    "hi": "01a11d89-e0a9-7e90-b274-fbe9429ad047",
    "fil": "01a11d89-f758-7af0-8762-4cef339f8adf",
    "el": "01a11d8a-2158-7703-87e9-b5531db0b715",
    "bg": "01a11d8a-3163-7951-8fe7-fef68a3e9428",
    "sr": "01a11d8a-4424-70e3-add2-1a8a30c8c105",
    "sw": "01a11d8a-53c3-7b83-8a1c-ae3481eabbdb",
    "he": "01a11d8a-6270-7ce3-abb6-1ad6386d6ac7",
}


def parse_running_sessions(output):
    running = {locale: [] for locale in SESSIONS}
    for line in output.splitlines():
        match = re.match(r"\s*(\d+)\s+(?:\S*/)?codex exec resume "
                         r"(?:--json )?([0-9a-f-]{36})(?:\s|$)", line)
        if match:
            for locale, session in SESSIONS.items():
                if match.group(2) == session:
                    running[locale].append(int(match.group(1)))
    return running


def running_sessions():
    output = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
    return parse_running_sessions(output)


def latest_turn_status(session):
    matches = list((Path.home() / ".codex/sessions").rglob("*" + session + ".jsonl"))
    if len(matches) != 1:
        return "session-file-missing-or-ambiguous"
    path = matches[0]
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 2_000_000))
        if stream.tell():
            stream.readline()
        lines = stream.readlines()
    status = "unknown"
    for raw in lines:
        try:
            row = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            continue
        if row.get("type") == "event_msg":
            kind = row.get("payload", {}).get("type")
            if kind in ("task_started", "task_complete", "turn_aborted"):
                status = kind
    return status


def readiness():
    return {row["locale"]: row for row in snapshot(exact=True)["locales"]}


def load_state(rows):
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {locale: {"baseline": row["authoredRows"],
                     "baselineProblems": len(row["problems"]),
                     "baselineValidated": row["structurallyValidatedRows"],
                     "stalledTurns": 0,
                     "status": "observing"} for locale, row in rows.items()}


def save_state(state):
    RUNS.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n")
    temporary.replace(STATE)


def resume(locale, state, row):
    session = SESSIONS[locale]
    prompt = (
        f"Continue the existing {locale} text-only game localization chat from its "
        "latest verified checkpoint. First reconcile its last successful turn, "
        "current files, source and glossary fingerprints. Translate remaining "
        "accepted Russian IDs with context, validate each batch, preserve exact "
        "spans and placeholders, then perform semantic and independent diff review. "
        f"Own only Translations/{locale}/ and its previously assigned locale-specific "
        "progress files. Do not touch shared scripts/state, the Git index, game "
        "fixture, images or textures. Do not launch the game. Operational messages "
        "in English. If this finite turn ends before completion, leave an exact "
        "checkpoint and next action."
    )
    path = RUNS / f"{locale}-{int(time.time())}.jsonl"
    codex = shutil.which("codex")
    if not codex:
        state["status"] = "launcher-missing-needs-review"
        print(f"{locale} {state['status']}", flush=True)
        return
    try:
        with path.open("wb") as output:
            process = subprocess.Popen(
                [codex, "exec", "resume", "--json", session, prompt],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output,
                stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    except OSError as error:
        state["status"] = "launcher-failed-needs-review"
        print(f"{locale} {state['status']}: {error}", flush=True)
        return
    state["baseline"] = row["authoredRows"]
    state["baselineProblems"] = len(row["problems"])
    state["baselineValidated"] = row["structurallyValidatedRows"]
    state["pid"] = process.pid
    state["log"] = str(path.relative_to(ROOT))
    state["status"] = "running"
    print(f"resumed {locale} pid={process.pid} rows={row['authoredRows']}", flush=True)


def inspect(state, rows, running, launch):
    for locale, session in SESSIONS.items():
        row = rows[locale]
        item = state.setdefault(locale, {"baseline": row["authoredRows"],
                                         "baselineProblems": len(row["problems"]),
                                         "baselineValidated": row["structurallyValidatedRows"],
                                         "stalledTurns": 0, "status": "observing"})
        pids = running[locale]
        if len(pids) > 1:
            item["status"] = "duplicate-processes-needs-review"
            print(locale, item["status"], pids, flush=True)
            continue
        if pids:
            item["pid"] = pids[0]
            item["status"] = "running"
            continue
        if row["authoredRows"] == DENOMINATOR and not row["problems"]:
            item["status"] = "draft-complete-editorial-review-needed"
            continue
        if item["status"] in ("stalled-needs-review", "interrupted-needs-review",
                              "duplicate-processes-needs-review", "launcher-missing-needs-review",
                              "launcher-failed-needs-review"):
            continue
        terminal = latest_turn_status(session)
        if terminal != "task_complete":
            item["status"] = "interrupted-needs-review"
            print(locale, item["status"], terminal, flush=True)
            continue
        baseline = item["baseline"]
        if item["status"] == "running":
            progressed = (row["authoredRows"] > baseline or
                          len(row["problems"]) < item.get("baselineProblems", 0) or
                          row["structurallyValidatedRows"] >
                          item.get("baselineValidated", 0))
            if not progressed:
                item["stalledTurns"] += 1
            else:
                item["stalledTurns"] = 0
        if item["stalledTurns"] >= 2:
            item["status"] = "stalled-needs-review"
            print(locale, item["status"], flush=True)
            continue
        item["status"] = "ready-to-resume"
        if launch:
            resume(locale, item, row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supervise", action="store_true",
                        help="Continue successful finite turns until draft coverage is complete")
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()
    if args.interval < 5:
        parser.error("--interval must be at least 5 seconds")
    RUNS.mkdir(parents=True, exist_ok=True)
    lock = (RUNS / "supervisor.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("another locale chat supervisor is already running")
    while True:
        rows = readiness()
        state = load_state(rows)
        inspect(state, rows, running_sessions(), args.supervise)
        save_state(state)
        print(" ".join(f"{locale}:{rows[locale]['authoredRows']}/{DENOMINATOR}:"
                       f"{state[locale]['status']}" for locale in SESSIONS), flush=True)
        if not args.supervise or all(item["status"] in (
                "draft-complete-editorial-review-needed", "stalled-needs-review",
                "interrupted-needs-review", "duplicate-processes-needs-review",
                "launcher-missing-needs-review", "launcher-failed-needs-review")
                for item in state.values()):
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
