"""
油田 MCP Server 本地测试脚本
用于在不启动完整 MCP 服务的情况下测试工具函数
"""

import sys
from datetime import date

# 导入主服务器（会自动初始化数据库和数据）
from oilfield_mcp_server import (
    search_wells,
    get_well_summary,
    get_well_casing,
    get_daily_report,
    analyze_npt_events,
    compare_wells_overview,
    compare_drilling_pace,
    compare_npt_statistics,
    get_period_drilling_summary,
    get_block_period_summary,
    track_mud_properties
)

def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

def test_search():
    """测试井搜索"""
    print_section("测试 1: 搜索井")
    result = search_wells.fn(keyword="Block-A", status="All", user_role="admin")
    print(result)

def test_well_summary():
    """测试井概览"""
    print_section("测试 2: 井概览")
    result = get_well_summary.fn(well_id="ZT-102", user_role="admin")
    print(result)

def test_well_casing():
    """测试井身结构"""
    print_section("测试 3: 井身结构")
    result = get_well_casing.fn(well_id="ZT-102", user_role="admin")
    print(result)

def test_daily_report():
    """测试日报查询"""
    print_section("测试 4: 日报查询")
    result = get_daily_report.fn(
        well_id="ZT-102",
        date="2023-11-06",  # 这天有井漏事故
        user_role="admin"
    )
    print(result)

def test_npt_analysis():
    """测试NPT分析"""
    print_section("测试 5: NPT分析")
    result = analyze_npt_events.fn(well_id="ZT-102", user_role="admin")
    print(result)

def test_compare_overview():
    """测试多井对比"""
    print_section("测试 6: 多井基本对比")
    result = compare_wells_overview.fn(
        well_ids="ZT-102,ZT-105",
        user_role="admin"
    )
    print(result)

def test_compare_pace():
    """测试钻井速度对比"""
    print_section("测试 7: 钻井速度对比")
    result = compare_drilling_pace.fn(
        well_ids="ZT-102,ZT-105",
        user_role="admin"
    )
    print(result)

def test_compare_npt():
    """测试NPT对比"""
    print_section("测试 8: NPT对比")
    result = compare_npt_statistics.fn(
        well_ids="ZT-102,ZT-105",
        user_role="admin"
    )
    print(result)

def test_period_summary():
    """测试单井期间报告"""
    print_section("测试 9: 单井期间报告（周报数据）")
    result = get_period_drilling_summary.fn(
        well_id="ZT-102",
        start_date="2023-11-01",
        end_date="2023-11-07",
        user_role="admin"
    )
    print(result)

def test_block_summary():
    """测试区块报告"""
    print_section("测试 10: 区块汇总报告")
    result = get_block_period_summary.fn(
        block_name="Block-A",
        start_date="2023-11-01",
        end_date="2023-11-10",
        user_role="admin"
    )
    print(result)

def test_mud_tracking():
    """测试泥浆参数追踪"""
    print_section("测试 11: 泥浆密度追踪")
    result = track_mud_properties.fn(
        well_id="ZT-102",
        property_name="density",
        user_role="admin"
    )
    print(result)

def test_permission_deny():
    """测试权限拒绝"""
    print_section("测试 12: 权限控制（engineer角色访问XY-009）")
    result = get_well_summary.fn(well_id="XY-009", user_role="engineer")
    print(result)

def test_chinese_well_id():
    """测试中文井号归一化"""
    print_section("测试 13: 中文井号识别")
    result = get_well_summary.fn(well_id="中102", user_role="admin")
    print(result)

def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("*" * 60)
    print("  油田 MCP Server 功能测试")
    print("*" * 60)
    
    try:
        test_search()
        test_well_summary()
        test_well_casing()
        test_daily_report()
        test_npt_analysis()
        test_compare_overview()
        test_compare_pace()
        test_compare_npt()
        test_period_summary()
        test_block_summary()
        test_mud_tracking()
        test_permission_deny()
        test_chinese_well_id()
        
        print("\n" + "=" * 60)
        print("  ✅ 所有测试完成！")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
