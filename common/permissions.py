"""
权限控制模块
提供基于角色的访问控制（RBAC）功能
"""
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# 开发模式配置
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ["true", "1", "yes"]

# 权限配置
USER_PERMISSIONS = {
    "ADMIN": {
        "wells": "*",
        "blocks": "*",
        "role": "admin",
        "description": "管理员 - 完全访问权限"
    },
    "ENGINEER": {
        "wells": ["ZT-102", "ZT-105"],
        "blocks": ["Block-A"],
        "role": "engineer",
        "description": "工程师 - Block-A的部分井 + 公共数据"
    },
    "VIEWER": {
        "wells": ["ZT-102"],
        "blocks": ["Block-A"],
        "role": "viewer",
        "description": "查看者 - ZT-102只读 + 公共数据"
    },
    "USER": {
        "wells": [],
        "blocks": [],
        "role": "user",
        "description": "普通用户 - 仅公共数据"
    },
    "GUEST": {
        "wells": [],
        "blocks": [],
        "role": "guest",
        "description": "访客 - 仅公共数据"
    }
}

class PermissionService:
    """权限管理服务"""
    
    @staticmethod
    def check_well_access(user_role: str, well_id: str) -> bool:
        """检查用户是否有权限访问特定井"""
        if DEV_MODE:
            return True
        
        perms = USER_PERMISSIONS.get(user_role.upper(), USER_PERMISSIONS["GUEST"])
        
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
        
        perms = USER_PERMISSIONS.get(user_role.upper(), USER_PERMISSIONS["GUEST"])
        
        if perms["role"] == "admin":
            return True
        
        if perms["blocks"] == "*" or block_name in perms["blocks"]:
            return True
        
        return False
    
    @staticmethod
    def get_accessible_wells(user_role: str) -> List[str]:
        """获取用户可访问的所有井号"""
        if DEV_MODE:
            return "*"
        
        perms = USER_PERMISSIONS.get(user_role.upper(), USER_PERMISSIONS["GUEST"])
        if perms["wells"] == "*":
            return "*"
        return perms["wells"]

def filter_wells_by_permission(wells: List[Dict], user_role: str, user_id: str = "", user_email: str = "") -> List[Dict]:
    """
    根据用户角色过滤井数据
    
    Args:
        wells: 井数据列表
        user_role: 用户角色
        user_id: 用户ID
        user_email: 用户邮箱
        
    Returns:
        过滤后的井数据列表
    """
    if DEV_MODE:
        logger.info(f"🔓 开发模式：用户 {user_email} ({user_role}) 访问所有数据")
        return wells
    
    role_upper = user_role.upper() if user_role else "GUEST"
    
    # ADMIN角色：查看所有井
    if role_upper == "ADMIN":
        logger.info(f"✅ ADMIN用户 {user_email} 访问所有 {len(wells)} 口井")
        return wells
    
    # 获取角色权限配置
    perms = USER_PERMISSIONS.get(role_upper, USER_PERMISSIONS["GUEST"])
    allowed_wells = perms.get("wells", [])
    
    # 如果配置了特定的井列表
    if allowed_wells == "*":
        logger.info(f"✅ {role_upper}用户 {user_email} 访问所有 {len(wells)} 口井")
        return wells
    elif allowed_wells:
        # 过滤出权限列表中的井
        filtered = [
            well for well in wells
            if well.get('well_name') in allowed_wells or well.get('id') in allowed_wells
        ]
        logger.info(f"🔒 {role_upper}用户 {user_email} 访问 {len(filtered)}/{len(wells)} 口井（权限配置）")
        return filtered
    else:
        # 普通USER或GUEST：可以看所有公共数据
        logger.info(f"✅ {role_upper}用户 {user_email} 访问所有公共数据 {len(wells)} 口井")
        return wells
