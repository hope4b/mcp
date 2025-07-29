#!/usr/bin/env python3
"""Quick login script."""

import os

# Set required environment variables
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def quick_login():
    """Quick login with provided credentials."""
    print("🔄 Авторизуюсь как av2@ontonet.ru...")
    print("=" * 50)
    
    try:
        # Login with provided credentials
        result = resources.login_with_credentials("av2@ontonet.ru", "av233")
        print("Результат авторизации:")
        print(result)
        print()
        
        # Check status after login
        print("📊 Проверяем статус после авторизации:")
        status = resources.get_auth_status()
        print(status)
        print()
        
        # Test API access
        if "successfully" in result.lower() or "успешно" in result.lower():
            print("🎉 Авторизация успешна! Тестирую доступ к API...")
            try:
                realms = resources.list_available_realms()
                print(realms)
            except Exception as e:
                print(f"⚠️ Ошибка при тестировании API: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка при авторизации: {e}")

if __name__ == "__main__":
    quick_login() 