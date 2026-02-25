"""
油田钻井数据查询 MCP Server
功能：鉴权、单井查询、多井对比、日报总结、周报月报生成
基于 FastMCP 开发
"""

import os
import re
import time
import json
import logging
import functools
import pandas as pd
from typing import List, Optional, Literal, Dict, Any
from datetime import date, datetime, timedelta
from fastmcp import FastMCP, Context
from pydantic import Field
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==========================================
# Part 1: 配置与日志基础设施
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OilfieldMCP")

# 开发模式配置：设置 DEV_MODE=true 可跳过权限检查（方便测试）
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ["true", "1", "yes"]

# 权限配置 - 可以从配置文件或环境变量加载
USER_PERMISSIONS = {
    "admin": {"wells": "*", "blocks": "*", "role": "admin"},
    "engineer": {"wells": ["ZT-102", "ZT-105"], "blocks": ["Block-A"], "role": "engineer"},
    "viewer": {"wells": ["ZT-102"], "blocks": ["Block-A"], "role": "viewer"},
    "default": {"wells": [], "blocks": [], "role": "guest"}
}

class PermissionService:
    """权限管理服务"""
    
    @staticmethod
    def check_well_access(user_role: str, well_id: str) -> bool:
        """检查用户是否有权限访问特定井"""
        # 🔓 开发模式：跳过权限检查
        if DEV_MODE:
            return True
        
        perms = USER_PERMISSIONS.get(user_role, USER_PERMISSIONS["default"])
        
        # 管理员有所有权限
        if perms["role"] == "admin":
            return True
        
        # 检查是否在允许列表中
        if perms["wells"] == "*" or well_id in perms["wells"]:
            return True
        
        return False
    
    @staticmethod
    def check_block_access(user_role: str, block_name: str) -> bool:
        """检查用户是否有权限访问特定区块"""
        # 🔓 开发模式：跳过权限检查
        if DEV_MODE:
            return True
        
        perms = USER_PERMISSIONS.get(user_role, USER_PERMISSIONS["default"])
        
        if perms["role"] == "admin":
            return True
        
        if perms["blocks"] == "*" or block_name in perms["blocks"]:
            return True
        
        return False
    
    @staticmethod
    def get_accessible_wells(user_role: str) -> List[str]:
        """获取用户可访问的所有井号"""
        # 🔓 开发模式：返回所有井
        if DEV_MODE:
            return "*"
        
        perms = USER_PERMISSIONS.get(user_role, USER_PERMISSIONS["default"])
        if perms["wells"] == "*":
            return "*"
        return perms["wells"]


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
                    # 提取用户角色（如果有）
                    user_role = kwargs.get('user_role', 'default')
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
# Part 2: 数据库模型定义
# ==========================================

Base = declarative_base()

class Well(Base):
    """井基本信息表"""
    __tablename__ = 'wells'
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    block = Column(String(50))
    target_depth = Column(Float)
    spud_date = Column(Date)
    status = Column(String(20))  # Active, Completed, Suspended
    well_type = Column(String(30))  # Vertical, Horizontal, Directional
    team = Column(String(50))
    rig = Column(String(50))
    
    reports = relationship("DailyReport", back_populates="well")
    casings = relationship("CasingProgram", back_populates="well")

class DailyReport(Base):
    """钻井日报表"""
    __tablename__ = 'daily_reports'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    report_date = Column(Date)
    report_no = Column(Integer)
    
    # 深度与进尺
    current_depth = Column(Float)
    progress = Column(Float)  # 日进尺
    
    # 泥浆参数
    mud_density = Column(Float)  # 密度 (sg)
    mud_viscosity = Column(Float)  # 粘度 (s)
    mud_ph = Column(Float)
    
    # 作业描述
    operation_summary = Column(Text)
    next_plan = Column(Text)
    
    # 关键参数
    avg_rop = Column(Float)  # 平均机械钻速 (m/h)
    bit_number = Column(Integer)
    
    npt_events = relationship("NPTEvent", back_populates="report")
    well = relationship("Well", back_populates="reports")

class NPTEvent(Base):
    """非生产时间/复杂事故表"""
    __tablename__ = 'npt_events'
    
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'))
    category = Column(String(50))  # Lost Circulation, Kick, Equipment Failure, etc.
    duration = Column(Float)  # 损失时间（小时）
    severity = Column(String(20))  # Low, Medium, High
    description = Column(Text)
    
    report = relationship("DailyReport", back_populates="npt_events")

class CasingProgram(Base):
    """套管程序/井身结构表"""
    __tablename__ = 'casing_programs'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    run_number = Column(Integer)
    run_date = Column(Date)
    size = Column(Float)  # 套管尺寸 (inch)
    shoe_depth = Column(Float)  # 下入深度 (m)
    cement_top = Column(Float)  # 水泥返高 (m)
    
    well = relationship("Well", back_populates="casings")

# ==========================================
# Part 3: 数据库初始化与模拟数据
# ==========================================

# 使用内存数据库（生产环境替换为实际数据库连接）
engine = create_engine('sqlite:///:memory:', echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def seed_mock_data():
    """注入模拟数据"""
    session = Session()
    
    try:
        # 创建井信息
        wells = [
            Well(id="ZT-102", name="中塔-102", block="Block-A", target_depth=4500, 
                 spud_date=date(2023, 10, 1), status="Active", well_type="Horizontal",
                 team="Team-701", rig="Rig-50"),
            Well(id="ZT-105", name="中塔-105", block="Block-A", target_depth=4200,
                 spud_date=date(2023, 10, 5), status="Active", well_type="Vertical",
                 team="Team-702", rig="Rig-51"),
            Well(id="ZT-108", name="中塔-108", block="Block-A", target_depth=5000,
                 spud_date=date(2023, 9, 20), status="Completed", well_type="Directional",
                 team="Team-701", rig="Rig-50"),
            Well(id="XY-009", name="新疆-009", block="Block-B", target_depth=5500,
                 spud_date=date(2023, 9, 15), status="Active", well_type="Horizontal",
                 team="Team-808", rig="Rig-88"),
        ]
        session.add_all(wells)
        
        # 创建日报数据
        base_date = date(2023, 11, 1)
        
        # ZT-102: 正常钻进 + 一次井漏事故
        for i in range(10):
            report_date = base_date + timedelta(days=i)
            is_npt_day = (i == 5)  # 第6天发生井漏
            
            progress = 50 if is_npt_day else 150
            current_depth = 3000 + sum([50 if j == 5 else 150 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="ZT-102",
                report_date=report_date,
                report_no=25 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.25 if i < 5 else 1.28,  # 事故后加重泥浆
                mud_viscosity=55 + i * 0.5,
                mud_ph=9.5,
                avg_rop=25.0 if not is_npt_day else 8.0,
                bit_number=3 if i < 7 else 4,
                operation_summary=f"钻进8.5寸井段，{'遇井漏，循环压井' if is_npt_day else '作业正常'}。当前井深{current_depth}米。",
                next_plan="继续钻进" if not is_npt_day else "观察井况，准备处理井漏"
            )
            
            if is_npt_day:
                npt = NPTEvent(
                    category="Lost Circulation",
                    duration=12.5,
                    severity="High",
                    description="井深3750米处发生井漏，漏失速率15立方米/小时，泵注堵漏材料处理。"
                )
                r.npt_events.append(npt)
            
            session.add(r)
        
        # ZT-105: 快速钻井，无事故
        for i in range(10):
            report_date = base_date + timedelta(days=i)
            r = DailyReport(
                well_id="ZT-105",
                report_date=report_date,
                report_no=30 + i,
                current_depth=3200 + i * 180,
                progress=180,
                mud_density=1.22,
                mud_viscosity=52.0,
                mud_ph=9.8,
                avg_rop=30.0,
                bit_number=2,
                operation_summary=f"钻进顺利，机械钻速高，地层稳定。当前井深{3200 + i * 180}米。",
                next_plan="继续正常钻进"
            )
            session.add(r)
        
        # ZT-108: 已完井，有历史数据
        for i in range(5):
            report_date = base_date + timedelta(days=i)
            r = DailyReport(
                well_id="ZT-108",
                report_date=report_date,
                report_no=80 + i,
                current_depth=4800 + i * 40,
                progress=40,
                mud_density=1.30,
                mud_viscosity=60.0,
                mud_ph=9.3,
                avg_rop=15.0,
                bit_number=5,
                operation_summary=f"完井作业中，当前井深{4800 + i * 40}米。",
                next_plan="准备下套管"
            )
            session.add(r)
        
        # XY-009: Block-B的井（用于测试权限）
        for i in range(5):
            report_date = base_date + timedelta(days=i)
            r = DailyReport(
                well_id="XY-009",
                report_date=report_date,
                report_no=15 + i,
                current_depth=2500 + i * 120,
                progress=120,
                mud_density=1.18,
                mud_viscosity=48.0,
                mud_ph=10.0,
                avg_rop=28.0,
                bit_number=1,
                operation_summary=f"钻进正常，当前井深{2500 + i * 120}米。",
                next_plan="继续钻进"
            )
            session.add(r)
        
        # 套管数据
        casings = [
            CasingProgram(well_id="ZT-102", run_number=1, run_date=date(2023, 10, 5),
                         size=13.375, shoe_depth=800, cement_top=0),
            CasingProgram(well_id="ZT-102", run_number=2, run_date=date(2023, 10, 20),
                         size=9.625, shoe_depth=2500, cement_top=500),
            CasingProgram(well_id="ZT-105", run_number=1, run_date=date(2023, 10, 8),
                         size=13.375, shoe_depth=850, cement_top=0),
        ]
        session.add_all(casings)
        
        session.commit()
        logger.info("✅ Mock data seeded successfully.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error seeding data: {e}")
        raise
    finally:
        session.close()

# 初始化数据
seed_mock_data()

# ==========================================
# Part 4: MCP Server 定义
# ==========================================

mcp = FastMCP("Oilfield Intelligence Server")

# 辅助函数
def df_to_markdown(df: pd.DataFrame) -> str:
    """将DataFrame转换为Markdown表格"""
    if df.empty:
        return "无数据"
    return df.to_markdown(index=False)

def normalize_well_id(well_id: str) -> str:
    """
    归一化井号（处理中文井号和各种别名）
    参考 many-tool.md 第1868-1876行的参数归一化策略
    """
    # 简单的映射表（优先匹配）
    mappings = {
        "中102": "ZT-102",
        "中塔102": "ZT-102",
        "中105": "ZT-105",
        "中塔105": "ZT-105",
        "中108": "ZT-108",
        "中塔108": "ZT-108",
        "102井": "ZT-102",
        "105井": "ZT-105",
        "108井": "ZT-108",
        "新009": "XY-009",
        "新疆009": "XY-009",
    }
    
    # 优先使用映射表
    if well_id in mappings:
        return mappings[well_id]
    
    # 智能提取：从各种格式中提取数字
    # 支持："中102"、"ZT102"、"102" 等格式
    match = re.search(r'(\d+)', well_id)
    if match:
        number = match.group(1)
        
        # 根据前缀判断井号类型
        if any(prefix in well_id.lower() for prefix in ['中', 'zt', '塔']):
            return f"ZT-{number}"
        elif any(prefix in well_id.lower() for prefix in ['新', 'xy', '疆']):
            return f"XY-{number}"
    
    # 无法识别，返回原值
    return well_id


def normalize_date(date_str: str) -> str:
    """
    归一化日期描述（处理模糊时间）
    参考 many-tool.md 第1877-1880行的时间描述处理
    
    支持：
    - "昨天"、"yesterday" → 2024-01-25
    - "上周"、"last_week" → 计算上周日期范围
    - "本月"、"this_month" → 当月第一天
    - 标准格式 "2024-01-26" → 直接返回
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    
    # 已经是标准格式
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # 中文和英文的模糊时间映射
    mappings = {
        # 相对日期
        "今天": today,
        "昨天": today - timedelta(days=1),
        "前天": today - timedelta(days=2),
        "tomorrow": today + timedelta(days=1),
        "yesterday": today - timedelta(days=1),
        
        # 周
        "上周": today - timedelta(days=7),
        "last_week": today - timedelta(days=7),
        "本周": today - timedelta(days=today.weekday()),
        "this_week": today - timedelta(days=today.weekday()),
        
        # 月
        "本月": today.replace(day=1),
        "this_month": today.replace(day=1),
        "上月": (today.replace(day=1) - timedelta(days=1)).replace(day=1),
        "last_month": (today.replace(day=1) - timedelta(days=1)).replace(day=1),
    }
    
    date_lower = date_str.lower().strip()
    if date_lower in mappings:
        return mappings[date_lower].strftime("%Y-%m-%d")
    
    # 无法识别，返回今天
    logger.warning(f"无法识别日期 '{date_str}'，默认使用今天")
    return today.strftime("%Y-%m-%d")


def parse_date_range(range_str: str) -> tuple:
    """
    解析日期范围描述
    
    支持：
    - "上周" → (2024-01-15, 2024-01-21)
    - "本月" → (2024-01-01, 2024-01-26)
    - "最近7天" → (2024-01-19, 2024-01-26)
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    
    if "上周" in range_str or "last_week" in range_str.lower():
        # 上周一到上周日
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return (last_monday.strftime("%Y-%m-%d"), last_sunday.strftime("%Y-%m-%d"))
    
    elif "本周" in range_str or "this_week" in range_str.lower():
        # 本周一到今天
        this_monday = today - timedelta(days=today.weekday())
        return (this_monday.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))
    
    elif "本月" in range_str or "this_month" in range_str.lower():
        # 本月1号到今天
        first_day = today.replace(day=1)
        return (first_day.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))
    
    elif "最近" in range_str:
        # 提取数字："最近7天"
        match = re.search(r'(\d+)', range_str)
        if match:
            days = int(match.group(1))
            start_date = today - timedelta(days=days)
            return (start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))
    
    # 默认返回最近7天
    return ((today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))

# ==========================================
# 模块 0: 术语查询与意图规划工具
# ==========================================

# 钻井术语词典（支持中英文和行业黑话）
DRILLING_TERMINOLOGY = {
    # 作业活动类
    "憋泵": {
        "standard": "Pump Pressure Spike",
        "category": "Equipment",
        "description": "泵压异常升高，可能是钻头堵塞或井眼缩径",
        "related_tools": ["get_daily_report", "analyze_npt_events"]
    },
    "起下钻": {
        "standard": "Tripping",
        "category": "Activity",
        "description": "起钻或下钻作业，取出或放入钻具",
        "related_tools": ["get_daily_report"]
    },
    "划眼": {
        "standard": "Reaming",
        "category": "Activity",
        "description": "通过扩眼工具扩大井眼直径",
        "related_tools": ["get_daily_report"]
    },
    "通井": {
        "standard": "Circulation",
        "category": "Activity",
        "description": "循环钻井液，清洁井眼",
        "related_tools": ["get_daily_report", "track_mud_properties"]
    },
    "蹩钻": {
        "standard": "Bit Sticking",
        "category": "NPT",
        "description": "钻头被卡住，无法正常钻进",
        "related_tools": ["analyze_npt_events"]
    },
    
    # 事故类型
    "井漏": {
        "standard": "Lost Circulation",
        "category": "NPT",
        "description": "钻井液漏失到地层中，循环系统失去泥浆",
        "related_tools": ["analyze_npt_events", "track_mud_properties"]
    },
    "溢流": {
        "standard": "Kick",
        "category": "NPT",
        "description": "地层流体侵入井筒，井口返出超过泵入",
        "related_tools": ["analyze_npt_events"]
    },
    "卡钻": {
        "standard": "Stuck Pipe",
        "category": "NPT",
        "description": "钻具被卡在井内无法活动",
        "related_tools": ["analyze_npt_events"]
    },
    "井塌": {
        "standard": "Wellbore Collapse",
        "category": "NPT",
        "description": "井壁失稳坍塌，可能导致卡钻",
        "related_tools": ["analyze_npt_events", "track_mud_properties"]
    },
    "井喷": {
        "standard": "Blowout",
        "category": "NPT",
        "description": "严重的井控事故，地层流体不受控制喷出",
        "related_tools": ["analyze_npt_events"]
    },
    
    # 钻井参数
    "泥浆": {
        "standard": "Drilling Fluid / Mud",
        "category": "Parameter",
        "description": "钻井液，用于冷却钻头、携带岩屑、平衡地层压力",
        "related_tools": ["track_mud_properties", "get_daily_report"]
    },
    "比重": {
        "standard": "Density / Specific Gravity",
        "category": "Parameter",
        "description": "泥浆密度，影响井底压力",
        "related_tools": ["track_mud_properties"]
    },
    "粘度": {
        "standard": "Viscosity",
        "category": "Parameter",
        "description": "泥浆粘度，影响携砂和摩阻",
        "related_tools": ["track_mud_properties"]
    },
    "钻速": {
        "standard": "ROP (Rate of Penetration)",
        "category": "Parameter",
        "description": "机械钻速，米/小时",
        "related_tools": ["compare_drilling_pace", "get_daily_report"]
    },
    "进尺": {
        "standard": "Progress / Footage",
        "category": "Parameter",
        "description": "钻井进尺，通常指日进尺（米/天）",
        "related_tools": ["get_period_drilling_summary", "compare_drilling_pace"]
    },
    
    # 井身结构
    "套管": {
        "standard": "Casing",
        "category": "Well Structure",
        "description": "下入井内的钢管，用于支撑井壁",
        "related_tools": ["get_well_casing"]
    },
    "固井": {
        "standard": "Cementing",
        "category": "Activity",
        "description": "在套管和井壁之间注入水泥",
        "related_tools": ["get_well_casing"]
    },
    "完井": {
        "standard": "Well Completion",
        "category": "Activity",
        "description": "钻井结束后的井筒准备工作",
        "related_tools": ["get_well_summary"]
    },
    
    # 其他常用词
    "开钻": {
        "standard": "Spud",
        "category": "Activity",
        "description": "开始钻井作业",
        "related_tools": ["get_well_summary"]
    },
    "钻遇": {
        "standard": "Drilling Through",
        "category": "Activity",
        "description": "钻头钻穿某个地层",
        "related_tools": ["get_daily_report"]
    },
    "复杂": {
        "standard": "Complex Situation",
        "category": "NPT",
        "description": "井下复杂情况，通常指各种事故",
        "related_tools": ["analyze_npt_events"]
    },
    "提速": {
        "standard": "Speed Up / Increase ROP",
        "category": "Optimization",
        "description": "提高钻井速度，缩短钻井周期",
        "related_tools": ["compare_drilling_pace"]
    }
}


@mcp.tool()
@AuditLog.trace("lookup_terminology")
def lookup_terminology(
    term: str = Field(..., description="需要查询的钻井术语或行业黑话，例如：'憋泵'、'井漏'、'起下钻'")
) -> str:
    """
    [场景] 查询钻井术语的标准定义、分类和相关工具。用于理解用户的行业黑话。
    [关键词] 术语、黑话、什么是、定义
    
    参考 many-tool.md 第1914-1930行的"澄清工具"策略。
    当用户使用行业黑话或不确定的术语时，先查询术语标准定义。
    """
    # 精确匹配
    if term in DRILLING_TERMINOLOGY:
        info = DRILLING_TERMINOLOGY[term]
        tools_list = "\n".join([f"  - {tool}" for tool in info["related_tools"]])
        
        return f"""
### 📖 术语查询结果

**原始术语**: {term}

**标准名称**: {info['standard']}

**分类**: {info['category']}

**定义**: {info['description']}

**相关工具**:
{tools_list}

---
💡 **建议**：根据您的查询意图，可以调用上述相关工具获取具体数据。
"""
    
    # 模糊匹配（部分匹配）
    matches = []
    for key, info in DRILLING_TERMINOLOGY.items():
        if term in key or key in term or term.lower() in info['standard'].lower():
            matches.append((key, info))
    
    if matches:
        results = []
        for key, info in matches[:5]:  # 最多返回5个匹配结果
            results.append(f"- **{key}** ({info['standard']}): {info['description']}")
        
        results_str = "\n".join(results)
        return f"""
### 🔍 找到 {len(matches)} 个相似术语

{results_str}

---
💡 请使用 `lookup_terminology` 工具查询具体术语的详细信息。
"""
    
    # 未找到
    return f"""
❌ 未找到术语 '{term}' 的标准定义。

可能的原因：
1. 术语拼写错误
2. 该术语未收录在词典中

**建议**：
- 请尝试描述具体的情况或问题
- 或直接说明您想查询什么数据

**示例**：
- "查询ZT-102井昨天的作业情况" → 调用 get_daily_report
- "分析ZT-102井的事故记录" → 调用 analyze_npt_events
- "对比两口井的钻井速度" → 调用 compare_drilling_pace
"""


@mcp.tool()
@AuditLog.trace("plan_data_retrieval")
def plan_data_retrieval(
    intent_category: Literal["single_well_status", "multi_well_compare", "historical_report", "realtime_monitor", "report_generation"] = Field(
        ..., description="用户意图分类"
    ),
    entities: List[str] = Field(
        ..., description="涉及的实体（井号、区块等），例如：['ZT-102', 'Block-A']"
    ),
    time_range: str = Field(
        default="today", description="时间范围描述，例如：'today', 'last_week', '2024-01-01到2024-01-31'"
    ),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 这是一个规划工具。当用户的问题比较复杂、涉及多个步骤时，先调用此工具进行意图分类和规划。
    [关键词] 规划、分析、怎么查、如何、复杂查询
    
    这个工具不会查询数据库，只会帮助LLM理解用户意图并规划下一步操作。
    
    参考 many-tool.md 第1849-1863行的"思考工具"策略。
    """
    # 记录规划信息
    logger.info(f"意图规划: category={intent_category}, entities={entities}, time_range={time_range}")
    
    # 根据意图类别提供建议
    suggestions = {
        "single_well_status": {
            "description": "查询单井状态",
            "recommended_tools": ["get_well_summary", "get_daily_report", "analyze_npt_events"],
            "next_step": "调用 get_well_summary 获取井概况"
        },
        "multi_well_compare": {
            "description": "多井对比分析",
            "recommended_tools": ["compare_wells_overview", "compare_drilling_pace", "compare_npt_statistics"],
            "next_step": "调用 compare_drilling_pace 对比钻井速度"
        },
        "historical_report": {
            "description": "历史报告查询",
            "recommended_tools": ["get_period_drilling_summary", "get_block_period_summary"],
            "next_step": "调用 get_period_drilling_summary 获取期间数据"
        },
        "realtime_monitor": {
            "description": "实时监控",
            "recommended_tools": ["get_daily_report", "track_mud_properties"],
            "next_step": "调用 get_daily_report 查看最新日报"
        },
        "report_generation": {
            "description": "报告生成",
            "recommended_tools": ["get_period_drilling_summary", "get_block_period_summary"],
            "next_step": "先获取数据，然后基于数据撰写报告"
        }
    }
    
    plan = suggestions.get(intent_category, suggestions["single_well_status"])
    
    # 归一化实体
    normalized_entities = [normalize_well_id(e) for e in entities]
    
    # 解析时间范围
    if "到" in time_range or "to" in time_range.lower():
        # 已经是范围格式
        date_info = time_range
    else:
        # 单个时间描述，尝试解析为范围
        try:
            start, end = parse_date_range(time_range)
            date_info = f"{start} 到 {end}"
        except:
            date_info = normalize_date(time_range)
    
    return f"""
### 📋 意图规划结果

**意图分类**: {plan['description']} ({intent_category})

**涉及实体**: {', '.join(normalized_entities)}

**时间范围**: {date_info}

**推荐工具**: {', '.join(plan['recommended_tools'])}

**下一步操作**: {plan['next_step']}

---
💡 建议：{plan['next_step']}
"""


# ==========================================
# 模块 1: 井信息发现与概览
# ==========================================

@mcp.tool()
@AuditLog.trace("search_wells")
def search_wells(
    keyword: str = Field(..., description="搜索关键词（井号、井名或区块名），例如：'ZT'、'Block-A'、'中塔'"),
    status: Literal["Active", "Completed", "Suspended", "All"] = Field(
        "All", description="井状态过滤，默认显示所有状态"
    ),
    user_role: str = Field("admin", description="当前用户角色（admin/engineer/viewer）")
) -> str:
    """
    [场景] 模糊搜索油井。当用户不知道准确的井号时使用。
    [关键词] 查询井、找井、搜索井号、区块查询
    """
    session = Session()
    try:
        # 构建查询
        query = session.query(Well).filter(
            (Well.name.contains(keyword)) | 
            (Well.block.contains(keyword)) |
            (Well.id.contains(keyword))
        )
        
        if status != "All":
            query = query.filter(Well.status == status)
        
        wells = query.all()
        
        # 权限过滤
        accessible_wells = PermissionService.get_accessible_wells(user_role)
        if accessible_wells != "*":
            wells = [w for w in wells if w.id in accessible_wells]
        
        if not wells:
            return f"未找到匹配关键词 '{keyword}' 的井（状态：{status}）。"
        
        # 格式化输出
        data = [{
            "井号": w.id,
            "井名": w.name,
            "区块": w.block,
            "状态": w.status,
            "井型": w.well_type,
            "设计井深(m)": w.target_depth,
            "钻井队": w.team
        } for w in wells]
        
        return f"### 🔍 搜索结果（共 {len(wells)} 口井）\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        session.close()


@mcp.tool()
@AuditLog.trace("get_well_summary")
def get_well_summary(
    well_id: str = Field(..., description="井号，例如：'ZT-102'"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 获取单井的完整画像和概览信息。
    [关键词] 井概况、井信息、井画像、基本信息
    """
    # 归一化井号
    well_id = normalize_well_id(well_id)
    
    # 权限检查
    if not PermissionService.check_well_access(user_role, well_id):
        return f"🚫 权限拒绝：用户角色 ({user_role}) 无权访问井号 {well_id}。"
    
    session = Session()
    try:
        well = session.query(Well).filter_by(id=well_id).first()
        
        if not well:
            return f"❌ 未找到井号 '{well_id}'。"
        
        # 获取最新日报
        latest_report = session.query(DailyReport)\
            .filter_by(well_id=well_id)\
            .order_by(DailyReport.report_date.desc())\
            .first()
        
        current_depth = latest_report.current_depth if latest_report else 0
        last_report_date = latest_report.report_date if latest_report else "无数据"
        
        return f"""
### 🆔 井基本信息：{well.name} ({well.id})

| 项目 | 信息 |
|---|---|
| **区块** | {well.block} |
| **井型** | {well.well_type} |
| **状态** | {well.status} |
| **开钻日期** | {well.spud_date} |
| **设计井深** | {well.target_depth} m |
| **当前井深** | {current_depth} m |
| **钻井队** | {well.team} |
| **钻机** | {well.rig} |
| **最新日报** | {last_report_date} |
"""
    
    finally:
        session.close()


@mcp.tool()
@AuditLog.trace("get_well_casing")
def get_well_casing(
    well_id: str = Field(..., description="井号"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 查询井身结构、套管程序。
    [关键词] 套管、井身结构、固井、水泥返高
    """
    well_id = normalize_well_id(well_id)
    
    if not PermissionService.check_well_access(user_role, well_id):
        return f"🚫 权限拒绝：无权访问井号 {well_id}。"
    
    session = Session()
    try:
        casings = session.query(CasingProgram)\
            .filter_by(well_id=well_id)\
            .order_by(CasingProgram.shoe_depth)\
            .all()
        
        if not casings:
            return f"未找到井号 {well_id} 的套管数据。"
        
        data = [{
            "趟次": c.run_number,
            "下入日期": c.run_date,
            "尺寸(in)": c.size,
            "鞋深(m)": c.shoe_depth,
            "水泥返高(m)": c.cement_top
        } for c in casings]
        
        return f"### 🏗️ 井身结构：{well_id}\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        session.close()


# ==========================================
# 模块 2: 日报查询与NPT分析
# ==========================================

# 添加查询缓存避免重复调用
_daily_report_cache = {}
_cache_ttl = 60  # 缓存有效期60秒

@mcp.tool()
@AuditLog.trace("get_daily_report")
def get_daily_report(
    well_id: str = Field(..., description="井号，支持中文井号如'中102'"),
    date: str = Field(default="", description="日期格式：YYYY-MM-DD（如'2023-11-10'）。⚠️ 只有当用户明确说出具体日期时才填写，否则留空，系统会列出可用日期供选择。"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 查询某天的钻井日报（DDR）。支持模糊时间描述。
    [关键词] 日报、DDR、当天作业、每日报告、昨天、今天
    
    ⚠️ 重要说明：
    1. 此工具会自动处理日期格式，请只调用一次，不要重复调用！
    2. 只有当用户明确说出具体日期时才填写date参数（如'2023-11-10'、'昨天'），其他情况一律留空
    3. 如果用户说"查询某井的日报"但没说日期，date参数必须留空，系统会列出可用日期
    4. 绝不要猜测日期或多次尝试！
    
    参考 many-tool.md 第1877-1880行，支持模糊时间描述如"昨天"、"yesterday"等。
    """
    # 归一化井号
    well_id = normalize_well_id(well_id)
    
    # 扩大空值判断：包括空字符串、None、或者模糊表达（如"最新"、"今天"）
    # 如果用户说的是模糊词汇，也应该先展示可用日期
    ambiguous_keywords = ["最新", "latest", "recent", "当前", "current", "now"]
    is_empty_or_ambiguous = (
        not date or 
        date.strip() == "" or
        date.lower().strip() in ambiguous_keywords
    )
    
    # 如果用户未提供明确日期，列出最近可用的日报供选择
    if is_empty_or_ambiguous:
        session = Session()
        try:
            # 查询该井最近的5条日报记录
            recent_reports = session.query(DailyReport)\
                .filter_by(well_id=well_id)\
                .order_by(DailyReport.report_date.desc())\
                .limit(5)\
                .all()
            
            if not recent_reports:
                return f"❌ 未找到井号 {well_id} 的任何日报记录。"
            
            # 生成日期列表
            date_list = []
            for report in recent_reports:
                date_list.append(f"- {report.report_date} (井深: {report.current_depth}m, 进尺: {report.progress}m)")
            
            return f"""
### ℹ️ 请明确查询日期

您查询的是 **{well_id}** 的日报，但未指定具体日期。

以下是该井最近的日报记录：

{chr(10).join(date_list)}

**请明确指定日期**，例如：
- "查询 {well_id} 在 {recent_reports[0].report_date} 的日报"
- "查询 {well_id} 昨天的日报"
- "查询 {well_id} 最新的日报"（将查询 {recent_reports[0].report_date}）
"""
        finally:
            session.close()
    
    # 归一化日期
    date = normalize_date(date)
    
    # 检查缓存
    cache_key = f"{well_id}_{date}_{user_role}"
    if cache_key in _daily_report_cache:
        cache_time, cached_result = _daily_report_cache[cache_key]
        if (datetime.now() - cache_time).seconds < _cache_ttl:
            logger.info(f"✅ 使用缓存数据: {cache_key}")
            return cached_result
    
    if not PermissionService.check_well_access(user_role, well_id):
        return f"🚫 权限拒绝：无权访问井号 {well_id}。"
    
    # 验证日期格式
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"日期格式错误：{date}，原始输入可能未被正确归一化")
        return f"❌ 日期格式错误：{date}。请使用标准格式 YYYY-MM-DD（如 2023-11-10）或使用'昨天'、'today'等。系统已自动尝试转换，但转换失败。"
    
    session = Session()
    try:
        report = session.query(DailyReport)\
            .filter_by(well_id=well_id, report_date=report_date)\
            .first()
        
        if not report:
            return f"未找到 {well_id} 在 {date} 的日报。"
        
        # 获取NPT事件
        npt_summary = "无"
        if report.npt_events:
            npt_list = []
            for npt in report.npt_events:
                npt_list.append(f"- {npt.category} ({npt.duration}小时，{npt.severity}): {npt.description}")
            npt_summary = "\n".join(npt_list)
        
        result = f"""
### 📋 钻井日报：{well_id} - {date} (报告编号：{report.report_no})

#### 基本信息
- **当前井深**: {report.current_depth} m
- **日进尺**: {report.progress} m
- **平均机械钻速**: {report.avg_rop} m/h
- **钻头编号**: #{report.bit_number}

#### 泥浆参数
- **密度**: {report.mud_density} sg
- **粘度**: {report.mud_viscosity} s
- **pH值**: {report.mud_ph}

#### 作业摘要
{report.operation_summary}

#### 下步计划
{report.next_plan}

#### 非生产时间(NPT)
{npt_summary}
"""
        
        # 保存到缓存
        _daily_report_cache[cache_key] = (datetime.now(), result)
        return result
    
    finally:
        session.close()


@mcp.tool()
@AuditLog.trace("analyze_npt_events")
def analyze_npt_events(
    well_id: str = Field(..., description="井号"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 分析某井的所有非生产时间（NPT）事件和复杂情况。
    [关键词] 事故、复杂、井漏、溢流、NPT、非生产时间
    """
    well_id = normalize_well_id(well_id)
    
    if not PermissionService.check_well_access(user_role, well_id):
        return f"🚫 权限拒绝：无权访问井号 {well_id}。"
    
    session = Session()
    try:
        # 联表查询
        results = session.query(DailyReport, NPTEvent)\
            .join(NPTEvent)\
            .filter(DailyReport.well_id == well_id)\
            .order_by(DailyReport.report_date)\
            .all()
        
        if not results:
            return f"✅ 井号 {well_id} 无NPT记录，作业安全高效。"
        
        # 统计分析
        total_npt_hours = sum([npt.duration for _, npt in results])
        event_count = len(results)
        
        # 按类别统计
        category_stats = {}
        for _, npt in results:
            if npt.category not in category_stats:
                category_stats[npt.category] = {"count": 0, "hours": 0}
            category_stats[npt.category]["count"] += 1
            category_stats[npt.category]["hours"] += npt.duration
        
        # 详细事件列表
        events = []
        for report, npt in results:
            events.append({
                "日期": report.report_date,
                "井深(m)": report.current_depth,
                "类别": npt.category,
                "损失(小时)": npt.duration,
                "严重程度": npt.severity,
                "描述": npt.description[:50] + "..." if len(npt.description) > 50 else npt.description
            })
        
        # 分类统计表
        category_df = pd.DataFrame([
            {"事故类别": k, "发生次数": v["count"], "总损失时间(小时)": v["hours"]}
            for k, v in category_stats.items()
        ])
        
        return f"""
### ⚠️ NPT分析报告：{well_id}

#### 汇总统计
- **总事件数**: {event_count} 次
- **总损失时间**: {total_npt_hours} 小时
- **平均单次损失**: {total_npt_hours / event_count:.1f} 小时

#### 事故分类统计
{df_to_markdown(category_df)}

#### 详细事件清单
{df_to_markdown(pd.DataFrame(events))}
"""
    
    finally:
        session.close()


# ==========================================
# 模块 3: 多井对比分析
# ==========================================

@mcp.tool()
@AuditLog.trace("compare_wells_overview")
def compare_wells_overview(
    well_ids: str = Field(..., description="逗号分隔的井号列表，支持中文井号，例如：'ZT-102,ZT-105' 或 '中102,中105'"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 对比多口井的基本信息和关键指标。支持中文井号。
    [关键词] 对比、比较、邻井、多井
    
    参考 many-tool.md 第1868-1876行，支持中文井号自动归一化。
    """
    ids = [normalize_well_id(w.strip()) for w in well_ids.split(',')]
    
    # 权限检查：必须对所有井都有权限
    denied_wells = [wid for wid in ids if not PermissionService.check_well_access(user_role, wid)]
    
    if denied_wells:
        return f"🚫 权限拒绝：用户角色 ({user_role}) 无权访问井号 {', '.join(denied_wells)}。"
    
    accessible_ids = ids
    
    session = Session()
    try:
        wells = session.query(Well).filter(Well.id.in_(accessible_ids)).all()
        
        if not wells:
            return "未找到指定的井。"
        
        data = []
        for w in wells:
            # 获取最新井深
            latest = session.query(DailyReport)\
                .filter_by(well_id=w.id)\
                .order_by(DailyReport.report_date.desc())\
                .first()
            
            current_depth = latest.current_depth if latest else 0
            
            data.append({
                "井号": w.id,
                "井名": w.name,
                "区块": w.block,
                "井型": w.well_type,
                "状态": w.status,
                "设计井深(m)": w.target_depth,
                "当前井深(m)": current_depth,
                "完成度(%)": round(current_depth / w.target_depth * 100, 1) if w.target_depth > 0 else 0,
                "开钻日期": w.spud_date,
                "钻井队": w.team
            })
        
        return f"### 📊 多井对比概览\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        session.close()


@mcp.tool()
@AuditLog.trace("compare_drilling_pace")
def compare_drilling_pace(
    well_ids: str = Field(..., description="逗号分隔的井号列表，支持中文井号，例如：'ZT-102,ZT-105' 或 '中102,中105'"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 对比多口井的钻井速度、进尺效率。用于识别标杆井。支持中文井号。
    [关键词] 钻速、ROP、进尺、效率、谁快、提速
    
    参考 many-tool.md 第1820-1821行的意图映射策略。
    """
    ids = [normalize_well_id(w.strip()) for w in well_ids.split(',')]
    
    # 权限检查：必须对所有井都有权限
    denied_wells = [wid for wid in ids if not PermissionService.check_well_access(user_role, wid)]
    
    if denied_wells:
        return f"🚫 权限拒绝：用户角色 ({user_role}) 无权访问井号 {', '.join(denied_wells)}。"
    
    accessible_ids = ids
    
    session = Session()
    try:
        reports = session.query(DailyReport)\
            .filter(DailyReport.well_id.in_(accessible_ids))\
            .all()
        
        if not reports:
            return "无对比数据。"
        
        # 转为DataFrame进行聚合
        df = pd.DataFrame([{
            "well_id": r.well_id,
            "progress": r.progress,
            "avg_rop": r.avg_rop,
            "depth": r.current_depth,
            "date": r.report_date
        } for r in reports])
        
        # 计算各井的关键指标
        stats = df.groupby("well_id").agg({
            "progress": ["sum", "mean"],
            "avg_rop": "mean",
            "depth": "max",
            "date": ["min", "max"]
        }).reset_index()
        
        stats.columns = ["井号", "总进尺(m)", "平均日进尺(m)", "平均ROP(m/h)", 
                        "最大井深(m)", "开始日期", "最新日期"]
        
        # 计算钻井天数
        stats["钻井天数"] = stats.apply(
            lambda row: (row["最新日期"] - row["开始日期"]).days + 1, axis=1
        )
        
        # 计算效率指标
        stats["米/天"] = stats["总进尺(m)"] / stats["钻井天数"]
        
        # 排序
        stats = stats.sort_values("米/天", ascending=False)
        
        # 格式化输出列
        output_cols = ["井号", "总进尺(m)", "平均日进尺(m)", "平均ROP(m/h)", 
                      "钻井天数", "米/天", "最大井深(m)"]
        
        return f"""
### 🏎️ 钻井速度对比分析

{df_to_markdown(stats[output_cols].round(1))}

**分析建议**：
- 排名第一的井为提速标杆井
- 关注平均ROP和米/天指标的差异
- 建议深入分析标杆井的作业参数
"""
    
    finally:
        session.close()


@mcp.tool()
@AuditLog.trace("compare_npt_statistics")
def compare_npt_statistics(
    well_ids: str = Field(..., description="逗号分隔的井号列表，支持中文井号"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 对比多口井的NPT情况，识别风险井。支持中文井号。
    [关键词] 事故对比、风险对比、复杂情况对比
    
    参考 many-tool.md 第1825行，NPT意图识别策略。
    """
    ids = [normalize_well_id(w.strip()) for w in well_ids.split(',')]
    
    # 权限检查：必须对所有井都有权限
    denied_wells = [wid for wid in ids if not PermissionService.check_well_access(user_role, wid)]
    
    if denied_wells:
        return f"🚫 权限拒绝：用户角色 ({user_role}) 无权访问井号 {', '.join(denied_wells)}。"
    
    accessible_ids = ids
    
    session = Session()
    try:
        results = session.query(NPTEvent, DailyReport)\
            .join(DailyReport)\
            .filter(DailyReport.well_id.in_(accessible_ids))\
            .all()
        
        if not results:
            return "✅ 对比井均无NPT记录，作业安全。"
        
        # 构建数据
        data = []
        for npt, report in results:
            data.append({
                "well_id": report.well_id,
                "category": npt.category,
                "duration": npt.duration
            })
        
        df = pd.DataFrame(data)
        
        # 透视表：井 vs 事故类别
        pivot = df.pivot_table(
            index="well_id",
            columns="category",
            values="duration",
            aggfunc="sum",
            fill_value=0
        )
        
        # 添加总计列
        pivot["总NPT(小时)"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("总NPT(小时)", ascending=False)
        
        # 事故次数统计
        count_df = df.groupby("well_id").size().reset_index(name="事故次数")
        
        return f"""### ⚠️ NPT对比分析矩阵

#### 按事故类别统计（单位：小时）
{pivot.to_markdown()}

#### 事故频次统计
{df_to_markdown(count_df)}

**风险提示**：
- NPT最高的井需要重点关注
- 建议分析事故原因并制定预防措施

---
💡 **可视化建议**：此数据适合用 **柱状图** 展示，可以直观对比各井的NPT总时长和事故频次。
"""
    
    finally:
        session.close()


# ==========================================
# 模块 4: 周报/月报生成
# ==========================================

@mcp.tool()
@AuditLog.trace("get_period_drilling_summary")
def get_period_drilling_summary(
    well_id: str = Field(..., description="井号，支持中文井号"),
    start_date: str = Field(..., description="开始日期，支持：'YYYY-MM-DD'、'上周'、'本月'等"),
    end_date: str = Field(..., description="结束日期，支持：'YYYY-MM-DD'、'今天'、'yesterday'等"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 汇总某口井在指定时间段的钻井数据，用于生成周报或月报。支持模糊时间描述。
    [关键词] 周报、月报、汇总、总结、期间报告、上周、本月
    
    参考 many-tool.md 第1877-1880行，支持"上周"、"本月"等模糊时间描述。
    """
    # 归一化井号和日期
    well_id = normalize_well_id(well_id)
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    
    if not PermissionService.check_well_access(user_role, well_id):
        return "🚫 权限拒绝。"
    
    # 验证日期
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return f"❌ 日期格式错误：{start_date} 或 {end_date}"
    
    session = Session()
    try:
        reports = session.query(DailyReport)\
            .filter(
                DailyReport.well_id == well_id,
                DailyReport.report_date >= s_date,
                DailyReport.report_date <= e_date
            )\
            .order_by(DailyReport.report_date)\
            .all()
        
        if not reports:
            return f"期间 {start_date} 至 {end_date} 无钻井数据。"
        
        # 构建数据
        data = []
        for r in reports:
            npt_hours = sum(n.duration for n in r.npt_events)
            npt_desc = "; ".join([f"{n.category}({n.duration}h)" for n in r.npt_events])
            
            data.append({
                "date": r.report_date,
                "depth": r.current_depth,
                "progress": r.progress,
                "avg_rop": r.avg_rop,
                "mud_density": r.mud_density,
                "npt_hours": npt_hours,
                "npt_desc": npt_desc,
                "summary": r.operation_summary
            })
        
        df = pd.DataFrame(data)
        
        # 核心指标计算
        total_days = len(df)
        start_depth = df.iloc[0]['depth'] - df.iloc[0]['progress']
        end_depth = df.iloc[-1]['depth']
        total_footage = end_depth - start_depth
        avg_daily_progress = df['progress'].mean()
        avg_rop = df['avg_rop'].mean()
        
        total_npt = df['npt_hours'].sum()
        npt_days = (df['npt_hours'] > 0).sum()
        
        # 泥浆变化
        mud_min = df['mud_density'].min()
        mud_max = df['mud_density'].max()
        mud_trend = "稳定" if (mud_max - mud_min) < 0.03 else f"调整({mud_min:.2f} → {mud_max:.2f})"
        
        # 构建每日时间轴
        timeline = []
        for _, row in df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            icon = "⚠️" if row['npt_hours'] > 0 else "✅"
            npt_text = f" [NPT: {row['npt_desc']}]" if row['npt_hours'] > 0 else ""
            summary_short = row['summary'][:80] + "..." if len(row['summary']) > 80 else row['summary']
            
            timeline.append(
                f"- **{date_str}** {icon}: 井深{row['depth']}m (+{row['progress']}m), "
                f"ROP={row['avg_rop']}m/h. {summary_short}{npt_text}"
            )
        
        timeline_str = "\n".join(timeline)
        
        return f"""
### 📊 钻井期间报告数据汇总：{well_id}
**期间**: {start_date} 至 {end_date}

#### 1. 核心指标
| 指标 | 数值 |
|---|---|
| **作业天数** | {total_days} 天 |
| **完成进尺** | {total_footage:.1f} m |
| **深度区间** | {start_depth:.1f} m → {end_depth:.1f} m |
| **平均日进尺** | {avg_daily_progress:.1f} m/天 |
| **平均机械钻速** | {avg_rop:.1f} m/h |
| **总NPT** | {total_npt:.1f} 小时 ({npt_days} 天有事故) |
| **泥浆密度** | {mud_trend} sg |

#### 2. 每日作业时间轴
{timeline_str}

#### 3. 报告生成建议
- 使用以上指标撰写"绩效概览"部分
- 使用时间轴内容撰写"关键作业"部分
- 将⚠️标记的事项汇总到"HSE与风险"部分
- 根据平均ROP和日进尺评价提速效果
"""
    
    finally:
        session.close()


@mcp.tool()
@AuditLog.trace("get_block_period_summary")
def get_block_period_summary(
    block_name: str = Field(..., description="区块名称，例如：'Block-A'"),
    start_date: str = Field(..., description="开始日期，支持：'YYYY-MM-DD'、'上周'、'本月'等"),
    end_date: str = Field(..., description="结束日期，支持：'YYYY-MM-DD'、'今天'等"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 生成整个区块或采油厂的汇总报告，用于管理层汇报。支持模糊时间描述。
    [关键词] 区块报告、厂级报告、汇总报告、生产报告、本月、上周
    
    参考 many-tool.md 第1877-1880行，支持模糊时间描述。
    """
    # 归一化日期
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    if not PermissionService.check_block_access(user_role, block_name):
        return f"🚫 权限拒绝：无权访问区块 {block_name}。"
    
    # 验证日期
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return "❌ 日期格式错误。"
    
    session = Session()
    try:
        # 查找区块下的所有井
        wells = session.query(Well).filter_by(block=block_name).all()
        well_ids = [w.id for w in wells]
        
        if not well_ids:
            return f"区块 {block_name} 下无井数据。"
        
        # 权限过滤
        accessible_wells = PermissionService.get_accessible_wells(user_role)
        if accessible_wells != "*":
            well_ids = [wid for wid in well_ids if wid in accessible_wells]
        
        if not well_ids:
            return "🚫 您无权访问该区块下的任何井。"
        
        # 获取期间内的所有日报
        reports = session.query(DailyReport, Well)\
            .join(Well)\
            .filter(
                DailyReport.well_id.in_(well_ids),
                DailyReport.report_date >= s_date,
                DailyReport.report_date <= e_date
            )\
            .all()
        
        if not reports:
            return f"区块 {block_name} 在该期间无作业数据。"
        
        # 构建数据
        data = []
        for r, w in reports:
            npt_hours = sum(n.duration for n in r.npt_events)
            data.append({
                "well_id": w.id,
                "well_name": w.name,
                "team": w.team,
                "progress": r.progress,
                "npt": npt_hours,
                "depth": r.current_depth
            })
        
        df = pd.DataFrame(data)
        
        # 宏观指标
        active_wells = df['well_id'].nunique()
        total_footage = df['progress'].sum()
        total_npt = df['npt'].sum()
        avg_rop_block = df['progress'].mean()
        
        # 排名分析
        well_stats = df.groupby(['well_id', 'well_name']).agg({
            'progress': 'sum',
            'npt': 'sum'
        }).reset_index()
        well_stats.columns = ['井号', '井名', '总进尺(m)', '总NPT(小时)']
        well_stats = well_stats.sort_values('总进尺(m)', ascending=False)
        
        top_performer = well_stats.iloc[0]['井号'] if not well_stats.empty else "N/A"
        
        # 问题井（NPT最多）
        trouble_df = well_stats[well_stats['总NPT(小时)'] > 0].sort_values('总NPT(小时)', ascending=False)
        trouble_well = trouble_df.iloc[0]['井号'] if not trouble_df.empty else "无"
        
        # 队伍统计
        team_stats = df.groupby('team').agg({
            'progress': 'sum',
            'npt': 'sum'
        }).reset_index()
        team_stats.columns = ['钻井队', '总进尺(m)', '总NPT(小时)']
        team_stats = team_stats.sort_values('总进尺(m)', ascending=False)
        
        return f"""
### 🏭 区块汇总报告：{block_name}
**期间**: {start_date} 至 {end_date}

#### 1. 宏观绩效
| 指标 | 数值 |
|---|---|
| **动用井数** | {active_wells} 口 |
| **总完成进尺** | {total_footage:.1f} m |
| **总NPT** | {total_npt:.1f} 小时 |
| **区块平均日进尺** | {avg_rop_block:.1f} m/天 |
| **提速标杆井** | {top_performer} |
| **重点关注井** | {trouble_well} (NPT最高) |

#### 2. 单井绩效排名
{df_to_markdown(well_stats)}

#### 3. 钻井队绩效
{df_to_markdown(team_stats)}

#### 4. 管理建议
- 标杆井 {top_performer} 的优秀做法值得在区块内推广
- 需加强对问题井 {trouble_well} 的技术支持
- 区块整体NPT控制需要加强，建议召开技术分析会
"""
    
    finally:
        session.close()


# ==========================================
# 模块 5: 泥浆参数追踪
# ==========================================

@mcp.tool()
@AuditLog.trace("track_mud_properties")
def track_mud_properties(
    well_id: str = Field(..., description="井号，支持中文井号如'中102'"),
    property_name: Literal["density", "viscosity", "ph"] = Field(
        "density", description="要追踪的泥浆参数：密度/粘度/pH值"
    ),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 追踪泥浆参数变化趋势，用于判断井筒稳定性。支持中文井号。
    [关键词] 泥浆、密度、粘度、井筒稳定、泥浆性能
    
    参考 many-tool.md 第1868-1876行，支持中文井号归一化。
    """
    well_id = normalize_well_id(well_id)
    
    if not PermissionService.check_well_access(user_role, well_id):
        return "🚫 权限拒绝。"
    
    session = Session()
    try:
        reports = session.query(DailyReport)\
            .filter_by(well_id=well_id)\
            .order_by(DailyReport.report_date)\
            .all()
        
        if not reports:
            return "无泥浆数据。"
        
        # 映射
        prop_map = {
            "density": ("mud_density", "密度(sg)"),
            "viscosity": ("mud_viscosity", "粘度(s)"),
            "ph": ("mud_ph", "pH值")
        }
        
        field, label = prop_map[property_name]
        
        data = []
        for r in reports:
            value = getattr(r, field)
            data.append({
                "日期": r.report_date,
                "井深(m)": r.current_depth,
                label: value
            })
        
        df = pd.DataFrame(data)
        
        # 计算趋势
        values = df[label].values
        trend = "上升" if values[-1] > values[0] else "下降" if values[-1] < values[0] else "稳定"
        
        return f"""
### 🧪 泥浆参数追踪：{well_id} - {label}

**趋势分析**: {trend} ({values[0]:.2f} → {values[-1]:.2f})

{df_to_markdown(df)}

**建议**：
- 密度变化可能反映地层压力变化或井控需要
- 粘度异常可能影响携砂能力
- pH值变化需关注泥浆化学性能
"""
    
    finally:
        session.close()


# ==========================================
# Part 5: 启动服务
# ==========================================

if __name__ == "__main__":
    # 设置 Windows 控制台 UTF-8 编码
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("🚀 油田钻井智能查询 MCP Server 已启动")
    print("=" * 60)
    print("\n📌 系统功能：")
    print("  ✓ 鉴权管理（基于角色的权限控制）")
    print("  ✓ 单井数据查询（概览、日报、NPT分析）")
    print("  ✓ 多井对比分析（速度、事故、绩效）")
    print("  ✓ 周报/月报生成（单井和区块级别）")
    print("  ✓ 泥浆参数追踪（密度、粘度、pH）")
    
    # 显示当前权限模式
    if DEV_MODE:
        print("\n🔓 权限模式：开发模式 (所有用户拥有 admin 权限)")
        print("   提示：生产环境请设置环境变量 DEV_MODE=false")
    else:
        print("\n🔒 权限模式：生产模式 (严格权限控制)")
        print("\n📌 权限角色：")
        print("  • admin   - 全部权限")
        print("  • engineer - Block-A的部分井")
        print("  • viewer  - ZT-102只读")
        print("  • default - 受限访问")
    print("\n📌 使用方式：")
    print("  1. 配置到 Claude Desktop 的 MCP Server")
    print("  2. 在对话中调用工具，例如：")
    print("     - '查询ZT-102井的概况'")
    print("     - '对比ZT-102和ZT-105谁钻得快'")
    print("     - '生成Block-A区块的11月报告'")
    print("\n⏳ 等待客户端连接...\n")
    
    # 运行MCP服务（默认stdio模式）
    mcp.run()
