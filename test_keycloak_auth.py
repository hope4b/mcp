#!/usr/bin/env python3
"""
Test script for Keycloak authentication in Onto MCP Server.
Demonstrates various authentication methods.
"""

from onto_mcp.keycloak_auth import KeycloakAuth
from onto_mcp.resources import keycloak_auth, get_user_spaces
import os
import pytest

@pytest.mark.interactive
def interactive_password_auth():
    """Interactive test for username/password authentication."""
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

@pytest.mark.interactive
def interactive_auth_url():
    """Interactive test for OAuth 2.0 authorization URL generation."""
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

@pytest.mark.interactive
def interactive_token_info():
    """Interactive test for token information and validation."""
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

@pytest.mark.interactive
def interactive_auth_status():
    """Interactive test for authentication status."""
    print("\n📊 Authentication Status")
    print("=" * 50)
    
    is_auth = keycloak_auth.is_authenticated()
    print(f"Authentication status: {'✅ Authenticated' if is_auth else '❌ Not authenticated'}")
    
    if is_auth:
        user_info = keycloak_auth.get_user_info()
        if user_info:
            print(f"User: {user_info.get('preferred_username', 'Unknown')}")
            print(f"Email: {user_info.get('email', 'Unknown')}")

# Real unit tests for CI/CD
@pytest.mark.unit
def test_keycloak_initialization():
    """Test that KeycloakAuth initializes properly."""
    auth = KeycloakAuth()
    assert auth.base_url == "https://app.ontonet.ru"
    assert auth.realm == "onto"
    assert auth.client_id == "frontend-prod"

@pytest.mark.unit
def test_token_endpoint_urls():
    """Test that Keycloak endpoint URLs are generated correctly."""
    auth = KeycloakAuth()
    
    assert auth.token_endpoint == "https://app.ontonet.ru/realms/onto/protocol/openid-connect/token"
    assert auth.auth_endpoint == "https://app.ontonet.ru/realms/onto/protocol/openid-connect/auth"
    assert auth.userinfo_endpoint == "https://app.ontonet.ru/realms/onto/protocol/openid-connect/userinfo"

@pytest.mark.unit
def test_authorization_url_generation():
    """Test OAuth 2.0 authorization URL generation."""
    auth = KeycloakAuth()
    redirect_uri = "http://localhost:8080/callback"
    
    auth_url = auth.get_authorization_url(redirect_uri)
    
    assert "https://app.ontonet.ru/realms/onto/protocol/openid-connect/auth" in auth_url
    assert "client_id=frontend-prod" in auth_url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback" in auth_url
    assert "response_type=code" in auth_url
    assert "scope=openid+profile+email" in auth_url

@pytest.mark.unit
def test_jwt_token_validation():
    """Test JWT token validation functions."""
    auth = KeycloakAuth()
    
    # Test with invalid token
    invalid_token = "invalid.token.format"
    with pytest.raises(ValueError):
        auth.decode_jwt_payload(invalid_token)
    
    # Test token expiration check with invalid token
    assert auth.is_token_expired(invalid_token) == True

@pytest.mark.unit
def test_authentication_status_without_tokens():
    """Test authentication status when no tokens are stored."""
    auth = KeycloakAuth()
    
    # Clear any existing tokens
    auth.token_storage.clear_tokens()
    
    assert auth.is_authenticated() == False
    assert auth.get_valid_access_token() is None

def main():
    """Main interactive test function."""
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
            interactive_password_auth()
        elif choice == "2":
            interactive_auth_url()
        elif choice == "3":
            interactive_token_info()
        elif choice == "4":
            interactive_auth_status()
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