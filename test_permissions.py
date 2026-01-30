"""
测试MCP服务器权限控制的脚本
演示不同角色的用户访问权限差异

使用前请确保MCP服务器正在运行：
  python oilfield_mcp_http_server.py
"""
import sys
import json

try:
    import requests
except ImportError:
    print("❌ 请先安装 requests 库: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8080"

def test_search_wells(role, email, user_id, description):
    """测试搜索井功能"""
    print(f"\n{'='*60}")
    print(f"测试场景: {description}")
    print(f"用户角色: {role}, 邮箱: {email}, ID: {user_id}")
    print('='*60)
    
    headers = {
        "Content-Type": "application/json",
        "X-User-Role": role,
        "X-User-Email": email,
        "X-User-ID": user_id
    }
    
    data = {
        "name": "search_wells",
        "arguments": {
            "keyword": "",
            "status": "All"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/call-tool",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 请求成功 (状态码: {response.status_code})")
            if result.get("content"):
                content = result["content"][0].get("text", "")
                # 提取井数量
                if "共" in content and "口井" in content:
                    import re
                    match = re.search(r'共 (\d+) 口井', content)
                    if match:
                        count = match.group(1)
                        print(f"📊 可访问井数量: {count} 口")
                
                # 显示部分结果
                lines = content.split('\n')[:15]
                print("\n返回数据预览:")
                print('\n'.join(lines))
                if len(content.split('\n')) > 15:
                    print("... (内容已截断)")
        else:
            print(f"\n❌ 请求失败 (状态码: {response.status_code})")
            print(f"响应: {response.text}")
    
    except Exception as e:
        print(f"\n⚠️ 请求错误: {str(e)}")

def test_get_well_detail(role, email, user_id, well_id, description):
    """测试获取单井详情"""
    print(f"\n{'='*60}")
    print(f"测试场景: {description}")
    print(f"用户: {email} ({role}) 尝试访问井号: {well_id}")
    print('='*60)
    
    headers = {
        "Content-Type": "application/json",
        "X-User-Role": role,
        "X-User-Email": email,
        "X-User-ID": user_id
    }
    
    data = {
        "name": "get_well_summary",
        "arguments": {
            "well_id": well_id
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/call-tool",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("content", [{}])[0].get("text", "")
            
            if "🚫 权限拒绝" in content:
                print(f"\n🚫 权限被拒绝（符合预期）")
                print(f"消息: {content[:100]}")
            elif "❌" in content:
                print(f"\n❌ 查询失败")
                print(f"消息: {content[:100]}")
            else:
                print(f"\n✅ 访问成功")
                # 显示部分结果
                lines = content.split('\n')[:10]
                print('\n'.join(lines))
        else:
            print(f"\n❌ 请求失败 (状态码: {response.status_code})")
    
    except Exception as e:
        print(f"\n⚠️ 请求错误: {str(e)}")

def main():
    """主测试流程"""
    print("🧪 MCP服务器权限控制测试")
    print("=" * 60)
    print("测试数据说明:")
    print("  ZT-102: user1@test.com (ID: 697c0cbebb4a93216518c3f9)")
    print("  ZT-105: user2@test.com (ID: 697c0cbebb4a93216518c3fd)")
    print("  ZT-108: 公共数据 (owner: None)")
    print("  XY-009: user1@test.com (ID: 697c0cbebb4a93216518c3f9)")
    print("=" * 60)
    
    # 测试1: ADMIN用户 - 应该看到所有井
    test_search_wells(
        role="ADMIN",
        email="admin@test.com",
        user_id="admin123",
        description="ADMIN用户搜索所有井（预期：4口井）"
    )
    
    # 测试2: User1 - 应该看到3口井（ZT-102, XY-009, ZT-108）
    test_search_wells(
        role="USER",
        email="user1@test.com",
        user_id="697c0cbebb4a93216518c3f9",
        description="User1搜索所有井（预期：3口井）"
    )
    
    # 测试3: User2 - 应该看到2口井（ZT-105, ZT-108）
    test_search_wells(
        role="USER",
        email="user2@test.com",
        user_id="697c0cbebb4a93216518c3fd",
        description="User2搜索所有井（预期：2口井）"
    )
    
    # 测试4: User1访问自己的井 - 应该成功
    test_get_well_detail(
        role="USER",
        email="user1@test.com",
        user_id="697c0cbebb4a93216518c3f9",
        well_id="ZT-102",
        description="User1访问自己的井ZT-102（预期：成功）"
    )
    
    # 测试5: User1访问User2的井 - 应该被拒绝
    test_get_well_detail(
        role="USER",
        email="user1@test.com",
        user_id="697c0cbebb4a93216518c3f9",
        well_id="ZT-105",
        description="User1尝试访问User2的井ZT-105（预期：拒绝）"
    )
    
    # 测试6: User2访问公共数据 - 应该成功
    test_get_well_detail(
        role="USER",
        email="user2@test.com",
        user_id="697c0cbebb4a93216518c3fd",
        well_id="ZT-108",
        description="User2访问公共井ZT-108（预期：成功）"
    )
    
    # 测试7: GUEST用户 - 只能看到公共数据
    test_search_wells(
        role="GUEST",
        email="guest@test.com",
        user_id="guest123",
        description="GUEST用户搜索（预期：仅公共数据）"
    )
    
    print(f"\n{'='*60}")
    print("✅ 测试完成！")
    print("=" * 60)
    print("\n提示：")
    print("  1. 如果所有用户都能看到所有数据，请确认DEV_MODE=false")
    print("  2. 查看服务器日志以了解详细的权限过滤过程")
    print("  3. 当前服务器运行在开发模式，需要重启并设置环境变量")
    print("\n如何启用生产模式：")
    print("  Windows PowerShell: $env:DEV_MODE=\"false\"; python oilfield_mcp_http_server.py")
    print("  Windows CMD: set DEV_MODE=false && python oilfield_mcp_http_server.py")

if __name__ == "__main__":
    main()
