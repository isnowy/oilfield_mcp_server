"""
快速测试基于角色的权限控制
测试ADMIN和USER角色的权限差异
"""
import requests
import json

BASE_URL = "http://localhost:8080"

def test_role(role, description):
    """测试特定角色的权限"""
    print(f"\n{'='*70}")
    print(f"测试: {description}")
    print(f"角色: {role}")
    print('='*70)
    
    headers = {
        "Content-Type": "application/json",
        "X-User-Role": role,
        "X-User-Email": f"{role.lower()}@test.com",
        "X-User-ID": f"{role.lower()}123"
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
            content = result.get("content", [{}])[0].get("text", "")
            
            # 提取井数量
            import re
            match = re.search(r'共 (\d+) 口井', content)
            if match:
                count = match.group(1)
                print(f"\n✅ 成功! 可访问 {count} 口井")
            
            # 显示表格部分
            lines = content.split('\n')
            in_table = False
            table_lines = []
            for line in lines:
                if '井号' in line or '---' in line or in_table:
                    table_lines.append(line)
                    in_table = True
                    if in_table and line.strip() == '':
                        break
            
            if table_lines:
                print("\n井列表:")
                for line in table_lines[:10]:  # 显示前10行
                    print(line)
        else:
            print(f"\n❌ 请求失败 (状态码: {response.status_code})")
            print(response.text[:200])
    
    except Exception as e:
        print(f"\n⚠️ 错误: {str(e)}")

def test_access_specific_well(role, well_id, should_succeed):
    """测试访问特定井的权限"""
    print(f"\n{'='*70}")
    print(f"测试: {role} 访问井 {well_id}")
    print(f"预期: {'✅ 应该成功' if should_succeed else '🚫 应该被拒绝'}")
    print('='*70)
    
    headers = {
        "Content-Type": "application/json",
        "X-User-Role": role,
        "X-User-Email": f"{role.lower()}@test.com",
        "X-User-ID": f"{role.lower()}123"
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
                print(f"\n🚫 权限被拒绝 {'✅ (符合预期)' if not should_succeed else '❌ (不符合预期)'}")
            elif "井信息概览" in content or "井号" in content:
                print(f"\n✅ 访问成功 {'✅ (符合预期)' if should_succeed else '❌ (不符合预期)'}")
                # 显示前几行
                lines = content.split('\n')[:8]
                for line in lines:
                    print(line)
            else:
                print(f"\n⚠️ 未知响应")
                print(content[:200])
        else:
            print(f"\n❌ 请求失败 (状态码: {response.status_code})")
    
    except Exception as e:
        print(f"\n⚠️ 错误: {str(e)}")

def main():
    print("🧪 基于角色的权限控制测试")
    print("="*70)
    print("\n权限规则:")
    print("  • ADMIN    - 管理员，可访问所有4口井")
    print("  • ENGINEER - 工程师，可访问ZT-102, ZT-105 + 公共数据(ZT-108) = 3口井")
    print("  • VIEWER   - 查看者，可访问ZT-102 + 公共数据(ZT-108) = 2口井")
    print("  • USER     - 普通用户，仅公共数据(ZT-108) = 1口井")
    print("  • GUEST    - 访客，仅公共数据(ZT-108) = 1口井")
    
    # 测试不同角色搜索所有井
    test_role("ADMIN", "管理员 - 应该看到所有4口井")
    test_role("ENGINEER", "工程师 - 应该看到3口井")
    test_role("VIEWER", "查看者 - 应该看到2口井")
    test_role("USER", "普通用户 - 应该只看到1口公共井")
    test_role("GUEST", "访客 - 应该只看到1口公共井")
    
    # 测试访问特定井的权限
    print("\n\n" + "="*70)
    print("测试特定井的访问权限")
    print("="*70)
    
    # ADMIN访问任意井 - 应该成功
    test_access_specific_well("ADMIN", "ZT-102", True)
    test_access_specific_well("ADMIN", "XY-009", True)
    
    # USER访问公共数据 - 应该成功
    test_access_specific_well("USER", "ZT-108", True)
    
    # USER访问非公共数据 - 应该被拒绝
    test_access_specific_well("USER", "ZT-102", False)
    test_access_specific_well("USER", "XY-009", False)
    
    # ENGINEER访问权限内的井 - 应该成功
    test_access_specific_well("ENGINEER", "ZT-102", True)
    test_access_specific_well("ENGINEER", "ZT-105", True)
    
    # ENGINEER访问权限外的井 - 应该被拒绝
    test_access_specific_well("ENGINEER", "XY-009", False)
    
    print(f"\n{'='*70}")
    print("✅ 测试完成!")
    print("="*70)
    print("\n提示：")
    print("  1. 如果所有角色都能看到所有数据，服务器可能在开发模式")
    print("  2. 要启用生产模式: $env:DEV_MODE=\"false\"; python oilfield_mcp_http_server.py")
    print("  3. 查看服务器日志了解详细的权限过滤过程")

if __name__ == "__main__":
    main()
