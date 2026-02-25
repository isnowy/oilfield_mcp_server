"""
油田钻井数据MCP Server - HTTP/SSE版本（真实数据库）
支持动态用户权限控制，连接PostgreSQL数据库查询真实数据

特性：
- 使用FastAPI实现HTTP端点
- 支持SSE (Server-Sent Events) 传输
- 从HTTP headers动态获取用户角色
- 每个请求独立验证权限
- 单个MCP Server实例服务所有用户
- 连接PostgreSQL数据库查询真实油井数据
"""
from mcp.server import Server
from mcp.server.sse import SseServerTransport  
from mcp.types import Tool, TextContent
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
import os
import re
import json
import time
import logging
import functools
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.applications import Starlette
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, DateTime, Boolean, Numeric
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# 日志配置
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OilfieldMCP_TRUE")

# 开发模式配置：设置 DEV_MODE=true 可跳过权限检查（方便测试）
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ["true", "1", "yes"]

# 数据库配置 - 从环境变量读取，默认连接到本地PostgreSQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'rag'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

# 权限配置 - 可以从配置文件或环境变量加载
USER_PERMISSIONS = {
    "ADMIN": {
        "wells": "*",           # 所有井
        "blocks": "*",          # 所有区块
        "role": "admin",
        "description": "管理员 - 完全访问权限"
    },
    "ENGINEER": {
        "wells": ["ZT-102", "ZT-105"],  # 指定井列表
        "blocks": ["Block-A"],
        "role": "engineer",
        "description": "工程师 - Block-A的部分井 + 公共数据"
    },
    "VIEWER": {
        "wells": ["ZT-102"],    # 指定井列表
        "blocks": ["Block-A"],
        "role": "viewer",
        "description": "查看者 - ZT-102只读 + 公共数据"
    },
    "USER": {
        "wells": [],            # 空列表表示只能看公共数据
        "blocks": [],
        "role": "user",
        "description": "普通用户 - 仅公共数据"
    },
    "GUEST": {
        "wells": [],            # 空列表表示只能看公共数据
        "blocks": [],
        "role": "guest",
        "description": "访客 - 仅公共数据"
    }
}

# ==========================================
# 权限管理服务
# ==========================================

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
    根据用户角色过滤井数据（基于角色权限）
    
    权限规则：
    - ADMIN: 可以查看所有井
    - ENGINEER/VIEWER: 根据USER_PERMISSIONS配置的井列表
    - USER/GUEST: 所有公共数据
    
    注意：真实数据库中的oil_wells表没有owner_user_id字段，所以所有数据都是公共数据
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
        # 过滤出权限列表中的井（真实数据都是公共数据，所以只需检查井号）
        filtered = [
            well for well in wells
            if well.get('well_name') in allowed_wells or well.get('id') in allowed_wells
        ]
        logger.info(f"🔒 {role_upper}用户 {user_email} 访问 {len(filtered)}/{len(wells)} 口井（权限配置）")
        return filtered
    else:
        # 普通USER或GUEST：可以看所有公共数据（真实数据库中都是公共数据）
        logger.info(f"✅ {role_upper}用户 {user_email} 访问所有公共数据 {len(wells)} 口井")
        return wells

class AuditLog:
    """装饰器：用于记录工具调用的输入、输出、耗时和状态"""
    
    @staticmethod
    def trace(tool_name: str):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_ts = time.time()
                trace_id = f"{int(time.time() * 1000)}"[-8:]
                
                try:
                    user_role = kwargs.get('user_role', 'GUEST')
                    logger.info(json.dumps({
                        "event": "TOOL_START",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "user": user_role,
                        "params": {k: v for k, v in kwargs.items() if k != 'user_role'}
                    }, ensure_ascii=False))
                    
                    result = func(*args, **kwargs)
                    duration = round((time.time() - start_ts) * 1000, 2)
                    
                    logger.info(json.dumps({
                        "event": "TOOL_SUCCESS",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "duration_ms": duration,
                        "result_length": len(str(result))
                    }, ensure_ascii=False))
                    
                    return result
                    
                except Exception as e:
                    duration = round((time.time() - start_ts) * 1000, 2)
                    logger.error(json.dumps({
                        "event": "TOOL_ERROR",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "duration_ms": duration,
                        "error": str(e)
                    }, ensure_ascii=False))
                    
                    return f"⚠️ 系统错误 (TraceID: {trace_id}): {str(e)}"
            
            return wrapper
        return decorator

# ==========================================
# 数据库连接管理
# ==========================================

def get_db_connection():
    """获取PostgreSQL数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def test_db_connection():
    """测试数据库连接"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM oil_wells")
        result = cursor.fetchone()
        count = result['count']
        cursor.close()
        conn.close()
        logger.info(f"✅ 数据库连接成功，共有 {count} 口井")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接测试失败: {e}")
        return False

# ==========================================
# 辅助工具函数
# ==========================================

def df_to_markdown(df: pd.DataFrame) -> str:
    """将DataFrame转换为Markdown表格"""
    if df.empty:
        return "无数据"
    return df.to_markdown(index=False)

def normalize_well_id(well_id: str) -> str:
    """归一化井号（处理中文井号和各种别名）"""
    # 这里根据实际数据调整
    return well_id.strip()

def normalize_date(time_desc: str) -> str:
    """归一化日期描述为ISO格式"""
    today = date.today()
    
    if "今天" in time_desc or "today" in time_desc.lower():
        return str(today)
    elif "昨天" in time_desc or "yesterday" in time_desc.lower():
        return str(today - timedelta(days=1))
    elif "前天" in time_desc:
        return str(today - timedelta(days=2))
    
    date_match = re.search(r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})', time_desc)
    if date_match:
        y, m, d = date_match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    
    return time_desc

def parse_date_range(time_desc: str) -> tuple:
    """解析时间范围描述"""
    today = date.today()
    
    if "本周" in time_desc or "this week" in time_desc.lower():
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return str(start), str(end)
    
    if "本月" in time_desc or "this month" in time_desc.lower():
        start = today.replace(day=1)
        if today.month == 12:
            end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        return str(start), str(end)
    
    if "上月" in time_desc or "last month" in time_desc.lower():
        if today.month == 1:
            start = date(today.year - 1, 12, 1)
            end = date(today.year, 1, 1) - timedelta(days=1)
        else:
            start = date(today.year, today.month - 1, 1)
            end = today.replace(day=1) - timedelta(days=1)
        return str(start), str(end)
    
    match = re.search(r'(\d{4})[年\-/](\d{1,2})', time_desc)
    if match:
        y, m = match.groups()
        y, m = int(y), int(m)
        start = date(y, m, 1)
        if m == 12:
            end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(y, m + 1, 1) - timedelta(days=1)
        return str(start), str(end)
    
    return str(today), str(today)

# ==========================================
# 用户上下文管理
# ==========================================

class UserContext(BaseModel):
    """用户上下文信息"""
    role: str = "GUEST"
    email: str = "unknown"
    user_id: str = "unknown"

# 使用contextvars来存储每个请求的用户上下文（线程安全）
from contextvars import ContextVar
current_user_context: ContextVar[UserContext] = ContextVar('current_user_context', default=UserContext())

def extract_user_context(
    x_user_role: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> UserContext:
    """从HTTP请求头中提取用户上下文"""
    role = x_user_role or "GUEST"
    email = x_user_email or "unknown"
    user_id = x_user_id or "unknown"
    
    logger.info("=" * 60)
    logger.info("📋 提取用户上下文")
    logger.info(f"  角色: {role}")
    logger.info(f"  邮箱: {email}")
    logger.info(f"  用户ID: {user_id}")
    logger.info("=" * 60)
    
    return UserContext(role=role, email=email, user_id=user_id)

# ==========================================
# MCP Server实例
# ==========================================

# 创建标准 MCP Server
mcp_server = Server("oilfield-drilling-true")

# 创建 SSE Transport
sse_transport = SseServerTransport("/sse")

# FastAPI应用
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 油田钻井数据MCP Server (真实数据库) 启动中...")
    logger.info(f"📍 监听地址: http://0.0.0.0:8081")
    logger.info(f"🔒 权限模式: {'开发模式(跳过权限)' if DEV_MODE else '生产模式(严格权限)'}")
    logger.info(f"🗄️  数据库: PostgreSQL @ {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    # 测试数据库连接
    if test_db_connection():
        logger.info("✅ 数据库连接正常")
    else:
        logger.warning("⚠️  数据库连接失败，请检查配置")
    
    yield
    logger.info("👋 MCP Server 关闭")

app = FastAPI(
    title="油田钻井数据MCP Server (真实数据)",
    description="基于HTTP/SSE的MCP服务器，连接PostgreSQL真实数据库",
    version="2.0.0-real",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 健康检查端点 ============

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "油田钻井数据MCP Server (真实数据)",
        "version": "2.0.0-real",
        "status": "running",
        "database": f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    db_ok = test_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now().isoformat()
    }

# ============ SSE Endpoint ============

@app.get("/sse")
async def handle_sse_get(request: Request):
    """SSE GET endpoint - 建立SSE连接"""
    logger.info("🌊 SSE GET请求 - 建立连接")
    
    try:
        return await sse_transport.connect_sse(request, mcp_server)
    except Exception as e:
        logger.error(f"❌ SSE GET错误: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.head("/sse")
async def handle_sse_head():
    """SSE HEAD endpoint - 检查服务可用性"""
    return Response(status_code=200)

@app.post("/sse")
async def handle_sse_post(request: Request):
    """SSE POST endpoint - 处理JSON-RPC消息（无状态模式）"""
    session_id = request.query_params.get("sessionId") or request.query_params.get("session_id")
    
    # 提取用户信息
    user_role = request.headers.get("x-user-role", "GUEST")
    user_email = request.headers.get("x-user-email", "unknown")
    user_id = request.headers.get("x-user-id", "unknown")
    
    # 设置全局用户上下文
    user_ctx = UserContext(role=user_role, email=user_email, user_id=user_id)
    current_user_context.set(user_ctx)
    
    logger.info(f"🌊 SSE POST请求 - session_id: {session_id}")
    logger.info(f"👤 用户信息: {user_email} ({user_role}) [ID: {user_id}]")
    
    try:
        # 读取请求体
        body = await request.body()
        body_json = json.loads(body.decode())
        logger.info(f"📝 POST请求体: {body_json}")
        
        # 无状态模式：直接处理 JSON-RPC 请求
        if not session_id:
            logger.info("🔧 无状态模式 - 直接处理JSON-RPC请求")
            
            # 处理 initialize 请求
            if body_json.get("method") == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": body_json.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "prompts": {},
                            "resources": {}
                        },
                        "serverInfo": {
                            "name": "oilfield-drilling-true",
                            "version": "2.0.0-real"
                        }
                    }
                }
                logger.info(f"✅ Initialize响应: {response}")
                return JSONResponse(content=response)
            
            # 处理 initialized 通知
            elif body_json.get("method") == "notifications/initialized":
                logger.info("✅ Initialized通知已接收")
                return JSONResponse(content={})
            
            # 处理 tools/list 请求
            elif body_json.get("method") == "tools/list":
                # 返回工具列表
                tools_list = [
                    {
                        "name": "search_wells",
                        "description": "搜索油井信息（真实数据库），支持批量搜索多个关键词、区块。💡重要：查询所有油井时，将keyword设为空字符串''或不传递keyword参数即可。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "keywords": {"type": "array", "items": {"type": "string"}, "description": "搜索关键词列表（井号、区块等）。留空返回所有油井"},
                                "keyword": {"type": "string", "description": "单个搜索关键词（兼容旧接口）。空字符串''返回所有油井"},
                                "limit": {"type": "integer", "default": 50, "description": "返回结果数量限制"}
                            },
                            "required": []
                        }
                    },
                    {
                        "name": "get_well_details",
                        "description": "获取单井或多井详细信息（真实数据），包括所有字段",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "well_ids": {"type": "array", "items": {"type": "string"}, "description": "井名列表"},
                                "well_id": {"type": "string", "description": "单个井名（兼容旧接口）"}
                            },
                            "required": []
                        }
                    },
                    {
                        "name": "get_wells_by_block",
                        "description": "按区块查询油井（真实数据）",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "block": {"type": "string", "description": "区块名称"},
                                "limit": {"type": "integer", "default": 50}
                            },
                            "required": ["block"]
                        }
                    },
                    {
                        "name": "get_wells_by_project",
                        "description": "按项目查询油井（真实数据）",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "project": {"type": "string", "description": "项目名称（ktxm字段）"},
                                "limit": {"type": "integer", "default": 50}
                            },
                            "required": ["project"]
                        }
                    },
                    {
                        "name": "get_statistics",
                        "description": "获取油井统计信息（真实数据）",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "group_by": {"type": "string", "enum": ["block", "project", "well_type"], "default": "block"}
                            },
                            "required": []
                        }
                    }
                ]
                
                response = {
                    "jsonrpc": "2.0",
                    "id": body_json.get("id"),
                    "result": {
                        "tools": tools_list
                    }
                }
                logger.info(f"✅ Tools列表响应: {len(tools_list)} 个工具")
                return JSONResponse(content=response)
            
            # 处理 tools/call 请求
            elif body_json.get("method") == "tools/call":
                params = body_json.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                logger.info(f"🔧 调用工具: {tool_name}, 参数: {tool_args}")
                logger.info(f"👤 调用用户: {user_email} ({user_role})")
                
                # 调用对应的业务逻辑函数
                try:
                    result_text = None
                    
                    if tool_name == "search_wells":
                        result_text = search_wells(
                            keywords=tool_args.get('keywords'),
                            keyword=tool_args.get('keyword', ''),
                            limit=tool_args.get('limit', 50),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "get_well_details":
                        result_text = get_well_details(
                            well_ids=tool_args.get('well_ids'),
                            well_id=tool_args.get('well_id', ''),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "get_wells_by_block":
                        result_text = get_wells_by_block(
                            block=tool_args.get('block', ''),
                            limit=tool_args.get('limit', 50),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "get_wells_by_project":
                        result_text = get_wells_by_project(
                            project=tool_args.get('project', ''),
                            limit=tool_args.get('limit', 50),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "get_statistics":
                        result_text = get_statistics(
                            group_by=tool_args.get('group_by', 'block'),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    else:
                        raise ValueError(f"未知工具: {tool_name}")
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": body_json.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result_text
                                }
                            ]
                        }
                    }
                    logger.info(f"✅ 工具调用成功: {tool_name}")
                    return JSONResponse(content=response)
                    
                except Exception as tool_error:
                    logger.error(f"❌ 工具调用失败: {tool_error}", exc_info=True)
                    response = {
                        "jsonrpc": "2.0",
                        "id": body_json.get("id"),
                        "error": {
                            "code": -32603,
                            "message": str(tool_error)
                        }
                    }
                    return JSONResponse(content=response)
            
            # 未知方法
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": body_json.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {body_json.get('method')}"
                    }
                }
                return JSONResponse(content=response)
        
        # 有 session_id 的情况，使用标准 SSE transport
        else:
            logger.info(f"🔗 有状态模式 - 使用session: {session_id}")
            response_data = {}
            response_status = 200
            
            async def receive():
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False
                }
            
            async def send(message):
                nonlocal response_data, response_status
                if message["type"] == "http.response.start":
                    response_status = message.get("status", 200)
                elif message["type"] == "http.response.body":
                    body = message.get("body", b"")
                    if body:
                        try:
                            response_data = json.loads(body.decode())
                        except:
                            response_data = {"body": body.decode()}
            
            await sse_transport.handle_post_message(
                request.scope,
                receive,
                send
            )
            
            return JSONResponse(
                status_code=response_status,
                content=response_data if response_data else {"jsonrpc": "2.0", "result": {}}
            )
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析错误: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
        )
    except Exception as e:
        logger.error(f"❌ SSE POST错误: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
        )

# ==========================================
# MCP Server Handlers
# ==========================================

@mcp_server.list_tools()
async def handle_list_tools():
    """列出所有可用的工具"""
    return [
        Tool(
            name="search_wells",
            description="搜索油井（真实数据库），支持批量搜索。💡重要：查询所有油井时，将keyword设为空字符串''或不传递keyword参数即可。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {"type": "array", "items": {"type": "string"}, "description": "搜索关键词列表。留空可返回所有油井"},
                    "keyword": {"type": "string", "description": "单个搜索关键词（兼容旧接口）。设为空字符串''可返回所有油井"},
                    "limit": {"type": "integer", "default": 50, "description": "返回结果数量限制"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_well_details",
            description="获取单井或多井详细信息（真实数据），包括所有字段",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_ids": {"type": "array", "items": {"type": "string"}, "description": "井名列表"},
                    "well_id": {"type": "string", "description": "单个井名（兼容旧接口）"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_wells_by_block",
            description="按区块查询油井（真实数据）",
            inputSchema={
                "type": "object",
                "properties": {
                    "block": {"type": "string", "description": "区块名称"},
                    "limit": {"type": "integer", "default": 50}
                },
                "required": ["block"]
            }
        ),
        Tool(
            name="get_wells_by_project",
            description="按项目查询油井（真实数据）",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "项目名称（ktxm字段）"},
                    "limit": {"type": "integer", "default": 50}
                },
                "required": ["project"]
            }
        ),
        Tool(
            name="get_statistics",
            description="获取油井统计信息（真实数据）",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_by": {"type": "string", "enum": ["block", "project", "well_type"], "default": "block"}
                },
                "required": []
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """处理工具调用"""
    logger.info(f"🔧 MCP工具调用: {name}")
    logger.debug(f"📝 参数: {json.dumps(arguments, ensure_ascii=False)}")
    
    # 从ContextVar获取用户上下文
    user_ctx = current_user_context.get()
    user_role = user_ctx.role
    user_id = user_ctx.user_id
    user_email = user_ctx.email
    
    logger.info(f"👤 调用用户: {user_email} ({user_role})")
    
    try:
        result = None
        
        if name == "search_wells":
            result = search_wells(
                keywords=arguments.get('keywords'),
                keyword=arguments.get('keyword', ''),
                limit=arguments.get('limit', 50),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_well_details":
            result = get_well_details(
                well_ids=arguments.get('well_ids'),
                well_id=arguments.get('well_id', ''),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_wells_by_block":
            result = get_wells_by_block(
                block=arguments.get('block', ''),
                limit=arguments.get('limit', 50),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_wells_by_project":
            result = get_wells_by_project(
                project=arguments.get('project', ''),
                limit=arguments.get('limit', 50),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_statistics":
            result = get_statistics(
                group_by=arguments.get('group_by', 'block'),
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
# 业务逻辑函数（真实数据库查询）
# ==========================================

@AuditLog.trace("search_wells")
def search_wells(keywords: List[str] = None, keyword: str = None, limit: int = 50, user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """搜索油井 - 真实数据库"""
    # 兼容旧接口
    if keywords is None:
        if keyword:
            keywords = [keyword]
        else:
            keywords = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 如果没有关键词，返回所有油井
        if not keywords or (len(keywords) == 1 and not keywords[0]):
            query = f"""
                SELECT well_name, qk, jx, sjjs, sjrq, ktxm
                FROM oil_wells 
                WHERE is_deleted = false
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
        else:
            # 有关键词的搜索
            conditions = []
            params = []
            
            for kw in keywords:
                if not kw:
                    continue
                conditions.append("""
                    (well_name ILIKE %s OR qk ILIKE %s OR ktxm ILIKE %s)
                """)
                like_pattern = f"%{kw}%"
                params.extend([like_pattern, like_pattern, like_pattern])
            
            if not conditions:
                # 所有关键词都是空的
                query = f"""
                    SELECT well_name, qk, jx, sjjs, sjrq, ktxm
                    FROM oil_wells 
                    WHERE is_deleted = false
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            else:
                query = f"""
                    SELECT well_name, qk, jx, sjjs, sjrq, ktxm
                    FROM oil_wells 
                    WHERE is_deleted = false AND ({' OR '.join(conditions)})
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                params.append(limit)
                cursor.execute(query, params)
        
        results = cursor.fetchall()
        
        # 转换为字典列表
        wells = [dict(row) for row in results]
        
        # 权限过滤
        wells = filter_wells_by_permission(wells, user_role, user_id, user_email)
        
        if not wells:
            keywords_str = "、".join([k for k in keywords if k]) if keywords else "全部"
            return f"未找到匹配关键词 '{keywords_str}' 的井。"
        
        # 格式化输出
        data = []
        for w in wells:
            data.append({
                "井名": w.get('well_name', ''),
                "区块": w.get('qk', ''),
                "井型": w.get('jx', ''),
                "设计井深(m)": float(w.get('sjjs', 0)) if w.get('sjjs') else 0,
                "设计日期": str(w.get('sjrq', '')) if w.get('sjrq') else '',
                "项目": w.get('ktxm', '')
            })
        
        keywords_str = "、".join([k for k in keywords if k]) if keywords else "全部"
        return f"### 🔍 搜索结果（关键词：{keywords_str}，共 {len(wells)} 口井）\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        cursor.close()
        conn.close()

@AuditLog.trace("get_well_details")
def get_well_details(well_ids: List[str] = None, well_id: str = None, user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """获取井详细信息 - 真实数据库"""
    # 兼容旧接口
    if well_ids is None:
        if well_id:
            well_ids = [well_id]
        else:
            return "❌ 请提供井名"
    
    well_ids = [normalize_well_id(wid) for wid in well_ids]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        results = []
        
        for wid in well_ids:
            query = """
                SELECT * FROM oil_wells 
                WHERE well_name = %s AND is_deleted = false
            """
            cursor.execute(query, (wid,))
            result = cursor.fetchone()
            
            if not result:
                results.append(f"❌ 未找到井名: {wid}")
                continue
            
            well = dict(result)
            
            # 权限检查
            filtered = filter_wells_by_permission([well], user_role, user_id, user_email)
            if not filtered:
                results.append(f"🚫 权限拒绝：无权访问井名 {wid}。")
                continue
            
            # 格式化输出
            well_info = f"""
### 🏭 井详细信息：{well.get('well_name', '')}

#### 基本信息
- **井名**: {well.get('well_name', '')}
- **区块**: {well.get('qk', '')}
- **区块代码**: {well.get('qkdm', '')}
- **井型**: {well.get('jx', '')}
- **井别**: {well.get('jb', '')}
- **层位**: {well.get('cw', '')}

#### 项目信息
- **勘探项目类别**: {well.get('ktxmlb', '')}
- **勘探项目**: {well.get('ktxm', '')}
- **勘探子项目**: {well.get('ktzxm', '')}

#### 设计参数
- **设计日期**: {well.get('sjrq', '')}
- **设计井深**: {well.get('sjjs', '')} 米
- **设计钻至标高**: {well.get('sjzzbx', '')}
- **设计海拔标高**: {well.get('sjhzby', '')}
- **设计目的层**: {well.get('sjmdc', '')}
- **设计完钻层位**: {well.get('sjwzcw', '')}

#### 钻探信息
- **钻探目的**: {well.get('ztmd', '')}
- **完钻原则**: {well.get('wzyz', '')}

#### 地理位置
- **地貌海拔**: {well.get('dmhb', '')}
- **所在省市**: {well.get('ss', '')}
- **实有位置**: {well.get('sywz', '')}

#### 其他信息
- **合同期号**: {well.get('htqh', '')}
- **操作人**: {well.get('czr', '')}
- **录入人**: {well.get('lrr', '')}
- **备注**: {well.get('bz', '')}
"""
            results.append(well_info)
        
        if len(results) == 1:
            return results[0]
        else:
            return "\n\n---\n\n".join(results)
    
    finally:
        cursor.close()
        conn.close()

@AuditLog.trace("get_wells_by_block")
def get_wells_by_block(block: str, limit: int = 50, user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """按区块查询油井 - 真实数据库"""
    if not block:
        return "❌ 请提供区块名称"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT well_name, qk, jx, sjjs, sjrq, ktxm
            FROM oil_wells 
            WHERE qk ILIKE %s AND is_deleted = false
            ORDER BY created_at DESC
            LIMIT %s
        """
        cursor.execute(query, (f"%{block}%", limit))
        results = cursor.fetchall()
        
        wells = [dict(row) for row in results]
        
        # 权限过滤
        wells = filter_wells_by_permission(wells, user_role, user_id, user_email)
        
        if not wells:
            return f"未找到区块 '{block}' 的油井。"
        
        data = []
        for w in wells:
            data.append({
                "井名": w.get('well_name', ''),
                "区块": w.get('qk', ''),
                "井型": w.get('jx', ''),
                "设计井深(m)": float(w.get('sjjs', 0)) if w.get('sjjs') else 0,
                "设计日期": str(w.get('sjrq', '')) if w.get('sjrq') else '',
                "项目": w.get('ktxm', '')
            })
        
        return f"### 🔍 区块 '{block}' 的油井（共 {len(wells)} 口）\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        cursor.close()
        conn.close()

@AuditLog.trace("get_wells_by_project")
def get_wells_by_project(project: str, limit: int = 50, user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """按项目查询油井 - 真实数据库"""
    if not project:
        return "❌ 请提供项目名称"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT well_name, qk, jx, sjjs, sjrq, ktxm
            FROM oil_wells 
            WHERE ktxm ILIKE %s AND is_deleted = false
            ORDER BY created_at DESC
            LIMIT %s
        """
        cursor.execute(query, (f"%{project}%", limit))
        results = cursor.fetchall()
        
        wells = [dict(row) for row in results]
        
        # 权限过滤
        wells = filter_wells_by_permission(wells, user_role, user_id, user_email)
        
        if not wells:
            return f"未找到项目 '{project}' 的油井。"
        
        data = []
        for w in wells:
            data.append({
                "井名": w.get('well_name', ''),
                "区块": w.get('qk', ''),
                "井型": w.get('jx', ''),
                "设计井深(m)": float(w.get('sjjs', 0)) if w.get('sjjs') else 0,
                "设计日期": str(w.get('sjrq', '')) if w.get('sjrq') else '',
                "项目": w.get('ktxm', '')
            })
        
        return f"### 🔍 项目 '{project}' 的油井（共 {len(wells)} 口）\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        cursor.close()
        conn.close()

@AuditLog.trace("get_statistics")
def get_statistics(group_by: str = "block", user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """获取统计信息 - 真实数据库（带可视化提示）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if group_by == "block":
            query = """
                SELECT qk as name, COUNT(*) as count, AVG(sjjs) as avg_depth
                FROM oil_wells 
                WHERE is_deleted = false AND qk IS NOT NULL
                GROUP BY qk
                ORDER BY count DESC
            """
        elif group_by == "project":
            query = """
                SELECT ktxm as name, COUNT(*) as count, AVG(sjjs) as avg_depth
                FROM oil_wells 
                WHERE is_deleted = false AND ktxm IS NOT NULL
                GROUP BY ktxm
                ORDER BY count DESC
            """
        elif group_by == "well_type":
            query = """
                SELECT jx as name, COUNT(*) as count, AVG(sjjs) as avg_depth
                FROM oil_wells 
                WHERE is_deleted = false AND jx IS NOT NULL
                GROUP BY jx
                ORDER BY count DESC
            """
        else:
            return "❌ 不支持的分组方式"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            return f"暂无统计数据（按{group_by}分组）"
        
        data = []
        for row in results:
            data.append({
                "名称": row['name'],
                "井数": row['count'],
                "平均设计井深(m)": round(float(row['avg_depth']), 2) if row['avg_depth'] else 0
            })
        
        group_name_map = {
            "block": "区块",
            "project": "项目",
            "well_type": "井型"
        }
        
        # 判断最佳图表类型
        data_count = len(data)
        if group_by == "well_type" and data_count <= 6:
            chart_type = "饼图"
            chart_description = "适合展示各井型的占比分布"
        else:
            chart_type = "柱状图"
            chart_description = f"适合对比不同{group_name_map.get(group_by)}的油井数量"
        
        # 添加可视化提示
        return f"""### 📊 油井统计（按{group_name_map.get(group_by, group_by)}分组）

{df_to_markdown(pd.DataFrame(data))}

---
💡 **可视化建议**：此数据适合用 **{chart_type}** 展示，可以更直观地{chart_description}。"""
    
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 主程序入口
# ==========================================

if __name__ == "__main__":
    import sys
    import io
    
    # Windows控制台UTF-8支持
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("🚀 油田钻井智能查询 MCP Server (真实数据库版本)")
    print("=" * 60)
    print("\n📌 系统功能：")
    print("  ✓ 连接PostgreSQL真实数据库")
    print("  ✓ 油井搜索和详细信息查询")
    print("  ✓ 按区块、项目查询")
    print("  ✓ 统计分析功能")
    print("  ✓ 基于角色的权限控制")
    
    # 显示当前权限模式
    if DEV_MODE:
        print("\n🔓 权限模式：开发模式 (跳过权限检查)")
        print("   提示：生产环境请设置环境变量 DEV_MODE=false")
    else:
        print("\n🔒 权限模式：生产模式 (基于角色的权限控制)")
    
    print(f"\n🗄️  数据库配置：")
    print(f"  主机: {DB_CONFIG['host']}")
    print(f"  端口: {DB_CONFIG['port']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    print(f"  用户: {DB_CONFIG['user']}")
    
    print("\n📌 HTTP端点：")
    print("  GET  /         - 服务状态")
    print("  GET  /health   - 健康检查")
    print("  GET  /sse      - SSE连接")
    print("  POST /sse      - SSE消息处理")
    
    print("\n🌐 访问地址: http://0.0.0.0:8081")
    print("\n⏳ 服务器启动中...\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081,
        log_level="info"
    )
