#!/usr/bin/env python3
"""
快速测试权限配置
测试不同角色对各种工具的访问权限
"""
import os
import sys
from typing import List, Dict

# 确保能导入permissions模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from permissions import PermissionChecker, UserRole, TOOL_PERMISSIONS, ROLE_PERMISSIONS

def print_separator(char="=", length=70):
    """打印分隔线"""
    print(char * length)

def test_role_permissions(role: str, email: str):
    """
    测试指定角色的权限
    
    Args:
        role: 角色名称 (ADMIN/USER/GUEST)
        email: 用户邮箱
    """
    print_separator()
    print(f"🧪 测试角色: {role}")
    print(f"📧 用户邮箱: {email}")
    print_separator()
    
    # 设置环境变量
    os.environ["LIBRECHAT_USER_ROLE"] = role
    os.environ["LIBRECHAT_USER_EMAIL"] = email
    os.environ["LIBRECHAT_USER_USERNAME"] = email.split("@")[0]
    os.environ["DEV_MODE"] = "false"  # 启用权限检查
    
    # 创建权限检查器
    checker = PermissionChecker()
    
    # 显示用户信息
    user_context = checker.get_user_context()
    print(f"\n📊 用户上下文:")
    for key, value in user_context.items():
        print(f"   {key}: {value}")
    
    # 显示角色权限
    try:
        role_enum = UserRole[role]
        role_perms = ROLE_PERMISSIONS.get(role_enum, [])
        print(f"\n🔐 角色 '{role}' 拥有的权限:")
        if role_perms:
            for perm in role_perms:
                print(f"   ✅ {perm.value}")
        else:
            print("   ❌ 无权限")
    except KeyError:
        print(f"\n⚠️  未知角色: {role}")
    
    # 测试所有工具
    print(f"\n🔧 工具访问测试:")
    print("-" * 70)
    
    # 按权限分组显示工具
    tools_by_permission = {
        "READ": [],
        "WRITE": [],
        "DELETE": [],
        "ADMIN": []
    }
    
    for tool_name, required_perms in TOOL_PERMISSIONS.items():
        has_permission, error = checker.has_permission(tool_name)
        status = "✅" if has_permission else "❌"
        
        # 确定工具的主要权限类别
        if required_perms:
            main_perm = required_perms[0].value
            tools_by_permission[main_perm.upper()].append((tool_name, has_permission, error))
    
    # 显示分组结果
    for perm_type, tools in tools_by_permission.items():
        if tools:
            print(f"\n  [{perm_type} 权限工具]")
            for tool_name, has_perm, error in tools:
                status = "✅" if has_perm else "❌"
                print(f"    {status} {tool_name}")
                if not has_perm and error:
                    print(f"       💬 {error}")
    
    # 统计信息
    allowed_tools = checker.get_allowed_tools()
    total_tools = len(TOOL_PERMISSIONS)
    print(f"\n📈 统计:")
    print(f"   允许使用: {len(allowed_tools)}/{total_tools} 个工具")
    print(f"   访问率: {len(allowed_tools)/total_tools*100:.1f}%")
    
    print()


def test_all_roles():
    """测试所有预定义角色"""
    test_cases = [
        ("ADMIN", "admin@oilfield.com"),
        ("USER", "engineer@oilfield.com"),
        ("GUEST", "guest@oilfield.com"),
    ]
    
    print("\n")
    print_separator("=", 70)
    print("🚀 MCP Server 权限系统全面测试")
    print_separator("=", 70)
    
    for role, email in test_cases:
        test_role_permissions(role, email)
    
    print_separator("=", 70)
    print("✅ 测试完成!")
    print_separator("=", 70)
    print()


def test_dev_mode():
    """测试开发模式"""
    print_separator()
    print("🔓 测试开发模式 (DEV_MODE=true)")
    print_separator()
    
    os.environ["LIBRECHAT_USER_ROLE"] = "USER"
    os.environ["LIBRECHAT_USER_EMAIL"] = "test@example.com"
    os.environ["DEV_MODE"] = "true"  # 开发模式
    
    checker = PermissionChecker()
    
    print(f"\n⚠️  开发模式已启用 - 所有权限检查将被跳过")
    print(f"用户角色: {checker.get_user_role().value}")
    print(f"\n测试工具权限:")
    
    test_tools = [
        "query_drilling_data",
        "add_drilling_record",
        "delete_drilling_record",
        "export_all_data"
    ]
    
    for tool in test_tools:
        has_perm, error = checker.has_permission(tool)
        status = "✅" if has_perm else "❌"
        print(f"  {status} {tool} - {has_perm}")
    
    print()


def compare_roles():
    """对比不同角色的权限"""
    print_separator()
    print("📊 角色权限对比表")
    print_separator()
    
    roles = ["ADMIN", "USER", "GUEST"]
    
    # 获取所有工具
    all_tools = list(TOOL_PERMISSIONS.keys())
    
    # 打印表头
    print(f"\n{'工具名称':<30} | {'ADMIN':<8} | {'USER':<8} | {'GUEST':<8}")
    print("-" * 70)
    
    # 为每个工具测试所有角色
    for tool in all_tools:
        tool_name = tool[:28] if len(tool) > 28 else tool
        row = f"{tool_name:<30}"
        
        for role in roles:
            os.environ["LIBRECHAT_USER_ROLE"] = role
            os.environ["DEV_MODE"] = "false"
            checker = PermissionChecker()
            
            has_perm, _ = checker.has_permission(tool)
            symbol = "✅" if has_perm else "❌"
            row += f" | {symbol:<8}"
        
        print(row)
    
    print()


def interactive_test():
    """交互式测试"""
    print_separator()
    print("🎮 交互式权限测试")
    print_separator()
    
    print("\n请选择角色:")
    print("  1. ADMIN")
    print("  2. USER")
    print("  3. GUEST")
    
    choice = input("\n输入选项 (1-3): ").strip()
    
    role_map = {"1": "ADMIN", "2": "USER", "3": "GUEST"}
    role = role_map.get(choice, "USER")
    
    email = input(f"输入邮箱 (默认: {role.lower()}@example.com): ").strip()
    if not email:
        email = f"{role.lower()}@example.com"
    
    test_role_permissions(role, email)


def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "all":
            test_all_roles()
        elif command == "dev":
            test_dev_mode()
        elif command == "compare":
            compare_roles()
        elif command == "interactive":
            interactive_test()
        elif command in ["admin", "user", "guest"]:
            role = command.upper()
            email = f"{command}@oilfield.com"
            test_role_permissions(role, email)
        else:
            print(f"未知命令: {command}")
            print_usage()
    else:
        # 默认运行所有测试
        test_all_roles()
        print("\n")
        compare_roles()


def print_usage():
    """打印使用说明"""
    print("\n用法:")
    print("  python test_permissions_quick.py [命令]")
    print("\n可用命令:")
    print("  all         - 测试所有角色 (默认)")
    print("  admin       - 只测试ADMIN角色")
    print("  user        - 只测试USER角色")
    print("  guest       - 只测试GUEST角色")
    print("  dev         - 测试开发模式")
    print("  compare     - 对比所有角色权限")
    print("  interactive - 交互式测试")
    print("\n示例:")
    print("  python test_permissions_quick.py all")
    print("  python test_permissions_quick.py admin")
    print("  python test_permissions_quick.py compare")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 测试中断\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
