#!/usr/bin/env python3
"""Test template search in personal realm."""

import os

# Set required environment variables for testing
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def test_personal_realm():
    """Test template search in personal realm."""
    print("🏠 Testing Personal Realm Template Search")
    print("=" * 60)
    
    # Get available realms
    spaces = resources.get_user_spaces()
    if not spaces or 'error' in spaces[0]:
        print("❌ Not authenticated or no spaces available")
        return
    
    print("Available realms:")
    for i, space in enumerate(spaces):
        print(f"{i+1}. {space['name']} ({space['id']})")
    
    # Find personal realm (usually contains email or 'personal')
    personal_realm = None
    for space in spaces:
        if 'personal' in space['name'].lower() or '@' in space['name']:
            personal_realm = space
            break
    
    if not personal_realm:
        print("⚠️ No personal realm found, using first available")
        personal_realm = spaces[0]
    
    realm_id = personal_realm['id']
    realm_name = personal_realm['name']
    
    print(f"\n🎯 Testing in realm: {realm_name}")
    print(f"   Realm ID: {realm_id}")
    
    # Test various searches in this specific realm
    search_terms = ["a", "test", "entity", "user", "person"]
    
    for term in search_terms:
        print(f"\n--- Searching for '{term}' in {realm_name} ---")
        try:
            result = resources.search_templates(term, realm_id=realm_id)
            print(result)
            
            # If we found something, show details and continue
            if "Found" in result and "template(s)" in result:
                print("✅ Found templates!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test with empty search to potentially get all templates
    print(f"\n--- Testing broader search ---")
    try:
        # Some APIs accept empty or single character searches to return more results
        for term in ["", " "]:
            if term == "":
                continue  # Skip empty for now
            print(f"Searching for '{term}':")
            result = resources.search_templates(term, realm_id=realm_id)
            print(result)
    except Exception as e:
        print(f"❌ Error in broad search: {e}")

if __name__ == "__main__":
    test_personal_realm() 