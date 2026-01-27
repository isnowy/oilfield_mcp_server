Description​​

数据层：基于 SQLAlchemy 的 ORM 设计与模拟数据注入。

功能层：包含单井查询、多井对比、区块报表、NPT分析。

监控层：基于装饰器的全链路调用日志追踪。

交互层：针对 LLM 优化的 Markdown 输出与 Pydantic 校验。

你可以直接复制这段代码保存为server.py，并在本地运行。

1. 架构概览
2. 环境准备
你需要安装以下 Python 库：
pip install fastmcp sqlalchemy pandas pydantic
3. 完整代码实现 ( server.py)
import time
import json
import logging
import functools
import pandas as pd
from typing import List, Optional, Literal
from datetime import date, datetime, timedelta
from fastmcp import FastMCP, Context
from pydantic import Field
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==========================================
# Part 1: 配置与日志基础设施 (Audit & Config)
# ==========================================

# 配置结构化日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OilfieldMCP")

class AuditLog:
    """装饰器：用于记录工具调用的输入、输出、耗时和状态"""
    @staticmethod
    def trace(tool_name: str):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_ts = time.time()
                try:
                    logger.info(f"🔧 [START] Tool: {tool_name} | Params: {kwargs}")
                    result = func(*args, **kwargs)
                    duration = round((time.time() - start_ts) * 1000, 2)
                    logger.info(f"✅ [SUCCESS] Tool: {tool_name} | Time: {duration}ms")
                    return result
                except Exception as e:
                    duration = round((time.time() - start_ts) * 1000, 2)
                    logger.error(f"❌ [ERROR] Tool: {tool_name} | Time: {duration}ms | Error: {str(e)}")
                    # 返回友好的错误信息给 LLM，防止对话中断
                    return f"System Error in tool '{tool_name}': {str(e)}"
            return wrapper
        return decorator

# ==========================================
# Part 2: 数据库模型与初始化 (Data Layer)
# ==========================================

Base = declarative_base()

class Well(Base):
    __tablename__ = 'wells'
    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    block = Column(String(50))
    target_depth = Column(Float)
    spud_date = Column(Date)
    status = Column(String(20))
    team = Column(String(50))
    
    reports = relationship("DailyReport", back_populates="well")
    casings = relationship("CasingProgram", back_populates="well")

class DailyReport(Base):
    __tablename__ = 'daily_reports'
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    report_date = Column(Date)
    current_depth = Column(Float)
    progress = Column(Float)  # 日进尺
    mud_density = Column(Float)
    summary = Column(Text)
    
    npt_events = relationship("NPTEvent", back_populates="report")
    well = relationship("Well", back_populates="reports")

class NPTEvent(Base):
    __tablename__ = 'npt_events'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'))
    category = Column(String(50))  # e.g., "Loss", "Kick"
    duration = Column(Float)       # Hours
    description = Column(Text)
    report = relationship("DailyReport", back_populates="npt_events")

class CasingProgram(Base):
    __tablename__ = 'casing_programs'
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    size = Column(Float)
    depth = Column(Float)
    well = relationship("Well", back_populates="casings")

# 初始化内存数据库 (Mock Data)
engine = create_engine('sqlite:///:memory:', echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def seed_data():
    session = Session()
    # 1. 创建井
    wells = [
        Well(id="ZT-102", name="Zhong-102", block="Block-A", target_depth=4500, spud_date=date(2023,10,1), status="Active", team="Team-701"),
        Well(id="ZT-105", name="Zhong-105", block="Block-A", target_depth=4000, spud_date=date(2023,10,5), status="Active", team="Team-702"),
        Well(id="XY-009", name="XiYu-009", block="Block-B", target_depth=5000, spud_date=date(2023,9,15), status="Completed", team="Team-808"),
    ]
    session.add_all(wells)
    
    # 2. 创建日报与事件
    # ZT-102: 正常进尺 + 一次井漏
    dates = [date(2023,11,1) + timedelta(days=i) for i in range(5)]
    depths = [3000, 3150, 3200, 3350, 3500]
    
    for i, d in enumerate(dates):
        # 模拟第3天发生井漏
        is_npt = (i == 2)
        prog = 50 if is_npt else 150
        r = DailyReport(
            well_id="ZT-102", report_date=d, current_depth=depths[i], progress=prog,
            mud_density=1.25 if i < 2 else 1.28, # 加重压井
            summary=f"Drilling 8.5in section. {'Experienced losses.' if is_npt else 'Smooth operation.'}"
        )
        if is_npt:
            r.npt_events.append(NPTEvent(category="Lost Circulation", duration=12.5, description="Loss rate 15m3/hr."))
        session.add(r)
        
    # ZT-105: 极速钻井，无事故
    for i, d in enumerate(dates):
        r = DailyReport(
            well_id="ZT-105", report_date=d, current_depth=3000 + (i*200), progress=200,
            mud_density=1.20, summary="Drilling ahead fast. ROP high."
        )
        session.add(r)

    # 3. 套管数据
    session.add(CasingProgram(well_id="ZT-102", size=13.375, depth=800))
    session.add(CasingProgram(well_id="ZT-102", size=9.625, depth=2500))
    
    session.commit()
    session.close()

seed_data()
print("✅ Mock Database Seeded.")

# ==========================================
# Part 3: MCP Server 定义 (Logic Layer)
# ==========================================

mcp = FastMCP("Oilfield Intelligence Server")

# 辅助：Pandas 转 Markdown
def df_to_md(df: pd.DataFrame) -> str:
    if df.empty: return "No data available."
    return df.to_markdown(index=False)

# --- 模块 1: 发现与概览 ---

@mcp.tool()
@AuditLog.trace("search_wells")
def search_wells(
    keyword: str = Field(..., description="Search keyword (Well Name or Block Name)."),
    status: Literal["Active", "Completed", "All"] = "All"
) -> str:
    """Find wells by name or block. Returns ID, Status, and Team."""
    session = Session()
    try:
        query = session.query(Well).filter(
            (Well.name.contains(keyword)) | (Well.block.contains(keyword))
        )
        if status != "All":
            query = query.filter(Well.status == status)
        
        results = [{"ID": w.id, "Name": w.name, "Block": w.block, "Status": w.status, "Team": w.team} for w in query.all()]
        
        if not results: return f"No wells found for '{keyword}'."
        return f"### Search Results\n{df_to_md(pd.DataFrame(results))}"
    finally:
        session.close()

@mcp.tool()
@AuditLog.trace("get_well_casing")
def get_well_casing(well_id: str) -> str:
    """Get Wellbore Geometry (Casing Program)."""
    session = Session()
    try:
        casings = session.query(CasingProgram).filter_by(well_id=well_id).all()
        data = [{"Size (in)": c.size, "Shoe Depth (m)": c.depth} for c in casings]
        if not data: return f"No casing data for {well_id}."
        return f"### Well Structure: {well_id}\n{df_to_md(pd.DataFrame(data))}"
    finally:
        session.close()

# --- 模块 2: 多井对比与分析 ---

@mcp.tool()
@AuditLog.trace("compare_drilling_pace")
def compare_drilling_pace(
    well_ids: str = Field(..., description="Comma-separated Well IDs, e.g., 'ZT-102,ZT-105'")
) -> str:
    """
    Compare drilling speed (ROP) and progress between multiple wells.
    Use this to identify the fastest well or perform benchmarking.
    """
    ids = [w.strip() for w in well_ids.split(',')]
    session = Session()
    try:
        reports = session.query(DailyReport).filter(DailyReport.well_id.in_(ids)).all()
        if not reports: return "No data for comparison."
        
        # 使用 Pandas 进行聚合分析
        df = pd.DataFrame([{
            "Well": r.well_id, "Date": r.report_date, "Progress": r.progress, "Depth": r.current_depth
        } for r in reports])
        
        # 1. 计算平均日进尺
        stats = df.groupby("Well")["Progress"].mean().reset_index()
        stats.columns = ["Well", "Avg ROP (m/day)"]
        
        # 2. 计算当前最大井深
        max_depth = df.groupby("Well")["Depth"].max().reset_index()
        max_depth.columns = ["Well", "Current Depth (m)"]
        
        merged = pd.merge(stats, max_depth, on="Well")
        
        return f"### 🏎️ Drilling Pace Comparison\n{df_to_md(merged)}"
    finally:
        session.close()

# --- 模块 3: 报表生成 (RAG) ---

@mcp.tool()
@AuditLog.trace("get_block_period_summary")
def get_block_period_summary(
    block_name: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Generate a summarized report for a whole Block (e.g., 'Block-A').
    Aggregates Footage, NPT, and identifies Top/Bottom performers.
    """
    # 格式化日期校验
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except:
        return "Error: Date must be YYYY-MM-DD."

    session = Session()
    try:
        # 关联查询 Well -> Report -> NPT
        query = session.query(DailyReport, Well).join(Well).filter(
            Well.block == block_name,
            DailyReport.report_date >= s_date,
            DailyReport.report_date <= e_date
        )
        data = []
        for r, w in query.all():
            npt_hours = sum(n.duration for n in r.npt_events)
            data.append({
                "Well": w.id, "Progress": r.progress, "NPT": npt_hours
            })
            
        if not data: return f"No data for {block_name}."
        
        df = pd.DataFrame(data)
        
        # 核心指标计算
        total_footage = df["Progress"].sum()
        total_npt = df["NPT"].sum()
        
        # 排名
        top_well = df.groupby("Well")["Progress"].sum().idxmax()
        trouble_well_series = df.groupby("Well")["NPT"].sum()
        trouble_well = trouble_well_series.idxmax() if trouble_well_series.max() > 0 else "None"

        return f"""
### 📊 Block Summary: {block_name} ({start_date} to {end_date})
| Metric | Value |
|---|---|
| **Total Footage** | {total_footage} m |
| **Total NPT** | {total_npt} hours |
| **Top Performer** | {top_well} |
| **Most Troublesome** | {trouble_well} |

#### Detailed Breakdown
{df_to_md(df.groupby("Well")[["Progress", "NPT"]].sum().reset_index())}
"""
    finally:
        session.close()

# --- 模块 4: 细粒度工程参数 ---

@mcp.tool()
@AuditLog.trace("track_mud_properties")
def track_mud_properties(well_id: str) -> str:
    """Track mud density changes to detect wellbore stability issues."""
    session = Session()
    try:
        reports = session.query(DailyReport).filter_by(well_id=well_id).order_by(DailyReport.report_date).all()
        data = [{"Date": r.report_date, "Depth": r.current_depth, "Mud Density (sg)": r.mud_density} for r in reports]
        return f"### Mud Properties: {well_id}\n{df_to_md(pd.DataFrame(data))}"
    finally:
        session.close()

# ==========================================
# Part 4: 启动入口
# ==========================================

if __name__ == "__main__":
    print("🚀 Oilfield MCP Server is running...")
    # FastMCP 默认使用 stdio 模式，适配 Claude Desktop
    mcp.run()
	
4. 客户端配置 (Claude Desktop)
Claude Desktop

配置文件位置：

MacOS:~/Library/Application Support/Claude/claude_desktop_config.json

Windows:%APPDATA%\Claude\claude_desktop_config.json

写入内容：	
{
  "mcpServers": {
    "oilfield-data": {
      "command": "python",
      "args": [
        "/绝对路径/path/to/your/server.py" 
      ]
    }
  }
}
注意：请将python径（如/Users/name/venv/bin/python），防止依赖找不到。
5. 关键：System Prompt 设置
Claude Prompt, Cursor, Project Rules.

你是一个专业的油田钻井数据助手。你连接了一个 MCP 数据服务。
在调用工具前，请遵循以下 [思维链协议]：

1. **实体归一化 (Entity Normalization)**:
   - 将用户口语中的 "中102", "102井" 转换为标准 ID "ZT-102"。
   - 将 "Block A" 转换为 "Block-A"。

2. **日期推断 (Date Inference)**:
   - 如果用户说 "最近一周"，基于当前时间推算 YYYY-MM-DD 范围。
   - 默认结束时间为今日。

3. **意图映射 (Intent Mapping)**:
   - "谁钻得快" -> 调用 `compare_drilling_pace`。
   - "有什么事故", "井漏" -> 调用 `get_block_period_summary` 查看 NPT 或查询日报详情。
   - "井身结构", "套管" -> 调用 `get_well_casing`。

4. **处理流程**:
   - 如果是简单查询，直接调用对应工具。
   - 如果是复杂分析（如"写周报"），先调用 `get_block_period_summary` 获取数据，然后基于 Markdown 表格生成自然语言报告。
   
6. 测试案例
Download Claude Desktop 中尝试以下提问：

Discovery : "帮我查一下 A 区块有哪些活跃的井？"

Comparison : "对比一下 ZT-102 和 ZT-105 谁钻得快？"

Reporting : "生成 Block-A 区块 2023年11月的生产总结报告，重点关注有没有事故。"

Engineering : "ZT-102 的泥浆密度最近有变化吗？"

Players for MVP交互逻辑，可以直接用于演示或二次开发。