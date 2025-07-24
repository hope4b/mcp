#!/usr/bin/env python3
"""
Test script for Keycloak authentication in Onto MCP Server.
Demonstrates various authentication methods.
"""

from onto_mcp.keycloak_auth import KeycloakAuth
from onto_mcp.resources import keycloak_auth, get_user_spaces
import os

def test_password_auth():
    """Test username/password authentication."""
    print("🔐 Testing Password Authentication")
    print("=" * 50)
    
    username = input("Enter username (email): ").strip()
    password = input("Enter password: ").strip()
    
    if keycloak_auth.authenticate_with_password(username, password):
        print("✅ Authentication successful!")
        
        # Get user info
        user_info = keycloak_auth.get_user_info()
        if user_info:
            print(f"👤 User: {user_info.get('name', 'Unknown')}")
            print(f"📧 Email: {user_info.get('email', 'Unknown')}")
        
        # Test API access
        try:
            spaces = get_user_spaces()
            print(f"📁 Found {len(spaces)} spaces")
            for space in spaces[:3]:  # Show first 3
                print(f"  • {space['name']}")
        except Exception as e:
            print(f"❌ API access failed: {e}")
    else:
        print("❌ Authentication failed")

def test_auth_url():
    """Test OAuth 2.0 authorization URL generation."""
    print("\n🌐 Testing OAuth 2.0 Authorization URL")
    print("=" * 50)
    
    redirect_uri = "http://localhost:8080/callback"
    auth_url = keycloak_auth.get_authorization_url(redirect_uri)
    
    print(f"Authorization URL:\n{auth_url}")
    print("\n📝 Instructions:")
    print("1. Open the URL above in your browser")
    print("2. Login with your Onto credentials")
    print("3. Copy the 'code' parameter from the callback URL")
    print("4. Use exchange_auth_code() tool with that code")

def test_token_info():
    """Test token information and validation."""
    print("\n🔍 Testing Token Information")
    print("=" * 50)
    
    token = keycloak_auth.get_valid_access_token()
    if token:
        try:
            payload = keycloak_auth.decode_jwt_payload(token)
            print(f"👤 Subject: {payload.get('sub', 'Unknown')}")
            print(f"📧 Email: {payload.get('email', 'Unknown')}")
            print(f"⏰ Expires: {payload.get('exp', 'Unknown')}")
            print(f"🏢 Issuer: {payload.get('iss', 'Unknown')}")
            
            # Check if expired
            is_expired = keycloak_auth.is_token_expired(token)
            print(f"🔄 Token expired: {is_expired}")
            
        except Exception as e:
            print(f"❌ Error decoding token: {e}")
    else:
        print("❌ No access token available")

def test_auth_status():
    """Test authentication status."""
    print("\n📊 Authentication Status")
    print("=" * 50)
    
    is_auth = keycloak_auth.is_authenticated()
    print(f"Authentication status: {'✅ Authenticated' if is_auth else '❌ Not authenticated'}")
    
    if is_auth:
        user_info = keycloak_auth.get_user_info()
        if user_info:
            print(f"User: {user_info.get('preferred_username', 'Unknown')}")
            print(f"Email: {user_info.get('email', 'Unknown')}")

def main():
    """Main test function."""
    print("🚀 Onto MCP Keycloak Authentication Test")
    print("=" * 60)
    
    print(f"Keycloak Base URL: {keycloak_auth.base_url}")
    print(f"Realm: {keycloak_auth.realm}")
    print(f"Client ID: {keycloak_auth.client_id}")
    
    while True:
        print("\n📋 Available Tests:")
        print("1. Password Authentication")
        print("2. Generate OAuth Authorization URL")
        print("3. Show Token Information")
        print("4. Check Authentication Status")
        print("5. Test API Access (get spaces)")
        print("6. Logout")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            test_password_auth()
        elif choice == "2":
            test_auth_url()
        elif choice == "3":
            test_token_info()
        elif choice == "4":
            test_auth_status()
        elif choice == "5":
            try:
                spaces = get_user_spaces()
                print(f"\n📁 Found {len(spaces)} spaces:")
                for i, space in enumerate(spaces, 1):
                    print(f"  {i}. {space['name']} ({space['id']})")
            except Exception as e:
                print(f"❌ Error getting spaces: {e}")
        elif choice == "6":
            if keycloak_auth.logout():
                print("✅ Logged out successfully")
            else:
                print("❌ Logout failed")
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main() 