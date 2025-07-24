"""
Keycloak authentication module for Onto MCP Server.
Handles OAuth 2.0 flows and token management.
"""
from __future__ import annotations

import os
import time
import json
import base64
from typing import Dict, Optional, Any
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta


class KeycloakAuth:
    """Handle Keycloak authentication and token management."""
    
    def __init__(self):
        self.base_url = os.getenv("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
        self.realm = os.getenv("KEYCLOAK_REALM", "onto")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "frontend-prod")
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
        
        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self._refresh_expires_at: Optional[float] = None
    
    @property
    def token_endpoint(self) -> str:
        """Get the token endpoint URL."""
        return f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
    
    @property
    def auth_endpoint(self) -> str:
        """Get the authorization endpoint URL."""
        return f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/auth"
    
    @property
    def userinfo_endpoint(self) -> str:
        """Get the userinfo endpoint URL."""
        return f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/userinfo"
    
    def decode_jwt_payload(self, token: str) -> Dict[str, Any]:
        """Decode JWT token payload without verification."""
        try:
            # Split token and get payload part
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")
            
            # Decode payload (add padding if needed)
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(f"Failed to decode JWT: {e}")
    
    def is_token_expired(self, token: str, buffer_seconds: int = 30) -> bool:
        """Check if token is expired with optional buffer."""
        try:
            payload = self.decode_jwt_payload(token)
            exp = payload.get('exp', 0)
            return time.time() + buffer_seconds >= exp
        except Exception:
            return True
    
    def authenticate_with_password(self, username: str, password: str) -> bool:
        """
        Authenticate using username/password (Resource Owner Password Credentials).
        
        Args:
            username: User's username or email
            password: User's password
            
        Returns:
            True if authentication successful, False otherwise
        """
        data = {
            'grant_type': 'password',
            'client_id': self.client_id,
            'username': username,
            'password': password,
            'scope': 'openid profile email'
        }
        
        if self.client_secret:
            data['client_secret'] = self.client_secret
        
        try:
            response = requests.post(
                self.token_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._store_tokens(token_data)
                return True
            else:
                print(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def authenticate_with_client_credentials(self) -> bool:
        """
        Authenticate using client credentials flow.
        Requires client_secret to be set.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not self.client_secret:
            raise ValueError("Client secret required for client credentials flow")
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'openid profile email'
        }
        
        try:
            response = requests.post(
                self.token_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._store_tokens(token_data)
                return True
            else:
                print(f"Client credentials auth failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Client credentials auth error: {e}")
            return False
    
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Get authorization URL for OAuth 2.0 Authorization Code flow.
        
        Args:
            redirect_uri: Callback URL after authorization
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid profile email'
        }
        
        if state:
            params['state'] = state
        
        return f"{self.auth_endpoint}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> bool:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect URI used in authorization request
            
        Returns:
            True if token exchange successful, False otherwise
        """
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        if self.client_secret:
            data['client_secret'] = self.client_secret
        
        try:
            response = requests.post(
                self.token_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._store_tokens(token_data)
                return True
            else:
                print(f"Token exchange failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Token exchange error: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """
        Refresh access token using refresh token.
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self._refresh_token:
            print("No refresh token available")
            return False
        
        # Check if refresh token is expired
        if self._refresh_expires_at and time.time() >= self._refresh_expires_at:
            print("Refresh token expired")
            self.clear_tokens()
            return False
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'refresh_token': self._refresh_token
        }
        
        if self.client_secret:
            data['client_secret'] = self.client_secret
        
        try:
            response = requests.post(
                self.token_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._store_tokens(token_data)
                return True
            else:
                print(f"Token refresh failed: {response.status_code} - {response.text}")
                self.clear_tokens()
                return False
                
        except Exception as e:
            print(f"Token refresh error: {e}")
            self.clear_tokens()
            return False
    
    def get_valid_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token or None if authentication required
        """
        # Check if we have an access token
        if not self._access_token:
            return None
        
        # Check if access token is expired
        if self._token_expires_at and time.time() >= self._token_expires_at - 30:
            print("Access token expired, attempting refresh...")
            if not self.refresh_access_token():
                return None
        
        return self._access_token
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get user information using current access token.
        
        Returns:
            User info dictionary or None if failed
        """
        token = self.get_valid_access_token()
        if not token:
            return None
        
        try:
            response = requests.get(
                self.userinfo_endpoint,
                headers={'Authorization': f'Bearer {token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Get user info failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Get user info error: {e}")
            return None
    
    def _store_tokens(self, token_data: Dict[str, Any]) -> None:
        """Store tokens and calculate expiration times."""
        self._access_token = token_data.get('access_token')
        self._refresh_token = token_data.get('refresh_token', self._refresh_token)
        
        # Calculate expiration times
        now = time.time()
        
        if 'expires_in' in token_data:
            self._token_expires_at = now + token_data['expires_in']
        
        if 'refresh_expires_in' in token_data:
            self._refresh_expires_at = now + token_data['refresh_expires_in']
        
        print("Tokens stored successfully")
    
    def clear_tokens(self) -> None:
        """Clear all stored tokens."""
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._refresh_expires_at = None
        print("Tokens cleared")
    
    def logout(self) -> bool:
        """
        Logout and revoke tokens.
        
        Returns:
            True if logout successful, False otherwise
        """
        if not self._refresh_token:
            self.clear_tokens()
            return True
        
        # Revoke refresh token
        data = {
            'client_id': self.client_id,
            'refresh_token': self._refresh_token
        }
        
        if self.client_secret:
            data['client_secret'] = self.client_secret
        
        try:
            revoke_endpoint = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/revoke"
            response = requests.post(
                revoke_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            self.clear_tokens()
            return response.status_code == 200
            
        except Exception as e:
            print(f"Logout error: {e}")
            self.clear_tokens()
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self.get_valid_access_token() is not None 