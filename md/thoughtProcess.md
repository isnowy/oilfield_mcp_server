按用户权限查询的MCP方案
1. 推荐的 MCP 开发框架
针对你的需求（数据查询、后端逻辑），Python是首选，因为油田数据分析、Pandas处理以及与现有企业数据库的连接在 Python?
A. 官方 SDK (最稳健)
名称： mcp (Python SDK)
来源： Anthropic / Model Context Protocol
特点：官方维护，底层支持最全，适合需要深度定制协议细节的场景。
适用：如果你需要完全控制生命周期、传输层（SSE/Stdio），选择这个。

B. FastMCP (开发效率最高-强烈推荐)
名称： fastmcp
特点：类似 FastAPI的体验，通过装饰器定义工具和资源。它封装了底层繁琐的协议握手，让你专注于业务逻辑。
Python业务逻辑。

C. Spring AI (如果你是 Java 技术栈)
特点：如果你们的企业后台是基于 Java/Spring Boot 的，Spring AI 最近增加了对 MCP Spring Security Service

2. 系统设计架构
在设计这个 MCP Server 时，核心挑战在于**“按用户权限 (RBAC)”**。MCP的执行层，而不是 Prompt

核心设计三要素
Resources (资源 - 用于读取静态/实时上下文)
  Reference: Resource。
  URI 模式： oilfield://wells/{well_id}/realtime
  LLM ​Context:
Tools (工具 - 用于执行查询)
  SQL Server 2018
  工具示例：
   search_wells_by_region(region_name)
   get_drilling_parameters(well_id, start_time, end_time, params=['rop', 'wob'])(钻压、钻速等)
   get_mud_logging_data(well_id, depth_range)
Prompts (提示词模板)
预设一些常用的分析模板，例如：“分析该井段的工程异常”。

3. 关键难点：如何设计“权限控制”？
在 MCP 中，AI 客户端（如 Claude Desktop 或 IDE）连接到你的 Server。通常这是一个本地连接或通过 SSE的长连接。

鉴权方案推荐：

方案 A：基于环境上下文的鉴权 (Token Passing)
MCP Server User Manual
MCP Server page: Server page IAM (Identity and Access Management) page
Tool 内部鉴权：
  不要在 Prompt 里写“请只查询我有权限的数据”。
  必须在 Python 代码中拦截：
Python
@mcp.tool()
def get_drilling_data(well_id: str, ctx: Context) -> str:
    # 1. 获取当前用户身份 (通常通过 Server 初始化时的 Env 或 Header 传递)
    current_user = ctx.request_context.meta.get("user_id")

    # 2. 调用内部权限服务检查
    if not permission_service.can_access(user_id=current_user, well_id=well_id):
        return "Error: Permission Denied. You do not have access to Well " + well_id

    # 3. 执行查询
    return database.query(...)
方案 B：行级安全 (Row-Level Security) 数据库层
Download MCP from PostgreSQL to RLS from MCP Server户的数据库账号（或通过 Session模拟）连接，数据据行。

4. FastMCP
Python version

Python

from fastmcp import FastMCP
from pydantic import Field
from typing import List

# 初始化 MCP Server
mcp = FastMCP("Oilfield Data Server")

# 模拟的权限系统
def check_permission(user_role: str, well_id: str) -> bool:
    # 实际场景中这里会调用 LDAP 或 数据库
    if user_role == "admin":
        return True
    if user_role == "engineer" and well_id.startswith("OPEN_"):
        return True
    return False

# 模拟数据库数据
MOCK_DATA = {
    "OPEN_001": {"depth": 3500, "rop": 25.5, "status": "Drilling"},
    "SECURE_999": {"depth": 5200, "rop": 12.0, "status": "Casing"},
}

@mcp.tool()
def query_well_status(
    well_id: str = Field(..., description="The unique identifier of the oil well (e.g., OPEN_001)"),
    user_role: str = Field("engineer", description="Current user role context") # 实际部署时应由 System Prompt 自动注入或 Env 注入
) -> str:
    """
    根据井号查询当前的钻井状态（井深、钻速、工况）。
    """
    
    # 1. 权限拦截
    if not check_permission(user_role, well_id):
        return f"🚫 权限拒绝: 用户 ({user_role}) 无权访问井号 {well_id} 的敏感数据。"

    # 2. 数据获取
    data = MOCK_DATA.get(well_id)
    if not data:
        return f"未找到井号 {well_id} 的数据。"

    # 3. 返回结构化文本
    return f"""
    === 井号: {well_id} ===
    当前井深: {data['depth']} m
    机械钻速: {data['rop']} m/h
    当前工况: {data['status']}
    """

if __name__ == "__main__":
    mcp.run()
5. 针对油田数据的最佳实践建议
单位转换标准化：

AI Tool的输出中，强制明确单位。不要返回{"depth": 3000},要返回{"depth_meters": 3000}或在描述中写明。

Note:

不要一次性返回数万条测井曲线数据给Window。

设计工具支持**“降采样”或“统计特征”**。例如：get_average_params(interval='1h')。

数据脱敏：

在 MCP 输出层增加一个Middleware, Middleware

总结
Download FastMCP (Python ) version

User Manual SQL Tool

不能依赖 AI 的自觉性。

WITSML 标准或自定义SQLFastMCP SQLAlchemy Guide
钻井业务数据繁多，我应该怎么在一个MCP服务上合理设计多个TOOL并暴露给LLM？

Drilling​ ​Data: Depth-based technology中设计不当（例如把几百个字段拆成几百个 Tool，或者搞一个万能 Tool），LLM会陷入选择困难或上下文爆炸。
建议采用“按业务维度分层 + 动态聚合”的策略来设计 Tool。以下是具体的架构建议：

1. 核心设计原则：三个维度
不要按照数据库表结构设计Tool，要按照工程师的提三个维度：

返回文本/摘要）。

工程/深度维度：地质导向、钻具组合、井身结构（返回结构化对象）。

Reference : WITS/WITSML (ROP, WOB, Torque)

2. 推荐的 Tool 清单设计 (由粗到细)
90% 的场景。

第一层：发现与概览 (Discovery)
Tool 1: search_wells(井号检索)

目的：LLM 通常不知道准确的井号（如Zhong-102-3），需要模糊搜索。

参数：

keyword(string): 井号关键字或区块名。

status(enum): 'Active' (在钻), 'Completed' (完井), 'All'.

返回：井号列表、井型、当前井深、所属区块。

Tool 2: get_well_summary(单井画像)

目的：获取该井的“身份证”信息。

参数：well_id。

返回：设计井深、当前井深、开钻日期、钻井队、当前工况（Activity Code）。

第二层：工程与日报 (Engineering & Reporting)
Tool 3: get_daily_report(日报查询 - DDR)

目的：查询某天发生了什么（非结构化数据的重灾区）。

参数：

well_id

date(YYYY-MM-DD)

section(enum, optional): 'mud' (泥浆), 'bit' (钻头), 'npt' (非生产时间), 'remarks' (备注).

技巧：如果 LLM 问“上周有什么事故”，它会多次调用此 Tool Note get_npt_events:

Tool 4: get_bha_config(钻具组合)

目的：BHA）

参数：well_id, depth_range(井段).

第三层：曲线与参数 (Data Curves - 最难点)
Tool 5: fetch_drilling_curves(获取曲线数据)

痛点：数据量太大。数据库可能有 10 万个点。

Downloaded from www.downsampling.com

参数：

well_id

start_depth/ end_depth(可选，默认当前井段)

channels(list): ['ROP', 'WOB', 'Torque', 'RPM', 'Gamma'] (支持简写).

resolution(string): '1m' (每米一个点), '10m', 'raw' (原始数据，慎用).

返回：JSON 格式的序列数据，限制最大返回点数（如 500 点）。如果超过，提示 LLM缩小范围。

3. 如何解决“数据太多撑爆 LLM 上下文”？
不要把原始数据丢给 LLM 处理。

策略 A：内置统计分析 Tool
ROP 数据让 LLM 算。
 增加Tool :analyze_interval_data
 逻辑：Server is SQL SELECT AVG(rop), MAX(torque) ...。
 返回：{"avg_rop": 25.4, "max_torque": 15000}。直接给结果。

策略 B：利用 MCP Resources (资源)
不要做成​Tool，要做成MCP Resources。
 URI :oilfield://wells/{id}/geology_plan
 用法：用户在 Prompt 中可以引用这些资源，LLM读取一次后作为背景知识，不需要反复调用工具查询。
4. 示例：Schema 定义 (FastMCP 写法)
from fastmcp import FastMCP
from pydantic import Field
from typing import List, Literal

mcp = FastMCP("DrillingDataService")

@mcp.tool()
def fetch_drilling_curves(
    well_id: str,
    channels: List[str] = Field(..., description="List of mnemonics to fetch. E.g. ['ROP', 'GR', 'HKLD']"),
    start_depth: float = Field(0.0, description="Start depth in meters"),
    end_depth: float = Field(..., description="End depth in meters"),
    step: int = Field(1, description="Resample step in meters. Increase this if range is large.")
):
    """
    Retrieve depth-based drilling log data. 
    IMPORTANT: Always specify a 'step' >= 10 if querying more than 1000m interval 
    to avoid context overflow.
    """
    # 1. 校验 channels 是否有效
    # 2. 校验 (end_depth - start_depth) / step 是否 > 2000 点
    #    如果太大，自动调大 step 并警告，或者返回 Error 提示 "Range too large, please increase step"
    # 3. SQL 查询并返回 JSON
    pass

5. 给 LLM 的“系统提示词” (System Prompt) 配合
MCP Software Tool Software端配置如下 System Prompt：

"你是一个专业的钻井数据助手。

先使用search_wells确认井号。

数据节约：查询曲线数据 ( fetch_drilling_curves)以step=10避免数据量过大。

单位：默认所有深度为米 (m)，压力为 MPa，除非用户特别指定英制。"

总结设计思路
1.少即是多：把 Tool 合并，通过参数（Type/Category）
2.计算下沉：把“求平均”、“找最大值”、“统计进尺”等逻辑写在 Tool 内部（SQL/Pandas），只给 LLM返回统计结果。
3.防御性编程：在 Tool 一次性索要整口井的数据导致 Crash。

为了达到“生产部署级”的标准，我在代码中增加了以下关键特性：
1.Pydantic School of Medicine LLM School of Medicine
2.错误处理 (Error Handling)，返回友好的错误提示，而不是让 Server 崩溃。
3.模拟数据库层 (Mock DB Layer)：你只需在RealDatabase类中填入 SQL查询即可无缝替换。
4.Download Docstring : MCP:

1. 依赖安装
pip install fastmcp pydantic
2. 完整Python 代码 ( oilfield_mcp.py)
from fastmcp import FastMCP
from pydantic import Field
from typing import List, Optional, Dict, Literal
from datetime import datetime

# ==========================================
# 1. 服务初始化
# ==========================================
mcp = FastMCP(
    "Oilfield Drilling Intel",
    description="专门用于查询油田钻井数据、日报(DDR)及工程参数的 MCP 服务。",
    dependencies=["pandas", "sqlalchemy"] # 声明依赖（仅作元数据）
)

# ==========================================
# 2. 模拟数据层 (生产环境请替换为 SQL)
# ==========================================
class DatabaseService:
    """
    数据访问层 (DAO)。
    在生产环境中，请将这里的字典查找替换为 SQLAlchemy 或 SQL 查询。
    """
    def __init__(self):
        # 模拟井基本信息表
        self.wells = {
            "ZT-102": {"id": "ZT-102", "name": "Zhong-102", "block": "Block A", "status": "Active", "type": "Horizontal", "current_depth": 3550.0, "design_depth": 4200.0, "spud_date": "2023-10-01", "team": "Team-701", "activity": "Drilling 8.5 inch section"},
            "ZT-105": {"id": "ZT-105", "name": "Zhong-105", "block": "Block A", "status": "Completed", "type": "Vertical", "current_depth": 3800.0, "design_depth": 3800.0, "spud_date": "2023-08-15", "team": "Team-702", "activity": "Rig Release"},
            "XJ-009": {"id": "XJ-009",  "name": "XinJiang-009", "block": "Block B", "status": "Active", "type": "Directional", "current_depth": 1200.0, "design_depth": 5000.0, "spud_date": "2023-11-20", "team": "Team-905", "activity": "Tripping out"},
        }
        
        # 模拟日报表 (DDR)
        self.reports = {
            "ZT-102_2023-11-01": {
                "mud": "MW: 1.25 sg, Vis: 65s, PV/YP: 15/12. No losses observed.",
                "bit": "Bit #4, Type: PDC, Size: 8.5in. Grading: 1-1-WT-A-X-I-NO-TD.",
                "npt": "None. 24hrs productive time.",
                "remarks": "Drilling ahead smoothly. Formation change expected at 3600m."
            },
            "ZT-102_2023-11-02": {
                "mud": "MW: 1.28 sg. Increased density due to gas reading.",
                "bit": "Bit #4 continuing.",
                "npt": "2.5 hrs. Repairing top drive hydraulic hose.",
                "remarks": "Encountered high torque spikes around 04:00."
            }
        }

        # 模拟 BHA 表
        self.bha_configs = {
            "ZT-102": [
                {"run": 1, "top_depth": 0, "bottom_depth": 1000, "components": ["Bit 17.5", "Motor 9.625", "MWD"]},
                {"run": 2, "top_depth": 1000, "bottom_depth": 3000, "components": ["Bit 12.25", "RSS", "LWD-GR-Res", "NMDC"]},
                {"run": 3, "top_depth": 3000, "bottom_depth": 4200, "components": ["Bit 8.5", "Motor", "MWD", "Stab"]}
            ]
        }

    def search_wells(self, keyword: str, status: str) -> List[Dict]:
        results = []
        for w in self.wells.values():
            # 简单的包含逻辑
            match_key = (keyword.lower() in w['name'].lower() or keyword.lower() in w['block'].lower())
            match_status = (status == "All" or w['status'] == status)
            if match_key and match_status:
                results.append(w)
        return results

    def get_well(self, well_id: str) -> Optional[Dict]:
        return self.wells.get(well_id)

    def get_report(self, well_id: str, date_str: str) -> Optional[Dict]:
        key = f"{well_id}_{date_str}"
        return self.reports.get(key)
    
    def get_bha(self, well_id: str) -> List[Dict]:
        return self.bha_configs.get(well_id, [])

# 实例化 DB 服务
db = DatabaseService()

# ==========================================
# 3. Tool 定义 (Layer 1: Discovery)
# ==========================================

@mcp.tool()
def search_wells(
    keyword: str = Field(..., description="Keywords for search, such as well name (e.g., 'ZT') or block name."),
    status: Literal["Active", "Completed", "All"] = Field("Active", description="Filter by well status. Defaults to 'Active'.")
) -> str:
    """
    Search for oil wells based on vague keywords. 
    Use this when the user does not provide a precise Well ID.
    """
    results = db.search_wells(keyword, status)
    
    if not results:
        return f"No wells found matching keyword '{keyword}' with status '{status}'."

    # 格式化输出为 Markdown 表格，方便 LLM 阅读
    output = f"Found {len(results)} wells:\n\n"
    output += "| Well ID | Name | Block | Status | Current Depth |\n"
    output += "|---|---|---|---|---|\n"
    for r in results:
        output += f"| {r['id']} | {r['name']} | {r['block']} | {r['status']} | {r['current_depth']}m |\n"
    
    return output

@mcp.tool()
def get_well_summary(
    well_id: str = Field(..., description="The unique identifier of the well (e.g., 'ZT-102')")
) -> str:
    """
    Get the 'ID Card' or comprehensive summary of a specific well.
    Includes spud date, contractor, and current activity code.
    """
    well = db.get_well(well_id)
    if not well:
        return f"Error: Well ID '{well_id}' not found in database."

    return f"""
### Well Summary: {well['name']} ({well['id']})
- **Block**: {well['block']}
- **Status**: {well['status']}
- **Type**: {well['type']}
- **Current Depth**: {well['current_depth']} m
- **Design Depth**: {well['design_depth']} m
- **Spud Date**: {well['spud_date']}
- **Drilling Team**: {well['team']}
- **Current Activity**: {well['activity']}
    """

# ==========================================
# 4. Tool 定义 (Layer 2: Engineering)
# ==========================================

@mcp.tool()
def get_daily_report(
    well_id: str = Field(..., description="Well ID"),
    date: str = Field(..., description="Report date in YYYY-MM-DD format"),
    section: Optional[Literal["mud", "bit", "npt", "remarks"]] = Field(None, description="Specific section to extract. If None, returns full report.")
) -> str:
    """
    Retrieve the Daily Drilling Report (DDR) text. 
    Use this to analyze events, accidents, or specifications for a specific day.
    """
    # 简单的日期格式校验
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format."

    report = db.get_report(well_id, date)
    
    if not report:
        return f"No report found for well {well_id} on {date}."

    if section:
        # 只返回特定部分，节省 Token
        content = report.get(section, "N/A")
        return f"### DDR {section.upper()} ({date})\n{content}"
    else:
        # 返回全量
        return f"""
### Daily Report for {well_id} on {date}
- **Mud**: {report['mud']}
- **Bit**: {report['bit']}
- **NPT**: {report['npt']}
- **Remarks**: {report['remarks']}
        """

@mcp.tool()
def get_bha_config(
    well_id: str = Field(..., description="Well ID"),
    depth_range: str = Field(..., description="Depth range of interest, e.g., '2000-3000' or 'bottom'.")
) -> str:
    """
    Get Bottom Hole Assembly (BHA) configuration. 
    Shows what tools (Bit, Motor, MWD) were used in a specific depth interval.
    """
    bha_list = db.get_bha(well_id)
    if not bha_list:
        return f"No BHA records found for {well_id}."

    # 解析请求的深度范围 (简单逻辑)
    target_top = 0.0
    target_bottom = 99999.0
    
    if "-" in depth_range:
        try:
            parts = depth_range.split("-")
            target_top = float(parts[0])
            target_bottom = float(parts[1])
        except:
            return "Error: depth_range format should be 'start-end' (e.g. 2000-3000)."
    
    # 筛选逻辑：查找与请求区间有重叠的 BHA Run
    matched_runs = []
    for run in bha_list:
        # 判断区间重叠 logic: max(start1, start2) < min(end1, end2)
        overlap_start = max(target_top, run['top_depth'])
        overlap_end = min(target_bottom, run['bottom_depth'])
        
        if overlap_start < overlap_end:
            matched_runs.append(run)

    if not matched_runs:
        return f"No BHA found overlapping depth {depth_range}."

    output = f"### BHA Configuration ({depth_range} m)\n"
    for run in matched_runs:
        components_str = " -> ".join(run['components'])
        output += f"- **Run #{run['run']}** ({run['top_depth']}-{run['bottom_depth']}m): {components_str}\n"
    
    return output

# ==========================================
# 5. 启动入口
# ==========================================
if __name__ == "__main__":
    # 运行 MCP Server
    # 开发模式下可以使用 stdio，或者 SSE
    print("Starting Oilfield Drilling Data MCP Server...")
    mcp.run()


这是一个可以直实现方案。

为了达到“生产部署级”的标准，我在代码中增加了以下关键特性：

Pydantic School of Medicine LLM School of Medicine

错误处理 (Error Handling)，返回友好的错误提示，而不是让 Server 崩溃。

模拟数据库层 (Mock DB Layer)：你只需在RealDatabase类中填入 SQL查询即可无缝替换。

Download Docstring : MCP:

1. 依赖安装
Bash

pip install fastmcp pydantic
2. 完整Python 代码 ( oilfield_mcp.py)
Python

from fastmcp import FastMCP
from pydantic import Field
from typing import List, Optional, Dict, Literal
from datetime import datetime

# ==========================================
# 1. 服务初始化
# ==========================================
mcp = FastMCP(
    "Oilfield Drilling Intel",
    description="专门用于查询油田钻井数据、日报(DDR)及工程参数的 MCP 服务。",
    dependencies=["pandas", "sqlalchemy"] # 声明依赖（仅作元数据）
)

# ==========================================
# 2. 模拟数据层 (生产环境请替换为 SQL)
# ==========================================
class DatabaseService:
    """
    数据访问层 (DAO)。
    在生产环境中，请将这里的字典查找替换为 SQLAlchemy 或 SQL 查询。
    """
    def __init__(self):
        # 模拟井基本信息表
        self.wells = {
            "ZT-102": {"id": "ZT-102", "name": "Zhong-102", "block": "Block A", "status": "Active", "type": "Horizontal", "current_depth": 3550.0, "design_depth": 4200.0, "spud_date": "2023-10-01", "team": "Team-701", "activity": "Drilling 8.5 inch section"},
            "ZT-105": {"id": "ZT-105", "name": "Zhong-105", "block": "Block A", "status": "Completed", "type": "Vertical", "current_depth": 3800.0, "design_depth": 3800.0, "spud_date": "2023-08-15", "team": "Team-702", "activity": "Rig Release"},
            "XJ-009": {"id": "XJ-009",  "name": "XinJiang-009", "block": "Block B", "status": "Active", "type": "Directional", "current_depth": 1200.0, "design_depth": 5000.0, "spud_date": "2023-11-20", "team": "Team-905", "activity": "Tripping out"},
        }
        
        # 模拟日报表 (DDR)
        self.reports = {
            "ZT-102_2023-11-01": {
                "mud": "MW: 1.25 sg, Vis: 65s, PV/YP: 15/12. No losses observed.",
                "bit": "Bit #4, Type: PDC, Size: 8.5in. Grading: 1-1-WT-A-X-I-NO-TD.",
                "npt": "None. 24hrs productive time.",
                "remarks": "Drilling ahead smoothly. Formation change expected at 3600m."
            },
            "ZT-102_2023-11-02": {
                "mud": "MW: 1.28 sg. Increased density due to gas reading.",
                "bit": "Bit #4 continuing.",
                "npt": "2.5 hrs. Repairing top drive hydraulic hose.",
                "remarks": "Encountered high torque spikes around 04:00."
            }
        }

        # 模拟 BHA 表
        self.bha_configs = {
            "ZT-102": [
                {"run": 1, "top_depth": 0, "bottom_depth": 1000, "components": ["Bit 17.5", "Motor 9.625", "MWD"]},
                {"run": 2, "top_depth": 1000, "bottom_depth": 3000, "components": ["Bit 12.25", "RSS", "LWD-GR-Res", "NMDC"]},
                {"run": 3, "top_depth": 3000, "bottom_depth": 4200, "components": ["Bit 8.5", "Motor", "MWD", "Stab"]}
            ]
        }

    def search_wells(self, keyword: str, status: str) -> List[Dict]:
        results = []
        for w in self.wells.values():
            # 简单的包含逻辑
            match_key = (keyword.lower() in w['name'].lower() or keyword.lower() in w['block'].lower())
            match_status = (status == "All" or w['status'] == status)
            if match_key and match_status:
                results.append(w)
        return results

    def get_well(self, well_id: str) -> Optional[Dict]:
        return self.wells.get(well_id)

    def get_report(self, well_id: str, date_str: str) -> Optional[Dict]:
        key = f"{well_id}_{date_str}"
        return self.reports.get(key)
    
    def get_bha(self, well_id: str) -> List[Dict]:
        return self.bha_configs.get(well_id, [])

# 实例化 DB 服务
db = DatabaseService()

# ==========================================
# 3. Tool 定义 (Layer 1: Discovery)
# ==========================================

@mcp.tool()
def search_wells(
    keyword: str = Field(..., description="Keywords for search, such as well name (e.g., 'ZT') or block name."),
    status: Literal["Active", "Completed", "All"] = Field("Active", description="Filter by well status. Defaults to 'Active'.")
) -> str:
    """
    Search for oil wells based on vague keywords. 
    Use this when the user does not provide a precise Well ID.
    """
    results = db.search_wells(keyword, status)
    
    if not results:
        return f"No wells found matching keyword '{keyword}' with status '{status}'."

    # 格式化输出为 Markdown 表格，方便 LLM 阅读
    output = f"Found {len(results)} wells:\n\n"
    output += "| Well ID | Name | Block | Status | Current Depth |\n"
    output += "|---|---|---|---|---|\n"
    for r in results:
        output += f"| {r['id']} | {r['name']} | {r['block']} | {r['status']} | {r['current_depth']}m |\n"
    
    return output

@mcp.tool()
def get_well_summary(
    well_id: str = Field(..., description="The unique identifier of the well (e.g., 'ZT-102')")
) -> str:
    """
    Get the 'ID Card' or comprehensive summary of a specific well.
    Includes spud date, contractor, and current activity code.
    """
    well = db.get_well(well_id)
    if not well:
        return f"Error: Well ID '{well_id}' not found in database."

    return f"""
### Well Summary: {well['name']} ({well['id']})
- **Block**: {well['block']}
- **Status**: {well['status']}
- **Type**: {well['type']}
- **Current Depth**: {well['current_depth']} m
- **Design Depth**: {well['design_depth']} m
- **Spud Date**: {well['spud_date']}
- **Drilling Team**: {well['team']}
- **Current Activity**: {well['activity']}
    """

# ==========================================
# 4. Tool 定义 (Layer 2: Engineering)
# ==========================================

@mcp.tool()
def get_daily_report(
    well_id: str = Field(..., description="Well ID"),
    date: str = Field(..., description="Report date in YYYY-MM-DD format"),
    section: Optional[Literal["mud", "bit", "npt", "remarks"]] = Field(None, description="Specific section to extract. If None, returns full report.")
) -> str:
    """
    Retrieve the Daily Drilling Report (DDR) text. 
    Use this to analyze events, accidents, or specifications for a specific day.
    """
    # 简单的日期格式校验
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: Date must be in YYYY-MM-DD format."

    report = db.get_report(well_id, date)
    
    if not report:
        return f"No report found for well {well_id} on {date}."

    if section:
        # 只返回特定部分，节省 Token
        content = report.get(section, "N/A")
        return f"### DDR {section.upper()} ({date})\n{content}"
    else:
        # 返回全量
        return f"""
### Daily Report for {well_id} on {date}
- **Mud**: {report['mud']}
- **Bit**: {report['bit']}
- **NPT**: {report['npt']}
- **Remarks**: {report['remarks']}
        """

@mcp.tool()
def get_bha_config(
    well_id: str = Field(..., description="Well ID"),
    depth_range: str = Field(..., description="Depth range of interest, e.g., '2000-3000' or 'bottom'.")
) -> str:
    """
    Get Bottom Hole Assembly (BHA) configuration. 
    Shows what tools (Bit, Motor, MWD) were used in a specific depth interval.
    """
    bha_list = db.get_bha(well_id)
    if not bha_list:
        return f"No BHA records found for {well_id}."

    # 解析请求的深度范围 (简单逻辑)
    target_top = 0.0
    target_bottom = 99999.0
    
    if "-" in depth_range:
        try:
            parts = depth_range.split("-")
            target_top = float(parts[0])
            target_bottom = float(parts[1])
        except:
            return "Error: depth_range format should be 'start-end' (e.g. 2000-3000)."
    
    # 筛选逻辑：查找与请求区间有重叠的 BHA Run
    matched_runs = []
    for run in bha_list:
        # 判断区间重叠 logic: max(start1, start2) < min(end1, end2)
        overlap_start = max(target_top, run['top_depth'])
        overlap_end = min(target_bottom, run['bottom_depth'])
        
        if overlap_start < overlap_end:
            matched_runs.append(run)

    if not matched_runs:
        return f"No BHA found overlapping depth {depth_range}."

    output = f"### BHA Configuration ({depth_range} m)\n"
    for run in matched_runs:
        components_str = " -> ".join(run['components'])
        output += f"- **Run #{run['run']}** ({run['top_depth']}-{run['bottom_depth']}m): {components_str}\n"
    
    return output

# ==========================================
# 5. 启动入口
# ==========================================
if __name__ == "__main__":
    # 运行 MCP Server
    # 开发模式下可以使用 stdio，或者 SSE
    print("Starting Oilfield Drilling Data MCP Server...")
    mcp.run() 


3. 代码设计解读与部署建议
A. 为什么用fastmcp+ pydantic?
 Promptfastmcp Python Type DocstringHints LLM JSON Schema
    LLMget_daily_report​section​Literal​
 Python version of Markdown
    原因：JSON 虽然精确，但 Token 消耗大且阅读性差。Markdown 表格（如search_wells的返回）对于 Claude Token token
B. 生产环境如何对接库？
DatabaseServiceOracle 或 PostgreSQL 中。

SQLAlchemy 改造示例：
# 替换 DatabaseService.search_wells 方法
def search_wells(self, keyword: str, status: str) -> List[Dict]:
    with self.session_scope() as session:
        query = session.query(WellModel).filter(
            WellModel.name.ilike(f"%{keyword}%")
        )
        if status != "All":
            query = query.filter(WellModel.status == status)
        
        results = query.all()
        # 转换为 Dict 返回
        return [row.to_dict() for row in results]
		
C.你可以使用mcp官方提供的 Inspector,
# 在终端中运行 inspector 进行交互式调试
npx @modelcontextprotocol/inspector python oilfield_mcp.py

在 Inspector 界面中，你可以模拟 LLM 发送请求：
Call Tool : search_wells-> Arguments:{"keyword": "ZT", "status": "All"}
Call Tool : get_daily_report-> Arguments:{"well_id": "ZT-102", "date": "2023-11-01", "section": "npt"}
Copilot 的后端核心。


问：提供更详细的代码实现，包含整个调用过程的状态跟踪
“ State Tracking & Auditing” MCP 实现。

在企业级应用中，单纯的“调用工具”是不够的。我们需要知道：

Who & When : 谁在什么时间调用了工具？

Input/Output : 传入了什么参数？返回了什么结果？

Performance : 查询耗时多久？（用于优化慢查询）

Error Trace : 如果报错，堆栈是什么？

Python 的装饰器模式 (Decorator Pattern)来包裹所有的 MCP工具。这样可以将“业务逻辑”与“监控逻辑”解耦。
核心架构图解
1.Request : LLM 发起调用。
2.Trace IDAudit Layer :
3.Logic Layer : 执行具体的数据库查询。
4.Response : 返回结果，Audit Layer 拦截并记录“结束状态”和耗时。
完整代码实现 ( oilfield_advanced_mcp.py)
你可以直接保存并运行此文件。
import time
import uuid
import json
import logging
import functools
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
from fastmcp import FastMCP, Context
from pydantic import Field

# ==========================================
# 1. 基础设施层：日志与状态追踪
# ==========================================

# 配置结构化日志 (JSON Logs)，方便接入 ELK 或 Splunk
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DrillingMCP")

class AuditTracker:
    """
    负责跟踪工具调用的状态、耗时和结果。
    """
    @staticmethod
    def log_execution(tool_name: str):
        """
        装饰器：用于包裹 MCP Tool，自动处理日志和错误追踪
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 1. 生成唯一的追踪 ID (Trace ID)
                trace_id = str(uuid.uuid4())[:8]
                start_time = time.time()
                
                # 2. 记录调用开始 (State: STARTED)
                # 注意：实际生产中这里不要打印敏感密码/Token
                logger.info(json.dumps({
                    "event": "TOOL_START",
                    "trace_id": trace_id,
                    "tool": tool_name,
                    "params": str(kwargs)  # 简化参数打印
                }, ensure_ascii=False))

                try:
                    # 3. 执行实际业务逻辑
                    result = func(*args, **kwargs)
                    
                    # 4. 计算耗时
                    duration = round((time.time() - start_time) * 1000, 2)
                    
                    # 5. 记录调用成功 (State: SUCCESS)
                    logger.info(json.dumps({
                        "event": "TOOL_SUCCESS",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "duration_ms": duration,
                        "result_preview": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                    }, ensure_ascii=False))
                    
                    return result

                except Exception as e:
                    # 6. 记录异常 (State: ERROR)
                    duration = round((time.time() - start_time) * 1000, 2)
                    logger.error(json.dumps({
                        "event": "TOOL_ERROR",
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "duration_ms": duration,
                        "error": str(e)
                    }, ensure_ascii=False))
                    
                    # 返回友好的错误信息给 LLM，而不是抛出 Python 异常导致连接断开
                    return f"⚠️ System Error (TraceID: {trace_id}): The tool failed to execute. Reason: {str(e)}"
            return wrapper
        return decorator

# ==========================================
# 2. 数据层：模拟企业数据库 (Mock DB)
# ==========================================

class DrillingDatabase:
    def __init__(self):
        self.wells = [
            {"id": "ZT-102", "name": "Zhong-102", "block": "Block A", "status": "Active", "depth": 3550, "spud_date": "2023-10-01", "team": "Team-701"},
            {"id": "ZT-105", "name": "Zhong-105", "block": "Block A", "status": "Completed", "depth": 3800, "spud_date": "2023-08-15", "team": "Team-702"},
            {"id": "XJ-009", "name": "XinJiang-009", "block": "Block B", "status": "Active", "depth": 1200, "spud_date": "2023-11-20", "team": "Team-905"},
        ]
        self.reports = {
            "ZT-102_2023-11-01": {"mud": "MW: 1.25 sg", "bit": "Bit #4 PDC", "npt": "None", "remarks": "Drilling ahead."},
            "ZT-102_2023-11-02": {"mud": "MW: 1.28 sg", "bit": "Bit #4 PDC", "npt": "2.5 hrs repair", "remarks": "Torque spike."}
        }
        self.bha = {
            "ZT-102": [{"run": 1, "start": 0, "end": 1000, "comp": "Bit 17.5->Motor"}, {"run": 2, "start": 1000, "end": 3550, "comp": "Bit 12.25->RSS->LWD"}]
        }

    def query_wells(self, keyword, status):
        # 模拟 0.1秒 延迟
        time.sleep(0.1)
        return [w for w in self.wells if (keyword.lower() in w['name'].lower()) and (status == "All" or w['status'] == status)]

db = DrillingDatabase()

# ==========================================
# 3. MCP 服务定义
# ==========================================

mcp = FastMCP("Advanced Oilfield Server")

# ==========================================
# 4. Tool 实现 (应用了状态追踪)
# ==========================================

# --- Layer 1: Discovery ---

@mcp.tool()
@AuditTracker.log_execution("search_wells") # <--- 应用追踪装饰器
def search_wells(
    keyword: str = Field(..., description="Keywords for search (e.g., 'ZT' or 'Block A')"),
    status: Literal["Active", "Completed", "All"] = "Active"
) -> str:
    """模糊搜索井号。返回 Markdown 格式列表。"""
    
    wells = db.query_wells(keyword, status)
    
    if not wells:
        return f"No wells found for '{keyword}' ({status})."
    
    # 构造 Markdown 表格
    md = f"Found {len(wells)} wells:\n\n"
    md += "| Well ID | Name | Status | Depth |\n|---|---|---|---|\n"
    for w in wells:
        md += f"| {w['id']} | {w['name']} | {w['status']} | {w['depth']}m |\n"
    return md

@mcp.tool()
@AuditTracker.log_execution("get_well_summary")
def get_well_summary(well_id: str) -> str:
    """获取单井详情画像。"""
    # 模拟查找
    well = next((w for w in db.wells if w['id'] == well_id), None)
    
    if not well:
        # 抛出异常测试 Error Log 是否工作
        raise ValueError(f"Well ID {well_id} does not exist in registry.")
    
    return f"""
    === 🆔 Well Profile: {well['name']} ===
    - ID: {well['id']}
    - Team: {well['team']}
    - Spud Date: {well['spud_date']}
    - Status: {well['status']}
    """

# --- Layer 2: Engineering ---

@mcp.tool()
@AuditTracker.log_execution("get_daily_report")
def get_daily_report(
    well_id: str, 
    date: str, 
    section: Optional[Literal["mud", "bit", "npt", "remarks"]] = None
) -> str:
    """获取日报(DDR)。支持只获取特定段落。"""
    key = f"{well_id}_{date}"
    report = db.reports.get(key)
    
    if not report:
        return f"📝 No DDR found for {well_id} on {date}."
    
    if section:
        return f"**{section.upper()}**: {report.get(section, 'N/A')}"
    
    return json.dumps(report, indent=2)

@mcp.tool()
@AuditTracker.log_execution("get_bha_config")
def get_bha_config(well_id: str, depth_range: str) -> str:
    """查询 BHA 钻具组合。"""
    bha_list = db.bha.get(well_id, [])
    if not bha_list: 
        return "No BHA data."
    
    # 简化的逻辑，直接返回所有 Run 供展示
    return "\n".join([f"Run {b['run']} ({b['start']}-{b['end']}m): {b['comp']}" for b in bha_list])

# ==========================================
# 5. 启动
# ==========================================
if __name__ == "__main__":
    print("🚀 Advanced Oilfield MCP Server Started with Audit Logging...")
    # 在终端运行，FastMCP 默认使用 stdio 模式
    mcp.run()

代码深度解析：状态追踪是如何工作的？
AuditTrackerLLM 调用search_wells时，后台发生了什么：

1. 拦截与 ID 生成
当请求到达时，装饰器@AuditTracker.log_execution首先被触发。它生成一个Trace ID（例如a1b2c3d4）。
 Description : LLM
2. 开始状态 (STARTED)
Using JSON
{
  "event": "TOOL_START",
  "trace_id": "a1b2c3d4",
  "tool": "search_wells",
  "params": "{'keyword': 'ZT', 'status': 'Active'}"
}
用途：如果系统卡住了，你可以通过这个日志知道“请求进来了，但没出去”，从而定位是数据库死锁还是网络超时。
3. 异常捕获 (ERROR Handling)
代码get_well_summary不会Crashtry...except​
{
  "event": "TOOL_ERROR",
  "trace_id": "x9y8z7w6",
  "tool": "get_well_summary",
  "duration_ms": 45.2,
  "error": "Well ID ZT-999 does not exist..."
}
LLM Program⚠️ System Error (TraceID: x9y8z7w6): The tool failed to execute...
意义：LLM看到这个错误后，会尝试自我修正（例如：“抱歉，我可能输错了井号，我先搜索一下”），而不是直接断开连接。

4. 性能监控 (Performance)
日志中包含duration_ms。
Application : get_bha_config5000ms, 5000ms, 5000ms SQL Server


下一步优化建议
1.Context 传递用户信息： FastMCP从中ctx: Context提取 Request Header 中的 User ctxID，并记录到日志中。这样就实现了“张三在 10:00 查询了 ZT-102 井”的审计功能。
@mcp.tool()
def sensitive_query(ctx: Context, well_id: str):
    user = ctx.request_context.meta.get("user") # 获取用户信息
    logger.info(f"User {user} accessing {well_id}")
2.异步日志：目前的logger.info是同步的。如果并发量极高，建议将日志发送逻辑放入asyncio.create_task或使用消This is how Kafka/RabbitMQ works.


现在提供更详细钻井业务数据的查询代码实现(曲线数据和实时的数据获取除外)
这是一个非常扎实的工程需求. Curves）和毫秒级实时数据（WITS/ETP）后，“钻井业务数据”的核心其实是关系型数据（Relational Data）

Description Oracle/PostgreSQL Description

井身结构 (Wellbore Geometry)：套管、钻头、井径。

日报 (DDR - Daily Drilling Report)：时效分析、泥浆性能、钻井液、成本。

非生产时间 (NPT)：事故、复杂情况统计。

下面是一个基于 SQLAlchemy (ORM) + FastMCP的完整生产级实现.

目录结构规划
Note:

数据层 ( models.py+ db_init.py)：定义表结构和模拟数据。

服务层 ( main.py)：定义 MCP Tools 和业务逻辑。

第一部分：数据模型与模拟数据 (基于 SQLAlchemy)
这部分模拟了你在企业数据库中会看到的表结构。
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import date, datetime

# ==========================================
# 1. ORM 模型定义 (模拟企业数据库表结构)
# ==========================================
Base = declarative_base()

class Well(Base):
    __tablename__ = 'wells'
    id = Column(String(50), primary_key=True)  # 如 ZT-102
    name = Column(String(100))                 # 如 Zhong-102
    block = Column(String(50))                 # 区块
    spud_date = Column(Date)                   # 开钻日期
    target_depth = Column(Float)               # 设计井深
    status = Column(String(20))                # Active, Completed
    
    # 关联
    reports = relationship("DailyReport", back_populates="well")
    casings = relationship("CasingProgram", back_populates="well")

class CasingProgram(Base):
    """井身结构/套管数据"""
    __tablename__ = 'casing_programs'
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    run_date = Column(Date)
    size_inch = Column(Float)       # 套管尺寸 (e.g., 9.625)
    shoe_depth = Column(Float)      # 下入深度
    cement_top = Column(Float)      # 水泥返高
    
    well = relationship("Well", back_populates="casings")

class DailyReport(Base):
    """钻井日报 (DDR) 核心表"""
    __tablename__ = 'daily_reports'
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    report_date = Column(Date)
    report_no = Column(Integer)
    
    # 关键业务数据
    current_depth = Column(Float)       # 当前井深
    progress = Column(Float)            # 日进尺
    operation_summary = Column(Text)    # 24小时作业摘要
    next_24_plan = Column(Text)         # 下一步计划
    
    # 泥浆性能 (业务重点)
    mud_density = Column(Float)         # 密度 (sg)
    mud_viscosity = Column(Float)       # 粘度 (s)
    
    # 关联
    npt_events = relationship("NPTEvent", back_populates="report")
    well = relationship("Well", back_populates="reports")

class NPTEvent(Base):
    """非生产时间/复杂事故"""
    __tablename__ = 'npt_events'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'))
    category = Column(String(50))       # e.g., "Equipment Failure", "Loss"
    duration_hours = Column(Float)      # 损失工时
    description = Column(Text)          # 详细描述
    
    report = relationship("DailyReport", back_populates="npt_events")

# ==========================================
# 2. 数据库初始化与数据注入 (Mock Data)
# ==========================================
engine = create_engine('sqlite:///:memory:', echo=False) # 生产环境换成 connection string
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)
    session = Session()
    
    # 创建井
    w1 = Well(id="ZT-102", name="Zhong-102", block="Block-A", spud_date=date(2023, 10, 1), target_depth=4500, status="Active")
    session.add(w1)
    
    # 创建套管数据
    c1 = CasingProgram(well_id="ZT-102", run_date=date(2023, 10, 5), size_inch=13.375, shoe_depth=800, cement_top=0)
    c2 = CasingProgram(well_id="ZT-102", run_date=date(2023, 10, 20), size_inch=9.625, shoe_depth=2500, cement_top=500)
    session.add_all([c1, c2])
    
    # 创建日报 (正常钻进)
    r1 = DailyReport(
        well_id="ZT-102", report_date=date(2023, 11, 1), report_no=30,
        current_depth=3200, progress=150,
        operation_summary="Drilling 8.5in hole section from 3050m to 3200m. Parameters stable.",
        mud_density=1.25, mud_viscosity=55
    )
    
    # 创建日报 (发生事故)
    r2 = DailyReport(
        well_id="ZT-102", report_date=date(2023, 11, 2), report_no=31,
        current_depth=3220, progress=20, # 进尺很少
        operation_summary="Drilling to 3220m, experienced severe losses. POOH to shoe.",
        mud_density=1.20, mud_viscosity=60 # 调整泥浆
    )
    
    # 关联事故
    npt = NPTEvent(
        category="Lost Circulation", duration_hours=12.5,
        description="Loss rate 20 m3/hr at 3220m. Pumped LCM pill."
    )
    r2.npt_events.append(npt)
    
    session.add_all([r1, r2])
    session.commit()
    session.close()

# 初始化
init_db()
第二部分：MCP 服务实现 ( main.py)
NPT的痛点。
from fastmcp import FastMCP
from pydantic import Field
from typing import List, Optional, Literal
from sqlalchemy import func
# 引入上面的模型
# from models import Session, Well, DailyReport, CasingProgram, NPTEvent 

# 初始化 MCP
mcp = FastMCP("Drilling Business Intelligence")

# ==========================================
# 辅助函数：格式化 Markdown 表格
# ==========================================
def to_markdown_table(data: List[dict]) -> str:
    if not data:
        return "No data available."
    headers = data[0].keys()
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    rows = []
    for row in data:
        rows.append("| " + " | ".join(str(v) for v in row.values()) + " |")
    return "\n".join([header_row, separator] + rows)

# ==========================================
# Tool 1: 井身结构查询 (Engineering)
# ==========================================
@mcp.tool()
def get_well_casing_program(well_id: str) -> str:
    """
    Get the Casing and Cementing history (Wellbore Geometry).
    Use this to understand the physical structure of the well.
    """
    session = Session()
    try:
        casings = session.query(CasingProgram).filter_by(well_id=well_id).order_by(CasingProgram.shoe_depth).all()
        
        if not casings:
            return f"No casing records found for well {well_id}."
            
        data = []
        for c in casings:
            data.append({
                "Date": c.run_date,
                "Size (in)": c.size_inch,
                "Shoe Depth (m)": c.shoe_depth,
                "TOC (m)": c.cement_top
            })
            
        return f"### Wellbore Geometry: {well_id}\n\n" + to_markdown_table(data)
    finally:
        session.close()

# ==========================================
# Tool 2: 日报概览查询 (Reporting)
# ==========================================
@mcp.tool()
def get_daily_ops_summary(
    well_id: str, 
    date_start: str = Field(..., description="Start date YYYY-MM-DD"),
    date_end: str = Field(..., description="End date YYYY-MM-DD"),
) -> str:
    """
    Retrieve Daily Drilling Report (DDR) summaries for a date range.
    Includes depth progress, mud properties, and main operational summary.
    """
    session = Session()
    try:
        reports = session.query(DailyReport).filter(
            DailyReport.well_id == well_id,
            DailyReport.report_date >= date_start,
            DailyReport.report_date <= date_end
        ).order_by(DailyReport.report_date).all()
        
        if not reports:
            return f"No reports found for {well_id} between {date_start} and {date_end}."

        # 针对 LLM 优化输出：使用文本摘要格式，而不是纯表格，方便 LLM 理解上下文
        output = [f"### Operations Log: {well_id} ({date_start} to {date_end})"]
        
        for r in reports:
            entry = f"""
**Date: {r.report_date} (Report #{r.report_no})**
* **Depth**: {r.current_depth}m (Progress: +{r.progress}m)
* **Mud**: {r.mud_density} sg / {r.mud_viscosity} sec
* **Summary**: {r.operation_summary}
* **Plan**: {r.next_24_plan}
---"""
            output.append(entry)
            
        return "\n".join(output)
    finally:
        session.close()

# ==========================================
# Tool 3: NPT (非生产时间) 智能分析 (Analysis)
# ==========================================
@mcp.tool()
def analyze_npt_events(well_id: str) -> str:
    """
    Analyze Non-Productive Time (NPT) events and accidents for a well.
    Returns a statistical summary and detailed event list.
    """
    session = Session()
    try:
        # 联表查询：Report -> NPT
        results = session.query(DailyReport, NPTEvent).join(NPTEvent).filter(
            DailyReport.well_id == well_id
        ).all()
        
        if not results:
            return f"✅ No NPT (Non-Productive Time) events recorded for {well_id}. Operations are efficient."
        
        # 1. 统计数据
        total_lost_hours = sum([npt.duration_hours for _, npt in results])
        event_count = len(results)
        
        # 2. 详情列表
        details = []
        for report, npt in results:
            details.append({
                "Date": report.report_date,
                "Depth (m)": report.current_depth,
                "Category": npt.category,
                "Lost Hours": npt.duration_hours,
                "Description": npt.description
            })
            
        summary = f"""
### ⚠️ NPT Analysis: {well_id}
- **Total Incidents**: {event_count}
- **Total Lost Time**: {total_lost_hours} hours
        """
        
        return summary + "\n\n" + to_markdown_table(details)
    finally:
        session.close()

# ==========================================
# Tool 4: 泥浆性能追踪 (Fluids)
# ==========================================
@mcp.tool()
def track_mud_properties(well_id: str, property_name: Literal["density", "viscosity"]) -> str:
    """
    Track the evolution of specific mud properties over time.
    Useful for detecting wellbore stability issues (e.g., density increase).
    """
    session = Session()
    try:
        reports = session.query(DailyReport).filter_by(well_id=well_id).order_by(DailyReport.report_date).all()
        
        if not reports:
            return "No mud data found."
            
        data = []
        for r in reports:
            val = r.mud_density if property_name == "density" else r.mud_viscosity
            data.append({
                "Date": r.report_date,
                "Depth": r.current_depth,
                f"Value ({property_name})": val
            })
            
        return f"### Mud Property Tracking: {property_name}\n\n" + to_markdown_table(data)
    finally:
        session.close()

if __name__ == "__main__":
    # 可以在这里做简单的测试
    print("Drilling Business Data MCP Server Started.")
    mcp.run()

设计思路解析
1.数据关系处理 (Relational Handling)：
 Join ）。analyze_npt_events​JOIN​DailyReportNPTEvent
 LLM不需要自己去关联日期，这个 Tool直接返回了“日期-井深-事故描述-损失时间”的完整视图。
2.Markdown 表格输出：
 get_well_casing_program​track_mud_properties​to_markdown_table​
 原因：Claude/GPT 阅读 Markdown 表格的能力极强。相比于返回一堆 JSON，表格能让 LLM Downloaded by Claude Desktop
3.粒度控制：
  get_daily_ops_summary这四个最核心的业务字段Depth。MudSummaryPlan
  这防止了 Context Window 被无意义的字段、
4.场景化 Tool 设计：
  query_database_table(table_name)我没有设计一个通用式。
  相反，我设计了track_mud_properties。这符合工程师的思维：“我想看这口井的泥浆密度变化趋势”。

如果要部署到生产环境,你需要做的唯engine字符串：
# 修改前
engine = create_engine('sqlite:///:memory:')

# 修改后 (连接 Oracle)
engine = create_engine('oracle+cx_oracle://user:password@host:1521/?service_name=orcl')

# 修改后 (连接 PostgreSQL)
engine = create_engine('postgresql://user:password@localhost/drilling_db')

这套代码涵盖了钻井业务中最核心的**“井身结构”、“施工日报”和“复杂时效”**三大板块，足以应对大部分非实时数据的业务查询需求。

问：我要加入一些多井对比的功能，应该怎么实现
这是一个非常好的功能扩展。“多井对比”（Multi-Well Comparison）或者叫“邻井分析”（Offset Well Analysis）是钻险的核心手段。

在 MCP 中实现多井对比，千万不要让 LLM Context 消耗巨大。

Python​ compare_​Alignment Guide

以下是实现多井对实现：
核心场景设计
概览对比 (General Benchmarking)：

用户问：“对比 ZT-102 和 ZT-105 的基本情况。”

策略：横向表格，列出井深、周期、成本、钻机型号。

时效/进度对比 (Drilling Pace/ROP)：

用户问：“这两口井谁钻得快？”

策略：计算关键里程碑（如：完钻周期、钻至 2000m 用时、机械钻速 ROP 均值）。

风险对比 (NPT Analysis)：

用户问：“这一区块哪口井事故最少？”

(NPT )

代码实现 ( comparison_tools.py)
Pandasmain.py​sqlalchemy​pandas​在做数据对强大）。
from fastmcp import FastMCP
from pydantic import Field
from typing import List
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# 假设你复用了上一段代码的 models
# from models import Well, DailyReport, NPTEvent

mcp = FastMCP("Drilling Comparison Service")

# 数据库连接 (复用之前的配置)
engine = create_engine('sqlite:///:memory:') # 生产环境请替换
Session = sessionmaker(bind=engine)

# ==========================================
# Tool 1: 基础概览对比 (KPI Benchmarking)
# ==========================================
@mcp.tool()
def compare_wells_overview(
    well_ids: str = Field(..., description="Comma-separated list of Well IDs to compare. e.g. 'ZT-102,ZT-105'")
) -> str:
    """
    Compare high-level KPIs (Key Performance Indicators) between multiple wells.
    Includes: Target Depth, Actual Depth, Status, Spud Date.
    """
    # 1. 解析参数
    ids = [w.strip() for w in well_ids.split(',')]
    
    session = Session()
    try:
        # 2. 批量查询
        wells = session.query(Well).filter(Well.id.in_(ids)).all()
        
        if not wells:
            return "No wells found with the provided IDs."
            
        # 3. 使用 Pandas 进行转置 (Transpose)，适合对比查看
        data = []
        for w in wells:
            data.append({
                "Metric": "Well ID", "Value": w.id, "Well": w.id # 辅助列
            })
            data.append({"Metric": "Block", "Value": w.block, "Well": w.id})
            data.append({"Metric": "Status", "Value": w.status, "Well": w.id})
            data.append({"Metric": "Target Depth (m)", "Value": w.target_depth, "Well": w.id})
            data.append({"Metric": "Spud Date", "Value": str(w.spud_date), "Well": w.id})
        
        df = pd.DataFrame(data)
        
        # 透视表：行是指标，列是井号
        pivot_df = df.pivot(index="Metric", columns="Well", values="Value")
        
        return f"### 📊 Well Comparison Overview\n\n" + pivot_df.to_markdown()
    finally:
        session.close()

# ==========================================
# Tool 2: 提速分析 - 里程碑对比 (Performance)
# ==========================================
@mcp.tool()
def compare_drilling_pace(
    well_ids: str = Field(..., description="Comma-separated Well IDs, e.g. 'ZT-102,ZT-105'")
) -> str:
    """
    Compare drilling speed performance. 
    Calculates 'Days to Depth' milestones (e.g., Days to 1000m, 2000m) and Average ROP.
    """
    ids = [w.strip() for w in well_ids.split(',')]
    session = Session()
    try:
        # 获取所有日报
        reports = session.query(DailyReport).filter(DailyReport.well_id.in_(ids)).all()
        
        if not reports:
            return "No daily reports data found for comparison."
            
        # 转换为 DataFrame 处理
        data = [{"well_id": r.well_id, "date": r.report_date, "depth": r.current_depth, "progress": r.progress} for r in reports]
        df = pd.DataFrame(data)
        
        # 转换日期并按井、日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(['well_id', 'date'])
        
        comparison_results = []
        
        for wid in ids:
            well_df = df[df['well_id'] == wid]
            if well_df.empty:
                continue
                
            # 计算开钻以来的天数 (Cumulative Days)
            start_date = well_df['date'].min()
            well_df['days_from_spud'] = (well_df['date'] - start_date).dt.days + 1
            
            # 计算关键指标
            total_days = well_df['days_from_spud'].max()
            final_depth = well_df['depth'].max()
            avg_rop = well_df['progress'].mean() # 简单的日进尺平均
            
            # 计算里程碑 (Milestones): 钻到 1000m, 2000m, 3000m 花了几天
            milestones = {}
            for target in [1000, 2000, 3000, 4000]:
                # 找到第一个深度大于 target 的记录
                hit = well_df[well_df['depth'] >= target].head(1)
                if not hit.empty:
                    milestones[f"Days to {target}m"] = hit['days_from_spud'].values[0]
                else:
                    milestones[f"Days to {target}m"] = "-"
            
            row = {
                "Well ID": wid,
                "Total Days": total_days,
                "Final Depth": final_depth,
                "Avg Daily ROP (m/d)": round(avg_rop, 1),
                **milestones
            }
            comparison_results.append(row)
            
        return "### 🏎️ Drilling Speed & Milestones Comparison\n\n" + pd.DataFrame(comparison_results).to_markdown(index=False)
        
    finally:
        session.close()

# ==========================================
# Tool 3: 事故复杂对比 (NPT Analysis)
# ==========================================
@mcp.tool()
def compare_npt_statistics(
    well_ids: str = Field(..., description="Comma-separated Well IDs")
) -> str:
    """
    Compare Non-Productive Time (NPT) statistics.
    Identifies which well had more accidents and what the primary causes were.
    """
    ids = [w.strip() for w in well_ids.split(',')]
    session = Session()
    try:
        # 查询 NPT
        npts = session.query(NPTEvent, DailyReport).join(DailyReport).filter(DailyReport.well_id.in_(ids)).all()
        
        if not npts:
            return "✅ No NPT events found for these wells. Perfect operations!"
            
        data = []
        for npt, report in npts:
            data.append({
                "well_id": report.well_id,
                "category": npt.category,
                "hours": npt.duration_hours
            })
            
        df = pd.DataFrame(data)
        
        # 1. 总时效对比 (Pivot Table)
        # 统计每口井、每种事故类型的总小时数
        summary = df.pivot_table(index="well_id", columns="category", values="hours", aggfunc="sum", fill_value=0)
        
        # 添加总计列
        summary['Total NPT (Hours)'] = summary.sum(axis=1)
        
        return "### ⚠️ NPT (Risk) Comparison Matrix\n\n" + summary.to_markdown()
        
    finally:
        session.close()
功能亮点与设计哲学
1. “转置”的表格 (The Transposed View)
在compare_wells_overview中，我使用了pivot。
一行一个井。
Note :
人眼习惯左右扫视。Markdown LLM无法理解。将“指标”作为行，将“井号”作为列，是对比 2-4 口井的最佳展示方式。
2. “里程碑”计算 (Milestone Calculation)
 compare_drilling_pace
痛点：井 A 打了 30 天，井 B 打了 45 天，直接把两组数据扔给 LLM，它很难看出谁快。
方案：我在代码里计算了“钻到 1000米用了几天”、“钻到2000用了几天”。
ZT - 102 › 0-2000m › › › › 10 › › › › › ›这就是我们想要的智能分析。
3. 灵活的输入处理
参数设计为well_ids: str(逗号分隔)，而不是List[str]。
原因：虽然 FastMCP 支持 List，但部分 LLM 客户端在处理 JSON Python内split(',')最强。
客户端 Prompt 交互示例
当你在 Cursor/Claude Desktop 中加载了这个 MCP Server 后：
User : "帮我分析一下 ZT-102 和 ZT-105 这两口井，谁的表现更好？"
LLM (compare_wells_overview Thinking compare_drilling_pace) :
LLM (Tool Call) :compare_wells_overview(well_ids="ZT-102, ZT-105")
LLM (Tool Call) :compare_drilling_pace(well_ids="ZT-102, ZT-105")
LLM (Answer) : 根据数据对比分析：
Distance : ZT-102 (4200m)
Note : ZT-102: 150m/d, ZT-105, 2000m, ZT-102 8-year-old ZT-105 3-year-old parts
结论：ZT-102 整体机械钻速更高，是一口典型的提速标杆井。

问：我还要新增一个TOOL实现根据钻井日报自动总结钻井周报/月报
这是一个非常典型的RAG (检索增强生成)场景。要生成高质量的周报/月报，不能只把几十天的日报原文全部扔给LLM，而应该在Python 润色。
以下是Tool​​
1. 设计思路：从“罗列”到“聚合”
我们需要设计一个generate_period_summary工具，它不只是查数据库，它要做以下**ETL（提取-转换-加载）**工作：
  自动计算本周/本月的进尺总数、平均机械钻速、总 NPT 时间。
   Min -> Max）。
   Key Activity，并重点突出 NPT（事故）
2. 代码实现 ( reporting_tools.py)
Pandas 来处理时间序列models.py聚合。main.py
from fastmcp import FastMCP
from pydantic import Field
from typing import Optional
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# 假设复用之前的数据库连接
# from models import DailyReport, NPTEvent, Well

mcp = FastMCP("Drilling Reporting Service")
engine = create_engine('sqlite:///:memory:') # 生产环境请替换
Session = sessionmaker(bind=engine)

@mcp.tool()
def get_period_drilling_data(
    well_id: str,
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
) -> str:
    """
    Aggregates drilling data for a specific period (Weekly/Monthly) to generate reports.
    Returns statistical metrics, NPT summaries, and a daily activity timeline.
    """
    session = Session()
    try:
        # 1. 获取范围内所有日报
        reports = session.query(DailyReport).filter(
            DailyReport.well_id == well_id,
            DailyReport.report_date >= start_date,
            DailyReport.report_date <= end_date
        ).order_by(DailyReport.report_date).all()

        if not reports:
            return f"No reports found for {well_id} between {start_date} and {end_date}."

        # 2. 转换为 DataFrame 以便进行统计计算
        data = []
        for r in reports:
            # 获取当天的 NPT 详情
            npt_desc = []
            npt_hours = 0.0
            for npt in r.npt_events:
                npt_hours += npt.duration_hours
                npt_desc.append(f"{npt.category} ({npt.duration_hours}h)")
            
            data.append({
                "date": r.report_date,
                "depth": r.current_depth,
                "progress": r.progress,
                "mud_density": r.mud_density,
                "npt_hours": npt_hours,
                "npt_details": "; ".join(npt_desc),
                "summary": r.operation_summary
            })
        
        df = pd.DataFrame(data)
        
        # 3. 核心指标统计 (KPIs)
        total_days = len(df)
        start_depth = df.iloc[0]['depth'] - df.iloc[0]['progress'] # 推算起始井深
        end_depth = df.iloc[-1]['depth']
        total_footage = end_depth - start_depth
        avg_daily_progress = df['progress'].mean()
        
        total_npt = df['npt_hours'].sum()
        npt_days = df[df['npt_hours'] > 0]['date'].count() # 发生 NPT 的天数
        
        # 泥浆变化趋势
        mud_min = df['mud_density'].min()
        mud_max = df['mud_density'].max()
        mud_trend = "Stable" if (mud_max - mud_min) < 0.02 else f"Changed {mud_min}->{mud_max}"

        # 4. 构建每日摘要时间轴 (Timeline)
        # 技巧：只保留每天最重要的动作，给 LLM 提供写作素材
        timeline = []
        for _, row in df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            # 如果有 NPT，重点标记
            status_icon = "⚠️" if row['npt_hours'] > 0 else "✅"
            npt_text = f"[NPT: {row['npt_details']}]" if row['npt_hours'] > 0 else ""
            
            line = f"- **{date_str}** {status_icon}: Depth {row['depth']}m (+{row['progress']}m). {row['summary'][:100]}... {npt_text}"
            timeline.append(line)
        
        timeline_str = "\n".join(timeline)

        # 5. 组装给 LLM 的结构化提示
        # 注意：这里我们不直接写周报，而是返回“周报所需的所有素材”
        return f"""
### 📊 Period Report Data Source: {well_id}
**Period**: {start_date} to {end_date}

#### 1. Executive Summary Metrics
| Metric | Value |
|---|---|
| **Days Drilled** | {total_days} days |
| **Footage Drilled** | {total_footage:.1f} m |
| **Depth Interval** | {start_depth:.1f} m -> {end_depth:.1f} m |
| **Avg ROP/Day** | {avg_daily_progress:.1f} m/day |
| **Total NPT** | {total_npt:.1f} hours ({npt_days} days with incidents) |
| **Mud Density** | {mud_trend} sg |

#### 2. Daily Timeline & Highlights
{timeline_str}

#### 3. Instructions for Report Generation
- Use the metrics above to write the "Performance Overview".
- Use the timeline to write the "Key Activities" section.
- Summarize any ⚠️ items in a separate "HSE & Issues" section.
"""

    finally:
        session.close()
3. 如何使用 (Prompt Engineering)
LLM Tool​使用这些素材。

用户提问：

“帮我生成 ZT-102 井上周（2023-11-01 到 2023-11-07）的钻井周报。”

LLM Program
1.Identify Tool : 用户想要报表 -> 调用get_period_drilling_data(well_id="ZT-102", start_date="2023-11-01", end_date="2023-11-07")。
2.Receive Data : 获取到上面代码返回的 Markdown 格式的统计数据和时间轴。
3.Generate Output : LLM 基于素材生成最终文本。

生成的周报效果示例 (LLM 输出)：

📄钻井周报 (Weekly Drilling Report)
Name : ZT-102
周期: 2023-11-01 至 2023-11-07
1. 综述 (Executive Summary)
本周钻井作业整体进展顺利。期间共作业7天，完成进尺950米，当前井深达到4150米。平均日进尺为135.7米/天。本周泥浆密度从1.25 sg 提至 1.28 sg 以应对地层压力。
2. 关键时效 (Performance)
Distance : 3200.0 m
当前井深: 4150.0 m
( NPT )
3. 作业回顾 (Weekly Highlights)
11-01 : 3200m distance, 3200m distance
11-02 (重点关注) : ⚠️ 钻进至 3220m 时发生井漏（Lost Circulation），损失时间 12.5 。
11-03 至 11-07 : 恢复正常钻进，泥浆性能稳定，无复杂情况。
4. 问题与建议 (Issues & Actions)
本周主要风险点为11密切监测 4200m处地层承压能力，次漏失。
4. 进阶优化建议
1.自动计算日期： LLM 有时搞不清“上周”具体是几号。你可以在 Python 代码里增加一个简单的 NLP dateparserLLM：“Generate dates based on current time” 。
2.DailyCost加入成本估算 (Cost Estimate)：total_cost = df['daily_cost'].sum()。周报里加上“本周花费”是领导最关心的。
3.你可以循环调用get_period_drilling_data获取 Block A下所有井的数据，然后让 LLM 合并生成一份“区块综述”。

问：上面生成的是单井的钻井周报/月报，我需要的是某个区块或采油厂的总结报告
级别的报告，核心挑战在于数据聚合（Aggregation）和异常筛选（Outlier Detection）。

他们关心的是：

宏观指标：整个区块总进尺多少？动用了几部钻机？

效率排名：哪口井打得最快（提速标杆）？

问题聚焦：哪口井拖了后腿（NPT 最高）？

以下是专门针对多井聚合报表的 Tool 设计与代码实现。
1. Server-Side Aggregation
不要让 LLM 循环调用单井工具，get_block_period_summary在 Python 内部完成 SQL Panda Pandas​

2. 代码实现 ( block_reporting_tools.py)
在之前的models.py基础上扩展。
from fastmcp import FastMCP
from pydantic import Field
import pandas as pd
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
# 假设复用之前的模型
# from models import DailyReport, NPTEvent, Well, Session

mcp = FastMCP("Block Reporting Service")
engine = create_engine('sqlite:///:memory:') # 生产环境请替换
Session = sessionmaker(bind=engine)

@mcp.tool()
def get_block_period_summary(
    block_name: str = Field(..., description="Name of the Block or Plant (e.g., 'Block-A', 'No.3 Plant')"),
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
) -> str:
    """
    Generate a high-level summary report for an entire Block or Oil Plant.
    Aggregates metrics across all active wells, identifies top performers, and highlights systemic risks.
    """
    session = Session()
    try:
        # 1. 查找该区块下的所有井
        wells = session.query(Well).filter(Well.block == block_name).all()
        well_ids = [w.id for w in wells]
        
        if not well_ids:
            return f"❌ No wells found in block '{block_name}'."

        # 2. 获取这些井在指定时间段内的日报
        reports = session.query(DailyReport).filter(
            DailyReport.well_id.in_(well_ids),
            DailyReport.report_date >= start_date,
            DailyReport.report_date <= end_date
        ).all()
        
        if not reports:
            return f"No drilling activities found in {block_name} between {start_date} and {end_date}."

        # 3. 数据处理 (Pandas ETL)
        data = []
        for r in reports:
            # 计算当日 NPT
            daily_npt = sum([n.duration_hours for n in r.npt_events])
            data.append({
                "well_id": r.well_id,
                "date": r.report_date,
                "progress": r.progress,
                "npt": daily_npt,
                "depth": r.current_depth
            })
        
        df = pd.DataFrame(data)
        
        # --- 核心指标计算 ---
        
        # A. 宏观统计
        active_wells_count = df['well_id'].nunique() # 动用井数
        total_footage = df['progress'].sum()         # 总进尺
        total_npt = df['npt'].sum()                  # 总非生产时间
        avg_rop_block = df.groupby('well_id')['progress'].mean().mean() # 区块平均日进尺
        
        # B. 单井绩效排名 (Performance Ranking)
        # 按进尺总数排名 (找出功勋井)
        top_producers = df.groupby('well_id')['progress'].sum().sort_values(ascending=False).head(3)
        
        # 按 NPT 排名 (找出问题井)
        top_trouble_wells = df.groupby('well_id')['npt'].sum().sort_values(ascending=False)
        top_trouble_wells = top_trouble_wells[top_trouble_wells > 0].head(3) # 只看有事故的
        
        # C. 事故类型分布 (Pareto Analysis)
        # 这需要再查一次 NPT 表做细分，这里简化处理，假设我们从 report 中能提取
        
        # 4. 构建返回给 LLM 的结构化素材
        
        summary_md = f"""
### 🏭 Block Summary: {block_name}
**Period**: {start_date} to {end_date}

#### 1. KPI Overview (关键绩效)
| Metric | Value |
|---|---|
| **Active Rigs/Wells** | {active_wells_count} |
| **Total Footage** | {total_footage:.1f} m |
| **Total NPT** | {total_npt:.1f} hours |
| **Block Avg ROP** | {avg_rop_block:.1f} m/day |

#### 2. Star Performers (提速标杆)
The following wells contributed the most footage:
{top_producers.to_markdown(header=["Total Footage (m)"])}

#### 3. Focus Areas (重点关注/问题井)
Wells with highest Non-Productive Time:
{top_trouble_wells.to_markdown(header=["Lost Hours"])}

#### 4. Activity Summary
- **Rig Count**: {active_wells_count} active rigs operating in this period.
- **Efficiency**: The block average speed is {avg_rop_block:.1f} m/day.
- **Risk**: {len(top_trouble_wells)} wells experienced operational issues.
"""
        return summary_md

    finally:
        session.close()
3. LLM 交互与报告生成示例
月份的生产月报”时。

LLM 接收到的数据 (Tool Output):
### 🏭 Block Summary: Block-A
**Period**: 2023-11-01 to 2023-11-30

#### 1. KPI Overview
| Metric | Value |
|---|---|
| **Active Rigs/Wells** | 5 |
| **Total Footage** | 4500.0 m |
| **Total NPT** | 45.5 hours |
| **Block Avg ROP** | 120.5 m/day |

#### 2. Star Performers
| well_id | Total Footage (m) |
|---|---|
| ZT-102 | 1500.0 |
| ZT-105 | 1200.0 |
| ZT-108 | 900.0 |

#### 3. Focus Areas
| well_id | Lost Hours |
|---|---|
| ZT-102 | 25.5 |
| ZT-109 | 10.0 |
4. 优化建议：让报告更“懂行”
Python 代码中增加以下逻辑：
1.同环比分析 (YoY / MoM) :
  Tool 参数增加compare_with_last_month=True。
  PythonTotal Footage: 4500m (↑10% vs last month)​
  这样 LLM 就能写出：“本月进尺较上月增长 10%，生产势头良好。”
2.预算/成本聚合:
  米均成本，DailyCost聚合返回Total Cost和Cost per Meter
  KPI
3.队伍（Rig Team）排名:
  通常油田是按“钻井队”考核的。
  数据处理时，改为df.groupby('team_name')而不是well_id。
  输出：“701队本月进尺第一，705队事故率最高。”
总结
MCP Tool。它负责完成所有的 Sum, Count, GroupBy 和 Sort 操作，只把结论性数据喂给 LLM，这样既节省了Token，了报告数据的准确性（LLM 不会）。

问：怎么增强意图识别

把 Tool的定义写得像“操作手册”一样详细，并在 System Prompt 里给它几道“例题”。
在开发 MCP 服务时，意图识别（Intent Recognition）体验生死的关键。如果 LLM 选错了Tool，Chinese tool
的通用能力是不够的。你需要通过以下5个层级的策略来强制提高匹配精度。

第一层：精准的 Tool 定义 (The Foundation)
LLM Documentation (文档字符串)的一部分。
❌ 错误的写法(模糊)：
@mcp.tool()
def query_data(id: str, type: str):
    """Query data from database."""
    pass
LLM 困惑点：什么是 type？

✅ 正确的写法 (场景化 + 参数枚举)：
@mcp.tool()
def get_daily_drilling_report(
    well_id: str,
    date: str,
    section: Literal["mud", "npt", "cost", "full"] = "full"
):
    """
    [Scenario]: Use this tool when the user asks about daily activities, accidents (NPT), 
    fluid properties (mud weight/viscosity), or what happened on a specific day.
    
    [Keywords]: 'DDR', 'Daily Report', 'Operations', 'Mud', 'Accident'.
    """
    pass
优化技巧：
1.Scenario-Based Description : 在文档中明确写出“当用户问...时使用此工具”.
2.Keywords Tagging : DDR, NPT, BHA）
第二层：系统提示词增强 (System Prompt Engineering)
在 MCP Client 端（如 Claude Desktop 或你的自定义前端）配置 System Prompt，植入**“领域认知”**。
推荐的 System Prompt 模板：
你的任务是将用户的自然语言转化为精准的工具调用。

1. 术语映射规则 (Domain Dictionary) :

当用户说 "提速"、"钻得快不快" -> 意图是ROP (机械钻速) -> 调用compare_drilling_pace。

当用户说 "井身结构"、"套管" -> 意图是Wellbore Geometry -> 调用get_well_casing_program。

当用户说 "非生产时间"、"事故"、"复杂" -> 意图是NPT -> 调用analyze_npt_events。

2. 思考链 (Chain of Thought) :在调用工具前，先分析用户想要的是“单点数据”还是“对比分析”还是“趋势总结”。

3. 默认行为:

最近一天”的数据。

如果用户没提供井号，先调用search_wells。
第三层：Few-Shot Learning (少样本示例)
System Prompt 中直接给出User Query -> Tool Call的标准范例。

示例配置：
[Examples]
User: "ZT-102 昨天泥浆密度是多少？"
Assistant: get_daily_report(well_id="ZT-102", date="2023-11-05", section="mud")

User: "比较一下 Block A 哪口井最近跑得最快？"
Assistant: compare_drilling_pace(well_id="ZT-102,ZT-105,ZT-108") 
(注意：先根据 Block A 找到了这几口井，或者直接调用 get_block_period_summary)

User: "看看这口井有什么事故没"
Assistant: analyze_npt_events(well_id="ZT-102")

第四层：增加一个“思考工具” (Router/Planner Tool)
20个），直接匹配容易错。你可以设计一个纯逻辑工具，不查数据库，只用来辅助规划。

设计一个clarify_intent工具：
@mcp.tool()
def plan_data_retrieval(
    intent_category: Literal["single_well_status", "multi_well_compare", "historical_report", "realtime_monitor"],
    entities: List[str],
    time_range: str
) -> str:
    """
    这是一个虚拟工具。当用户的问题比较复杂，涉及多个步骤时，先调用此工具进行规划。
    """
    return f"Plan confirmed: Category={intent_category}, Entities={entities}. Next step: Call specific tools."
	效果： LLM会被迫先进行一次“分类”，一旦分类为multi_well_compare，它就从而缩小compare_搜索范围。

第五层：参数归一化与模糊匹配 (Robustness)
Python 代码需要做容错处理，反过来辅助 LLM。

场景 1：用户说的是中文井号，数据库是英文 ID
  用户说：“查一下中102井的日报”
  LLM 传参：well_id="中102"

代码层处理：
def get_daily_report(well_id: str, ...):
    # 自动清洗：中102 -> ZT-102
    normalized_id = normalize_well_id(well_id) 
    # ...
场景 2：模糊的时间描述
 用户说：“上周”
 LLM 传以接受date="last_week"这种特殊字符串，然后在 Python 内部计算datetime.now() - timedelta(days=7)。
 YYYY-MM-DDSystem Prompt 里强制要求
 
问：是否应该对用户输入的查询内容改写成更标准的问题，以使得LLM更精确的调用MCP TOOL
这是一个非常关键的架构决策。答案是：必须改写（Rewriting/Refining），但建议在 LLM 的“思维链（Chain of Thought）”

在钻井这种专业领域，用户的提问往往是口语化、含糊且带有行业黑话的，直接拿去匹配Tool 的 Schema 成功率很低。

我们将这个过程称为“查询对齐 (Query Alignment)”。以下是 3 种推荐的实施策略，按推荐程度排序：

策略一：基于思维链的隐式改写 (Chain of Thought Rewrite) ——最推荐
不要修改用户发给 LLM ?在调用工具前,先生成一个“标准化的思考步骤”。
实现方式
在 System Prompt 中加入如下指令：
"Chinese:

实体提取：将用户口语中的井号（如'中102'）转换为标准 ID（'ZT-102'）。

术语翻译：将行业黑话（如'憋泵'、'起下钻'）转换为工具对应的参数（'Pump Pressure Spike', 'Tripping'）。

问题重构：将用户模糊的“怎么回事”重写为具体的“查询日报摘要”或“分析 NPT”。

"
效果对比
用户输入：“ZT-102 昨天泥浆是不是加重了？”

LLM 内部思考 (隐式改写)：

Original : "ZT-102 昨天泥浆是不是加重了？"

Standardized : "Retrieve mud density data for ZT-102 on [Yesterday's Date] and check for density increase trend."

Tool Decision : track_mud_properties(well_id='ZT-102', property='density')Yes get_daily_report(..., section='mud').

策略二：前置“澄清工具” (The Clarifier Tool)
如果用户的查询确实太模糊（例如只说了一个“看下ZT-102”，单纯改写可能会导致“幻觉”。此时应设计一个不需要参数的纯逻辑工具，或者利用LLM 的反问能力。

但为了自动化，你可以引入一个search_knowledge_base或lookup_glossary工具作为中间跳板。

场景
用户输入：“ZT-102 井漏了吗？”

Theanalyze_npt_events book "Lost Circulation "

流程：

LLMlookup_terminology(term="井漏")​

Tool 返回：{"standard_term": "Lost Circulation", "category": "NPT"}。

LLM 再调用analyze_npt_events(category="Lost Circulation")。

策略三：查询分解 (Query Decomposition) —— 针对复杂问题
用户经常会把多个问题揉在一起。这时候“改写”实际上是“拆解”。

场景
用户输入：“对比一下 A 和 B 谁打得快，是不是因为泥浆没配好？”

改写/拆解逻辑： 这实际上是两个独立的标准查询：

Q1 (Performance) : "Compare ROP/Speed ​​between Well A and Well B." ->compare_drilling_pace

Q2 (Fluids) : “Retrieve Mud Properties for Well A and B.” ->track_mud_properties

实战：针对钻井业务的 System Prompt
把这段 Prompt 代码去正则替换要智能得多：
# Role
你是一个资深的钻井数据分析专家。你连接了一个基于 MCP 的数据服务。

# Query Alignment Protocol (查询对齐协议)
用户的输入通常是非标准的。在调用工具前，你必须进行以下思维转换：

1. **Date Normalization (日期归一化)**
   - User: "上周" -> Standard: "2023-XX-XX to 2023-XX-XX" (calculated based on current date).
   - User: "昨天" -> Standard: "YYYY-MM-DD".

2. **Entity Resolution (实体解析)**
   - User: "中102", "102井" -> Standard: "ZT-102".
   - User: "Block A", "A区" -> Standard: "Block-A".

3. **Intent Mapping (意图映射)**
   - "钻得慢", "打不动" -> Intent: Check ROP/NPT -> Tool: `compare_drilling_pace` or `analyze_npt_events`.
   - "泥浆", "粘度", "比重" -> Intent: Fluid Properties -> Tool: `track_mud_properties` or `get_daily_report(section='mud')`.
   - "井身", "套管", "下得深不深" -> Intent: Well Structure -> Tool: `get_well_casing_program`.

# Execution Rule
不要询问用户“你想查具体的哪个日期？”，除非信息完全缺失。尽可能根据上下文推断默认值（例如：默认最近一天，默认全井段）。
总结
是否应该改写？是的。

System Prompt ( System Prompt)

Python 字典写不完，但LLM原生就懂。

这种方法被称为Reflective Pattern (反思模式)，它能显著提高 MCP Slot Filling