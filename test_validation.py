#!/usr/bin/env python3
"""Test validation of missing environment variables."""

import os

print("Testing validation...")

# Clear environment variables
for key in ['KEYCLOAK_BASE_URL', 'KEYCLOAK_REALM', 'KEYCLOAK_CLIENT_ID', 'ONTO_API_BASE']:
    os.environ.pop(key, None)

try:
    from onto_mcp import settings
    print("❌ ERROR: Should have failed validation!")
except Exception as e:
    print(f"✅ Validation works correctly: {e}") 