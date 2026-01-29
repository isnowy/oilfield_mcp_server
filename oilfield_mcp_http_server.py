"""
油田钻井数据MCP Server - HTTP/SSE版本
支持动态用户权限控制

特性：
- 使用FastAPI实现HTTP端点
- 支持SSE (Server-Sent Events) 传输
- 从HTTP headers动态获取用户角色
- 每个请求独立验证权限
- 单个MCP Server实例服务所有用户
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from mcp.server import Server
from mcp.types import Tool, TextContent
from permissions import PermissionChecker, UserRole, Permission

# MCP Server实例
mcp_app = Server("oilfield-drilling-data")

# FastAPI应用
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 油田钻井数据MCP Server (HTTP/SSE) 启动中...")
    print(f"📍 监听地址: http://0.0.0.0:8080")
    yield
    print("👋 MCP Server 关闭")

app = FastAPI(
    title="油田钻井数据MCP Server",
    description="基于HTTP/SSE的MCP服务器，支持动态用户权限控制",
    version="2.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///d:/work/oilMCP/oilfield.db")
DB_PATH = DATABASE_URL.replace("sqlite:///", "")

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============ Pydantic模型 ============

class ToolCallRequest(BaseModel):
    """MCP工具调用请求"""
    name: str
    arguments: Dict[str, Any]

class ToolCallResponse(BaseModel):
    """MCP工具调用响应"""
    content: List[Dict[str, Any]]

class UserContext(BaseModel):
    """用户上下文"""
    role: str
    email: Optional[str] = None
    user_id: Optional[str] = None

# ============ 用户上下文提取 ============

def extract_user_context(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> UserContext:
    """
    从HTTP headers提取用户上下文
    LibreChat会在headers中传递用户信息
    """
    role_str = x_user_role or "GUEST"
    
    # 记录接收到的用户信息（调试用）
    print(f"\n📥 接收到用户上下文:")
    print(f"  Role: {role_str}")
    print(f"  Email: {x_user_email or 'N/A'}")
    print(f"  User ID: {x_user_id or 'N/A'}")
    
    return UserContext(
        role=role_str,
        email=x_user_email,
        user_id=x_user_id
    )

def validate_permission(tool_name: str, user_context: UserContext) -> bool:
    """验证用户是否有权限调用工具"""
    try:
        user_role = UserRole(user_context.role)
    except ValueError:
        print(f"⚠️  无效角色: {user_context.role}, 默认为GUEST")
        user_role = UserRole.GUEST
    
    checker = PermissionChecker(user_role, user_context.email)
    has_permission = checker.has_permission(tool_name)
    
    print(f"🔐 权限检查: {tool_name}")
    print(f"  用户角色: {user_role.value}")
    print(f"  是否允许: {'✓' if has_permission else '✗'}")
    
    return has_permission

# ============ 数据库操作函数 ============

def query_drilling_data(limit: int = 10) -> List[Dict]:
    """查询钻井数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM drilling_data 
        ORDER BY drilling_date DESC 
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def add_drilling_record(data: Dict) -> Dict:
    """添加钻井记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO drilling_data 
        (well_number, drilling_date, depth, drilling_speed, pressure, temperature)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get('well_number'),
        data.get('drilling_date'),
        data.get('depth'),
        data.get('drilling_speed'),
        data.get('pressure'),
        data.get('temperature')
    ))
    
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    
    return {"id": record_id, "message": "记录添加成功"}

def delete_drilling_record(record_id: int) -> Dict:
    """删除钻井记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM drilling_data WHERE id = ?", (record_id,))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected > 0:
        return {"message": f"记录 {record_id} 已删除"}
    else:
        return {"error": f"未找到记录 {record_id}"}

def export_all_data() -> Dict:
    """导出所有数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drilling_data")
    rows = cursor.fetchall()
    conn.close()
    
    data = [dict(row) for row in rows]
    return {
        "total_records": len(data),
        "data": data,
        "exported_at": datetime.now().isoformat()
    }

# ============ MCP工具定义 ============

@mcp_app.list_tools()
async def list_tools() -> List[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="query_drilling_data",
            description="查询钻井数据（需要READ权限）",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回记录数量",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="add_drilling_record",
            description="添加钻井记录（需要WRITE权限）",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_number": {"type": "string"},
                    "drilling_date": {"type": "string"},
                    "depth": {"type": "number"},
                    "drilling_speed": {"type": "number"},
                    "pressure": {"type": "number"},
                    "temperature": {"type": "number"}
                },
                "required": ["well_number", "drilling_date", "depth"]
            }
        ),
        Tool(
            name="delete_drilling_record",
            description="删除钻井记录（需要DELETE权限）",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "integer"}
                },
                "required": ["record_id"]
            }
        ),
        Tool(
            name="export_all_data",
            description="导出所有数据（需要ADMIN权限）",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]

# ============ HTTP端点 ============

@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "name": "油田钻井数据MCP Server",
        "version": "2.0.0",
        "transport": "HTTP/SSE",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drilling_data")
        count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_records": count
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.post("/mcp/call-tool")
async def call_tool(
    request: ToolCallRequest,
    user_context: UserContext = Header(None)
):
    """
    MCP工具调用端点
    LibreChat会调用此端点来执行工具
    """
    tool_name = request.name
    arguments = request.arguments
    
    print(f"\n🔧 工具调用: {tool_name}")
    print(f"📝 参数: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
    
    # 提取用户上下文（从依赖注入获取）
    if not user_context:
        # 手动从headers提取（备用方案）
        user_context = extract_user_context()
    
    # 权限验证
    if not validate_permission(tool_name, user_context):
        raise HTTPException(
            status_code=403,
            detail=f"权限不足：用户角色 {user_context.role} 无权访问工具 {tool_name}"
        )
    
    # 执行工具
    try:
        if tool_name == "query_drilling_data":
            result = query_drilling_data(arguments.get('limit', 10))
        elif tool_name == "add_drilling_record":
            result = add_drilling_record(arguments)
        elif tool_name == "delete_drilling_record":
            result = delete_drilling_record(arguments['record_id'])
        elif tool_name == "export_all_data":
            result = export_all_data()
        else:
            raise HTTPException(status_code=404, detail=f"工具不存在: {tool_name}")
        
        print(f"✓ 执行成功")
        
        return ToolCallResponse(
            content=[{
                "type": "text",
                "text": json.dumps(result, indent=2, ensure_ascii=False)
            }]
        )
    
    except Exception as e:
        print(f"✗ 执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/sse")
async def sse_endpoint(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """
    SSE端点（如果LibreChat使用SSE传输）
    """
    async def event_generator():
        user_context = UserContext(
            role=x_user_role or "GUEST",
            email=x_user_email,
            user_id=x_user_id
        )
        
        # 发送初始连接消息
        yield f"data: {json.dumps({'type': 'connected', 'user': user_context.dict()})}\n\n"
        
        # 保持连接...
        # 实际实现需要根据MCP SSE协议
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@app.get("/mcp/tools")
async def list_tools_http():
    """HTTP方式列出工具（用于调试）"""
    tools = await list_tools()
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            for tool in tools
        ]
    }

# ============ 主函数 ============

if __name__ == "__main__":
    print("=" * 60)
    print("油田钻井数据MCP Server - HTTP/SSE版本")
    print("=" * 60)
    print(f"数据库: {DB_PATH}")
    print(f"端口: 8080")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
