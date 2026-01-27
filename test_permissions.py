"""
权限模式测试脚本
用于验证开发模式和生产模式的权限控制是否正常工作
"""

import os
import sys
import io

# 设置 Windows 控制台 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置开发模式（可通过环境变量修改）
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ["true", "1", "yes"]

# 模拟权限配置
USER_PERMISSIONS = {
    "admin": {"wells": "*", "blocks": "*", "role": "admin"},
    "engineer": {"wells": ["ZT-102", "ZT-105"], "blocks": ["Block-A"], "role": "engineer"},
    "viewer": {"wells": ["ZT-102"], "blocks": ["Block-A"], "role": "viewer"},
    "default": {"wells": [], "blocks": [], "role": "guest"}
}

class PermissionService:
    """权限管理服务"""
    
    @staticmethod
    def check_well_access(user_role: str, well_id: str) -> bool:
        """检查用户是否有权限访问特定井"""
        if DEV_MODE:
            return True
        
        perms = USER_PERMISSIONS.get(user_role, USER_PERMISSIONS["default"])
        if perms["role"] == "admin":
            return True
        if perms["wells"] == "*" or well_id in perms["wells"]:
            return True
        return False
    
    @staticmethod
    def check_block_access(user_role: str, block_name: str) -> bool:
        """检查用户是否有权限访问特定区块"""
        if DEV_MODE:
            return True
        
        perms = USER_PERMISSIONS.get(user_role, USER_PERMISSIONS["default"])
        if perms["role"] == "admin":
            return True
        if perms["blocks"] == "*" or block_name in perms["blocks"]:
            return True
        return False

def test_permissions():
    """测试不同角色的权限"""
    
    print("=" * 70)
    print("🧪 权限模式测试")
    print("=" * 70)
    
    # 显示当前模式
    if DEV_MODE:
        print("\n🔓 当前模式：开发模式 (所有用户拥有全部权限)")
        print("   设置 DEV_MODE=false 可切换到生产模式\n")
    else:
        print("\n🔒 当前模式：生产模式 (严格权限控制)")
        print("   设置 DEV_MODE=true 可切换到开发模式\n")
    
    # 测试用例
    test_cases = [
        ("admin", "ZT-102", "Block-A"),
        ("engineer", "ZT-102", "Block-A"),
        ("engineer", "XY-009", "Block-B"),
        ("viewer", "ZT-102", "Block-A"),
        ("viewer", "ZT-105", "Block-A"),
        ("default", "ZT-102", "Block-A"),
    ]
    
    print("📊 权限测试结果：")
    print("-" * 70)
    print(f"{'角色':<12} {'访问井':<12} {'访问区块':<12} {'井权限':<10} {'区块权限':<10}")
    print("-" * 70)
    
    for role, well, block in test_cases:
        well_access = PermissionService.check_well_access(role, well)
        block_access = PermissionService.check_block_access(role, block)
        
        well_status = "✅ 允许" if well_access else "❌ 拒绝"
        block_status = "✅ 允许" if block_access else "❌ 拒绝"
        
        print(f"{role:<12} {well:<12} {block:<12} {well_status:<10} {block_status:<10}")
    
    print("-" * 70)
    
    # 权限说明
    if not DEV_MODE:
        print("\n📌 生产模式权限说明：")
        for role, perms in USER_PERMISSIONS.items():
            wells = perms['wells'] if perms['wells'] == "*" else ", ".join(perms['wells']) if perms['wells'] else "无"
            blocks = perms['blocks'] if perms['blocks'] == "*" else ", ".join(perms['blocks']) if perms['blocks'] else "无"
            print(f"  • {role:<12} - 井: {wells:<20} 区块: {blocks}")
    
    print("\n" + "=" * 70)
    
    # 给出建议
    if DEV_MODE:
        print("💡 提示：当前为开发模式，适合测试。")
        print("   生产环境请运行：$env:DEV_MODE=\"false\"; python test_permissions.py")
    else:
        print("💡 提示：当前为生产模式，权限严格控制。")
        print("   开发测试可运行：$env:DEV_MODE=\"true\"; python test_permissions.py")
    
    print("=" * 70)

if __name__ == "__main__":
    test_permissions()
