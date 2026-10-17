import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import refract_engine  # noqa: E402


class TestRefractEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.transcript_file = self.tmp_path / "transcript.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_transcript(self, steps: list[dict]) -> str:
        with self.transcript_file.open("w", encoding="utf-8") as f:
            for step in steps:
                f.write(json.dumps(step) + "\n")
        return str(self.transcript_file)

    def test_fast_bypass_on_mid_turn_invocation(self) -> None:
        hook_input = {"invocationNum": 2, "transcriptPath": ""}
        bypass, reason = refract_engine.should_bypass_hook(
            hook_input, "fix this bug", {"mode": "auto-intercept"}
        )
        self.assertTrue(bypass)
        self.assertIn("invocationNum > 1", reason)

    def test_fast_bypass_on_slash_command_and_confirmations(self) -> None:
        hook_input = {"invocationNum": 1}
        bypass_slash, _ = refract_engine.should_bypass_hook(
            hook_input, "/plan build a new service", {"mode": "auto-intercept"}
        )
        self.assertTrue(bypass_slash)

        bypass_confirm, _ = refract_engine.should_bypass_hook(
            hook_input, "Looks good!", {"mode": "auto-intercept"}
        )
        self.assertTrue(bypass_confirm)

    def test_transcript_parsing_and_context_binding(self) -> None:
        steps = [
            {
                "step_index": 0,
                "type": "USER_INPUT",
                "status": "DONE",
                "content": "<USER_REQUEST>\nRefactor the authentication middleware in auth_handler.py\n</USER_REQUEST>",
            },
            {
                "step_index": 1,
                "type": "PLANNER_RESPONSE",
                "status": "DONE",
                "tool_calls": [
                    {
                        "name": "replace_file_content",
                        "args": {"TargetFile": "\"/workspace/src/auth_handler.py\""},
                    },
                    {
                        "name": "run_command",
                        "args": {"CommandLine": "\"pytest tests/test_auth.py\""},
                    },
                ],
            },
            {
                "step_index": 2,
                "type": "GENERIC",
                "status": "DONE",
                "content": "The command exited with code 0.",
            },
            {
                "step_index": 3,
                "type": "USER_INPUT",
                "status": "DONE",
                "content": "<USER_REQUEST>\nnow do the same for this file and make it async\n</USER_REQUEST>",
            },
        ]
        t_path = self._write_transcript(steps)
        traj = refract_engine.parse_transcript(t_path)

        self.assertEqual(traj["turn_count"], 2)
        self.assertEqual(traj["latest_user_prompt"], "now do the same for this file and make it async")
        self.assertIn("/workspace/src/auth_handler.py", traj["recent_files"])
        self.assertIn("pytest tests/test_auth.py", traj["recent_commands"])

        eval_res = refract_engine.evaluate_prompt(traj["latest_user_prompt"], traj)
        self.assertIn("/workspace/src/auth_handler.py", eval_res["boundContext"]["files"])
        self.assertLess(eval_res["overallScore"], 75)

        spectrums = refract_engine.synthesize_spectrums(traj["latest_user_prompt"], eval_res, traj)
        self.assertIn("auth_handler.py", spectrums["precision"]["prompt"])
        self.assertIn("pytest tests/test_auth.py", spectrums["strict_spec"]["prompt"])

    def test_failure_spiral_detection_and_root_cause_recommendation(self) -> None:
        steps = [
            {
                "step_index": 0,
                "type": "USER_INPUT",
                "status": "DONE",
                "content": "<USER_REQUEST>\nFix the database connection pool timeout\n</USER_REQUEST>",
            },
            {
                "step_index": 1,
                "type": "PLANNER_RESPONSE",
                "status": "DONE",
                "tool_calls": [{"name": "view_file", "args": {"AbsolutePath": "\"/workspace/src/db_pool.py\""}}],
            },
            {
                "step_index": 2,
                "type": "GENERIC",
                "status": "ERROR",
                "content": "The command exited with code 1.\nAssertionError: PoolTimeout in db_pool.py:88",
            },
            {
                "step_index": 3,
                "type": "USER_INPUT",
                "status": "DONE",
                "content": "<USER_REQUEST>\nit still doesn't work, same error\n</USER_REQUEST>",
            },
        ]
        t_path = self._write_transcript(steps)
        traj = refract_engine.parse_transcript(t_path)
        eval_res = refract_engine.evaluate_prompt(traj["latest_user_prompt"], traj)

        self.assertTrue(eval_res["isFailureSpiral"])
        spectrums = refract_engine.synthesize_spectrums(traj["latest_user_prompt"], eval_res, traj)
        self.assertEqual(spectrums["recommended"]["key"], "root_cause")
        self.assertIn("db_pool.py", spectrums["root_cause"]["prompt"])

    def test_strong_prompt_passes_through_hook_unmodified(self) -> None:
        steps = [
            {
                "step_index": 0,
                "type": "USER_INPUT",
                "status": "DONE",
                "content": (
                    "<USER_REQUEST>\n"
                    "Refactor `parse_transcript` in `scripts/refract_engine.py` to cap `recent_files` at 6 items "
                    "while preserving existing return types, and verify by running `python3 -m unittest`."
                    "\n</USER_REQUEST>"
                ),
            }
        ]
        t_path = self._write_transcript(steps)
        stdin_payload = json.dumps({"invocationNum": 1, "transcriptPath": t_path})

        with patch("sys.stdin", io.StringIO(stdin_payload)), patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            rc = refract_engine.run_hook_from_stdin()
            self.assertEqual(rc, 0)
            self.assertEqual(mock_out.getvalue().strip(), "{}")

    def test_html_scorecard_generation(self) -> None:
        traj = {
            "turn_count": 4,
            "recent_files": ["/workspace/src/app.ts"],
            "recent_commands": ["npm test"],
            "recent_errors": [],
            "prior_user_prompts": ["Add user profile route"],
            "consecutive_errors": 0,
        }
        draft = "fix the bug in this file"
        eval_res = refract_engine.evaluate_prompt(draft, traj)
        spectrums = refract_engine.synthesize_spectrums(draft, eval_res, traj)
        out_html = self.tmp_path / "scorecard.html"

        refract_engine.generate_html_scorecard(draft, eval_res, spectrums, traj, out_html, "auto-intercept")
        self.assertTrue(out_html.exists())
        html_text = out_html.read_text(encoding="utf-8")
        self.assertIn("Refract Trajectory Scorecard", html_text)
        self.assertIn("app.ts", html_text)


if __name__ == "__main__":
    unittest.main()
