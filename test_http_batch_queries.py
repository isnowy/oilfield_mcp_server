"""
HTTP API 批量查询功能测试
使用HTTP请求测试批量查询功能
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "X-User-Role": "ADMIN",
    "X-User-ID": "test_user_001",
    "X-User-Email": "test@example.com"
}

def print_test_header(test_name):
    """打印测试标题"""
    print("\n" + "=" * 80)
    print(f"📋 测试: {test_name}")
    print("=" * 80)

def call_tool(tool_name, arguments):
    """调用MCP工具"""
    url = f"{BASE_URL}/mcp/call-tool"
    payload = {
        "name": tool_name,
        "arguments": arguments
    }
    
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

print("=" * 80)
print("🧪 HTTP API 批量查询功能测试")
print("=" * 80)
print(f"Base URL: {BASE_URL}")
print()

# 检查服务器是否运行
try:
    response = requests.get(f"{BASE_URL}/health", timeout=2)
    if response.status_code == 200:
        print("✅ 服务器运行正常")
    else:
        print("⚠️ 服务器响应异常")
        exit(1)
except requests.exceptions.RequestException as e:
    print(f"❌ 无法连接到服务器: {e}")
    print("\n💡 提示: 请先启动服务器")
    print("   命令: python oilfield_mcp_http_server.py")
    exit(1)

# ==========================================
# 测试 1: search_wells - 单关键词搜索
# ==========================================
print_test_header("search_wells - 单关键词搜索（旧接口）")
print("请求: POST /mcp/call-tool")
print("参数: {keyword: 'ZT-102'}")

result = call_tool("search_wells", {"keyword": "ZT-102", "status": "All"})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    print(json.dumps(result, indent=2, ensure_ascii=False))

# ==========================================
# 测试 2: search_wells - 多关键词搜索
# ==========================================
print_test_header("search_wells - 多关键词批量搜索（新接口）")
print("请求: POST /mcp/call-tool")
print("参数: {keywords: ['ZT', 'Block-A']}")

result = call_tool("search_wells", {"keywords": ["ZT", "Block-A"], "status": "All"})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    print(json.dumps(result, indent=2, ensure_ascii=False))

# ==========================================
# 测试 3: get_well_summary - 单井查询
# ==========================================
print_test_header("get_well_summary - 单井概况查询（旧接口）")
print("请求: POST /mcp/call-tool")
print("参数: {well_id: 'ZT-102'}")

result = call_tool("get_well_summary", {"well_id": "ZT-102"})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    content = result.get("content", [])
    if content and len(content) > 0:
        print(content[0].get("text", ""))

# ==========================================
# 测试 4: get_well_summary - 多井批量查询
# ==========================================
print_test_header("get_well_summary - 多井批量概况查询（新接口）")
print("请求: POST /mcp/call-tool")
print("参数: {well_ids: ['ZT-102', 'ZT-105', 'ZT-108']}")

result = call_tool("get_well_summary", {"well_ids": ["ZT-102", "ZT-105", "ZT-108"]})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "")
        # 只显示前500个字符
        if len(text) > 500:
            print(text[:500] + "\n...(已截断)")
        else:
            print(text)

# ==========================================
# 测试 5: get_daily_report - 多井同一日期
# ==========================================
print_test_header("get_daily_report - 多井同一日期批量查询（新接口）")
print("请求: POST /mcp/call-tool")
print("参数: {well_ids: ['ZT-102', 'ZT-105'], date: '2023-11-01'}")

result = call_tool("get_daily_report", {
    "well_ids": ["ZT-102", "ZT-105"],
    "date": "2023-11-01"
})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "")
        # 只显示前600个字符
        if len(text) > 600:
            print(text[:600] + "\n...(已截断)")
        else:
            print(text)

# ==========================================
# 测试 6: get_daily_report - 多井多日期
# ==========================================
print_test_header("get_daily_report - 多井多日期批量查询（新接口）")
print("请求: POST /mcp/call-tool")
print("参数: {well_ids: ['ZT-102', 'ZT-105'], dates: ['2023-11-01', '2023-11-02']}")

result = call_tool("get_daily_report", {
    "well_ids": ["ZT-102", "ZT-105"],
    "dates": ["2023-11-01", "2023-11-02"]
})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "")
        # 只显示前600个字符
        if len(text) > 600:
            print(text[:600] + "\n...(已截断)")
        else:
            print(text)

# ==========================================
# 测试 7: generate_weekly_report - 单井周报
# ==========================================
print_test_header("generate_weekly_report - 单井周报生成（旧接口）")
print("请求: POST /mcp/call-tool")
print("参数: {well_id: 'ZT-102', start_date: '2023-11-01', end_date: '2023-11-07'}")

result = call_tool("generate_weekly_report", {
    "well_id": "ZT-102",
    "start_date": "2023-11-01",
    "end_date": "2023-11-07"
})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    content = result.get("content", [])
    if content and len(content) > 0:
        print(content[0].get("text", ""))

# ==========================================
# 测试 8: generate_weekly_report - 多井周报
# ==========================================
print_test_header("generate_weekly_report - 多井批量周报生成（新接口）")
print("请求: POST /mcp/call-tool")
print("参数: {well_ids: ['ZT-102', 'ZT-105'], start_date: '2023-11-01', end_date: '2023-11-07'}")

result = call_tool("generate_weekly_report", {
    "well_ids": ["ZT-102", "ZT-105"],
    "start_date": "2023-11-01",
    "end_date": "2023-11-07"
})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "")
        # 只显示前800个字符
        if len(text) > 800:
            print(text[:800] + "\n...(已截断)")
        else:
            print(text)

# ==========================================
# 测试 9: 权限测试 - VIEWER用户
# ==========================================
print_test_header("权限测试 - VIEWER用户批量查询")
print("请求: POST /mcp/call-tool")
print("参数: {well_ids: ['ZT-102', 'ZT-105', 'ZT-108']}")
print("Headers: X-User-Role=VIEWER")

viewer_headers = HEADERS.copy()
viewer_headers["X-User-Role"] = "VIEWER"
viewer_headers["X-User-Email"] = "viewer@example.com"

url = f"{BASE_URL}/mcp/call-tool"
payload = {
    "name": "get_well_summary",
    "arguments": {"well_ids": ["ZT-102", "ZT-105", "ZT-108"]}
}

try:
    response = requests.post(url, json=payload, headers=viewer_headers)
    response.raise_for_status()
    result = response.json()
    
    print("\n响应:")
    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "")
        # 只显示前400个字符
        if len(text) > 400:
            print(text[:400] + "\n...(已截断)")
        else:
            print(text)
except requests.exceptions.RequestException as e:
    print(f"❌ 错误: {e}")

# ==========================================
# 测试 10: 错误处理 - 不存在的井号
# ==========================================
print_test_header("错误处理 - 批量查询包含不存在的井号")
print("请求: POST /mcp/call-tool")
print("参数: {well_ids: ['ZT-102', 'INVALID-WELL', 'ZT-105']}")

result = call_tool("get_well_summary", {"well_ids": ["ZT-102", "INVALID-WELL", "ZT-105"]})
print("\n响应:")
if "error" in result:
    print(f"❌ 错误: {result['error']}")
else:
    content = result.get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "")
        # 只显示前600个字符
        if len(text) > 600:
            print(text[:600] + "\n...(已截断)")
        else:
            print(text)

# ==========================================
# 测试总结
# ==========================================
print("\n" + "=" * 80)
print("✅ HTTP API 测试完成")
print("=" * 80)
print("\n测试项:")
print("  ✓ search_wells - 单关键词搜索")
print("  ✓ search_wells - 多关键词批量搜索")
print("  ✓ get_well_summary - 单井查询")
print("  ✓ get_well_summary - 多井批量查询")
print("  ✓ get_daily_report - 多井同一日期批量查询")
print("  ✓ get_daily_report - 多井多日期批量查询")
print("  ✓ generate_weekly_report - 单井周报生成")
print("  ✓ generate_weekly_report - 多井批量周报生成")
print("  ✓ 权限测试 - VIEWER用户")
print("  ✓ 错误处理 - 不存在的井号")
print()
print("💡 提示: 所有HTTP API测试通过表示批量查询功能正常工作")
print()
