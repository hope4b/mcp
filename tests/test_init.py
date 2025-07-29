#!/usr/bin/env python3
"""
Тест исправленного MCP API
"""
import os
import time

# Переменные окружения
env_vars = {
    "KEYCLOAK_BASE_URL": "https://app.ontonet.ru",
    "KEYCLOAK_REALM": "onto",
    "KEYCLOAK_CLIENT_ID": "frontend-prod", 
    "KEYCLOAK_CLIENT_SECRET": "",
    "ONTO_API_BASE": "https://app.ontonet.ru/api/v2/core",
    "MCP_TRANSPORT": "stdio"
}

for key, value in env_vars.items():
    os.environ[key] = value

print("=== Тест исправленного MCP API ===\n")

print("1. Тестируем внутреннюю функцию _get_user_spaces_data...")
try:
    from onto_mcp.resources import _get_user_spaces_data
    
    start_time = time.time()
    spaces = _get_user_spaces_data()
    elapsed = time.time() - start_time
    
    print(f"   ✅ Выполнено за {elapsed:.2f}s")
    print(f"   📊 Результат: {len(spaces)} пространств")
    if spaces and not spaces[0].get('error'):
        print(f"   📂 Первое: {spaces[0].get('name', 'N/A')}")
    elif spaces and spaces[0].get('error'):
        print(f"   ❌ Ошибка: {spaces[0]['error']}")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n2. Тестируем инструмент list_available_realms через .fn...")
try:
    from onto_mcp.resources import mcp
    
    # Получаем tool через async API
    import asyncio
    
    async def test_tool():
        list_realms_tool = await mcp.get_tool("list_available_realms")
        
        start_time = time.time()
        result = list_realms_tool.fn()  # Вызываем через .fn
        elapsed = time.time() - start_time
        
        print(f"   ✅ Tool выполнен за {elapsed:.2f}s")
        print(f"   📊 Результат (первые 200 символов): {result[:200]}...")
        
        return result
    
    result = asyncio.run(test_tool())
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Тестируем множественные вызовы для проверки производительности...")
try:
    from onto_mcp.resources import _get_user_spaces_data
    times = []
    
    for i in range(3):
        start_time = time.time()
        _get_user_spaces_data()
        elapsed = time.time() - start_time
        times.append(elapsed)
        print(f"   Вызов {i+1}: {elapsed:.2f}s")
    
    avg_time = sum(times) / len(times)
    print(f"   📊 Среднее время: {avg_time:.2f}s")
    
    if avg_time < 2.0:
        print("   ✅ Производительность в норме!")
    else:
        print("   ⚠️ Медленновато, но работает")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

print("\n4. Тестируем search_templates (использует исправленный код)...")
try:
    from onto_mcp.resources import mcp
    import asyncio
    
    async def test_search():
        search_tool = await mcp.get_tool("search_templates")
        
        start_time = time.time()
        result = search_tool.fn("test")  # Ищем что-то с именем "test"
        elapsed = time.time() - start_time
        
        print(f"   ✅ Search выполнен за {elapsed:.2f}s")
        print(f"   📊 Результат: {len(result)} символов")
        
    asyncio.run(test_search())
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

print(f"\n=== Исправления протестированы ===")
print("🚀 Теперь можно тестировать в Claude Desktop!")