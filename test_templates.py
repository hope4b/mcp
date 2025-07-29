#!/usr/bin/env python3
"""Test template search functionality."""

import os

# Set required environment variables for testing
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def test_template_search():
    """Test the template search functionality."""
    print("🚀 Testing Template Search Functionality")
    print("=" * 60)
    
    # Check authentication status
    print("1. Authentication Status:")
    status = resources.get_auth_status()
    print(status)
    print()
    
    # List available realms
    print("2. Available Realms:")
    realms = resources.list_available_realms()
    print(realms)
    print()
    
    # Search for templates (example search)
    print("3. Search Templates (example: 'user'):")
    try:
        templates = resources.search_templates("user")
        print(templates)
    except Exception as e:
        print(f"❌ Error: {e}")
    print()
    
    # Search with specific realm (if we have one)
    print("4. Testing realm-specific search:")
    try:
        spaces = resources.get_user_spaces()
        if spaces and 'id' in spaces[0]:
            realm_id = spaces[0]['id']
            realm_name = spaces[0]['name']
            print(f"Testing search in realm: {realm_name} ({realm_id})")
            
            templates = resources.search_templates("test", realm_id=realm_id)
            print(templates)
        else:
            print("❌ No realms available for testing")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_template_search() 