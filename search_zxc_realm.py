#!/usr/bin/env python3
"""Search templates in zxcxzcxzc realm."""

import os

# Set required environment variables
os.environ.setdefault("KEYCLOAK_BASE_URL", "https://app.ontonet.ru")
os.environ.setdefault("KEYCLOAK_REALM", "onto")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "frontend-prod")
os.environ.setdefault("ONTO_API_BASE", "https://app.ontonet.ru/api/v2/core")

from onto_mcp import resources

def search_zxc_realm():
    """Search for templates in zxcxzcxzc realm with various terms."""
    realm_id = "9c288f96-3e98-44fb-a4a3-50ab0ed28c58"
    realm_name = "zxcxzcxzc"
    
    print(f"🔍 Поиск шаблонов в пространстве: {realm_name}")
    print(f"🆔 ID реалма: {realm_id}")
    print("=" * 60)
    
    # Try different search terms to find all templates
    search_terms = [
        "e",        # Common letter
        "о",        # Russian letter 
        "и",        # Russian letter
        "система",  # Russian word
        "модель",   # Russian word
        "сервис",   # Russian word
        "решение",  # Russian word
        "arhi",     # Prefix from templates
        "интерфейс", # Russian word
        "приложение", # Russian word
    ]
    
    found_any = False
    
    for term in search_terms:
        print(f"\n--- Поиск '{term}' ---")
        try:
            result = resources.search_templates(term, realm_id=realm_id)
            
            if "Found" in result and "template(s)" in result:
                print(f"✅ Найдены шаблоны!")
                print(result)
                found_any = True
                # Continue searching to see if we find different results
            else:
                print("❌ Ничего не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    if found_any:
        print(f"\n🎉 Завершен поиск в реалме '{realm_name}'")
        print("💡 Используйте UUID шаблонов для дальнейшей работы с ними")
    else:
        print(f"\n⚠️ В реалме '{realm_name}' шаблоны не найдены")

if __name__ == "__main__":
    search_zxc_realm() 