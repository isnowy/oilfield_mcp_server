"""
批量查询功能测试
测试 search_wells、get_well_summary、get_daily_report、generate_weekly_report 的批量和单个查询功能
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入业务逻辑函数
from oilfield_mcp_http_server import (
    search_wells,
    get_well_summary,
    get_daily_report,
    generate_weekly_report,
    Session
)

print("=" * 80)
print("🧪 批量查询功能测试")
print("=" * 80)
print()

# 测试用户信息
TEST_USER_ROLE = "ADMIN"
TEST_USER_ID = "test_user_001"
TEST_USER_EMAIL = "test@example.com"

def print_test_header(test_name):
    """打印测试标题"""
    print("\n" + "=" * 80)
    print(f"📋 测试: {test_name}")
    print("=" * 80)

def print_result(result):
    """打印测试结果"""
    print(result)
    print()

# ==========================================
# 测试 1: search_wells - 单关键词搜索
# ==========================================
print_test_header("search_wells - 单关键词搜索（旧接口）")
print("参数: keyword='ZT-102'")
try:
    result = search_wells(
        keyword="ZT-102",
        status="All",
        user_role=TEST_USER_ROLE,
        user_id=TEST_USER_ID,
        user_email=TEST_USER_EMAIL
    )
    print_result(result)
except Exception as e:
    print(f"❌ 错误: {e}\n")

# ==========================================
# 测试 2: search_wells - 多关键词搜索
# ==========================================
print_test_header("search_wells - 多关键词批量搜索（新接口）")
print("参数: keywords=['ZT', 'Block-A']")
try:
    result = search_wells(
        keywords=["ZT", "Block-A"],
        status="All",
        user_role=TEST_USER_ROLE,
        user_id=TEST_USER_ID,
        user_email=TEST_USER_EMAIL
    )
    print_result(result)
except Exception as e:
    print(f"❌ 错误: {e}\n")

# ==========================================
# 测试 3: get_well_summary - 单井查询
# ==========================================
print_test_header("get_well_summary - 单井概况查询（旧接口）")
print("参数: well_id='ZT-102'")
try:
    result = get_well_summary(
        well_id="ZT-102",
        user_role=TEST_USER_ROLE,
        user_id=TEST_USER_ID,
        user_email=TEST_USER_EMAIL
    )
    print_result(result)
except Exception as e:
    print(f"❌ 错误: {e}\n")

# ==========================================
# 测试 4: get_well_summary - 多井批量查询
# ==========================================
print_test_header("get_well_summary - 多井批量概况查询（新接口）")
print("参数: well_ids=['ZT-102', 'ZT-105']")
try:
    result = get_well_summary(
        well_ids=["ZT-102", "ZT-105"],
        user_role=TEST_USER_ROLE,
        user_id=TEST_USER_ID,
        user_email=TEST_USER_EMAIL
    )
    print_result(result)
except Exception as e:
    print(f"❌ 错误: {e}\n")

# ==========================================
# 测试 5: get_daily_report - 单井单日期
# ==========================================
print_test_header("get_daily_report - 单井单日期查询（旧接口）")

# 先获取可用日期
session = Session()
try:
    from oilfield_mcp_http_server import DailyReport
    report = session.query(DailyReport).filter_by(well_id="ZT-102").first()
    if report:
        test_date = str(report.report_date)
        print(f"参数: well_id='ZT-102', date_str='{test_date}'")
        
        result = get_daily_report(
            well_id="ZT-102",
            date_str=test_date,
            user_role=TEST_USER_ROLE,
            user_id=TEST_USER_ID,
            user_email=TEST_USER_EMAIL
        )
        print_result(result)
    else:
        print("⚠️ 数据库中没有 ZT-102 的日报数据\n")
except Exception as e:
    print(f"❌ 错误: {e}\n")
finally:
    session.close()

# ==========================================
# 测试 6: get_daily_report - 日期为空（列出可用日期）
# ==========================================
print_test_header("get_daily_report - 日期为空（应列出可用日期）")
print("参数: well_id='ZT-102', date_str=''")
try:
    result = get_daily_report(
        well_id="ZT-102",
        date_str="",
        user_role=TEST_USER_ROLE,
        user_id=TEST_USER_ID,
        user_email=TEST_USER_EMAIL
    )
    print_result(result)
except Exception as e:
    print(f"❌ 错误: {e}\n")

# ==========================================
# 测试 7: get_daily_report - 多井同一日期
# ==========================================
print_test_header("get_daily_report - 多井同一日期批量查询（新接口）")

session = Session()
try:
    from oilfield_mcp_http_server import DailyReport
    report = session.query(DailyReport).first()
    if report:
        test_date = str(report.report_date)
        print(f"参数: well_ids=['ZT-102', 'ZT-105'], dates=['{test_date}']")
        
        result = get_daily_report(
            well_ids=["ZT-102", "ZT-105"],
            dates=[test_date],
            user_role=TEST_USER_ROLE,
            user_id=TEST_USER_ID,
            user_email=TEST_USER_EMAIL
        )
        print_result(result)
    else:
        print("⚠️ 数据库中没有日报数据\n")
except Exception as e:
    print(f"❌ 错误: {e}\n")
finally:
    session.close()

# ==========================================
# 测试 8: get_daily_report - 多井多日期（一一对应）
# ==========================================
print_test_header("get_daily_report - 多井多日期批量查询（新接口）")

session = Session()
try:
    from oilfield_mcp_http_server import DailyReport, Well
    
    # 获取两口井及其日期
    wells = session.query(Well).limit(2).all()
    if len(wells) >= 2:
        dates = []
        well_ids = []
        for well in wells:
            report = session.query(DailyReport).filter_by(well_id=well.id).first()
            if report:
                well_ids.append(well.id)
                dates.append(str(report.report_date))
        
        if len(well_ids) >= 2:
            print(f"参数: well_ids={well_ids}, dates={dates}")
            
            result = get_daily_report(
                well_ids=well_ids,
                dates=dates,
                user_role=TEST_USER_ROLE,
                user_id=TEST_USER_ID,
                user_email=TEST_USER_EMAIL
            )
            print_result(result)
        else:
            print("⚠️ 没有足够的日报数据\n")
    else:
        print("⚠️ 数据库中井数据不足\n")
except Exception as e:
    print(f"❌ 错误: {e}\n")
finally:
    session.close()

# ==========================================
# 测试 9: generate_weekly_report - 单井周报
# ==========================================
print_test_header("generate_weekly_report - 单井周报生成（旧接口）")

session = Session()
try:
    from oilfield_mcp_http_server import DailyReport
    
    # 获取一个井的日期范围
    reports = session.query(DailyReport).filter_by(well_id="ZT-102")\
        .order_by(DailyReport.report_date).limit(7).all()
    
    if len(reports) >= 2:
        start_date = str(reports[0].report_date)
        end_date = str(reports[-1].report_date)
        
        print(f"参数: well_id='ZT-102', start_date='{start_date}', end_date='{end_date}'")
        
        result = generate_weekly_report(
            well_id="ZT-102",
            start_date=start_date,
            end_date=end_date,
            user_role=TEST_USER_ROLE,
            user_id=TEST_USER_ID,
            user_email=TEST_USER_EMAIL
        )
        print_result(result)
    else:
        print("⚠️ ZT-102 的日报数据不足\n")
except Exception as e:
    print(f"❌ 错误: {e}\n")
finally:
    session.close()

# ==========================================
# 测试 10: generate_weekly_report - 多井周报
# ==========================================
print_test_header("generate_weekly_report - 多井批量周报生成（新接口）")

session = Session()
try:
    from oilfield_mcp_http_server import DailyReport
    
    # 获取日期范围
    reports = session.query(DailyReport)\
        .order_by(DailyReport.report_date).limit(7).all()
    
    if len(reports) >= 2:
        start_date = str(reports[0].report_date)
        end_date = str(reports[-1].report_date)
        
        print(f"参数: well_ids=['ZT-102', 'ZT-105'], start_date='{start_date}', end_date='{end_date}'")
        
        result = generate_weekly_report(
            well_ids=["ZT-102", "ZT-105"],
            start_date=start_date,
            end_date=end_date,
            user_role=TEST_USER_ROLE,
            user_id=TEST_USER_ID,
            user_email=TEST_USER_EMAIL
        )
        print_result(result)
    else:
        print("⚠️ 日报数据不足\n")
except Exception as e:
    print(f"❌ 错误: {e}\n")
finally:
    session.close()

# ==========================================
# 测试 11: 权限测试 - 非管理员用户
# ==========================================
print_test_header("权限测试 - VIEWER用户批量查询")
print("参数: well_ids=['ZT-102', 'ZT-105', 'ZT-108'], 用户角色=VIEWER")
try:
    result = get_well_summary(
        well_ids=["ZT-102", "ZT-105", "ZT-108"],
        user_role="VIEWER",
        user_id="viewer_001",
        user_email="viewer@example.com"
    )
    print_result(result)
except Exception as e:
    print(f"❌ 错误: {e}\n")

# ==========================================
# 测试 12: 错误处理 - 不存在的井号
# ==========================================
print_test_header("错误处理 - 批量查询包含不存在的井号")
print("参数: well_ids=['ZT-102', 'INVALID-WELL', 'ZT-105']")
try:
    result = get_well_summary(
        well_ids=["ZT-102", "INVALID-WELL", "ZT-105"],
        user_role=TEST_USER_ROLE,
        user_id=TEST_USER_ID,
        user_email=TEST_USER_EMAIL
    )
    print_result(result)
except Exception as e:
    print(f"❌ 错误: {e}\n")

# ==========================================
# 测试总结
# ==========================================
print("\n" + "=" * 80)
print("✅ 测试完成")
print("=" * 80)
print("\n测试项:")
print("  ✓ search_wells - 单关键词搜索")
print("  ✓ search_wells - 多关键词批量搜索")
print("  ✓ get_well_summary - 单井查询")
print("  ✓ get_well_summary - 多井批量查询")
print("  ✓ get_daily_report - 单井单日期查询")
print("  ✓ get_daily_report - 日期为空（列出可用日期）")
print("  ✓ get_daily_report - 多井同一日期批量查询")
print("  ✓ get_daily_report - 多井多日期批量查询")
print("  ✓ generate_weekly_report - 单井周报生成")
print("  ✓ generate_weekly_report - 多井批量周报生成")
print("  ✓ 权限测试 - 非管理员用户")
print("  ✓ 错误处理 - 不存在的井号")
print()
print("💡 提示: 如果某些测试显示警告或错误，可能是因为数据库中没有相应的测试数据")
print("         请先运行 init_db.py 初始化测试数据")
print()
