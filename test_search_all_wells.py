"""
测试查询所有油井功能
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from oilfield_mcp_http_server import search_wells

print("=" * 80)
print("🧪 测试查询所有油井功能")
print("=" * 80)
print()

# 测试1: 不传递任何参数
print("📋 测试1: 不传递任何参数（应返回所有油井）")
print("-" * 80)
result = search_wells(user_role="ADMIN", user_id="test", user_email="test@example.com")
print(result)
print()

# 测试2: 传递空字符串
print("📋 测试2: 传递空字符串 keyword=''（应返回所有油井）")
print("-" * 80)
result = search_wells(keyword="", user_role="ADMIN", user_id="test", user_email="test@example.com")
print(result)
print()

# 测试3: 传递具体关键词
print("📋 测试3: 传递关键词 keyword='ZT-102'（应返回匹配的井）")
print("-" * 80)
result = search_wells(keyword="ZT-102", user_role="ADMIN", user_id="test", user_email="test@example.com")
print(result)
print()

# 测试4: 传递空列表
print("📋 测试4: 传递空列表 keywords=[]（应返回所有油井）")
print("-" * 80)
result = search_wells(keywords=[], user_role="ADMIN", user_id="test", user_email="test@example.com")
print(result)
print()

print("✅ 测试完成")
