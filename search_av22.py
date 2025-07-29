#!/usr/bin/env python3
"""Search for templates containing AV22 in zxcxzcxzc realm."""

import os

# Set required environment variables
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def search_av22():
    """Search for templates containing AV22 in zxcxzcxzc realm."""
    realm_id = "9c288f96-3e98-44fb-a4a3-50ab0ed28c58"
    realm_name = "zxcxzcxzc"
    search_term = "AV22"
    
    print(f"🔍 Поиск шаблонов с '{search_term}' в пространстве: {realm_name}")
    print(f"🆔 ID реалма: {realm_id}")
    print("=" * 60)
    
    try:
        result = resources.search_templates(search_term, realm_id=realm_id)
        print(result)
        
        # Also try case variations
        if "No templates found" in result:
            print(f"\n🔄 Пробую поиск с вариациями регистра...")
            
            variations = ["av22", "Av22", "aV22"]
            
            for variant in variations:
                print(f"\n--- Поиск '{variant}' ---")
                try:
                    result = resources.search_templates(variant, realm_id=realm_id)
                    if "Found" in result and "template(s)" in result:
                        print(f"✅ Найдены шаблоны с '{variant}'!")
                        print(result)
                        break
                    else:
                        print("❌ Ничего не найдено")
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")

if __name__ == "__main__":
    search_av22() 