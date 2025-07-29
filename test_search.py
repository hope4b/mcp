#!/usr/bin/env python3
"""Test template search in different realms."""

import os

# Set required environment variables
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def test_search():
    """Test template search in available realms."""
    print("🔍 Тестируем поиск шаблонов во всех доступных реалмах")
    print("=" * 60)
    
    try:
        # Get available realms
        print("📁 Получаю список реалмов...")
        realms_result = resources.list_available_realms()
        print(realms_result)
        print()
        
        # Test search terms
        search_terms = ["модель", "a", "test", "entity", "класс"]
        
        # Realm IDs to test
        realm_ids = [
            ("av2@ontonet.ru personal realm", "0d37cb49-5c99-41b1-9351-eb1e61cc07f5"),
            ("zxcxzcxzc", "9c288f96-3e98-44fb-a4a3-50ab0ed28c58"),
            ("Примеры моделей", "25a4aee7-1619-48a7-9c8a-93dffaa19e4b")
        ]
        
        for term in search_terms:
            print(f"🔍 Поиск '{term}':")
            
            # Search in examples realm first (most likely to have templates)
            for realm_name, realm_id in [realm_ids[2]]:  # Just examples realm
                print(f"   В реалме: {realm_name}")
                try:
                    result = resources.search_templates(term, realm_id=realm_id)
                    if "Found" in result and "template(s)" in result:
                        print(f"   ✅ Найдены шаблоны!")
                        print(result)
                        return  # Stop on first success
                    else:
                        print(f"   ❌ Ничего не найдено")
                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")
            print()
        
        print("📝 Попробуем поиск без указания реалма (автовыбор):")
        try:
            result = resources.search_templates("a")
            print(result)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    test_search() 