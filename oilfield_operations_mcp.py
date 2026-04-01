"""
油田作业数据 MCP Server
提供分析化验、修井记录、射孔记录、井身结构图的保存功能
端口: 8083
"""
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.responses import Response
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextvars import ContextVar
import uvicorn

from common.db import get_db_connection, test_db_connection, DB_CONFIG
from common.permissions import DEV_MODE
from common.audit import AuditLog

# ==========================================
# 日志配置
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OilfieldOperationsMCP")

WRITE_ALLOWED_ROLES = {"ADMIN", "ENGINEER"}

# ==========================================
# 用户上下文管理
# ==========================================

class UserContext(BaseModel):
    role: str = "GUEST"
    email: str = "unknown"
    user_id: str = "unknown"

current_user_context: ContextVar[UserContext] = ContextVar('current_user_context', default=UserContext())

# ==========================================
# MCP Server 实例
# ==========================================

mcp_server = Server("oilfield-operations")
sse_transport = SseServerTransport("/sse")

# ==========================================
# FastAPI 应用
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 油田作业数据 MCP Server v1.0.0 启动中...")
    logger.info("📍 监听地址: http://0.0.0.0:8083")
    logger.info(f"🔒 权限模式: {'开发模式' if DEV_MODE else '生产模式'}")
    logger.info(f"🗄️  数据库: PostgreSQL @ {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    if test_db_connection():
        logger.info("✅ 数据库连接正常")
    else:
        logger.warning("⚠️  数据库连接失败")
    yield
    logger.info("👋 MCP Server 关闭")

app = FastAPI(
    title="油田作业数据 MCP Server",
    description="提供分析化验、修井记录、射孔记录、井身结构图的写入功能",
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
    return {"service": "油田作业数据 MCP Server", "version": "1.0.0", "status": "running", "tools": 4}

@app.get("/health")
async def health_check():
    db_ok = test_db_connection()
    return {"status": "healthy" if db_ok else "degraded", "database": "connected" if db_ok else "disconnected"}

# ==========================================
# SSE Endpoints
# ==========================================

@app.get("/sse")
async def handle_sse_get(request: Request):
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
    user_role = request.headers.get("x-user-role", "GUEST")
    user_email = request.headers.get("x-user-email", "unknown")
    user_id = request.headers.get("x-user-id", "unknown")
    current_user_context.set(UserContext(role=user_role, email=user_email, user_id=user_id))
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
                    "serverInfo": {"name": "oilfield-operations", "version": "1.0.0"}
                }
            })
        elif method == "notifications/initialized":
            return JSONResponse(content={})
        elif method == "tools/list":
            tools_list = await handle_list_tools()
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "result": {"tools": [
                    {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                    for t in tools_list
                ]}
            })
        elif method == "tools/call":
            params = body_json.get("params", {})
            result = await handle_call_tool(params.get("name"), params.get("arguments", {}))
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "result": {"content": [{"type": item.type, "text": item.text} for item in result]}
            })
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": body_json.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
    except Exception as e:
        logger.error(f"❌ SSE POST错误: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}})

# ==========================================
# MCP Server Handlers
# ==========================================

@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="save_well_analysis",
            description="将从文档中提取的分析化验数据（气样/水样）保存到数据库。需要 ENGINEER 或 ADMIN 角色权限。",
            inputSchema={
                "type": "object",
                "properties": {
                    "jh": {"type": "string", "description": "井号（必填）"},
                    "yplx": {"type": "string", "description": "样品类型（气样/水样，必填）"},
                    "qyrq": {"type": "string", "description": "取样日期（YYYY-MM-DD）"},
                    "cw": {"type": "string", "description": "层位"},
                    "bgbh": {"type": "string", "description": "报告编号"},
                    "ypbh": {"type": "string", "description": "样品编号"},
                    "ypmc": {"type": "string", "description": "样品名称"},
                    "qydd": {"type": "string", "description": "取样地点"},
                    "qyr": {"type": "string", "description": "取样人"},
                    "cyrq": {"type": "string", "description": "采样日期（YYYY-MM-DD）"},
                    "ch4": {"type": "number", "description": "甲烷 (mol%)"},
                    "c2h6": {"type": "number", "description": "乙烷 (mol%)"},
                    "c3h8": {"type": "number", "description": "丙烷 (mol%)"},
                    "c4h10": {"type": "number", "description": "丁烷 (mol%)"},
                    "c5h12": {"type": "number", "description": "戊烷 (mol%)"},
                    "ic4h10": {"type": "number", "description": "异丁烷 (mol%)"},
                    "nc4h10": {"type": "number", "description": "正丁烷 (mol%)"},
                    "ic5h12": {"type": "number", "description": "异戊烷 (mol%)"},
                    "nc5h12": {"type": "number", "description": "正戊烷 (mol%)"},
                    "c6_plus": {"type": "number", "description": "C6+ (mol%)"},
                    "co2": {"type": "number", "description": "二氧化碳 (mol%)"},
                    "n2": {"type": "number", "description": "氮气 (mol%)"},
                    "h2s": {"type": "number", "description": "硫化氢 (mol%)"},
                    "h2": {"type": "number", "description": "氢气 (mol%)"},
                    "co": {"type": "number", "description": "一氧化碳 (mol%)"},
                    "o2": {"type": "number", "description": "氧气 (mol%)"},
                    "molecular_weight": {"type": "number", "description": "计算分子量"},
                    "standard_density": {"type": "number", "description": "标准密度 (kg/m3)"},
                    "relative_density": {"type": "number", "description": "相对密度"},
                    "high_calorific_value": {"type": "number", "description": "高位发热量 (kJ/m3)"},
                    "low_calorific_value": {"type": "number", "description": "低位发热量 (kJ/m3)"},
                    "compressibility_factor": {"type": "number", "description": "压缩因子"},
                    "ph": {"type": "number", "description": "pH 值"},
                    "tds": {"type": "number", "description": "总溶解固体 (mg/L)"},
                    "cl_ion": {"type": "number", "description": "氯离子 (mg/L)"},
                    "so4_ion": {"type": "number", "description": "硫酸根 (mg/L)"},
                    "hco3_ion": {"type": "number", "description": "碳酸氢根 (mg/L)"},
                    "co3_ion": {"type": "number", "description": "碳酸根 (mg/L)"},
                    "ca_ion": {"type": "number", "description": "钙离子 (mg/L)"},
                    "mg_ion": {"type": "number", "description": "镁离子 (mg/L)"},
                    "na_k_ion": {"type": "number", "description": "钠钾离子 (mg/L)"},
                    "oh_ion": {"type": "number", "description": "氢氧根 (mg/L)"},
                    "mineralization": {"type": "number", "description": "矿化度 (mg/L)"},
                    "total_hardness": {"type": "number", "description": "总硬度(以CaCO3计) (mg/L)"},
                    "total_alkalinity": {"type": "number", "description": "总碱度(以CaCO3计) (mg/L)"},
                    "hyj": {"type": "string", "description": "化验机构"},
                    "bz": {"type": "string", "description": "备注"}
                },
                "required": ["jh", "yplx"]
            }
        ),
        Tool(
            name="save_workover_record",
            description="将从文档中提取的修井记录数据保存到数据库。需要 ENGINEER 或 ADMIN 角色权限。",
            inputSchema={
                "type": "object",
                "properties": {
                    "jh": {"type": "string", "description": "井号（必填）"},
                    "kssj": {"type": "string", "description": "作业开始日期（YYYY-MM-DD，必填）"},
                    "jssj": {"type": "string", "description": "作业结束日期（YYYY-MM-DD）"},
                    "azlx": {"type": "string", "description": "作业类型（必填）"},
                    "azmd": {"type": "string", "description": "作业目的"},
                    "sgnr": {"type": "string", "description": "施工内容"},
                    "sgsd": {"type": "number", "description": "作业深度 (m)"},
                    "azjg": {"type": "string", "description": "作业结果"},
                    "sgdw": {"type": "string", "description": "施工单位"},
                    "rgjd": {"type": "number", "description": "人工井底 (m)"},
                    "bsqzsd": {"type": "string", "description": "泵深/气嘴深"},
                    "bjqzdx": {"type": "string", "description": "泵径/气嘴大小"},
                    "ccyz": {"type": "string", "description": "冲程/油嘴"},
                    "cc": {"type": "string", "description": "冲次"},
                    "source_file": {"type": "string", "description": "来源文件名"},
                    "source_sheet": {"type": "string", "description": "来源工作表"},
                    "source_row_no": {"type": "number", "description": "来源行号"},
                    "bz": {"type": "string", "description": "备注"}
                },
                "required": ["jh", "kssj", "azlx"]
            }
        ),
        Tool(
            name="save_perforation_record",
            description="将从文档中提取的射孔记录数据保存到数据库。需要 ENGINEER 或 ADMIN 角色权限。",
            inputSchema={
                "type": "object",
                "properties": {
                    "jh": {"type": "string", "description": "井号（必填）"},
                    "sksj": {"type": "string", "description": "射孔日期（YYYY-MM-DD，必填）"},
                    "cw": {"type": "string", "description": "层位（必填）"},
                    "sk_top": {"type": "number", "description": "射孔顶深 (m)"},
                    "sk_bot": {"type": "number", "description": "射孔底深 (m)"},
                    "skhs": {"type": "number", "description": "射孔厚度 (m)"},
                    "skqx": {"type": "string", "description": "射孔枪型"},
                    "skmd": {"type": "number", "description": "射孔密度 (孔/m)"},
                    "kj": {"type": "number", "description": "孔径 (mm)"},
                    "skfs": {"type": "string", "description": "射孔方式"},
                    "zccs_rq": {"type": "string", "description": "增产措施日期（YYYY-MM-DD）"},
                    "zccs_cw": {"type": "string", "description": "增产措施层位"},
                    "ylfs": {"type": "string", "description": "压裂方式"},
                    "ylmc": {"type": "string", "description": "液名称"},
                    "zylq_nql": {"type": "string", "description": "总液量/氮气量"},
                    "sl_ss": {"type": "string", "description": "砂量/瞬时"},
                    "bl_tbyl": {"type": "string", "description": "破裂/停泵压力"},
                    "zccs_bz": {"type": "string", "description": "增产措施备注"},
                    "source_file": {"type": "string", "description": "来源文件名"},
                    "source_sheet": {"type": "string", "description": "来源工作表"},
                    "source_row_no": {"type": "number", "description": "来源行号"},
                    "bz": {"type": "string", "description": "备注"}
                },
                "required": ["jh", "sksj", "cw"]
            }
        ),
        Tool(
            name="save_wellbore_diagram",
            description="将井身结构图的文件引用信息保存到数据库（不存储图片本身，只存储文件 ID 和元数据）。需要 ENGINEER 或 ADMIN 角色权限。",
            inputSchema={
                "type": "object",
                "properties": {
                    "jh": {"type": "string", "description": "井号（必填）"},
                    "file_id": {"type": "string", "description": "LibreChat 文件 ID（必填）"},
                    "file_name": {"type": "string", "description": "原始文件名"},
                    "file_url": {"type": "string", "description": "可访问 URL"},
                    "diagram_type": {"type": "string", "description": "图件类型（井身结构图/套管程序图/完井图等）"},
                    "image_ref_id": {"type": "string", "description": "图像引用ID（如 Excel DISPIMG ID）"},
                    "source_file": {"type": "string", "description": "来源文件名"},
                    "source_sheet": {"type": "string", "description": "来源工作表"},
                    "source_cell": {"type": "string", "description": "来源单元格位置（如 N101）"},
                    "image_seq": {"type": "number", "description": "图像序号"},
                    "scsj": {"type": "string", "description": "上传/编制日期（YYYY-MM-DD）"},
                    "ms": {"type": "string", "description": "描述/备注"}
                },
                "required": ["jh", "file_id"]
            }
        ),
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    logger.info(f"🔧 工具调用: {name}")
    user_ctx = current_user_context.get()
    try:
        if name == "save_well_analysis":
            result = save_well_analysis(data=arguments, user_role=user_ctx.role, user_id=user_ctx.user_id, user_email=user_ctx.email)
        elif name == "save_workover_record":
            result = save_workover_record(data=arguments, user_role=user_ctx.role, user_id=user_ctx.user_id, user_email=user_ctx.email)
        elif name == "save_perforation_record":
            result = save_perforation_record(data=arguments, user_role=user_ctx.role, user_id=user_ctx.user_id, user_email=user_ctx.email)
        elif name == "save_wellbore_diagram":
            result = save_wellbore_diagram(data=arguments, user_role=user_ctx.role, user_id=user_ctx.user_id, user_email=user_ctx.email)
        else:
            raise ValueError(f"未知工具: {name}")
        logger.info(f"✅ 工具执行成功: {name}")
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"❌ 工具执行失败: {name} - {str(e)}")
        return [TextContent(type="text", text=f"⚠️ 执行错误: {str(e)}")]

# ==========================================
# 通用工具函数
# ==========================================

def _check_write_permission(user_role: str) -> str | None:
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
    update_cols = [c for c in fields if c not in key_cols]
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if update_cols:
            assignments = ", ".join(f"{c} = %s" for c in update_cols)
            where_clause = " AND ".join(f"{c} = %s" for c in key_cols)
            cursor.execute(
                f"UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP "
                f"WHERE {where_clause} RETURNING id",
                [fields[c] for c in update_cols] + [fields[c] for c in key_cols],
            )
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

# ==========================================
# 业务逻辑函数
# ==========================================

@AuditLog.trace("save_well_analysis")
def save_well_analysis(data: dict, user_role: str = "GUEST",
                       user_id: str = "unknown", user_email: str = "unknown") -> str:
    err = _check_write_permission(user_role)
    if err:
        return err

    jh = (data.get("jh") or "").strip()
    yplx = (data.get("yplx") or "").strip()
    if not jh:
        return "❌ 井号（jh）不能为空。"
    if not yplx:
        return "❌ 样品类型（yplx）不能为空。"

    number_fields = {
        "ch4", "c2h6", "c3h8", "c4h10", "c5h12", "ic4h10", "nc4h10", "ic5h12", "nc5h12", "c6_plus",
        "co2", "n2", "h2s", "h2", "co", "o2",
        "molecular_weight", "standard_density", "relative_density", "high_calorific_value", "low_calorific_value", "compressibility_factor",
        "ph", "tds", "cl_ion", "so4_ion", "hco3_ion", "co3_ion", "ca_ion", "mg_ion", "na_k_ion", "oh_ion",
        "mineralization", "total_hardness", "total_alkalinity",
    }
    allowed = {"jh", "yplx", "qyrq", "cw", "bgbh", "ypbh", "ypmc", "qydd", "qyr", "cyrq", "hyj", "bz"} | number_fields

    fields: dict = {"jh": jh, "yplx": yplx}
    for k, v in data.items():
        if k in ("jh", "yplx") or k not in allowed or v is None or v == "":
            continue
        fields[k] = _parse_number(v) if k in number_fields else v

    key_cols = ["jh", "qyrq", "yplx", "cw"]
    actual_keys = [c for c in key_cols if c in fields]
    return _upsert("well_analysis", actual_keys, fields, user_email)


@AuditLog.trace("save_workover_record")
def save_workover_record(data: dict, user_role: str = "GUEST",
                         user_id: str = "unknown", user_email: str = "unknown") -> str:
    err = _check_write_permission(user_role)
    if err:
        return err

    jh = (data.get("jh") or "").strip()
    kssj = (data.get("kssj") or "").strip()
    azlx = (data.get("azlx") or "").strip()
    if not jh:
        return "❌ 井号（jh）不能为空。"
    if not kssj:
        return "❌ 作业开始日期（kssj）不能为空。"
    if not azlx:
        return "❌ 作业类型（azlx）不能为空。"

    allowed = {
        "jh", "kssj", "jssj", "azlx", "azmd", "sgnr", "sgsd", "azjg", "sgdw",
        "rgjd", "bsqzsd", "bjqzdx", "ccyz", "cc",
        "source_file", "source_sheet", "source_row_no", "bz"
    }

    fields: dict = {"jh": jh, "kssj": kssj, "azlx": azlx}
    for k, v in data.items():
        if k in ("jh", "kssj", "azlx") or k not in allowed or v is None or v == "":
            continue
        fields[k] = _parse_number(v) if k in {"sgsd", "rgjd", "source_row_no"} else v

    return _upsert("workover_records", ["jh", "kssj", "azlx"], fields, user_email)


@AuditLog.trace("save_perforation_record")
def save_perforation_record(data: dict, user_role: str = "GUEST",
                            user_id: str = "unknown", user_email: str = "unknown") -> str:
    err = _check_write_permission(user_role)
    if err:
        return err

    jh = (data.get("jh") or "").strip()
    sksj = (data.get("sksj") or "").strip()
    cw = (data.get("cw") or "").strip()
    if not jh:
        return "❌ 井号（jh）不能为空。"
    if not sksj:
        return "❌ 射孔日期（sksj）不能为空。"
    if not cw:
        return "❌ 层位（cw）不能为空。"

    number_fields = {"sk_top", "sk_bot", "skhs", "skmd", "kj", "source_row_no"}
    allowed = {
        "jh", "sksj", "cw", "skqx", "skfs",
        "zccs_rq", "zccs_cw", "ylfs", "ylmc", "zylq_nql", "sl_ss", "bl_tbyl", "zccs_bz",
        "source_file", "source_sheet", "source_row_no", "bz"
    } | number_fields

    fields: dict = {"jh": jh, "sksj": sksj, "cw": cw}
    for k, v in data.items():
        if k in ("jh", "sksj", "cw") or k not in allowed or v is None or v == "":
            continue
        fields[k] = _parse_number(v) if k in number_fields else v

    key_cols = ["jh", "sksj", "cw"]
    if "sk_top" in fields:
        key_cols.append("sk_top")
    return _upsert("perforation_records", key_cols, fields, user_email)


@AuditLog.trace("save_wellbore_diagram")
def save_wellbore_diagram(data: dict, user_role: str = "GUEST",
                          user_id: str = "unknown", user_email: str = "unknown") -> str:
    err = _check_write_permission(user_role)
    if err:
        return err

    jh = (data.get("jh") or "").strip()
    file_id = (data.get("file_id") or "").strip()
    if not jh:
        return "❌ 井号（jh）不能为空。"
    if not file_id:
        return "❌ 文件 ID（file_id）不能为空。"

    allowed = {
        "jh", "file_id", "file_name", "file_url", "diagram_type",
        "image_ref_id", "source_file", "source_sheet", "source_cell", "image_seq",
        "scsj", "ms"
    }

    fields: dict = {"jh": jh, "file_id": file_id}
    for k, v in data.items():
        if k in ("jh", "file_id") or k not in allowed or v is None or v == "":
            continue
        fields[k] = _parse_number(v) if k == "image_seq" else v

    return _upsert("wellbore_diagrams", ["jh", "file_id"], fields, user_email)


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
    print("🚀 油田作业数据 MCP Server")
    print("=" * 60)
    print("\n📌 提供工具：")
    print("  ✓ save_well_analysis - 保存分析化验数据")
    print("  ✓ save_workover_record - 保存修井记录")
    print("  ✓ save_perforation_record - 保存射孔记录")
    print("  ✓ save_wellbore_diagram - 保存井身结构图引用")
    print(f"\n🔒 权限模式: {'开发模式' if DEV_MODE else '生产模式'}")
    print(f"\n🗄️  数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("\n🌐 访问地址: http://0.0.0.0:8083")
    print("\n⏳ 服务器启动中...\n")

    uvicorn.run(app, host="0.0.0.0", port=8083, log_level="info")
