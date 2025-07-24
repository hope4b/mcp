#!/usr/bin/env python3
"""
Simple test for persistent authentication system.
Run this to test the new authentication features.
"""

from onto_mcp import resources

def test_persistent_auth():
    """Test the persistent authentication system."""
    print("🚀 Testing Persistent Authentication System")
    print("=" * 50)
    
    # Check initial status
    print("1. Initial Authentication Status:")
    status = resources.get_auth_status()
    print(status)
    print()
    
    # Get session info
    print("2. Detailed Session Information:")
    session_info = resources.get_session_info()
    print(session_info)
    print()
    
    # Try to get spaces (this will show auth requirement if not authenticated)
    print("3. Testing API Access (get spaces):")
    try:
        spaces = resources.get_user_spaces()
        if spaces and isinstance(spaces, list):
            if 'error' in spaces[0]:
                print(f"❌ {spaces[0]['error']}")
            else:
                print(f"✅ Successfully retrieved {len(spaces)} spaces:")
                for space in spaces:
                    if 'name' in space:
                        print(f"  • {space['name']}")
        else:
            print("❌ Unexpected response format")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # Show setup instructions if not authenticated
    if "❌ Not authenticated" in status:
        print("4. Authentication Setup Instructions:")
        instructions = resources.setup_auth_interactive()
        print(instructions)

if __name__ == "__main__":
    test_persistent_auth() 