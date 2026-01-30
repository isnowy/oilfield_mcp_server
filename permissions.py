"""
MCP Server权限检查模块
用于检查LibreChat用户的角色和权限
"""
import os
import logging
from enum import Enum
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"

class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

# 角色权限映射 - 定义每个角色拥有哪些权限
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.ADMIN
    ],
    UserRole.USER: [
        Permission.READ,
        Permission.WRITE
    ],
    UserRole.GUEST: [
        Permission.READ
    ]
}

# 工具权限要求映射 - 定义每个工具需要哪些权限
TOOL_PERMISSIONS: Dict[str, List[Permission]] = {
    # 查询类工具 - 只需读权限
    "query_drilling_data": [Permission.READ],
    "query_well_info": [Permission.READ],
    "search_wells": [Permission.READ],
    "get_well_statistics": [Permission.READ],
    
    # 写入类工具 - 需要写权限
    "add_drilling_record": [Permission.WRITE],
    "update_drilling_data": [Permission.WRITE],
    "create_well": [Permission.WRITE],
    "update_well_info": [Permission.WRITE],
    
    # 删除类工具 - 需要删除权限(仅管理员)
    "delete_drilling_record": [Permission.DELETE],
    "delete_well": [Permission.DELETE],
    "archive_well": [Permission.DELETE],
    
    # 管理类工具 - 需要管理员权限
    "reset_database": [Permission.ADMIN],
    "export_all_data": [Permission.ADMIN],
    "import_data": [Permission.ADMIN],
    "manage_users": [Permission.ADMIN],
}

class PermissionChecker:
    """权限检查器 - 检查用户是否有权限执行指定操作"""
    
    def __init__(self):
        """初始化权限检查器"""
        self.dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
        if self.dev_mode:
            logger.warning("⚠️  DEV_MODE is enabled - permission checks will be skipped!")
    
    def get_user_context(self) -> dict:
        """
        从环境变量获取用户上下文信息
        
        Returns:
            包含用户信息的字典
        """
        return {
            "user_id": os.getenv("LIBRECHAT_USER_ID", "unknown"),
            "email": os.getenv("LIBRECHAT_USER_EMAIL", "unknown@example.com"),
            "role": os.getenv("LIBRECHAT_USER_ROLE", "USER"),
            "username": os.getenv("LIBRECHAT_USER_USERNAME", "unknown"),
            "email_verified": os.getenv("LIBRECHAT_USER_EMAILVERIFIED", "false"),
        }
    
    def get_user_role(self) -> UserRole:
        """
        获取当前用户的角色
        
        Returns:
            UserRole枚举值
        """
        role_str = os.getenv("LIBRECHAT_USER_ROLE", "USER").upper()
        try:
            return UserRole[role_str]
        except KeyError:
            logger.warning(f"Unknown role: {role_str}, defaulting to USER")
            return UserRole.USER
    
    def has_permission(self, tool_name: str) -> tuple[bool, Optional[str]]:
        """
        检查用户是否有权限执行指定工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            (has_permission, error_message) 元组
            - has_permission: True表示有权限,False表示无权限
            - error_message: 如果无权限,返回错误信息;有权限则为None
        """
        # 开发模式跳过权限检查
        if self.dev_mode:
            logger.info(f"[DEV MODE] ⚠️  Skipping permission check for tool: {tool_name}")
            return True, None
        
        user_context = self.get_user_context()
        user_role = self.get_user_role()
        
        logger.info(f"🔍 Permission check - User: {user_context['email']}, "
                   f"Role: {user_role.value}, Tool: {tool_name}")
        
        # 检查工具是否配置了权限要求
        required_permissions = TOOL_PERMISSIONS.get(tool_name, [])
        if not required_permissions:
            logger.warning(f"⚠️  No permission mapping for tool: {tool_name}, allowing by default")
            return True, None  # 未配置权限的工具默认允许
        
        # 获取用户角色的权限列表
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        
        # 检查用户是否拥有所有必需的权限
        missing_permissions = []
        for required_perm in required_permissions:
            if required_perm not in user_permissions:
                missing_permissions.append(required_perm.value)
        
        if missing_permissions:
            error_msg = (
                f"权限不足: 用户角色 '{user_role.value}' 缺少以下权限: {', '.join(missing_permissions)}。"
                f"工具 '{tool_name}' 需要这些权限才能执行。"
            )
            logger.warning(f"❌ Permission denied - {error_msg}")
            return False, error_msg
        
        logger.info(f"✅ Permission granted for {user_context['email']} to use {tool_name}")
        return True, None
    
    def check_specific_permission(self, permission: Permission) -> tuple[bool, Optional[str]]:
        """
        检查用户是否拥有特定权限
        
        Args:
            permission: 要检查的权限
            
        Returns:
            (has_permission, error_message) 元组
        """
        if self.dev_mode:
            return True, None
        
        user_role = self.get_user_role()
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        
        if permission not in user_permissions:
            error_msg = f"用户角色 '{user_role.value}' 没有 '{permission.value}' 权限"
            return False, error_msg
        
        return True, None
    
    def check_query_permission(self) -> tuple[bool, Optional[str]]:
        """
        检查查询权限(READ权限)
        
        Returns:
            (has_permission, error_message) 元组
        """
        return self.check_specific_permission(Permission.READ)
    
    def check_write_permission(self) -> tuple[bool, Optional[str]]:
        """
        检查写入权限(WRITE权限)
        
        Returns:
            (has_permission, error_message) 元组
        """
        return self.check_specific_permission(Permission.WRITE)
    
    def check_delete_permission(self) -> tuple[bool, Optional[str]]:
        """
        检查删除权限(DELETE权限)
        
        Returns:
            (has_permission, error_message) 元组
        """
        return self.check_specific_permission(Permission.DELETE)
    
    def check_admin_permission(self) -> tuple[bool, Optional[str]]:
        """
        检查管理员权限(ADMIN权限)
        
        Returns:
            (has_permission, error_message) 元组
        """
        return self.check_specific_permission(Permission.ADMIN)
    
    def is_admin(self) -> bool:
        """
        检查当前用户是否为管理员
        
        Returns:
            True表示是管理员,False表示不是
        """
        if self.dev_mode:
            return True
        return self.get_user_role() == UserRole.ADMIN
    
    def log_access(self, tool_name: str, success: bool, error: Optional[str] = None):
        """
        记录访问日志
        
        Args:
            tool_name: 工具名称
            success: 操作是否成功
            error: 错误信息(如果有)
        """
        user_context = self.get_user_context()
        status_emoji = "✅" if success else "❌"
        log_msg = (
            f"{status_emoji} Access Log - "
            f"User: {user_context['email']}, "
            f"Role: {user_context['role']}, "
            f"Tool: {tool_name}, "
            f"Success: {success}"
        )
        if error:
            log_msg += f", Error: {error}"
        
        if success:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)
    
    def get_allowed_tools(self) -> List[str]:
        """
        获取当前用户允许使用的所有工具列表
        
        Returns:
            允许使用的工具名称列表
        """
        if self.dev_mode:
            return list(TOOL_PERMISSIONS.keys())
        
        user_role = self.get_user_role()
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        
        allowed_tools = []
        for tool_name, required_perms in TOOL_PERMISSIONS.items():
            # 检查用户是否拥有该工具所需的所有权限
            if all(perm in user_permissions for perm in required_perms):
                allowed_tools.append(tool_name)
        
        return allowed_tools
    
    def get_permission_summary(self) -> dict:
        """
        获取当前用户的权限摘要
        
        Returns:
            包含权限信息的字典
        """
        user_context = self.get_user_context()
        user_role = self.get_user_role()
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        allowed_tools = self.get_allowed_tools()
        
        return {
            "user": user_context,
            "role": user_role.value,
            "permissions": [p.value for p in user_permissions],
            "allowed_tools": allowed_tools,
            "total_tools": len(TOOL_PERMISSIONS),
            "dev_mode": self.dev_mode
        }


# 便捷函数 - 创建全局权限检查器实例
_global_checker: Optional[PermissionChecker] = None

def get_permission_checker() -> PermissionChecker:
    """
    获取全局权限检查器实例(单例模式)
    
    Returns:
        PermissionChecker实例
    """
    global _global_checker
    if _global_checker is None:
        _global_checker = PermissionChecker()
    return _global_checker


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("MCP Server 权限模块测试")
    print("=" * 60)
    
    # 设置测试环境变量
    os.environ["LIBRECHAT_USER_ROLE"] = "USER"
    os.environ["LIBRECHAT_USER_EMAIL"] = "test@example.com"
    os.environ["DEV_MODE"] = "false"
    
    checker = get_permission_checker()
    
    print("\n用户上下文:")
    print(checker.get_user_context())
    
    print("\n权限摘要:")
    summary = checker.get_permission_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n工具权限测试:")
    test_tools = [
        "query_drilling_data",
        "add_drilling_record",
        "delete_drilling_record"
    ]
    
    for tool in test_tools:
        has_perm, error = checker.has_permission(tool)
        status = "✅ 允许" if has_perm else "❌ 拒绝"
        print(f"  {status} - {tool}")
        if error:
            print(f"    原因: {error}")
