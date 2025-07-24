"""
Persistent token storage for Onto MCP Server.
Handles secure storage and retrieval of authentication tokens.
"""
from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any
import base64


class TokenStorage:
    """Handle persistent storage of authentication tokens."""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize token storage.
        
        Args:
            storage_dir: Directory to store tokens (default: user home/.onto_mcp)
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.home() / '.onto_mcp'
        
        self.storage_dir.mkdir(exist_ok=True)
        self.token_file = self.storage_dir / 'tokens.json'
        
        # Simple obfuscation key (not cryptographically secure, just basic protection)
        self._obfuscation_key = "onto_mcp_2025"
        
        # Current session tokens
        self._session_data: Dict[str, Any] = {}
        
        # Load tokens on initialization
        self._load_tokens()
    
    def _obfuscate(self, data: str) -> str:
        """Simple obfuscation of sensitive data."""
        if not data:
            return ""
        
        try:
            # Simple XOR-based obfuscation
            key_bytes = self._obfuscation_key.encode('utf-8')
            data_bytes = data.encode('utf-8')
            
            obfuscated = bytearray()
            for i, byte in enumerate(data_bytes):
                obfuscated.append(byte ^ key_bytes[i % len(key_bytes)])
            
            return base64.b64encode(obfuscated).decode('utf-8')
        except Exception:
            return data
    
    def _deobfuscate(self, obfuscated_data: str) -> str:
        """Reverse simple obfuscation."""
        if not obfuscated_data:
            return ""
        
        try:
            # Reverse XOR-based obfuscation
            key_bytes = self._obfuscation_key.encode('utf-8')
            data_bytes = base64.b64decode(obfuscated_data.encode('utf-8'))
            
            deobfuscated = bytearray()
            for i, byte in enumerate(data_bytes):
                deobfuscated.append(byte ^ key_bytes[i % len(key_bytes)])
            
            return deobfuscated.decode('utf-8')
        except Exception:
            return obfuscated_data
    
    def _load_tokens(self) -> None:
        """Load tokens from persistent storage."""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    stored_data = json.load(f)
                
                # Deobfuscate sensitive data
                if 'access_token' in stored_data and stored_data['access_token']:
                    stored_data['access_token'] = self._deobfuscate(stored_data['access_token'])
                
                if 'refresh_token' in stored_data and stored_data['refresh_token']:
                    stored_data['refresh_token'] = self._deobfuscate(stored_data['refresh_token'])
                
                self._session_data = stored_data
                print(f"📁 Loaded tokens from {self.token_file}")
            else:
                self._session_data = {}
        except Exception as e:
            print(f"⚠️ Failed to load tokens: {e}")
            self._session_data = {}
    
    def _save_tokens(self) -> None:
        """Save tokens to persistent storage."""
        try:
            # Prepare data for storage
            storage_data = self._session_data.copy()
            
            # Obfuscate sensitive data
            if 'access_token' in storage_data and storage_data['access_token']:
                storage_data['access_token'] = self._obfuscate(storage_data['access_token'])
            
            if 'refresh_token' in storage_data and storage_data['refresh_token']:
                storage_data['refresh_token'] = self._obfuscate(storage_data['refresh_token'])
            
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(storage_data, f, indent=2)
            
            print(f"💾 Saved tokens to {self.token_file}")
        except Exception as e:
            print(f"⚠️ Failed to save tokens: {e}")
    
    def store_tokens(self, token_data: Dict[str, Any]) -> None:
        """
        Store authentication tokens.
        
        Args:
            token_data: Token data from authentication response
        """
        now = time.time()
        
        # Store tokens
        if 'access_token' in token_data:
            self._session_data['access_token'] = token_data['access_token']
        
        if 'refresh_token' in token_data:
            self._session_data['refresh_token'] = token_data['refresh_token']
        
        # Calculate and store expiration times
        if 'expires_in' in token_data:
            self._session_data['access_token_expires_at'] = now + token_data['expires_in']
        
        if 'refresh_expires_in' in token_data:
            self._session_data['refresh_token_expires_at'] = now + token_data['refresh_expires_in']
        
        # Store metadata
        self._session_data['last_updated'] = now
        self._session_data['token_type'] = token_data.get('token_type', 'Bearer')
        
        # Save to file
        self._save_tokens()
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token."""
        return self._session_data.get('access_token')
    
    def get_refresh_token(self) -> Optional[str]:
        """Get current refresh token."""
        return self._session_data.get('refresh_token')
    
    def is_access_token_expired(self, buffer_seconds: int = 30) -> bool:
        """Check if access token is expired."""
        expires_at = self._session_data.get('access_token_expires_at')
        if not expires_at:
            return True
        
        return time.time() + buffer_seconds >= expires_at
    
    def is_refresh_token_expired(self, buffer_seconds: int = 30) -> bool:
        """Check if refresh token is expired."""
        expires_at = self._session_data.get('refresh_token_expires_at')
        if not expires_at:
            return True
        
        return time.time() + buffer_seconds >= expires_at
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about stored tokens."""
        access_token = self.get_access_token()
        refresh_token = self.get_refresh_token()
        
        info = {
            'has_access_token': bool(access_token),
            'has_refresh_token': bool(refresh_token),
            'access_token_expired': self.is_access_token_expired() if access_token else True,
            'refresh_token_expired': self.is_refresh_token_expired() if refresh_token else True,
            'last_updated': self._session_data.get('last_updated'),
        }
        
        if access_token:
            info['access_token_length'] = len(access_token)
        
        if refresh_token:
            info['refresh_token_length'] = len(refresh_token)
        
        return info
    
    def clear_tokens(self) -> None:
        """Clear all stored tokens."""
        self._session_data.clear()
        
        # Remove file
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                print(f"🗑️ Removed token file {self.token_file}")
        except Exception as e:
            print(f"⚠️ Failed to remove token file: {e}")
    
    def has_valid_session(self) -> bool:
        """Check if we have a valid authentication session."""
        access_token = self.get_access_token()
        if not access_token:
            return False
        
        # If access token is not expired, we're good
        if not self.is_access_token_expired():
            return True
        
        # If access token is expired but refresh token is valid, we can refresh
        refresh_token = self.get_refresh_token()
        if refresh_token and not self.is_refresh_token_expired():
            return True
        
        return False
    
    def get_session_status(self) -> str:
        """Get human-readable session status."""
        if not self.get_access_token():
            return "❌ No authentication tokens"
        
        if not self.is_access_token_expired():
            return "✅ Authenticated (access token valid)"
        
        if self.get_refresh_token() and not self.is_refresh_token_expired():
            return "🔄 Authenticated (access token expired, refresh available)"
        
        return "⏰ Authentication expired (re-authentication required)"


# Global token storage instance
_token_storage = TokenStorage()


def get_token_storage() -> TokenStorage:
    """Get the global token storage instance."""
    return _token_storage 