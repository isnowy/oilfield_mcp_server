"""
测试日期追问机制
"""
import sys
sys.path.insert(0, 'd:/work/oilMCP')

from oilfield_mcp_http_server import get_daily_report

print("=" * 60)
print("测试1：用户未指定日期（应该返回可用日期列表）")
print("=" * 60)
result1 = get_daily_report("DG-092", "", "ADMIN", "test_user", "test@example.com")
print(result1)
print()

print("=" * 60)
print("测试2：用户指定了日期（应该返回具体日报）")
print("=" * 60)
result2 = get_daily_report("DG-092", "2023-10-31", "ADMIN", "test_user", "test@example.com")
print(result2[:500] + "...")  # 只显示前500字符
print()

print("=" * 60)
print("测试3：再次查询相同日期（应该使用缓存）")
print("=" * 60)
result3 = get_daily_report("DG-092", "2023-10-31", "ADMIN", "test_user", "test@example.com")
print("使用了缓存" if result3 == result2 else "未使用缓存")
print()
