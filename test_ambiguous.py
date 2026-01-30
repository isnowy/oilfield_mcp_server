"""
测试模糊关键词的空值判断
"""
import sys
sys.path.insert(0, 'd:/work/oilMCP')

from oilfield_mcp_http_server import get_daily_report

print("=" * 60)
print("测试：传入模糊关键词（应该返回可用日期列表）")
print("=" * 60)

test_cases = [
    ("", "空字符串"),
    ("最新", "中文：最新"),
    ("latest", "英文：latest"),
    ("recent", "英文：recent"),
    ("当前", "中文：当前"),
]

for date_input, description in test_cases:
    print(f"\n--- {description} ---")
    result = get_daily_report("DG-092", date_input, "ADMIN", "test", "test@example.com")
    if "请明确查询日期" in result:
        print("✅ 正确返回日期选择列表")
    else:
        print(f"❌ 错误！返回了具体日报：{result[:100]}...")
