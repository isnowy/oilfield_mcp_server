"""
油井基础数据 MCP Server
提供油井搜索、详情查询、统计分析等功能
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
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 导入共享模块
from common.db import get_db_connection, test_db_connection, DB_CONFIG
from common.permissions import PermissionService, filter_wells_by_permission, DEV_MODE
from common.utils import df_to_markdown, normalize_well_id
from common.audit import AuditLog

# ==========================================
# 日志配置
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OilfieldWellsMCP")

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

mcp_server = Server("oilfield-wells")
sse_transport = SseServerTransport("/sse")

# ==========================================
# FastAPI应用
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 油井基础数据 MCP Server 启动中...")
    logger.info(f"📍 监听地址: http://0.0.0.0:8081")
    logger.info(f"🔒 权限模式: {'开发模式' if DEV_MODE else '生产模式'}")
    logger.info(f"🗄️  数据库: PostgreSQL @ {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    if test_db_connection():
        logger.info("✅ 数据库连接正常")
    else:
        logger.warning("⚠️  数据库连接失败")
    
    yield
    logger.info("👋 MCP Server 关闭")

app = FastAPI(
    title="油井基础数据 MCP Server",
    description="提供油井搜索、详情查询、统计分析等功能",
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
        "service": "油井基础数据 MCP Server",
        "version": "1.0.0",
        "status": "running",
        "tools": 5
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
        
        # 处理各种 JSON-RPC 方法
        method = body_json.get("method")
        
        if method == "initialize":
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
                    "serverInfo": {"name": "oilfield-wells", "version": "1.0.0"}
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
            name="search_wells",
            description="搜索油井信息。支持批量搜索多个关键词。💡重要：查询所有油井时，将keyword设为空字符串''或不传递keyword参数即可。",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索关键词列表。留空返回所有油井"
                    },
                    "keyword": {
                        "type": "string",
                        "description": "单个搜索关键词（井号、区块等）。空字符串''返回所有油井"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 500,
                        "description": "返回结果数量限制（默认500，最大10000）"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_well_details",
            description="获取单井或多井的详细信息，包括所有字段数据",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "井名列表"
                    },
                    "well_id": {
                        "type": "string",
                        "description": "单个井名（兼容旧接口）"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_wells_by_block",
            description="按区块查询油井列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "block": {
                        "type": "string",
                        "description": "区块名称"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "返回结果数量限制"
                    }
                },
                "required": ["block"]
            }
        ),
        Tool(
            name="get_wells_by_project",
            description="按项目查询油井列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "项目名称（ktxm字段）"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "返回结果数量限制"
                    }
                },
                "required": ["project"]
            }
        ),
        Tool(
            name="get_statistics",
            description="获取油井统计信息，支持按区块、项目、井型分组统计",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_by": {
                        "type": "string",
                        "enum": ["block", "project", "well_type"],
                        "default": "block",
                        "description": "分组方式"
                    }
                },
                "required": []
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
        
        if name == "search_wells":
            result = search_wells(
                keywords=arguments.get('keywords'),
                keyword=arguments.get('keyword', ''),
                limit=arguments.get('limit', 500),
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
# 业务逻辑函数
# ==========================================

@AuditLog.trace("search_wells")
def search_wells(keywords: List[str] = None, keyword: str = None, limit: int = 500, 
                 user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """搜索油井"""
    # 兼容旧接口
    if keywords is None:
        if keyword:
            keywords = [keyword]
        else:
            keywords = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 判断是否为"查询所有"
        is_query_all = not keywords or (len(keywords) == 1 and not keywords[0])
        
        # 如果是查询所有，先检查总数
        if is_query_all:
            cursor.execute("SELECT COUNT(*) as count FROM oil_wells WHERE is_deleted = false")
            total_count = cursor.fetchone()['count']
            
            # 如果总数超过200，返回统计摘要
            if total_count > 200:
                logger.info(f"📊 数据量较大({total_count}口井)，返回统计摘要")
                
                # 按区块统计
                cursor.execute("""
                    SELECT qk, COUNT(*) as count, AVG(sjjs) as avg_depth
                    FROM oil_wells 
                    WHERE is_deleted = false AND qk IS NOT NULL AND qk != ''
                    GROUP BY qk
                    ORDER BY count DESC
                    LIMIT 10
                """)
                block_stats = cursor.fetchall()
                
                # 构建统计报告
                report = f"""### 📊 油井数据统计摘要

**💡 提示**：由于数据量较大（共 **{total_count}** 口井），为提高查询效率，这里展示统计摘要。如需查看详细列表，请使用更具体的查询条件。

---

#### 🗺️ 区块分布（前10名）

"""
                if block_stats:
                    block_data = []
                    for row in block_stats:
                        block_data.append({
                            "区块": row['qk'],
                            "井数": row['count'],
                            "平均井深(m)": round(float(row['avg_depth']), 2) if row['avg_depth'] else 0
                        })
                    report += df_to_markdown(pd.DataFrame(block_data))
                
                report += """

---

#### 💡 查询建议

如需查看详细井列表，请尝试：
- **按区块查询**：使用 `get_wells_by_block` 工具
- **按项目查询**：使用 `get_wells_by_project` 工具
- **按井号搜索**：使用 `search_wells` 并指定井号关键词
"""
                return report
        
        # 正常查询流程
        if is_query_all:
            query = """
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
                conditions.append("(well_name ILIKE %s OR qk ILIKE %s OR ktxm ILIKE %s)")
                like_pattern = f"%{kw}%"
                params.extend([like_pattern, like_pattern, like_pattern])
            
            if not conditions:
                query = """
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
def get_well_details(well_ids: List[str] = None, well_id: str = None, 
                     user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """获取井详细信息"""
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
            query = "SELECT * FROM oil_wells WHERE well_name = %s AND is_deleted = false"
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
            well_info = f"""### 🏭 井详细信息：{well.get('well_name', '')}

#### 基本信息
- **井名**: {well.get('well_name', '')}
- **区块**: {well.get('qk', '')}
- **井型**: {well.get('jx', '')}
- **井别**: {well.get('jb', '')}
- **层位**: {well.get('cw', '')}

#### 项目信息
- **勘探项目**: {well.get('ktxm', '')}
- **勘探子项目**: {well.get('ktzxm', '')}

#### 设计参数
- **设计日期**: {well.get('sjrq', '')}
- **设计井深**: {well.get('sjjs', '')} 米
- **设计目的层**: {well.get('sjmdc', '')}
- **设计完钻层位**: {well.get('sjwzcw', '')}

#### 地理位置
- **地貌海拔**: {well.get('dmhb', '')}
- **所在省市**: {well.get('ss', '')}
- **实有位置**: {well.get('sywz', '')}
"""
            results.append(well_info)
        
        return "\n\n---\n\n".join(results) if len(results) > 1 else results[0]
    
    finally:
        cursor.close()
        conn.close()

@AuditLog.trace("get_wells_by_block")
def get_wells_by_block(block: str, limit: int = 50, 
                       user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """按区块查询油井"""
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
def get_wells_by_project(project: str, limit: int = 50, 
                         user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """按项目查询油井"""
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
def get_statistics(group_by: str = "block", 
                   user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """获取统计信息"""
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
        
        group_name_map = {"block": "区块", "project": "项目", "well_type": "井型"}
        
        # 判断最佳图表类型
        data_count = len(data)
        if group_by == "well_type" and data_count <= 6:
            chart_type = "饼图"
            chart_description = "适合展示各井型的占比分布"
        else:
            chart_type = "柱状图"
            chart_description = f"适合对比不同{group_name_map.get(group_by)}的油井数量"
        
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
    
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("🚀 油井基础数据 MCP Server")
    print("=" * 60)
    print("\n📌 提供工具：")
    print("  ✓ search_wells - 搜索油井")
    print("  ✓ get_well_details - 井详细信息")
    print("  ✓ get_wells_by_block - 按区块查询")
    print("  ✓ get_wells_by_project - 按项目查询")
    print("  ✓ get_statistics - 统计分析")
    print(f"\n🔒 权限模式: {'开发模式' if DEV_MODE else '生产模式'}")
    print(f"\n🗄️  数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("\n🌐 访问地址: http://0.0.0.0:8081")
    print("\n⏳ 服务器启动中...\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info")
