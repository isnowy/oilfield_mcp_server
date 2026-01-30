"""
油田钻井数据MCP Server - HTTP/SSE版本
支持动态用户权限控制

特性：
- 使用FastAPI实现HTTP端点
- 支持SSE (Server-Sent Events) 传输
- 从HTTP headers动态获取用户角色
- 每个请求独立验证权限
- 单个MCP Server实例服务所有用户
- 完整的井数据查询、多井对比、报告生成功能
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

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==========================================
# 日志配置
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OilfieldMCP_HTTP")

# 开发模式配置：设置 DEV_MODE=true 可跳过权限检查（方便测试）
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ["true", "1", "yes"]

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

def filter_wells_by_permission(wells: List[Any], user_role: str, user_id: str, user_email: str) -> List[Any]:
    """
    根据用户角色过滤井数据（基于角色权限）
    
    权限规则：
    - ADMIN: 可以查看所有井
    - ENGINEER/VIEWER: 根据USER_PERMISSIONS配置的井列表
    - USER/GUEST: 只能查看公共数据（owner_user_id为None）
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
        # 过滤出权限列表中的井 + 公共数据
        filtered = [
            well for well in wells
            if well.id in allowed_wells or well.owner_user_id is None
        ]
        logger.info(f"🔒 {role_upper}用户 {user_email} 访问 {len(filtered)}/{len(wells)} 口井（权限配置+公共数据）")
        return filtered
    else:
        # 普通USER或GUEST：只能看公共数据
        filtered = [well for well in wells if well.owner_user_id is None]
        logger.info(f"🔒 {role_upper}用户 {user_email} 访问 {len(filtered)}/{len(wells)} 口井（仅公共数据）")
        return filtered

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
# 数据库模型定义
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
    status = Column(String(20))
    well_type = Column(String(30))
    team = Column(String(50))
    rig = Column(String(50))
    
    # 数据权限字段
    owner_user_id = Column(String(100), nullable=True)  # 数据所有者用户ID
    owner_email = Column(String(200), nullable=True)     # 数据所有者邮箱
    
    reports = relationship("DailyReport", back_populates="well")
    casings = relationship("CasingProgram", back_populates="well")

class DailyReport(Base):
    """钻井日报表"""
    __tablename__ = 'daily_reports'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    report_date = Column(Date)
    report_no = Column(Integer)
    
    current_depth = Column(Float)
    progress = Column(Float)
    
    mud_density = Column(Float)
    mud_viscosity = Column(Float)
    mud_ph = Column(Float)
    
    operation_summary = Column(Text)
    next_plan = Column(Text)
    
    avg_rop = Column(Float)
    bit_number = Column(Integer)
    
    npt_events = relationship("NPTEvent", back_populates="report")
    well = relationship("Well", back_populates="reports")

class NPTEvent(Base):
    """非生产时间/复杂事故表"""
    __tablename__ = 'npt_events'
    
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('daily_reports.id'))
    category = Column(String(50))
    duration = Column(Float)
    severity = Column(String(20))
    description = Column(Text)
    
    report = relationship("DailyReport", back_populates="npt_events")

class CasingProgram(Base):
    """套管程序/井身结构表"""
    __tablename__ = 'casing_programs'
    
    id = Column(Integer, primary_key=True)
    well_id = Column(String(50), ForeignKey('wells.id'))
    run_number = Column(Integer)
    run_date = Column(Date)
    size = Column(Float)
    shoe_depth = Column(Float)
    cement_top = Column(Float)
    
    well = relationship("Well", back_populates="casings")

# 数据库初始化
engine = create_engine('sqlite:///:memory:', echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def seed_mock_data():
    """注入模拟数据"""
    session = Session()
    
    try:
        # 检查数据是否已存在
        existing_wells_count = session.query(Well).count()
        if existing_wells_count > 0:
            logger.info(f"✅ 数据库已有 {existing_wells_count} 口井，跳过数据初始化")
            session.close()
            return
        
        logger.info("📝 开始初始化模拟数据...")
        
        wells = [
            # 私有数据井（user1）
            Well(id="ZT-102", name="中塔-102", block="Block-A", target_depth=4500, 
                 spud_date=date(2023, 10, 1), status="Active", well_type="Horizontal",
                 team="Team-701", rig="Rig-50",
                 owner_user_id="697c0cbebb4a93216518c3f9", owner_email="user1@test.com"),
            
            # 私有数据井（user2）
            Well(id="ZT-105", name="中塔-105", block="Block-A", target_depth=4200,
                 spud_date=date(2023, 10, 5), status="Active", well_type="Vertical",
                 team="Team-702", rig="Rig-51",
                 owner_user_id="697c0cbebb4a93216518c3fd", owner_email="user2@test.com"),
            
            # 私有数据井（user1）
            Well(id="XY-009", name="新疆-009", block="Block-B", target_depth=5500,
                 spud_date=date(2023, 9, 15), status="Active", well_type="Horizontal",
                 team="Team-808", rig="Rig-88",
                 owner_user_id="697c0cbebb4a93216518c3f9", owner_email="user1@test.com"),
            
            # ===== 以下是公共数据井 =====
            Well(id="ZT-108", name="中塔-108", block="Block-A", target_depth=5000,
                 spud_date=date(2023, 9, 20), status="Completed", well_type="Directional",
                 team="Team-701", rig="Rig-50",
                 owner_user_id=None, owner_email=None),
            
            Well(id="ZT-201", name="中塔-201", block="Block-A", target_depth=4800,
                 spud_date=date(2023, 11, 10), status="Active", well_type="Horizontal",
                 team="Team-703", rig="Rig-52",
                 owner_user_id=None, owner_email=None),
            
            Well(id="XY-015", name="新疆-015", block="Block-B", target_depth=5200,
                 spud_date=date(2023, 10, 20), status="Active", well_type="Vertical",
                 team="Team-809", rig="Rig-89",
                 owner_user_id=None, owner_email=None),
            
            Well(id="DG-088", name="东港-088", block="Block-C", target_depth=3800,
                 spud_date=date(2023, 11, 1), status="Active", well_type="Directional",
                 team="Team-901", rig="Rig-91",
                 owner_user_id=None, owner_email=None),
            
            Well(id="DG-092", name="东港-092", block="Block-C", target_depth=4100,
                 spud_date=date(2023, 10, 15), status="Completed", well_type="Horizontal",
                 team="Team-902", rig="Rig-92",
                 owner_user_id=None, owner_email=None),
            
            Well(id="HB-156", name="华北-156", block="Block-D", target_depth=4600,
                 spud_date=date(2023, 9, 25), status="Active", well_type="Horizontal",
                 team="Team-1001", rig="Rig-101",
                 owner_user_id=None, owner_email=None),
        ]
        session.add_all(wells)
        
        base_date = date(2023, 11, 1)
        
        # ZT-102: 正常钻进 + 一次井漏事故（私有数据）
        for i in range(10):
            report_date = base_date + timedelta(days=i)
            is_npt_day = (i == 5)
            
            progress = 50 if is_npt_day else 150
            current_depth = 3000 + sum([50 if j == 5 else 150 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="ZT-102",
                report_date=report_date,
                report_no=25 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.25 if i < 5 else 1.28,
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
        
        # ZT-105: 快速钻井（私有数据）
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
        
        # ZT-201: 公共数据井 - 水平井，有一次卡钻事故
        for i in range(12):
            report_date = base_date + timedelta(days=i)
            is_npt_day = (i == 7)
            
            progress = 120 if not is_npt_day else 40
            current_depth = 2800 + sum([120 if j != 7 else 40 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="ZT-201",
                report_date=report_date,
                report_no=15 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.26,
                mud_viscosity=58.0 + i * 0.3,
                mud_ph=9.6,
                avg_rop=20.0 if not is_npt_day else 6.5,
                bit_number=2 if i < 8 else 3,
                operation_summary=f"钻进12.25寸井段，{'遭遇卡钻，倒划眼处理' if is_npt_day else '正常钻进'}。当前井深{current_depth}米。",
                next_plan="继续钻进至设计井深" if not is_npt_day else "加强泥浆性能，防止卡钻"
            )
            
            if is_npt_day:
                npt = NPTEvent(
                    category="Stuck Pipe",
                    duration=18.0,
                    severity="High",
                    description="井深3640米处发生卡钻，上提悬重120吨，倒划眼18小时解卡成功。"
                )
                r.npt_events.append(npt)
            
            session.add(r)
        
        # XY-015: 公共数据井 - 直井，钻进平稳
        for i in range(15):
            report_date = base_date + timedelta(days=i)
            
            progress = 160 + i * 2
            current_depth = 2500 + sum([160 + j * 2 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="XY-015",
                report_date=report_date,
                report_no=10 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.20,
                mud_viscosity=50.0,
                mud_ph=9.8,
                avg_rop=28.0 + i * 0.5,
                bit_number=1 if i < 10 else 2,
                operation_summary=f"直井钻进，地层稳定，钻速良好。当前井深{current_depth}米。",
                next_plan="保持参数，继续钻进"
            )
            session.add(r)
        
        # DG-088: 公共数据井 - 定向井，有井壁垮塌事故
        for i in range(10):
            report_date = base_date + timedelta(days=i)
            is_npt_day = (i == 4)
            
            progress = 80 if not is_npt_day else 20
            current_depth = 2200 + sum([80 if j != 4 else 20 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="DG-088",
                report_date=report_date,
                report_no=20 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.30 if i < 5 else 1.35,
                mud_viscosity=60.0,
                mud_ph=9.4,
                avg_rop=18.0 if not is_npt_day else 4.0,
                bit_number=2,
                operation_summary=f"定向井段钻进，{'井壁不稳定，发生垮塌' if is_npt_day else '控制井斜角度'}。当前井深{current_depth}米。",
                next_plan="继续定向钻进" if not is_npt_day else "提高泥浆密度，稳定井壁"
            )
            
            if is_npt_day:
                npt = NPTEvent(
                    category="Hole Instability",
                    duration=14.5,
                    severity="Medium",
                    description="井深2520米处井壁垮塌，循环清洗14.5小时，提高泥浆密度至1.35。"
                )
                r.npt_events.append(npt)
            
            session.add(r)
        
        # DG-092: 公共数据井 - 已完井，完整钻井周期
        for i in range(20):
            report_date = base_date - timedelta(days=20-i)
            
            progress = 180 if i < 18 else 100
            current_depth = 1800 + sum([180 if j < 18 else 100 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="DG-092",
                report_date=report_date,
                report_no=1 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.24,
                mud_viscosity=54.0,
                mud_ph=9.7,
                avg_rop=32.0 if i < 18 else 20.0,
                bit_number=1 if i < 12 else 2,
                operation_summary=f"{'完井作业' if i >= 18 else '正常钻进'}。当前井深{current_depth}米。",
                next_plan="完井测试" if i >= 18 else "继续钻进"
            )
            session.add(r)
        
        # HB-156: 公共数据井 - 有多次小型NPT事件
        for i in range(14):
            report_date = base_date + timedelta(days=i)
            is_npt_day = i in [3, 8, 11]
            
            progress = 140 if not is_npt_day else 90
            current_depth = 2600 + sum([140 if j not in [3, 8, 11] else 90 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="HB-156",
                report_date=report_date,
                report_no=5 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.28,
                mud_viscosity=56.0,
                mud_ph=9.5,
                avg_rop=24.0 if not is_npt_day else 15.0,
                bit_number=1 if i < 7 else 2,
                operation_summary=f"水平井段钻进，{'设备维护' if is_npt_day else '作业正常'}。当前井深{current_depth}米。",
                next_plan="继续钻进"
            )
            
            if is_npt_day:
                if i == 3:
                    npt = NPTEvent(
                        category="Equipment Maintenance",
                        duration=6.0,
                        severity="Low",
                        description="钻井泵维护保养，更换缸套。"
                    )
                elif i == 8:
                    npt = NPTEvent(
                        category="Weather Delay",
                        duration=8.5,
                        severity="Low",
                        description="大风天气，暂停作业等待。"
                    )
                else:  # i == 11
                    npt = NPTEvent(
                        category="Equipment Maintenance",
                        duration=5.5,
                        severity="Low",
                        description="顶驱系统故障检修。"
                    )
                r.npt_events.append(npt)
            
            session.add(r)
        
        # 添加套管程序数据
        casings = [
            # ZT-102
            CasingProgram(well_id="ZT-102", run_number=1, run_date=date(2023, 10, 3), 
                         size=17.5, shoe_depth=800, cement_top=0),
            CasingProgram(well_id="ZT-102", run_number=2, run_date=date(2023, 10, 15), 
                         size=12.25, shoe_depth=2500, cement_top=1800),
            
            # ZT-201 (公共数据)
            CasingProgram(well_id="ZT-201", run_number=1, run_date=date(2023, 11, 12), 
                         size=17.5, shoe_depth=750, cement_top=0),
            CasingProgram(well_id="ZT-201", run_number=2, run_date=date(2023, 11, 20), 
                         size=12.25, shoe_depth=2300, cement_top=1700),
            
            # XY-015 (公共数据)
            CasingProgram(well_id="XY-015", run_number=1, run_date=date(2023, 10, 22), 
                         size=20.0, shoe_depth=900, cement_top=0),
            CasingProgram(well_id="XY-015", run_number=2, run_date=date(2023, 11, 2), 
                         size=13.375, shoe_depth=2800, cement_top=2000),
            
            # DG-088 (公共数据)
            CasingProgram(well_id="DG-088", run_number=1, run_date=date(2023, 11, 3), 
                         size=17.5, shoe_depth=700, cement_top=0),
            CasingProgram(well_id="DG-088", run_number=2, run_date=date(2023, 11, 10), 
                         size=12.25, shoe_depth=2000, cement_top=1500),
            
            # DG-092 (公共数据，已完井)
            CasingProgram(well_id="DG-092", run_number=1, run_date=date(2023, 10, 16), 
                         size=20.0, shoe_depth=850, cement_top=0),
            CasingProgram(well_id="DG-092", run_number=2, run_date=date(2023, 10, 25), 
                         size=13.375, shoe_depth=2500, cement_top=1800),
            CasingProgram(well_id="DG-092", run_number=3, run_date=date(2023, 10, 31), 
                         size=9.625, shoe_depth=4100, cement_top=3200),
            
            # HB-156 (公共数据)
            CasingProgram(well_id="HB-156", run_number=1, run_date=date(2023, 9, 27), 
                         size=17.5, shoe_depth=780, cement_top=0),
            CasingProgram(well_id="HB-156", run_number=2, run_date=date(2023, 10, 8), 
                         size=12.25, shoe_depth=2400, cement_top=1750),
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

seed_mock_data()

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
    }
    
    for pattern, normalized in mappings.items():
        if pattern in well_id:
            return normalized
    
    return well_id.upper()

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
mcp_server = Server("oilfield-drilling")

# 创建 SSE Transport
sse_transport = SseServerTransport("/sse")

# FastAPI应用
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 油田钻井数据MCP Server (HTTP/SSE) 启动中...")
    logger.info(f"📍 监听地址: http://0.0.0.0:8080")
    logger.info(f"🔒 权限模式: {'开发模式(跳过权限)' if DEV_MODE else '生产模式(严格权限)'}")
    # 初始化模拟数据
    seed_mock_data()
    logger.info("✅ 模拟数据已加载")
    yield
    logger.info("👋 MCP Server 关闭")

app = FastAPI(
    title="油田钻井数据MCP Server",
    description="基于HTTP/SSE的MCP服务器，支持动态用户权限控制",
    version="2.0.0",
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

# ============ SSE Endpoint ============

@app.get("/sse")
async def handle_sse_get(request: Request):
    """SSE GET endpoint - 建立SSE连接"""
    logger.info("🌊 SSE GET请求 - 建立连接")
    
    try:
        # 使用connect_sse建立SSE连接
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
                            "name": "oilfield-drilling",
                            "version": "2.0.0"
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
                # 返回工具列表（手动定义）
                tools_list = [
                    {
                        "name": "search_wells",
                        "description": "搜索油井信息，支持按关键字、区块或状态搜索",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "keyword": {"type": "string", "description": "搜索关键字（井号、区块等）"},
                                "status": {"type": "string", "enum": ["All", "Drilling", "Completed", "Suspended"], "default": "All"}
                            },
                            "required": []
                        }
                    },
                    {
                        "name": "get_well_summary",
                        "description": "获取单井概况（位置、钻井参数、当前状态等）",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "well_id": {"type": "string", "description": "井号"}
                            },
                            "required": ["well_id"]
                        }
                    },
                    {
                        "name": "get_daily_report",
                        "description": "获取指定日期的钻井日报。⚠️ 重要规则：只有当用户明确说出具体日期时才填写date参数（如'2023-11-10'、'昨天'），其他情况一律留空，系统会自动列出可用日期供用户选择。绝不要猜测或多次尝试！",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "well_id": {"type": "string", "description": "井号"},
                                "date": {"type": "string", "description": "日期(YYYY-MM-DD)。只有用户明确说出具体日期时才填写，否则留空。"}
                            },
                            "required": ["well_id"]
                        }
                    },
                    {
                        "name": "compare_wells",
                        "description": "多井对比分析，可对比钻速或NPT事件",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "well_ids": {"type": "array", "items": {"type": "string"}, "description": "井号列表"},
                                "metric": {"type": "string", "enum": ["speed", "npt"], "default": "speed"}
                            },
                            "required": ["well_ids"]
                        }
                    },
                    {
                        "name": "generate_weekly_report",
                        "description": "生成指定时间段的周报或阶段报告",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "well_id": {"type": "string", "description": "井号"},
                                "start_date": {"type": "string", "description": "开始日期(YYYY-MM-DD)"},
                                "end_date": {"type": "string", "description": "结束日期(YYYY-MM-DD)"}
                            },
                            "required": ["well_id", "start_date", "end_date"]
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
                            keyword=tool_args.get('keyword', ''),
                            status=tool_args.get('status', 'All'),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "get_well_summary":
                        result_text = get_well_summary(
                            well_id=tool_args.get('well_id', ''),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "get_daily_report":
                        result_text = get_daily_report(
                            well_id=tool_args.get('well_id', ''),
                            date_str=tool_args.get('date', ''),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "compare_wells":
                        result_text = compare_wells(
                            well_ids=tool_args.get('well_ids', []),
                            metric=tool_args.get('metric', 'speed'),
                            user_role=user_role,
                            user_id=user_id,
                            user_email=user_email
                        )
                    elif tool_name == "generate_weekly_report":
                        result_text = generate_weekly_report(
                            well_id=tool_args.get('well_id', ''),
                            start_date=tool_args.get('start_date', ''),
                            end_date=tool_args.get('end_date', ''),
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
            # 捕获响应数据
            response_data = {}
            response_status = 200
            
            # 使用ASGI接口处理POST消息
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
            
            # 调用handle_post_message with ASGI parameters
            await sse_transport.handle_post_message(
                request.scope,
                receive,
                send
            )
            
            # 返回捕获的响应
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

# ============ Pydantic模型 ============

class ToolCallRequest(BaseModel):
    """MCP工具调用请求"""
    name: str
    arguments: Dict[str, Any] = {}

class ToolCallResponse(BaseModel):
    """MCP工具调用响应"""
    content: List[Dict[str, Any]]
    isError: bool = False

class UserContext(BaseModel):
    """用户上下文"""
    role: str = "GUEST"
    email: Optional[str] = None
    user_id: Optional[str] = None

# ============ 用户上下文提取 ============

def extract_user_context(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> UserContext:
    """从HTTP headers提取用户上下文"""
    role_str = (x_user_role or "GUEST").upper()
    
    logger.info(f"📥 用户上下文 - Role: {role_str}, Email: {x_user_email or 'N/A'}, ID: {x_user_id or 'N/A'}")
    
    return UserContext(
        role=role_str,
        email=x_user_email,
        user_id=x_user_id
    )

# ==========================================
# MCP Server Handlers
# ==========================================

@mcp_server.list_tools()
async def handle_list_tools():
    '''列出所有可用的工具'''
    return [
        Tool(
            name="search_wells",
            description="搜索油井（支持井号、井名、区块）",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "status": {"type": "string", "enum": ["Active", "Completed", "Suspended", "All"], "default": "All"}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="get_well_summary",
            description="获取单井概况，包括基本信息、当前状态和最新进展",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "井号，如ZT-102或中102"}
                },
                "required": ["well_id"]
            }
        ),
        Tool(
            name="get_daily_report",
            description="获取指定日期的钻井日报。如用户未指定日期，工具会列出可用日期供选择，避免盲目查询",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "井号"},
                    "date": {"type": "string", "description": "日期(YYYY-MM-DD)，如用户未明确指定则留空"}
                },
                "required": ["well_id"]
            }
        ),
        Tool(
            name="compare_wells",
            description="多井对比分析，可对比钻速或NPT事件",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_ids": {"type": "array", "items": {"type": "string"}, "description": "井号列表"},
                    "metric": {"type": "string", "enum": ["speed", "npt"], "default": "speed"}
                },
                "required": ["well_ids"]
            }
        ),
        Tool(
            name="generate_weekly_report",
            description="生成指定时间段的周报或阶段报告",
            inputSchema={
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "井号"},
                    "start_date": {"type": "string", "description": "开始日期(YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "结束日期(YYYY-MM-DD)"}
                },
                "required": ["well_id", "start_date", "end_date"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    '''处理工具调用'''
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
                keyword=arguments.get('keyword', ''),
                status=arguments.get('status', 'All'),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_well_summary":
            result = get_well_summary(
                well_id=arguments.get('well_id', ''),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "get_daily_report":
            result = get_daily_report(
                well_id=arguments.get('well_id', ''),
                date_str=arguments.get('date', ''),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "compare_wells":
            result = compare_wells(
                well_ids=arguments.get('well_ids', []),
                metric=arguments.get('metric', 'speed'),
                user_role=user_role,
                user_id=user_id,
                user_email=user_email
            )
        elif name == "generate_weekly_report":
            result = generate_weekly_report(
                well_id=arguments.get('well_id', ''),
                start_date=arguments.get('start_date', ''),
                end_date=arguments.get('end_date', ''),
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
def search_wells(keyword: str, status: str = "All", user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """搜索油井"""
    session = Session()
    try:
        query = session.query(Well).filter(
            (Well.name.contains(keyword)) | 
            (Well.block.contains(keyword)) |
            (Well.id.contains(keyword))
        )
        
        if status != "All":
            query = query.filter(Well.status == status)
        
        all_wells = query.all()
        
        # 使用新的权限过滤函数
        wells = filter_wells_by_permission(all_wells, user_role, user_id, user_email)
        
        if not wells:
            return f"未找到匹配关键词 '{keyword}' 的井（状态：{status}）。"
        
        data = [{
            "井号": w.id,
            "井名": w.name,
            "区块": w.block,
            "状态": w.status,
            "井型": w.well_type,
            "设计井深(m)": w.target_depth,
            "钻井队": w.team,
            "数据所有者": w.owner_email or "公共数据"
        } for w in wells]
        
        return f"### 🔍 搜索结果（共 {len(wells)} 口井）\n\n{df_to_markdown(pd.DataFrame(data))}"
    
    finally:
        session.close()

@AuditLog.trace("get_well_summary")
def get_well_summary(well_id: str, user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """获取单井概况"""
    well_id = normalize_well_id(well_id)
    
    session = Session()
    try:
        well = session.query(Well).filter_by(id=well_id).first()
        
        if not well:
            return f"❌ 未找到井号: {well_id}"
        
        # 权限检查：使用filter函数
        filtered = filter_wells_by_permission([well], user_role, user_id, user_email)
        if not filtered:
            return f"🚫 权限拒绝：无权访问井号 {well_id}。"
        
        reports = session.query(DailyReport).filter_by(well_id=well_id)\
            .order_by(DailyReport.report_date.desc()).limit(1).first()
        
        current_depth = reports.current_depth if reports else 0
        latest_date = reports.report_date if reports else "无数据"
        
        casings = session.query(CasingProgram).filter_by(well_id=well_id)\
            .order_by(CasingProgram.run_number).all()
        casing_info = "\n".join([
            f"- 第{c.run_number}次: {c.size}英寸，鞋深{c.shoe_depth}米"
            for c in casings
        ]) if casings else "暂无套管数据"
        
        npt_count = session.query(NPTEvent)\
            .join(DailyReport)\
            .filter(DailyReport.well_id == well_id).count()
        
        return f"""
### 🏭 井信息概览：{well.name} ({well.id})

#### 基本信息
- **区块**: {well.block}
- **井型**: {well.well_type}
- **状态**: {well.status}
- **开钻日期**: {well.spud_date}
- **设计井深**: {well.target_depth} m
- **当前井深**: {current_depth} m
- **钻井队**: {well.team}
- **钻机**: {well.rig}

#### 最新动态
- **最新数据**: {latest_date}
- **NPT事件数**: {npt_count} 次

#### 套管程序
{casing_info}
"""
    
    finally:
        session.close()

# 添加查询缓存避免重复调用
_daily_report_cache_http = {}
_cache_ttl_http = 60  # 缓存有效期60秒

@AuditLog.trace("get_daily_report")
def get_daily_report(well_id: str, date_str: str = "", user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """获取日报"""
    well_id = normalize_well_id(well_id)
    
    # 扩大空值判断：包括空字符串、None、或者模糊表达（如"最新"、"今天"）
    # 如果用户说的是模糊词汇，也应该先展示可用日期
    ambiguous_keywords = ["最新", "latest", "recent", "当前", "current", "now"]
    is_empty_or_ambiguous = (
        not date_str or 
        date_str.strip() == "" or
        date_str.lower().strip() in ambiguous_keywords
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
    
    # 检查缓存
    cache_key = f"{well_id}_{date_str}_{user_role}"
    if cache_key in _daily_report_cache_http:
        cache_time, cached_result = _daily_report_cache_http[cache_key]
        if (datetime.now() - cache_time).seconds < _cache_ttl_http:
            logger.info(f"✅ [HTTP] 使用缓存数据: {cache_key}")
            return cached_result
    
    session = Session()
    try:
        well = session.query(Well).filter_by(id=well_id).first()
        if not well:
            return f"❌ 未找到井号: {well_id}"
        
        # 权限检查
        filtered = filter_wells_by_permission([well], user_role, user_id, user_email)
        if not filtered:
            return f"🚫 权限拒绝：无权访问井号 {well_id}。"
        
        # 解析日期
        try:
            report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return f"❌ 日期格式错误：{date_str}"
        
        # 查询日报
        report = session.query(DailyReport)\
            .filter_by(well_id=well_id, report_date=report_date)\
            .first()
        
        if not report:
            return f"未找到 {well_id} 在 {date_str} 的日报。"
        
        npt_summary = "无"
        if report.npt_events:
            npt_list = []
            for npt in report.npt_events:
                npt_list.append(f"- {npt.category} ({npt.duration}小时，{npt.severity}): {npt.description}")
            npt_summary = "\n".join(npt_list)
        
        result = f"""
### 📋 钻井日报：{well_id} - {date_str} (报告编号：{report.report_no})

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
        _daily_report_cache_http[cache_key] = (datetime.now(), result)
        return result
    
    finally:
        session.close()

@AuditLog.trace("compare_wells")
def compare_wells(well_ids: List[str], metric: str = "speed", user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """多井对比分析"""
    well_ids = [normalize_well_id(w) for w in well_ids]
    
    session = Session()
    try:
        # 查询所有井
        all_wells = session.query(Well).filter(Well.id.in_(well_ids)).all()
        
        # 权限过滤
        wells = filter_wells_by_permission(all_wells, user_role, user_id, user_email)
        
        if not wells:
            return f"🚫 权限拒绝：无权访问这些井。"
        
        # 检查是否有井被过滤掉
        filtered_ids = [w.id for w in wells]
        blocked_ids = [wid for wid in well_ids if wid not in filtered_ids]
        if blocked_ids:
            logger.warning(f"部分井被权限过滤: {blocked_ids}")
        results = []
        
        for well_id in well_ids:
            well = session.query(Well).filter_by(id=well_id).first()
            if not well:
                continue
            
            reports = session.query(DailyReport).filter_by(well_id=well_id).all()
            
            if metric == "speed":
                avg_rop = sum([r.avg_rop for r in reports]) / len(reports) if reports else 0
                total_progress = sum([r.progress for r in reports])
                results.append({
                    "井号": well_id,
                    "平均机械钻速(m/h)": round(avg_rop, 2),
                    "累计进尺(m)": round(total_progress, 1),
                    "天数": len(reports)
                })
            elif metric == "npt":
                npt_count = session.query(NPTEvent)\
                    .join(DailyReport)\
                    .filter(DailyReport.well_id == well_id).count()
                results.append({
                    "井号": well_id,
                    "NPT事件数": npt_count
                })
        
        if not results:
            return "无对比数据"
        
        df = pd.DataFrame(results)
        
        if metric == "speed":
            df = df.sort_values("平均机械钻速(m/h)", ascending=False)
            winner = df.iloc[0]["井号"]
            return f"""
### 🏆 多井对比分析（机械钻速）

{df_to_markdown(df)}

**结论**: {winner} 钻速最快
"""
        else:
            df = df.sort_values("NPT事件数")
            winner = df.iloc[0]["井号"]
            return f"""
### 🏆 多井对比分析（NPT事件）

{df_to_markdown(df)}

**结论**: {winner} 最安全
"""
    
    finally:
        session.close()

@AuditLog.trace("generate_weekly_report")
def generate_weekly_report(well_id: str, start_date: str, end_date: str, user_role: str = "GUEST", user_id: str = "unknown", user_email: str = "unknown") -> str:
    """生成周报"""
    well_id = normalize_well_id(well_id)
    
    session = Session()
    try:
        well = session.query(Well).filter_by(id=well_id).first()
        if not well:
            return f"❌ 未找到井号: {well_id}"
        
        # 权限检查
        filtered = filter_wells_by_permission([well], user_role, user_id, user_email)
        if not filtered:
            return f"🚫 权限拒绝：无权访问井号 {well_id}。"
        
        # 解析日期
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return "❌ 日期格式错误"
        
        # 查询报告
        reports = session.query(DailyReport)\
            .filter(DailyReport.well_id == well_id)\
            .filter(DailyReport.report_date >= start)\
            .filter(DailyReport.report_date <= end)\
            .all()
        
        if not reports:
            return f"时间段 {start_date} 至 {end_date} 无数据"
        
        total_progress = sum([r.progress for r in reports])
        avg_rop = sum([r.avg_rop for r in reports]) / len(reports)
        start_depth = reports[0].current_depth - reports[0].progress
        end_depth = reports[-1].current_depth
        
        npt_events = []
        for r in reports:
            if r.npt_events:
                for npt in r.npt_events:
                    npt_events.append({
                        "日期": r.report_date,
                        "类别": npt.category,
                        "损失时间(h)": npt.duration
                    })
        
        npt_section = "无" if not npt_events else df_to_markdown(pd.DataFrame(npt_events))
        
        return f"""
### 📊 周报：{well.name} ({well_id})
**时间段**: {start_date} ~ {end_date}

#### 进度汇总
- **钻进天数**: {len(reports)} 天
- **累计进尺**: {total_progress:.1f} m
- **日均进尺**: {total_progress / len(reports):.1f} m
- **平均机械钻速**: {avg_rop:.2f} m/h
- **起始井深**: {start_depth:.1f} m
- **结束井深**: {end_depth:.1f} m

#### NPT事件
{npt_section}

#### 综合评价
- 钻井效率: {'优秀' if avg_rop > 25 else '良好' if avg_rop > 20 else '一般'}
- 安全性: {'优秀' if len(npt_events) == 0 else '需改进'}
"""
    
    finally:
        session.close()

# ============ HTTP端点 ============

@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "name": "油田钻井数据MCP Server",
        "version": "2.0.0",
        "transport": "HTTP/SSE",
        "status": "running",
        "dev_mode": DEV_MODE
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        session = Session()
        wells_count = session.query(Well).count()
        reports_count = session.query(DailyReport).count()
        session.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "wells": wells_count,
            "reports": reports_count
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.get("/mcp/tools")
async def list_tools_http():
    """列出所有可用工具"""
    tools = [
        {
            "name": "search_wells",
            "description": "搜索油井（支持井号、井名、区块）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "status": {"type": "string", "enum": ["Active", "Completed", "Suspended", "All"], "default": "All"},
                },
                "required": ["keyword"]
            }
        },
        {
            "name": "get_well_summary",
            "description": "获取单井概况",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "井号，如ZT-102或中102"},
                },
                "required": ["well_id"]
            }
        },
        {
            "name": "get_daily_report",
            "description": "获取指定日期的钻井日报。⚠️ 重要：只有当用户明确说出具体日期时才填写date参数，其他情况一律留空，系统会列出可用日期。绝不要猜测或多次尝试！",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "井号"},
                    "date": {"type": "string", "description": "日期(YYYY-MM-DD)。只有用户明确说出具体日期时才填写，否则留空"},
                },
                "required": ["well_id"]
            }
        },
        {
            "name": "compare_wells",
            "description": "多井对比分析",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "well_ids": {"type": "array", "items": {"type": "string"}, "description": "井号列表"},
                    "metric": {"type": "string", "enum": ["speed", "npt"], "default": "speed"},
                },
                "required": ["well_ids"]
            }
        },
        {
            "name": "generate_weekly_report",
            "description": "生成周报",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "井号"},
                    "start_date": {"type": "string", "description": "开始日期(YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "结束日期(YYYY-MM-DD)"},
                },
                "required": ["well_id", "start_date", "end_date"]
            }
        },
    ]
    
    return {"tools": tools}

@app.post("/mcp/call-tool")
async def call_tool(
    request: ToolCallRequest,
    user_context: UserContext = Depends(extract_user_context)
):
    """MCP工具调用端点（HTTP方式）"""
    tool_name = request.name
    arguments = request.arguments
    
    logger.info(f"🔧 HTTP工具调用: {tool_name} | 用户: {user_context.role}")
    logger.debug(f"📝 参数: {json.dumps(arguments, ensure_ascii=False)}")
    
    try:
        # 执行工具
        if tool_name == "search_wells":
            result = search_wells(
                keyword=arguments.get('keyword', ''),
                status=arguments.get('status', 'All'),
                user_role=user_context.role,
                user_id=user_context.user_id,
                user_email=user_context.email
            )
        elif tool_name == "get_well_summary":
            result = get_well_summary(
                well_id=arguments.get('well_id', ''),
                user_role=user_context.role,
                user_id=user_context.user_id,
                user_email=user_context.email
            )
        elif tool_name == "get_daily_report":
            result = get_daily_report(
                well_id=arguments.get('well_id', ''),
                date_str=arguments.get('date', ''),
                user_role=user_context.role,
                user_id=user_context.user_id,
                user_email=user_context.email
            )
        elif tool_name == "compare_wells":
            result = compare_wells(
                well_ids=arguments.get('well_ids', []),
                metric=arguments.get('metric', 'speed'),
                user_role=user_context.role,
                user_id=user_context.user_id,
                user_email=user_context.email
            )
        elif tool_name == "generate_weekly_report":
            result = generate_weekly_report(
                well_id=arguments.get('well_id', ''),
                start_date=arguments.get('start_date', ''),
                end_date=arguments.get('end_date', ''),
                user_role=user_context.role,
                user_id=user_context.user_id,
                user_email=user_context.email
            )
        else:
            raise HTTPException(status_code=404, detail=f"工具不存在: {tool_name}")
        
        logger.info(f"✅ 工具执行成功: {tool_name}")
        
        return ToolCallResponse(
            content=[{
                "type": "text",
                "text": result
            }],
            isError=False
        )
    
    except Exception as e:
        logger.error(f"❌ 工具执行失败: {tool_name} - {str(e)}")
        return ToolCallResponse(
            content=[{
                "type": "text",
                "text": f"⚠️ 执行错误: {str(e)}"
            }],
            isError=True
        )

# ============ 主函数 ============

if __name__ == "__main__":
    # 设置 Windows 控制台 UTF-8 编码
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("🚀 油田钻井智能查询 MCP Server (HTTP/SSE版本)")
    print("=" * 60)
    print("\n📌 系统功能：")
    print("  ✓ 鉴权管理（基于角色的权限控制）")
    print("  ✓ 单井数据查询（概览、日报、NPT分析）")
    print("  ✓ 多井对比分析（速度、事故、绩效）")
    print("  ✓ 周报/月报生成（单井和区块级别）")
    print("  ✓ 泥浆参数追踪（密度、粘度、pH）")
    
    # 显示当前权限模式
    if DEV_MODE:
        print("\n🔓 权限模式：开发模式 (跳过权限检查)")
        print("   提示：生产环境请设置环境变量 DEV_MODE=false")
    else:
        print("\n🔒 权限模式：生产模式 (基于角色的权限控制)")
        print("\n📌 权限角色说明：")
        print("  • ADMIN    - 管理员，可访问所有井")
        print("  • ENGINEER - 工程师，可访问Block-A的部分井 + 公共数据")
        print("  • VIEWER   - 查看者，可访问ZT-102 + 公共数据")
        print("  • USER     - 普通用户，仅可访问公共数据")
        print("  • GUEST    - 访客，仅可访问公共数据")
    
    print("\n📌 HTTP端点：")
    print("  GET  /         - 服务状态")
    print("  GET  /health   - 健康检查")
    print("  GET  /mcp/tools - 列出所有工具")
    print("  POST /mcp/call-tool - 调用工具")
    
    print("\n📌 使用方式：")
    print("  1. 配置到 LibreChat 的 MCP Server")
    print("  2. 在HTTP headers中传递用户角色：")
    print("     - X-User-Role: ADMIN|ENGINEER|VIEWER|GUEST")
    print("     - X-User-Email: user@example.com")
    print("     - X-User-ID: user123")
    print("\n🌐 访问地址: http://0.0.0.0:8080")
    print("\n⏳ 服务器启动中...\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
