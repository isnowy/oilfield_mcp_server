"""
HTTP MCP Server 测试脚本
用于验证HTTP Server功能和权限控制
"""

import requests
import json
from typing import Dict, List

BASE_URL = "http://localhost:8080"

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}{title}{Colors.END}")
    print('='*60)

def print_success(msg: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    """打印错误消息"""
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg: str):
    """打印信息"""
    print(f"{Colors.YELLOW}ℹ {msg}{Colors.END}")

def test_health_check():
    """测试健康检查"""
    print_section("测试1: 健康检查")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        print_success(f"Server状态: {data['status']}")
        print_success(f"数据库: {data['database']}")
        print_success(f"记录数: {data['total_records']}")
        return True
    except Exception as e:
        print_error(f"健康检查失败: {str(e)}")
        return False

def test_list_tools():
    """测试列出工具"""
    print_section("测试2: 列出可用工具")
    try:
        response = requests.get(f"{BASE_URL}/mcp/tools")
        response.raise_for_status()
        data = response.json()
        tools = data['tools']
        print_success(f"发现 {len(tools)} 个工具:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        return True
    except Exception as e:
        print_error(f"列出工具失败: {str(e)}")
        return False

def call_tool(tool_name: str, arguments: Dict, role: str = "ADMIN", email: str = "test@example.com") -> Dict:
    """调用工具"""
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/call-tool",
            headers={
                "Content-Type": "application/json",
                "X-User-Role": role,
                "X-User-Email": email,
                "X-User-ID": "test-user-id"
            },
            json={
                "name": tool_name,
                "arguments": arguments
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        return {"error": e.response.status_code, "detail": e.response.json()}
    except Exception as e:
        return {"error": "unknown", "detail": str(e)}

def test_admin_permissions():
    """测试管理员权限"""
    print_section("测试3: 管理员权限")
    
    # 测试基础查询（READ权限）
    print("\n3.1 测试查询工具（READ权限）")
    result = call_tool("query_drilling_data", {"limit": 3}, role="ADMIN")
    if "error" not in result:
        print_success("查询成功")
        print(f"  返回 {len(result['content'])} 个结果")
    else:
        print_error(f"查询失败: {result.get('detail', 'unknown')}")
    
    # 测试添加记录（WRITE权限）
    print("\n3.2 测试添加记录（WRITE权限）")
    result = call_tool("add_drilling_record", {
        "well_number": "TEST-001",
        "drilling_date": "2024-01-29",
        "depth": 1500.0,
        "drilling_speed": 25.5,
        "pressure": 120.0,
        "temperature": 85.0
    }, role="ADMIN")
    if "error" not in result:
        print_success("添加记录成功")
    else:
        print_error(f"添加记录失败: {result.get('detail', 'unknown')}")
    
    # 测试删除记录（DELETE权限）
    print("\n3.3 测试删除记录（DELETE权限）")
    result = call_tool("delete_drilling_record", {"record_id": 1}, role="ADMIN")
    if "error" not in result:
        print_success("删除记录成功")
    else:
        print_error(f"删除记录失败: {result.get('detail', 'unknown')}")
    
    # 测试导出数据（ADMIN权限）
    print("\n3.4 测试导出数据（ADMIN权限）")
    result = call_tool("export_all_data", {}, role="ADMIN")
    if "error" not in result:
        print_success("导出数据成功")
        content = json.loads(result['content'][0]['text'])
        print(f"  导出 {content['total_records']} 条记录")
    else:
        print_error(f"导出数据失败: {result.get('detail', 'unknown')}")

def test_user_permissions():
    """测试普通用户权限"""
    print_section("测试4: 普通用户权限")
    
    # 测试基础查询（应该成功）
    print("\n4.1 测试查询工具（应该成功）")
    result = call_tool("query_drilling_data", {"limit": 3}, role="USER")
    if "error" not in result:
        print_success("查询成功 - 符合预期")
    else:
        print_error(f"查询失败 - 不符合预期: {result.get('detail', 'unknown')}")
    
    # 测试添加记录（应该成功）
    print("\n4.2 测试添加记录（应该成功）")
    result = call_tool("add_drilling_record", {
        "well_number": "TEST-002",
        "drilling_date": "2024-01-29",
        "depth": 1200.0
    }, role="USER")
    if "error" not in result:
        print_success("添加记录成功 - 符合预期")
    else:
        print_error(f"添加记录失败 - 不符合预期: {result.get('detail', 'unknown')}")
    
    # 测试删除记录（应该被拒绝）
    print("\n4.3 测试删除记录（应该被拒绝）")
    result = call_tool("delete_drilling_record", {"record_id": 1}, role="USER")
    if "error" in result and result["error"] == 403:
        print_success("删除被拒绝 - 符合预期（权限不足）")
    else:
        print_error("删除未被拒绝 - 不符合预期（权限控制失效）")
    
    # 测试导出数据（应该被拒绝）
    print("\n4.4 测试导出数据（应该被拒绝）")
    result = call_tool("export_all_data", {}, role="USER")
    if "error" in result and result["error"] == 403:
        print_success("导出被拒绝 - 符合预期（权限不足）")
    else:
        print_error("导出未被拒绝 - 不符合预期（权限控制失效）")

def test_guest_permissions():
    """测试访客权限"""
    print_section("测试5: 访客权限")
    
    # 测试基础查询（应该成功）
    print("\n5.1 测试查询工具（应该成功）")
    result = call_tool("query_drilling_data", {"limit": 3}, role="GUEST")
    if "error" not in result:
        print_success("查询成功 - 符合预期")
    else:
        print_error(f"查询失败 - 不符合预期: {result.get('detail', 'unknown')}")
    
    # 测试添加记录（应该被拒绝）
    print("\n5.2 测试添加记录（应该被拒绝）")
    result = call_tool("add_drilling_record", {
        "well_number": "TEST-003",
        "drilling_date": "2024-01-29",
        "depth": 1000.0
    }, role="GUEST")
    if "error" in result and result["error"] == 403:
        print_success("添加被拒绝 - 符合预期（权限不足）")
    else:
        print_error("添加未被拒绝 - 不符合预期（权限控制失效）")

def generate_summary():
    """生成测试总结"""
    print_section("测试总结")
    
    print("\n预期权限配置:")
    print(f"  ADMIN:  ✓ 查询  ✓ 添加  ✓ 删除  ✓ 导出")
    print(f"  USER:   ✓ 查询  ✓ 添加  ✗ 删除  ✗ 导出")
    print(f"  GUEST:  ✓ 查询  ✗ 添加  ✗ 删除  ✗ 导出")
    
    print("\n配置验证:")
    print_info("如果所有测试通过，说明HTTP MCP Server配置正确")
    print_info("可以继续配置LibreChat的librechat.yaml文件")
    
    print("\n下一步:")
    print("1. 编辑 librechat.yaml 配置MCP Server")
    print("2. 设置headers传递用户信息")
    print("3. 重启LibreChat")
    print("4. 在LibreChat中测试工具调用")

def main():
    """主测试流程"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("HTTP MCP Server 测试套件")
    print(f"{'='*60}{Colors.END}\n")
    
    print_info(f"测试目标: {BASE_URL}")
    print_info("确保HTTP MCP Server正在运行: python oilfield_mcp_http_server.py\n")
    
    # 运行测试
    tests = [
        test_health_check,
        test_list_tools,
        test_admin_permissions,
        test_user_permissions,
        test_guest_permissions
    ]
    
    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print_error(f"测试异常: {str(e)}")
    
    # 生成总结
    generate_summary()

if __name__ == "__main__":
    main()
