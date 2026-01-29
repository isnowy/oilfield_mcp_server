"""
油田钻井数据MCP Server - 带权限控制示例
演示如何集成LibreChat用户角色权限
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# 导入权限检查模块
from permissions import get_permission_checker, PermissionChecker

# 配置日志
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化MCP服务器
app = Server("oilfield-data")

# 初始化权限检查器
permission_checker: PermissionChecker = get_permission_checker()


@app.list_tools()
async def list_tools() -> List[Tool]:
    """
    列出所有可用工具
    注意:工具列表对所有用户可见,但执行时会检查权限
    """
    return [
        # ========== 查询类工具 (需要READ权限) ==========
        Tool(
            name="query_drilling_data",
            description="查询钻井数据 [需要READ权限]",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_name": {
                        "type": "string",
                        "description": "井名"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "开始日期 (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "结束日期 (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    }
                },
                "required": ["well_name"]
            }
        ),
        
        Tool(
            name="query_well_info",
            description="查询油井基本信息 [需要READ权限]",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_name": {
                        "type": "string",
                        "description": "井名"
                    }
                },
                "required": ["well_name"]
            }
        ),
        
        Tool(
            name="search_wells",
            description="搜索油井列表 [需要READ权限]",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                }
            }
        ),
        
        Tool(
            name="get_well_statistics",
            description="获取油井统计信息 [需要READ权限]",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_name": {
                        "type": "string",
                        "description": "井名(可选,不填则统计所有井)"
                    }
                }
            }
        ),
        
        # ========== 写入类工具 (需要WRITE权限) ==========
        Tool(
            name="add_drilling_record",
            description="添加钻井记录 [需要WRITE权限]",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_name": {
                        "type": "string",
                        "description": "井名"
                    },
                    "depth": {
                        "type": "number",
                        "description": "深度(米)",
                        "minimum": 0
                    },
                    "date": {
                        "type": "string",
                        "description": "日期 (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    },
                    "notes": {
                        "type": "string",
                        "description": "备注信息"
                    }
                },
                "required": ["well_name", "depth", "date"]
            }
        ),
        
        Tool(
            name="update_drilling_data",
            description="更新钻井数据 [需要WRITE权限]",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "integer",
                        "description": "记录ID"
                    },
                    "depth": {
                        "type": "number",
                        "description": "新深度(米)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "新备注"
                    }
                },
                "required": ["record_id"]
            }
        ),
        
        Tool(
            name="create_well",
            description="创建新油井 [需要WRITE权限]",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_name": {
                        "type": "string",
                        "description": "井名"
                    },
                    "location": {
                        "type": "string",
                        "description": "位置"
                    },
                    "type": {
                        "type": "string",
                        "description": "井类型",
                        "enum": ["exploration", "production", "injection"]
                    }
                },
                "required": ["well_name", "location", "type"]
            }
        ),
        
        # ========== 删除类工具 (需要DELETE权限 - 仅管理员) ==========
        Tool(
            name="delete_drilling_record",
            description="删除钻井记录 [需要DELETE权限 - 仅管理员]",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "integer",
                        "description": "要删除的记录ID"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "确认删除",
                        "default": False
                    }
                },
                "required": ["record_id", "confirm"]
            }
        ),
        
        Tool(
            name="delete_well",
            description="删除油井及相关所有数据 [需要DELETE权限 - 仅管理员]",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_name": {
                        "type": "string",
                        "description": "要删除的井名"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "确认删除",
                        "default": False
                    }
                },
                "required": ["well_name", "confirm"]
            }
        ),
        
        # ========== 管理类工具 (需要ADMIN权限 - 仅管理员) ==========
        Tool(
            name="export_all_data",
            description="导出所有数据 [需要ADMIN权限 - 仅管理员]",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "导出格式",
                        "enum": ["json", "csv", "excel"],
                        "default": "json"
                    }
                }
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """
    执行工具调用 - 带权限检查
    
    Args:
        name: 工具名称
        arguments: 工具参数
        
    Returns:
        工具执行结果
    """
    logger.info(f"📞 Tool call request: {name} with args: {arguments}")
    
    # ========== 权限检查 ==========
    has_permission, error_message = permission_checker.has_permission(name)
    
    # 记录访问日志
    permission_checker.log_access(name, has_permission, error_message)
    
    if not has_permission:
        logger.warning(f"❌ Permission denied for tool: {name}")
        return [TextContent(
            type="text",
            text=f"❌ **权限被拒绝**\n\n{error_message}\n\n"
                 f"当前用户角色: {permission_checker.get_user_role().value}\n"
                 f"用户邮箱: {permission_checker.get_user_context()['email']}"
        )]
    
    # ========== 执行工具逻辑 ==========
    try:
        # 根据工具名称路由到相应的处理函数
        if name == "query_drilling_data":
            result = await query_drilling_data(arguments)
        elif name == "query_well_info":
            result = await query_well_info(arguments)
        elif name == "search_wells":
            result = await search_wells(arguments)
        elif name == "get_well_statistics":
            result = await get_well_statistics(arguments)
        elif name == "add_drilling_record":
            result = await add_drilling_record(arguments)
        elif name == "update_drilling_data":
            result = await update_drilling_data(arguments)
        elif name == "create_well":
            result = await create_well(arguments)
        elif name == "delete_drilling_record":
            result = await delete_drilling_record(arguments)
        elif name == "delete_well":
            result = await delete_well(arguments)
        elif name == "export_all_data":
            result = await export_all_data(arguments)
        else:
            result = f"❌ 未知工具: {name}"
        
        # 记录成功的访问
        permission_checker.log_access(name, True)
        return [TextContent(type="text", text=result)]
    
    except Exception as e:
        error_msg = f"执行工具 {name} 时出错: {str(e)}"
        logger.error(error_msg, exc_info=True)
        permission_checker.log_access(name, False, str(e))
        return [TextContent(
            type="text",
            text=f"❌ **执行失败**\n\n{error_msg}"
        )]


# ========== 查询类工具实现 ==========

async def query_drilling_data(arguments: dict) -> str:
    """查询钻井数据"""
    user_context = permission_checker.get_user_context()
    logger.info(f"🔍 Querying drilling data for user: {user_context['email']}")
    
    well_name = arguments.get("well_name")
    date_from = arguments.get("date_from", "2024-01-01")
    date_to = arguments.get("date_to", datetime.now().strftime("%Y-%m-%d"))
    
    # TODO: 实际查询数据库
    return f"""✅ **钻井数据查询成功**

**井名:** {well_name}
**时间范围:** {date_from} 至 {date_to}
**查询用户:** {user_context['email']}

**模拟数据:**
- 2024-01-15: 深度 1250m, 正常钻进
- 2024-01-20: 深度 1380m, 遇到硬层
- 2024-01-25: 深度 1520m, 正常钻进
"""


async def query_well_info(arguments: dict) -> str:
    """查询油井信息"""
    well_name = arguments.get("well_name")
    
    return f"""✅ **油井信息**

**井名:** {well_name}
**类型:** 生产井
**位置:** 东经118.5°, 北纬35.2°
**状态:** 正常生产
**开钻日期:** 2024-01-01
**当前深度:** 1520m
"""


async def search_wells(arguments: dict) -> str:
    """搜索油井"""
    keyword = arguments.get("keyword", "")
    limit = arguments.get("limit", 10)
    
    return f"""✅ **搜索结果** (关键词: {keyword})

找到 3 口井:
1. **井A-001** - 生产井 - 正常生产
2. **井A-002** - 探测井 - 钻探中
3. **井A-003** - 注水井 - 维护中

(显示前 {limit} 条结果)
"""


async def get_well_statistics(arguments: dict) -> str:
    """获取统计信息"""
    well_name = arguments.get("well_name")
    
    if well_name:
        return f"""✅ **{well_name} 统计信息**

**总记录数:** 125
**平均深度:** 1350m
**最大深度:** 1520m
**记录时间跨度:** 2024-01-01 至今
"""
    else:
        return """✅ **所有油井统计信息**

**总井数:** 48
**生产井:** 32
**探测井:** 10
**注水井:** 6
**平均深度:** 1420m
"""


# ========== 写入类工具实现 ==========

async def add_drilling_record(arguments: dict) -> str:
    """添加钻井记录"""
    user_context = permission_checker.get_user_context()
    logger.info(f"✏️  Adding drilling record for user: {user_context['email']}")
    
    well_name = arguments.get("well_name")
    depth = arguments.get("depth")
    date = arguments.get("date")
    notes = arguments.get("notes", "")
    
    # TODO: 实际写入数据库
    return f"""✅ **记录添加成功**

**井名:** {well_name}
**深度:** {depth}m
**日期:** {date}
**备注:** {notes}
**操作人:** {user_context['email']}
**记录ID:** 12345 (模拟)
"""


async def update_drilling_data(arguments: dict) -> str:
    """更新钻井数据"""
    record_id = arguments.get("record_id")
    depth = arguments.get("depth")
    notes = arguments.get("notes")
    
    return f"""✅ **数据更新成功**

**记录ID:** {record_id}
**新深度:** {depth}m (如有)
**新备注:** {notes} (如有)
**更新时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""


async def create_well(arguments: dict) -> str:
    """创建新油井"""
    well_name = arguments.get("well_name")
    location = arguments.get("location")
    well_type = arguments.get("type")
    
    return f"""✅ **油井创建成功**

**井名:** {well_name}
**位置:** {location}
**类型:** {well_type}
**创建时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**状态:** 已创建,待开钻
"""


# ========== 删除类工具实现 (仅管理员) ==========

async def delete_drilling_record(arguments: dict) -> str:
    """删除钻井记录"""
    record_id = arguments.get("record_id")
    confirm = arguments.get("confirm", False)
    
    if not confirm:
        return f"""⚠️  **需要确认删除**

**记录ID:** {record_id}

请在参数中设置 `confirm: true` 来确认删除操作。
**警告:** 此操作不可逆!
"""
    
    # TODO: 实际删除记录
    return f"""✅ **记录删除成功**

**记录ID:** {record_id}
**删除时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**操作人:** {permission_checker.get_user_context()['email']}
"""


async def delete_well(arguments: dict) -> str:
    """删除油井"""
    well_name = arguments.get("well_name")
    confirm = arguments.get("confirm", False)
    
    if not confirm:
        return f"""⚠️  **需要确认删除**

**井名:** {well_name}

请在参数中设置 `confirm: true` 来确认删除操作。
**警告:** 此操作将删除该井的所有相关数据,不可逆!
"""
    
    return f"""✅ **油井删除成功**

**井名:** {well_name}
**删除时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**操作人:** {permission_checker.get_user_context()['email']}
"""


# ========== 管理类工具实现 (仅管理员) ==========

async def export_all_data(arguments: dict) -> str:
    """导出所有数据"""
    format_type = arguments.get("format", "json")
    
    return f"""✅ **数据导出成功**

**格式:** {format_type}
**文件名:** oilfield_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{format_type}
**总记录数:** 1250 (模拟)
**文件大小:** 2.5 MB (模拟)
**导出时间:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**操作人:** {permission_checker.get_user_context()['email']}
"""


async def main():
    """启动MCP服务器"""
    logger.info("=" * 60)
    logger.info("🚀 Starting Oilfield MCP Server with Permission Control")
    logger.info("=" * 60)
    
    # 🔍 调试: 打印所有环境变量
    logger.info("🔍 Environment Variables Debug:")
    for key in ['LIBRECHAT_USER_ID', 'LIBRECHAT_USER_EMAIL', 'LIBRECHAT_USER_ROLE', 
                'LIBRECHAT_USER_USERNAME', 'DEV_MODE']:
        value = os.getenv(key, 'NOT_SET')
        logger.info(f"   {key} = {value}")
    
    # 显示配置信息
    summary = permission_checker.get_permission_summary()
    logger.info(f"📊 Permission Summary:")
    logger.info(f"   User: {summary['user']['email']}")
    logger.info(f"   Role: {summary['role']}")
    logger.info(f"   Permissions: {', '.join(summary['permissions'])}")
    logger.info(f"   Allowed Tools: {len(summary['allowed_tools'])}/{summary['total_tools']}")
    logger.info(f"   Dev Mode: {summary['dev_mode']}")
    
    if summary['dev_mode']:
        logger.warning("⚠️  DEV_MODE is enabled - all permission checks will be bypassed!")
    else:
        logger.info("✅ Production mode - permission checks enabled")
    
    logger.info("=" * 60)
    
    # 启动stdio服务器
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
