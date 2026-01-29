#!/usr/bin/env python3
"""
MCP Server环境变量诊断脚本
用于排查LibreChat是否正确传递用户上下文
"""
import os
import sys

print("=" * 70)
print("🔍 MCP Server 环境变量诊断")
print("=" * 70)

# 需要检查的环境变量
env_vars = {
    "LIBRECHAT_USER_ID": "用户ID",
    "LIBRECHAT_USER_EMAIL": "用户邮箱",
    "LIBRECHAT_USER_ROLE": "用户角色",
    "LIBRECHAT_USER_USERNAME": "用户名",
    "LIBRECHAT_USER_EMAILVERIFIED": "邮箱验证状态",
    "DEV_MODE": "开发模式",
    "DATABASE_URL": "数据库URL",
    "LOG_LEVEL": "日志级别",
}

print("\n📋 环境变量检查:")
print("-" * 70)

issues = []
for var_name, description in env_vars.items():
    value = os.getenv(var_name)
    
    if value is None:
        status = "❌ 未设置"
        issues.append(f"{var_name} 未设置")
    elif value.startswith("{{") and value.endswith("}}"):
        status = f"⚠️  占位符未替换: {value}"
        issues.append(f"{var_name} 占位符未被LibreChat替换")
    elif value == "":
        status = "⚠️  空值"
        issues.append(f"{var_name} 为空")
    else:
        status = f"✅ {value}"
    
    print(f"{var_name:<35} ({description:<12}): {status}")

print("\n" + "=" * 70)

if issues:
    print("❌ 发现问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    print("\n💡 解决方案:")
    
    if any("占位符未被LibreChat替换" in issue for issue in issues):
        print("\n  🔧 占位符未替换的解决方法:")
        print("     1. 确认LibreChat已重启")
        print("        cd d:\\work\\librechat")
        print("        docker-compose restart")
        print("        # 或在开发模式下重启进程")
        print()
        print("     2. 清除浏览器缓存并重新登录")
        print()
        print("     3. 检查librechat.yaml配置格式:")
        print("        env:")
        print('          LIBRECHAT_USER_ROLE: "{{LIBRECHAT_USER_ROLE}}"')
        print("        (注意要加引号)")
        print()
        print("     4. 确认LibreChat版本支持MCP占位符 (需要v0.8+)")
    
    if any("未设置" in issue for issue in issues):
        print("\n  🔧 环境变量未设置的解决方法:")
        print("     检查librechat.yaml中的mcpServers配置")
        print("     确保env部分包含所有必需的变量")
    
    print("\n" + "=" * 70)
    sys.exit(1)
else:
    print("✅ 所有环境变量配置正确!")
    
    # 显示权限检查结果
    from permissions import PermissionChecker
    
    checker = PermissionChecker()
    summary = checker.get_permission_summary()
    
    print("\n📊 权限配置:")
    print(f"  用户: {summary['user']['email']}")
    print(f"  角色: {summary['role']}")
    print(f"  权限: {', '.join(summary['permissions'])}")
    print(f"  可用工具: {len(summary['allowed_tools'])}/{summary['total_tools']}")
    print(f"  开发模式: {summary['dev_mode']}")
    
    print("\n✅ 环境变量和权限配置都正常!")
    print("=" * 70)
    sys.exit(0)
