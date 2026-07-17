from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests" / "_memory_artifact_schema_transport_probe.py"


class MemoryArtifactSchemaTransportTests(unittest.TestCase):
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

    def test_typed_dict_uses_python_311_compatible_source(self) -> None:
        source = (REPO_ROOT / "onto_mcp" / "api_resources.py").read_text(encoding="utf-8")

        self.assertIn("from typing_extensions import NotRequired, TypedDict", source)
        self.assertNotIn("from typing import Annotated, Any, Literal, NotRequired, TypedDict", source)

    def test_tools_list_exposes_explicit_non_empty_target_objects(self) -> None:
        schemas = self.evidence["schemas"]
        for tool_name in (
            "create_memory_artifact_draft",
            "update_memory_artifact_draft",
            "supersede_memory_artifact",
        ):
            with self.subTest(tool=tool_name):
                item_schema = schemas[tool_name]["item_schema"]
                self.assertEqual(schemas[tool_name]["container_type"], "array")
                self.assertEqual(schemas[tool_name]["min_items"], 1)
                self.assertEqual(item_schema["type"], "object")
                self.assertEqual(set(item_schema["properties"]), {"target_kind", "target_id", "role"})
                self.assertEqual(set(item_schema["required"]), {"target_kind", "target_id"})
                self.assertEqual(
                    item_schema["properties"]["target_kind"]["enum"],
                    ["realm", "template", "entity", "diagram"],
                )
                self.assertEqual(item_schema["properties"]["target_id"]["type"], "string")
                self.assertEqual(item_schema["properties"]["role"]["default"], "primary")

        self.assertTrue(schemas["create_memory_artifact_draft"]["targets_required"])
        self.assertTrue(schemas["supersede_memory_artifact"]["targets_required"])
        self.assertFalse(schemas["update_memory_artifact_draft"]["targets_required"])

    def test_protocol_preserves_target_arrays_for_all_three_backend_payloads(self) -> None:
        self.assertEqual(self.evidence["successful_calls"], [True, True, True])
        self.assertEqual(self.evidence["boundary_types"], ["list", "list", "list"])
        self.assertEqual(len(self.evidence["backend_shapes"]), 3)
        for shape in self.evidence["backend_shapes"]:
            self.assertEqual(shape["targets_type"], "list")
            self.assertEqual(shape["target_item_types"], ["dict", "dict"])
            self.assertEqual(shape["targets_count"], 2)

    def test_protocol_rejects_empty_target_arrays(self) -> None:
        self.assertEqual(self.evidence["empty_array_errors"], [True, True, True])


if __name__ == "__main__":
    unittest.main()
