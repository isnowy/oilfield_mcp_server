"""
工具函数模块
提供通用的数据处理和转换函数
"""
import re
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Tuple

def df_to_markdown(df: pd.DataFrame) -> str:
    """将DataFrame转换为Markdown表格"""
    if df.empty:
        return "无数据"
    return df.to_markdown(index=False)

def normalize_well_id(well_id: str) -> str:
    """归一化井号（处理中文井号和各种别名）"""
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

def parse_date_range(time_desc: str) -> Tuple[str, str]:
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
