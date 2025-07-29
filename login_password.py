#!/usr/bin/env python3
"""Interactive login with username/password."""

import os
import getpass

# Set required environment variables
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def login_with_password():
    """Interactive login with username and password."""
    print("🔑 Авторизация в Onto через логин/пароль")
    print("=" * 50)
    
    try:
        # Get credentials
        username = input("📧 Email: ").strip()
        if not username:
            print("❌ Email не может быть пустым")
            return
        
        password = getpass.getpass("🔒 Пароль: ")
        if not password:
            print("❌ Пароль не может быть пустым")
            return
        
        print("\n🔄 Авторизуюсь...")
        
        # Try to login
        result = resources.login_with_credentials(username, password)
        print(result)
        
        # Check if successful
        if "успешно" in result.lower() or "successfully" in result.lower():
            print("\n✅ Авторизация успешна!")
            print("\n📊 Текущий статус:")
            status = resources.get_auth_status()
            print(status)
            
            print("\n🎉 Теперь можете использовать все функции MCP!")
            print("   Например: python -c \"from onto_mcp import resources; print(resources.search_templates('user'))\"")
        else:
            print("\n❌ Авторизация не удалась. Проверьте учетные данные.")
            
    except KeyboardInterrupt:
        print("\n⏹️ Авторизация отменена пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    login_with_password() 