from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests" / "_realm_agent_admission_schema_transport_probe.py"


def _resolve(schema: dict, root: dict) -> dict:
    if "$ref" not in schema:
        return schema
    return root["$defs"][schema["$ref"].rsplit("/", 1)[-1]]


class RealmAgentAdmissionSchemaTransportTests(unittest.TestCase):
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

    def test_tools_list_has_one_new_two_argument_admission_tool(self) -> None:
        self.assertEqual(self.evidence["tool_count"], 65)
        self.assertEqual(self.evidence["admission_registration_count"], 1)
        schema = self.evidence["input_schema"]
        self.assertEqual(list(schema["properties"]), ["realm_id", "candidate"])
        self.assertEqual(schema["required"], ["realm_id", "candidate"])
        self.assertFalse(schema["additionalProperties"])

    def test_tools_list_candidate_is_recursively_closed(self) -> None:
        root = self.evidence["input_schema"]
        candidate = _resolve(root["properties"]["candidate"], root)
        self.assertFalse(candidate["additionalProperties"])
        for nested_name in ("charter_document", "registry_entry"):
            nested = _resolve(candidate["properties"][nested_name], root)
            self.assertFalse(nested["additionalProperties"])

    def test_protocol_rejects_unknown_missing_null_and_third_argument(self) -> None:
        self.assertEqual(self.evidence["invalid_is_error"], [True, True, True, True])

    def test_valid_call_is_one_exact_post_with_bare_candidate(self) -> None:
        self.assertFalse(self.evidence["valid_is_error"])
        self.assertFalse(self.evidence["mismatch_is_error"])
        self.assertEqual(len(self.evidence["requests"]), 1)
        request = self.evidence["requests"][0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(
            request["url"],
            "http://localhost:8080/api/core/realm/11111111-1111-4111-8111-111111111111/agent-population/admissions",
        )
        self.assertNotIn("candidate", request["json"])
        self.assertNotIn("confirm", request["json"])
        self.assertNotIn("candidate_fingerprint", request["json"])

    def test_output_schema_is_advertised(self) -> None:
        self.assertIsNotNone(self.evidence["output_schema"])


if __name__ == "__main__":
    unittest.main()
