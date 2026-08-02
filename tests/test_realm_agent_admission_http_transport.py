from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests" / "_realm_agent_admission_http_transport_probe.py"


class RealmAgentAdmissionHttpTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        completed = subprocess.run(
            [sys.executable, str(PROBE)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.evidence = ast.literal_eval(completed.stdout)

    def test_four_invalid_shapes_are_json_rpc_invalid_params(self) -> None:
        self.assertEqual(self.evidence["initialize_status"], 200)
        self.assertEqual(self.evidence["invalid_statuses"], [200, 200, 200, 200])
        self.assertEqual(
            self.evidence["invalid_payloads"],
            [
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": "Invalid params"},
                }
                for request_id in range(1, 5)
            ],
        )

    def test_invalid_shapes_make_zero_tool_body_and_backend_calls(self) -> None:
        self.assertEqual(
            self.evidence["calls_after_invalid"],
            {"tool_body": 0, "backend": 0},
        )

    def test_non_admission_validation_behavior_is_unchanged(self) -> None:
        payload = self.evidence["other_tool_payload"]
        self.assertNotIn("error", payload)
        self.assertTrue(payload["result"]["isError"])

    def test_valid_admission_remains_transparent(self) -> None:
        payload = self.evidence["valid_payload"]
        self.assertNotIn("error", payload)
        self.assertFalse(payload["result"].get("isError", False))
        self.assertEqual(self.evidence["final_tool_body_calls"], 1)
        self.assertEqual(self.evidence["final_backend_calls"], 1)


if __name__ == "__main__":
    unittest.main()
