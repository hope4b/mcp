#!/usr/bin/env python3
"""Extended test for template search functionality."""

import os

# Set required environment variables for testing
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def test_various_searches():
    """Test template search with various search terms."""
    print("🔍 Extended Template Search Testing")
    print("=" * 60)
    
    # Check authentication
    print("Authentication Status:")
    spaces = resources.get_user_spaces()
    if not spaces or 'error' in spaces[0]:
        print("❌ Not authenticated or no spaces available")
        return
    
    print(f"✅ Authenticated - Found {len(spaces)} realm(s)")
    
    # Test different search terms
    search_terms = [
        "",          # Empty search - might return all
        "a",         # Single letter - likely to find something
        "e",         # Common letter
        "entity",    # Common word in ontologies
        "class",     # Another common word
        "person",    # Common concept
        "api",       # From realm name
    ]
    
    for term in search_terms:
        print(f"\n--- Searching for: '{term}' ---")
        try:
            if term == "":
                print("⚠️ Skipping empty search term")
                continue
                
            result = resources.search_templates(term)
            print(result)
            
            # If we found results, break to avoid spam
            if "Found" in result and "template(s)" in result:
                print("\n✅ Found some templates! Stopping further searches.")
                break
                
        except Exception as e:
            print(f"❌ Error searching for '{term}': {e}")
    
    print("\n--- Testing advanced search options ---")
    try:
        # Test with children/parents flags
        result = resources.search_templates("a", include_children=True, include_parents=True)
        print("Search with children and parents:")
        print(result)
    except Exception as e:
        print(f"❌ Error in advanced search: {e}")

if __name__ == "__main__":
    test_various_searches() 