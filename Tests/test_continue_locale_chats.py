"""Keep locale chat continuation bound to the exact saved process and turn."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
import continue_locale_chats as chats  # noqa: E402


class ContinueLocaleChatsTest(unittest.TestCase):
    def test_detects_absolute_and_bare_codex_launchers(self):
        bg = chats.SESSIONS["bg"]
        he = chats.SESSIONS["he"]
        processes = (
            "48055 /Applications/ChatGPT.app/Contents/MacOS/codex exec "
            f"resume --json {bg} Continue\n"
            f"47403 codex exec resume --json {he} Continue\n"
            "48056 unrelated command\n"
        )
        found = chats.parse_running_sessions(processes)
        self.assertEqual(found["bg"], [48055])
        self.assertEqual(found["he"], [47403])
        self.assertTrue(all(not pids for locale, pids in found.items()
                            if locale not in ("bg", "he")))

    def test_live_chat_is_never_resumed_again(self):
        locale = "bg"
        state = {locale: {"baseline": 100, "stalledTurns": 0,
                          "status": "interrupted-needs-review"}}
        row = {"authoredRows": 120, "problems": [],
               "structurallyValidatedRows": 120}
        rows = {locale: row}
        running = {locale: [48055]}
        with patch.dict(chats.SESSIONS, {locale: chats.SESSIONS[locale]}, clear=True):
            with patch.object(chats, "resume") as resume:
                chats.inspect(state, rows, running, launch=True)
        resume.assert_not_called()
        self.assertEqual(state[locale]["status"], "running")

    def test_only_completed_turn_may_be_resumed(self):
        locale = "bg"
        row = {"authoredRows": 120, "problems": [],
               "structurallyValidatedRows": 120}
        rows = {locale: row}
        running = {locale: []}
        with patch.dict(chats.SESSIONS, {locale: chats.SESSIONS[locale]}, clear=True):
            state = {locale: {"baseline": 100, "stalledTurns": 0,
                              "status": "running"}}
            with patch.object(chats, "latest_turn_status", return_value="task_started"), \
                    patch.object(chats, "resume") as resume:
                chats.inspect(state, rows, running, launch=True)
            resume.assert_not_called()
            self.assertEqual(state[locale]["status"], "interrupted-needs-review")

            state[locale]["status"] = "running"
            with patch.object(chats, "latest_turn_status", return_value="task_complete"), \
                    patch.object(chats, "resume") as resume:
                chats.inspect(state, rows, running, launch=True)
            resume.assert_called_once()


if __name__ == "__main__":
    unittest.main()
