"""
自动化角色权限测试脚本
用于测试不同角色对相同查询的结果差异
"""

import sys
import os
import io
from datetime import date
from typing import Dict, List, Tuple

# 设置 Windows 控制台 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置生产模式进行测试
os.environ['DEV_MODE'] = 'false'

# 导入主服务器
from oilfield_mcp_server import (
    search_wells,
    get_well_summary,
    get_daily_report,
    analyze_npt_events,
    compare_wells_overview,
    get_period_drilling_summary,
    get_block_period_summary
)

# 测试角色列表
ROLES = ['admin', 'engineer', 'viewer', 'default']

# 测试用例定义
class TestCase:
    def __init__(self, name: str, description: str, test_func, expected_results: Dict[str, str]):
        self.name = name
        self.description = description
        self.test_func = test_func
        self.expected_results = expected_results

class RolePermissionTester:
    """角色权限测试器"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def print_header(self):
        """打印测试头部"""
        print("\n" + "=" * 80)
        print("  🧪 角色权限自动化测试")
        print("=" * 80)
        print(f"\n🔒 测试模式: 生产模式 (DEV_MODE=false)")
        print(f"👥 测试角色: {', '.join(ROLES)}\n")
    
    def print_test_header(self, test_num: int, test_name: str, description: str):
        """打印测试标题"""
        print("\n" + "-" * 80)
        print(f"📋 测试 {test_num}: {test_name}")
        print(f"   {description}")
        print("-" * 80)
    
    def run_test_for_role(self, role: str, test_func) -> Tuple[bool, str]:
        """为指定角色运行测试"""
        try:
            result = test_func(role)
            
            # 检查是否被拒绝
            if isinstance(result, str):
                if "权限拒绝" in result or "无权访问" in result:
                    return False, "权限拒绝"
                elif "未找到" in result:
                    return False, "未找到数据"
                else:
                    return True, "成功"
            else:
                return True, "成功"
        except Exception as e:
            return False, f"错误: {str(e)[:50]}"
    
    def run_test_case(self, test_num: int, test_case: TestCase):
        """运行单个测试用例"""
        self.print_test_header(test_num, test_case.name, test_case.description)
        
        results = {}
        for role in ROLES:
            success, message = self.run_test_for_role(role, test_case.test_func)
            results[role] = (success, message)
            
            # 检查是否符合预期
            expected = test_case.expected_results.get(role, "success")
            if expected == "deny":
                is_correct = not success
            else:
                is_correct = success
            
            status = "✅" if is_correct else "❌"
            
            print(f"{status} {role:<12} -> {message:<20} (预期: {expected})")
            
            if is_correct:
                self.passed += 1
            else:
                self.failed += 1
        
        return results
    
    def run_all_tests(self):
        """运行所有测试"""
        self.print_header()
        
        # 定义测试用例
        test_cases = [
            TestCase(
                name="搜索 Block-A 的井",
                description="engineer 和 viewer 应该能访问，default 应该被拒绝",
                test_func=lambda role: search_wells.fn(keyword="Block-A", status="All", user_role=role),
                expected_results={
                    'admin': 'success',
                    'engineer': 'success',
                    'viewer': 'success',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="搜索 Block-B 的井",
                description="只有 admin 可以访问，其他角色应该被拒绝",
                test_func=lambda role: search_wells.fn(keyword="Block-B", status="All", user_role=role),
                expected_results={
                    'admin': 'success',
                    'engineer': 'deny',
                    'viewer': 'deny',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="查询 ZT-102 井概览",
                description="engineer 和 viewer 都可以访问，default 被拒绝",
                test_func=lambda role: get_well_summary.fn(well_id="ZT-102", user_role=role),
                expected_results={
                    'admin': 'success',
                    'engineer': 'success',
                    'viewer': 'success',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="查询 ZT-105 井概览",
                description="engineer 可以访问，viewer 不能访问",
                test_func=lambda role: get_well_summary.fn(well_id="ZT-105", user_role=role),
                expected_results={
                    'admin': 'success',
                    'engineer': 'success',
                    'viewer': 'deny',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="查询 XY-009 井概览",
                description="只有 admin 可以访问",
                test_func=lambda role: get_well_summary.fn(well_id="XY-009", user_role=role),
                expected_results={
                    'admin': 'success',
                    'engineer': 'deny',
                    'viewer': 'deny',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="查询 ZT-102 日报",
                description="engineer 和 viewer 都可以访问",
                test_func=lambda role: get_daily_report.fn(well_id="ZT-102", date="2023-11-06", user_role=role),
                expected_results={
                    'admin': 'success',
                    'engineer': 'success',
                    'viewer': 'success',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="对比 ZT-102 和 ZT-105",
                description="engineer 可以对比，viewer 不能（ZT-105无权限）",
                test_func=lambda role: compare_wells_overview.fn(well_ids="ZT-102,ZT-105", user_role=role),
                expected_results={
                    'admin': 'success',
                    'engineer': 'success',
                    'viewer': 'deny',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="生成 Block-A 区块报告",
                description="engineer 和 viewer 都可以访问 Block-A",
                test_func=lambda role: get_block_period_summary.fn(
                    block_name="Block-A", 
                    start_date="2023-11-01", 
                    end_date="2023-11-07", 
                    user_role=role
                ),
                expected_results={
                    'admin': 'success',
                    'engineer': 'success',
                    'viewer': 'success',
                    'default': 'deny'
                }
            ),
            TestCase(
                name="生成 Block-B 区块报告",
                description="只有 admin 可以访问 Block-B",
                test_func=lambda role: get_block_period_summary.fn(
                    block_name="Block-B", 
                    start_date="2023-11-01", 
                    end_date="2023-11-07", 
                    user_role=role
                ),
                expected_results={
                    'admin': 'success',
                    'engineer': 'deny',
                    'viewer': 'deny',
                    'default': 'deny'
                }
            ),
        ]
        
        # 运行所有测试
        for i, test_case in enumerate(test_cases, 1):
            self.run_test_case(i, test_case)
        
        # 打印总结
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 80)
        print("  📊 测试总结")
        print("=" * 80)
        print(f"  总测试数: {total}")
        print(f"  ✅ 通过: {self.passed}")
        print(f"  ❌ 失败: {self.failed}")
        print(f"  📈 通过率: {pass_rate:.1f}%")
        print("=" * 80)
        
        if self.failed == 0:
            print("\n🎉 所有测试通过！权限控制正常工作。")
        else:
            print(f"\n⚠️  发现 {self.failed} 个问题，请检查权限配置。")
        
        print("\n💡 提示：如需查看详细输出，可以修改各测试函数打印结果。")
        print("=" * 80 + "\n")

    def generate_comparison_table(self):
        """生成角色对比表"""
        print("\n" + "=" * 80)
        print("  📋 角色权限对比表")
        print("=" * 80)
        print("\n| 查询内容 | admin | engineer | viewer | default |")
        print("|---------|-------|----------|--------|---------|")
        print("| ZT-102 井 | ✅ | ✅ | ✅ | ❌ |")
        print("| ZT-105 井 | ✅ | ✅ | ❌ | ❌ |")
        print("| XY-009 井 | ✅ | ❌ | ❌ | ❌ |")
        print("| Block-A 区块 | ✅ | ✅ | ✅ | ❌ |")
        print("| Block-B 区块 | ✅ | ❌ | ❌ | ❌ |")
        print("| 对比 ZT-102+ZT-105 | ✅ | ✅ | ❌ | ❌ |")
        print("\n" + "=" * 80 + "\n")


def main():
    """主函数"""
    print("\n")
    print("*" * 80)
    print("  角色权限自动化测试工具")
    print("  用于验证不同角色的查询结果是否符合权限设置")
    print("*" * 80)
    
    # 确认使用生产模式
    dev_mode = os.getenv('DEV_MODE', 'false').lower()
    if dev_mode == 'true':
        print("\n⚠️  警告：当前为开发模式，所有角色都有 admin 权限！")
        print("   测试结果可能不准确。建议使用生产模式：")
        print("   $env:DEV_MODE='false'; python test_role_permissions.py\n")
        response = input("是否继续测试？(y/n): ")
        if response.lower() != 'y':
            print("测试已取消。")
            return
    
    # 运行测试
    tester = RolePermissionTester()
    tester.run_all_tests()
    tester.generate_comparison_table()


if __name__ == "__main__":
    main()
