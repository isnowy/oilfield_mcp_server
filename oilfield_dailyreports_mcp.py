"""
油井日报系统 MCP Server
提供钻井工程日报、钻前工程日报、重点井试采日报查询功能
"""
from mcp.server import Server
from mcp.server.sse import SseServerTransport  
from mcp.types import Tool, TextContent
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
import os
import json
import logging
import pandas as pd
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 导入共享模块
from common.db import get_db_connection, test_db_connection, execute_write, DB_CONFIG
from common.permissions import PermissionService, DEV_MODE
from common.utils import df_to_markdown
from common.audit import AuditLog

WRITE_ALLOWED_ROLES = {"ADMIN", "ENGINEER"}

# ==========================================
# 日志配置
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OilfieldDailyReportsMCP")

# ==========================================
# 用户上下文管理
# ==========================================

class UserContext(BaseModel):
    """用户上下文信息"""
    role: str = "GUEST"
    email: str = "unknown"
    user_id: str = "unknown"

from contextvars import ContextVar
current_user_context: ContextVar[UserContext] = ContextVar('current_user_context', default=UserContext())

# ==========================================
# MCP Server实例
# ==========================================

mcp_server = Server("oilfield-dailyreports")
sse_transport = SseServerTransport("/sse")

# ==========================================
# FastAPI应用
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 油井日报系统 MCP Server 启动中...")
    logger.info(f"📍 监听地址: http://0.0.0.0:8082")
    logger.info(f"🔒 权限模式: {'开发模式' if DEV_MODE else '生产模式'}")
    logger.info(f"🗄️  数据库: PostgreSQL @ {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    if test_db_connection():
        logger.info("✅ 数据库连接正常")
    else:
        logger.warning("⚠️  数据库连接失败")
    
    yield
    logger.info("👋 MCP Server 关闭")

app = FastAPI(
    title="油井日报系统 MCP Server",
    description="提供钻井工程日报、钻前工程日报、重点井试采日报查询功能",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 健康检查端点
# ==========================================

@app.get("/")
async def root():
    return {
        "service": "油井日报系统 MCP Server",
        "version": "1.1.0",
        "status": "running",
        "tools": 6
    }

@app.get("/health")
async def health_check():
    db_ok = test_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected"
    }

# ==========================================
# SSE Endpoints
# ==========================================

@app.get("/sse")
async def handle_sse_get(request: Request):
    """SSE GET endpoint"""
    logger.info("🌊 SSE GET请求 - 建立连接")
    try:
        return await sse_transport.connect_sse(request, mcp_server)
    except Exception as e:
        logger.error(f"❌ SSE GET错误: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.head("/sse")
async def handle_sse_head():
    return Response(status_code=200)

@app.post("/sse")
async def handle_sse_post(request: Request):
    """SSE POST endpoint"""
    user_role = request.headers.get("x-user-role", "GUEST")
    user_email = request.headers.get("x-user-email", "unknown")
    user_id = request.headers.get("x-user-id", "unknown")
    
    user_ctx = UserContext(role=user_role, email=user_email, user_id=user_id)
    current_user_context.set(user_ctx)
    
    logger.info(f"🌊 SSE POST请求 - 用户: {user_email} ({user_role})")
    
    try:
        body = await request.body()
        body_json = json.loads(body.decode())
        
        method = body_json.get("method")
        
        if method == "initialize":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
                    "serverInfo": {"name": "oilfield-dailyreports", "version": "1.0.0"}
                }
            })
        
        elif method == "notifications/initialized":
            return JSONResponse(content={})
        
        elif method == "tools/list":
            tools_list = await handle_list_tools()
            # 将 Tool 对象转换为可序列化的字典
            serializable_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools_list
            ]
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "result": {"tools": serializable_tools}
            })
        
        elif method == "tools/call":
            params = body_json.get("params", {})
            result = await handle_call_tool(params.get("name"), params.get("arguments", {}))
            # 将 TextContent 对象转换为可序列化的字典
            serializable_result = [
                {"type": item.type, "text": item.text}
                for item in result
            ]
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "result": {"content": serializable_result}
            })
        
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
    
    except Exception as e:
        logger.error(f"❌ SSE POST错误: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)}
        })

# ==========================================
# MCP Server Handlers
# ==========================================

@mcp_server.list_tools()
async def handle_list_tools():
    """列出所有可用工具"""
    return [
        Tool(
            name="get_drilling_daily",
            description="查询钻井工程日报数据 - 支持按井号、日期范围查询钻井作业信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_id": {
                        "type": "string",
                        "description": "井号"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（YYYY-MM-DD格式）"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（YYYY-MM-DD格式）"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "返回结果数量限制"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_drilling_pre_daily",
            description="查询钻前工程日报数据 - 支持按项目、年度、井号查询钻前准备工作信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "勘探项目名称"
                    },
                    "year": {
                        "type": "integer",
                        "description": "实施年度"
                    },
                    "well_id": {
                        "type": "string",
                        "description": "井号"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "返回结果数量限制"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_key_well_daily",
            description="查询重点井试采日报数据 - 支持按井号、日期范围、区块查询，包括生产数据和压力参数",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_id": {
                        "type": "string",
                        "description": "井号"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（YYYY-MM-DD格式）"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（YYYY-MM-DD格式）"
                    },
                    "block": {
                        "type": "string",
                        "description": "区块名称"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "返回结果数量限制"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="save_drilling_daily",
            description="将从文档中提取的钻井工程日报数据保存到数据库。需要 ENGINEER 或 ADMIN 角色权限。",
            inputSchema={
                "type": "object",
                "properties": {
                    "jh": {"type": "string", "description": "井号（必填）"},
                    "rq": {"type": "string", "description": "日期（YYYY-MM-DD，必填）"},
                    "kzrq": {"type": "string", "description": "开钻日期（YYYY-MM-DD）"},
                    "drjs": {"type": "number", "description": "当日井深（米）"},
                    "zjrjc": {"type": "number", "description": "日进尺（米）"},
                    "ztlx": {"type": "string", "description": "钻头类型"},
                    "ztzj": {"type": "number", "description": "钻头直径（毫米）"},
                    "zy": {"type": "number", "description": "钻压（千牛）"},
                    "zs": {"type": "number", "description": "钻速（米/小时）"},
                    "bya": {"type": "number", "description": "泵压（兆帕）"},
                    "bpl": {"type": "number", "description": "排量（升/秒）"},
                    "zjymd": {"type": "number", "description": "钻井液密度（克/立方厘米）"},
                    "zjynd": {"type": "number", "description": "钻井液粘度（秒）"},
                    "czjljsj": {"type": "number", "description": "纯钻进累计时间（小时）"},
                    "brzygz": {"type": "string", "description": "本日主要工作"}
                },
                "required": ["jh", "rq"]
            }
        ),
        Tool(
            name="save_drilling_pre_daily",
            description="将从文档中提取的钻前工程日报数据保存到数据库。需要 ENGINEER 或 ADMIN 角色权限。",
            inputSchema={
                "type": "object",
                "properties": {
                    "jh": {"type": "string", "description": "井号（必填）"},
                    "ktxm": {"type": "string", "description": "勘探项目（必填）"},
                    "ssnd": {"type": "integer", "description": "实施年度"},
                    "jwzysj": {"type": "string", "description": "井位论证时间（YYYY-MM-DD）"},
                    "jwtjxdsj": {"type": "string", "description": "井位条件下达时间（YYYY-MM-DD）"},
                    "jwtclsj": {"type": "string", "description": "井位测量时间（YYYY-MM-DD）"},
                    "tzxdsj": {"type": "string", "description": "投资下达时间（YYYY-MM-DD）"},
                    "kjcgcwsj": {"type": "string", "description": "勘界成果完成时间（YYYY-MM-DD）"},
                    "hpsbsj": {"type": "string", "description": "环评上报时间（YYYY-MM-DD）"},
                    "ydsqsbsj": {"type": "string", "description": "用地申请上报时间（YYYY-MM-DD）"},
                    "gcfatlsj": {"type": "string", "description": "工程方案讨论时间（YYYY-MM-DD）"},
                    "zjdzsjspsj": {"type": "string", "description": "钻井地质设计审批时间（YYYY-MM-DD）"},
                    "zjgcsjspsj": {"type": "string", "description": "钻井工程设计审批时间（YYYY-MM-DD）"},
                    "hpxdsj": {"type": "string", "description": "环评下达时间（YYYY-MM-DD）"},
                    "zdcwsj": {"type": "string", "description": "征地完成时间（YYYY-MM-DD）"},
                    "tlsksj": {"type": "string", "description": "探临开始时间（YYYY-MM-DD）"},
                    "tljssj": {"type": "string", "description": "探临结束时间（YYYY-MM-DD）"},
                    "bjkssj": {"type": "string", "description": "搬家安装开始时间（YYYY-MM-DD）"},
                    "bjjssj": {"type": "string", "description": "搬家安装结束时间（YYYY-MM-DD）"}
                },
                "required": ["jh", "ktxm"]
            }
        ),
        Tool(
            name="save_key_well_daily",
            description="将从文档中提取的重点井试采日报数据保存到数据库。需要 ENGINEER 或 ADMIN 角色权限。",
            inputSchema={
                "type": "object",
                "properties": {
                    "jh": {"type": "string", "description": "井号（必填）"},
                    "rq": {"type": "string", "description": "日期（YYYY-MM-DD，必填）"},
                    "qk": {"type": "string", "description": "区块"},
                    "cw": {"type": "string", "description": "层位"},
                    "cxh": {"type": "string", "description": "层序号"},
                    "djsd1": {"type": "number", "description": "顶界深度1（米）"},
                    "djsd2": {"type": "number", "description": "底界深度2（米）"},
                    "zt": {"type": "string", "description": "状态"},
                    "cyfs": {"type": "string", "description": "采油方式"},
                    "yz": {"type": "string", "description": "油嘴"},
                    "gzsj": {"type": "string", "description": "工作时间"},
                    "gzzd": {"type": "string", "description": "工作制度"},
                    "rcql": {"type": "number", "description": "日产气量（万方）"},
                    "hs": {"type": "number", "description": "含水（%）"},
                    "yysx": {"type": "number", "description": "油压上限（兆帕）"},
                    "yyxx": {"type": "number", "description": "油压下限（兆帕）"},
                    "tysx": {"type": "number", "description": "套压上限（兆帕）"},
                    "tyxx": {"type": "number", "description": "套压下限（兆帕）"},
                    "hysx": {"type": "number", "description": "回压上限（兆帕）"},
                    "hyxx": {"type": "number", "description": "回压下限（兆帕）"},
                    "d_ly": {"type": "number", "description": "流压"},
                    "d_jy": {"type": "number", "description": "静压"},
                    "d_bz": {"type": "string", "description": "施工内容/备注"}
                },
                "required": ["jh", "rq"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """处理工具调用"""
    logger.info(f"🔧 工具调用: {name}")
    
    user_ctx = current_user_context.get()
    user_role = user_ctx.role
    user_id = user_ctx.user_id
    user_email = user_ctx.email
    
    try:
        result = None
        
        if name == "get_drilling_daily":
            result = get_drilling_daily(
                well_id=arguments.get('well_id', ''),
                start_date=arguments.get('start_date', ''),
                end_date=arguments.get('end_date', ''),
                limit=arguments.get('limit', 100),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_drilling_pre_daily":
            result = get_drilling_pre_daily(
                project=arguments.get('project', ''),
                year=arguments.get('year'),
                well_id=arguments.get('well_id', ''),
                limit=arguments.get('limit', 50),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_key_well_daily":
            result = get_key_well_daily(
                well_id=arguments.get('well_id', ''),
                start_date=arguments.get('start_date', ''),
                end_date=arguments.get('end_date', ''),
                block=arguments.get('block', ''),
                limit=arguments.get('limit', 100),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "save_drilling_daily":
            result = save_drilling_daily(
                data=arguments,
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "save_drilling_pre_daily":
            result = save_drilling_pre_daily(
                data=arguments,
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "save_key_well_daily":
            result = save_key_well_daily(
                data=arguments,
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        else:
            raise ValueError(f"未知工具: {name}")
        
        logger.info(f"✅ 工具执行成功: {name}")
        return [TextContent(type="text", text=result)]
    
    except Exception as e:
        logger.error(f"❌ 工具执行失败: {name} - {str(e)}")
        return [TextContent(type="text", text=f"⚠️ 执行错误: {str(e)}")]

# ==========================================
# 业务逻辑函数
# ==========================================

@AuditLog.trace("get_drilling_daily")
def get_drilling_daily(well_id: str = "", start_date: str = "", end_date: str = "", limit: int = 100, 
                       user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """查询钻井工程日报数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM drilling_daily WHERE is_deleted = false"
        params = []
        
        # 井号过滤
        if well_id:
            if not PermissionService.check_well_access(user_role, well_id):
                return f"🚫 权限拒绝：无权访问井号 {well_id} 的日报数据。"
            query += " AND jh = %s"
            params.append(well_id)
        
        # 日期范围过滤
        if start_date:
            query += " AND rq >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND rq <= %s"
            params.append(end_date)
        
        query += " ORDER BY rq DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            well_filter = f"井号 '{well_id}'" if well_id else ""
            date_filter = f"日期 {start_date} 到 {end_date}" if start_date or end_date else ""
            filter_str = " & ".join([f for f in [well_filter, date_filter] if f])
            return f"❌ 未找到匹配条件的钻井日报数据。（{filter_str}）"
        
        # 格式化输出
        data = []
        for row in results:
            data.append({
                "日期": str(row['rq']) if row['rq'] else '',
                "井号": row['jh'] or '未记录',
                "当日井深(m)": float(row['drjs']) if row['drjs'] else '',
                "日进尺(m)": float(row['zjrjc']) if row['zjrjc'] else '',
                "钻头类型": row['ztlx'] or '',
                "钻速(m/h)": float(row['zs']) if row['zs'] else '',
                "泵压(MPa)": float(row['bya']) if row['bya'] else '',
                "钻井液密度": float(row['zjymd']) if row['zjymd'] else ''
            })
        
        title = f"🔨 钻井工程日报"
        if well_id:
            title += f" - 井号: {well_id}"
        if start_date or end_date:
            title += f" ({start_date} 至 {end_date})"
        
        return f"### {title}\n\n**共 {len(data)} 条记录**\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        cursor.close()
        conn.close()

@AuditLog.trace("get_drilling_pre_daily")
def get_drilling_pre_daily(project: str = "", year: int = None, well_id: str = "", limit: int = 50, 
                           user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """查询钻前工程日报数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM drilling_pre_daily WHERE is_deleted = false"
        params = []
        
        # 项目过滤
        if project:
            query += " AND ktxm ILIKE %s"
            params.append(f"%{project}%")
        
        # 年度过滤
        if year is not None:
            query += " AND ssnd = %s"
            params.append(year)
        
        # 井号过滤
        if well_id:
            if not PermissionService.check_well_access(user_role, well_id):
                return f"🚫 权限拒绝：无权访问井号 {well_id} 的钻前日报数据。"
            query += " AND jh = %s"
            params.append(well_id)
        
        query += " ORDER BY ssnd DESC, ktxm LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            filter_str = []
            if project:
                filter_str.append(f"项目 '{project}'")
            if year:
                filter_str.append(f"年度 {year}")
            if well_id:
                filter_str.append(f"井号 '{well_id}'")
            filter_text = " & ".join(filter_str) if filter_str else "条件"
            return f"❌ 未找到匹配 {filter_text} 的钻前日报数据。"
        
        # 格式化输出 - 显示关键时间节点
        data = []
        for row in results:
            data.append({
                "井号": row['jh'] or '未记录',
                "项目": row['ktxm'] or '',
                "年度": row['ssnd'] or '',
                "井位论证": str(row['jwzysj']) if row['jwzysj'] else '—',
                "工程设计审批": str(row['zjgcsjspsj']) if row['zjgcsjspsj'] else '—',
                "环评下达": str(row['hpxdsj']) if row['hpxdsj'] else '—',
                "搬家安装": f"{row['bjkssj']} 至 {row['bjjssj']}" if row['bjkssj'] and row['bjjssj'] else '—'
            })
        
        title = "🏗️ 钻前工程日报"
        filters = []
        if project:
            filters.append(f"项目: {project}")
        if year:
            filters.append(f"年度: {year}")
        if well_id:
            filters.append(f"井号: {well_id}")
        if filters:
            title += f" ({' | '.join(filters)})"
        
        return f"### {title}\n\n**共 {len(data)} 条记录**\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        cursor.close()
        conn.close()

@AuditLog.trace("get_key_well_daily")
def get_key_well_daily(well_id: str = "", start_date: str = "", end_date: str = "", block: str = "", limit: int = 100, 
                       user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """查询重点井试采日报数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM key_well_daily WHERE is_deleted = false"
        params = []
        
        # 井号过滤
        if well_id:
            if not PermissionService.check_well_access(user_role, well_id):
                return f"🚫 权限拒绝：无权访问井号 {well_id} 的重点井日报数据。"
            query += " AND jh = %s"
            params.append(well_id)
        
        # 区块过滤
        if block:
            if not PermissionService.check_block_access(user_role, block):
                return f"🚫 权限拒绝：无权访问区块 {block} 的重点井日报数据。"
            query += " AND qk ILIKE %s"
            params.append(f"%{block}%")
        
        # 日期范围过滤
        if start_date:
            query += " AND rq >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND rq <= %s"
            params.append(end_date)
        
        query += " ORDER BY rq DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            filter_items = []
            if well_id:
                filter_items.append(f"井号 '{well_id}'")
            if block:
                filter_items.append(f"区块 '{block}'")
            if start_date or end_date:
                date_range = f"{start_date or '—'} 到 {end_date or '—'}"
                filter_items.append(f"日期 {date_range}")
            filter_str = " & ".join(filter_items) if filter_items else "条件"
            return f"❌ 未找到匹配 {filter_str} 的重点井日报数据。"
        
        # 格式化输出 - 包括生产数据和压力参数
        data = []
        for row in results:
            pressure_info = []
            if row['yysx'] is not None or row['yyxx'] is not None:
                pressure_info.append(f"油压: {row['yysx']}-{row['yyxx']}MPa")
            if row['tysx'] is not None or row['tyxx'] is not None:
                pressure_info.append(f"套压: {row['tysx']}-{row['tyxx']}MPa")
            if row['hysx'] is not None or row['hyxx'] is not None:
                pressure_info.append(f"回压: {row['hysx']}-{row['hyxx']}MPa")
            
            data.append({
                "日期": str(row['rq']) if row['rq'] else '',
                "井号": row['jh'] or '未记录',
                "区块": row['qk'] or '',
                "层位": row['cw'] or '',
                "状态": row['zt'] or '',
                "日产气量(万方)": float(row['rcql']) if row['rcql'] else '',
                "含水(%)": float(row['hs']) if row['hs'] else '',
                "油嘴": row['yz'] or '',
                "压力参数": ' | '.join(pressure_info) if pressure_info else '—'
            })
        
        title = "⛽ 重点井试采日报"
        filters = []
        if well_id:
            filters.append(f"井号: {well_id}")
        if block:
            filters.append(f"区块: {block}")
        if start_date or end_date:
            date_range = f"{start_date or '—'} 至 {end_date or '—'}"
            filters.append(f"日期: {date_range}")
        if filters:
            title += f" ({' | '.join(filters)})"
        
        return f"### {title}\n\n**共 {len(data)} 条记录**\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        cursor.close()
        conn.close()

def _check_write_permission(user_role: str) -> str | None:
    """Return an error message string if write is not allowed, else None."""
    if not DEV_MODE and (user_role or "GUEST").upper() not in WRITE_ALLOWED_ROLES:
        return f"🚫 权限拒绝：角色 {user_role} 无写入权限，需要 ENGINEER 或 ADMIN 角色。"
    return None


def _parse_number(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _upsert(table: str, key_cols: list[str], fields: dict, user_email: str) -> str:
    """Generic UPDATE-then-INSERT upsert returning a status string."""
    update_cols = [c for c in fields if c not in key_cols]
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if update_cols:
            assignments = ", ".join(f"{c} = %s" for c in update_cols)
            where_clause = " AND ".join(f"{c} = %s" for c in key_cols)
            update_q = (
                f"UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP "
                f"WHERE {where_clause} RETURNING id"
            )
            cursor.execute(update_q, [fields[c] for c in update_cols] + [fields[c] for c in key_cols])
        else:
            where_clause = " AND ".join(f"{c} = %s" for c in key_cols)
            cursor.execute(
                f"UPDATE {table} SET updated_at = CURRENT_TIMESTAMP WHERE {where_clause} RETURNING id",
                [fields[c] for c in key_cols],
            )

        row = cursor.fetchone()
        if row:
            conn.commit()
            logger.info(f"✅ {table} 更新 by {user_email}")
            return f"✅ 数据已更新（ID: {row['id']}）：{table}，写入字段 {len(update_cols)}。"

        col_str = ", ".join(fields.keys())
        placeholders = ", ".join(["%s"] * len(fields))
        cursor.execute(
            f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) RETURNING id",
            list(fields.values()),
        )
        inserted = cursor.fetchone()
        conn.commit()
        logger.info(f"✅ {table} 新增 by {user_email}")
        return f"✅ 数据已新增（ID: {inserted['id'] if inserted else '?'}）：{table}，写入字段 {len(fields)}。"
    except Exception as e:
        conn.rollback()
        logger.error(f"数据库写操作失败 ({table}): {e}")
        raise
    finally:
        cursor.close()
        conn.close()


@AuditLog.trace("save_drilling_daily")
def save_drilling_daily(data: dict, user_role: str = "GUEST",
                        user_id: str = "unknown", user_email: str = "unknown") -> str:
    """将文档提取的钻井日报数据保存到数据库"""
    err = _check_write_permission(user_role)
    if err:
        return err

    jh = (data.get("jh") or "").strip()
    rq = (data.get("rq") or "").strip()
    if not jh:
        return "❌ 井号（jh）不能为空。"
    if not rq:
        return "❌ 日期（rq）不能为空。"

    allowed = {
        "jh", "rq", "kzrq", "drjs", "zjrjc", "ztlx", "ztzj",
        "zy", "zs", "bya", "bpl", "zjymd", "zjynd", "czjljsj", "brzygz",
    }
    number_fields = {"drjs", "zjrjc", "ztzj", "zy", "zs", "bya", "bpl", "zjymd", "zjynd", "czjljsj"}

    fields: dict = {"jh": jh, "rq": rq}
    for k, v in data.items():
        if k in ("jh", "rq") or k not in allowed or v is None or v == "":
            continue
        fields[k] = _parse_number(v) if k in number_fields else v

    return _upsert("drilling_daily", ["jh", "rq"], fields, user_email)


@AuditLog.trace("save_drilling_pre_daily")
def save_drilling_pre_daily(data: dict, user_role: str = "GUEST",
                            user_id: str = "unknown", user_email: str = "unknown") -> str:
    """将文档提取的钻前日报数据保存到数据库"""
    err = _check_write_permission(user_role)
    if err:
        return err

    jh = (data.get("jh") or "").strip()
    ktxm = (data.get("ktxm") or "").strip()
    if not jh:
        return "❌ 井号（jh）不能为空。"
    if not ktxm:
        return "❌ 勘探项目（ktxm）不能为空。"

    date_fields = {
        "jwzysj", "jwtjxdsj", "jwtclsj", "tzxdsj", "kjcgcwsj",
        "hpsbsj", "ydsqsbsj", "gcfatlsj", "zjdzsjspsj", "zjgcsjspsj",
        "hpxdsj", "zdcwsj", "tlsksj", "tljssj", "bjkssj", "bjjssj",
    }
    allowed = {"jh", "ktxm", "ssnd"} | date_fields

    fields: dict = {"jh": jh, "ktxm": ktxm}
    for k, v in data.items():
        if k in ("jh", "ktxm") or k not in allowed or v is None or v == "":
            continue
        if k == "ssnd":
            try:
                fields[k] = int(v)
            except (ValueError, TypeError):
                pass
        else:
            fields[k] = v

    return _upsert("drilling_pre_daily", ["ktxm", "jh"], fields, user_email)


@AuditLog.trace("save_key_well_daily")
def save_key_well_daily(data: dict, user_role: str = "GUEST",
                        user_id: str = "unknown", user_email: str = "unknown") -> str:
    """将文档提取的重点井试采日报数据保存到数据库"""
    err = _check_write_permission(user_role)
    if err:
        return err

    jh = (data.get("jh") or "").strip()
    rq = (data.get("rq") or "").strip()
    if not jh:
        return "❌ 井号（jh）不能为空。"
    if not rq:
        return "❌ 日期（rq）不能为空。"

    allowed = {
        "jh", "rq", "qk", "cw", "cxh", "djsd1", "djsd2", "zt", "cyfs", "yz",
        "gzsj", "gzzd", "rcql", "hs", "yysx", "yyxx", "tysx", "tyxx",
        "hysx", "hyxx", "d_ly", "d_jy", "d_bz",
    }
    number_fields = {"djsd1", "djsd2", "rcql", "hs", "yysx", "yyxx", "tysx", "tyxx", "hysx", "hyxx", "d_ly", "d_jy"}

    fields: dict = {"jh": jh, "rq": rq}
    for k, v in data.items():
        if k in ("jh", "rq") or k not in allowed or v is None or v == "":
            continue
        fields[k] = _parse_number(v) if k in number_fields else v

    return _upsert("key_well_daily", ["jh", "rq"], fields, user_email)


# ==========================================
# 主程序入口
# ==========================================

if __name__ == "__main__":
    import sys
    import io
    
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("🚀 油井日报系统 MCP Server")
    print("=" * 60)
    print("\n📌 提供工具：")
    print("  ✓ get_drilling_daily - 钻井工程日报")
    print("  ✓ get_drilling_pre_daily - 钻前工程日报")
    print("  ✓ get_key_well_daily - 重点井试采日报")
    print("  ✓ save_drilling_daily - 保存钻井日报")
    print("  ✓ save_drilling_pre_daily - 保存钻前日报")
    print("  ✓ save_key_well_daily - 保存重点井日报")
    print(f"\n🔒 权限模式: {'开发模式' if DEV_MODE else '生产模式'}")
    print(f"\n🗄️  数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("\n🌐 访问地址: http://0.0.0.0:8082")
    print("\n⏳ 服务器启动中...\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8082, log_level="info")
