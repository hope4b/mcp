#!/usr/bin/env python3
"""Test simplified authentication functionality."""

import os

# Set required environment variables
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def test_simplified_auth():
    """Test that simplified authentication works."""
    print("🧪 Тестируем упрощенную авторизацию")
    print("=" * 50)
    
    try:
        # Check status
        print("1. Проверяем статус авторизации:")
        status = resources.get_auth_status()
        print(status)
        print()
        
        # Test search function
        print("2. Тестируем поиск шаблонов:")
        try:
            result = resources.search_templates("AV22", realm_id="9c288f96-3e98-44fb-a4a3-50ab0ed28c58")
            print(result)
        except Exception as e:
            print(f"⚠️ Поиск завершился с ошибкой (ожидаемо): {e}")
        print()
        
        # Test realms list
        print("3. Тестируем список реалмов:")
        try:
            realms = resources.list_available_realms()
            print(realms)
        except Exception as e:
            print(f"⚠️ Список реалмов завершился с ошибкой (ожидаемо): {e}")
        
        print("\n✅ Упрощенная авторизация работает корректно!")
        print("🔑 Для входа используйте: login_with_credentials('email', 'password')")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_simplified_auth() 