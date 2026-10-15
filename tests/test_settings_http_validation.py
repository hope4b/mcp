from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch


class SettingsHttpValidationTests(unittest.TestCase):
    def test_http_mode_does_not_require_session_state_api_key_or_server_onto_api_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ONTO_API_BASE": "http://localhost:8080/api/core",
                "MCP_TRANSPORT": "http",
                "PORT": "8091",
            },
            clear=True,
        ):
            import onto_mcp.settings as settings

            settings = importlib.reload(settings)
            settings.validate_runtime_settings()

    def test_stdio_mode_still_requires_server_onto_api_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ONTO_API_BASE": "http://localhost:8080/api/core",
                "MCP_TRANSPORT": "stdio",
            },
            clear=True,
        ):
            import onto_mcp.settings as settings

            settings = importlib.reload(settings)
            with self.assertRaises(EnvironmentError) as exc:
                settings.validate_runtime_settings()

        self.assertIn("ONTO_API_KEY", str(exc.exception))

    def test_legacy_header_configuration_does_not_change_http_contract(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ONTO_API_BASE": "http://localhost:8080/api/core",
                "MCP_TRANSPORT": "http",
                "ONTO_API_KEY_HEADER": "X-Custom-Outbound",
                "ONTO_API_KEY_PASSTHROUGH_HEADER": "X-Custom-Inbound",
            },
            clear=True,
        ):
            import onto_mcp.settings as settings

            settings = importlib.reload(settings)
            settings.validate_runtime_settings()

        self.assertFalse(hasattr(settings, "ONTO_API_KEY_HEADER"))
        self.assertFalse(hasattr(settings, "ONTO_API_KEY_PASSTHROUGH_HEADER"))


if __name__ == "__main__":
    unittest.main()
