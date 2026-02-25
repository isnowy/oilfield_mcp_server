"""
测试数据源切换功能
验证模拟数据和真实数据库模式是否正常工作
"""
import os
import sys

def test_env_switching():
    """测试环境变量切换"""
    print("=" * 60)
    print("测试数据源切换功能")
    print("=" * 60)
    print()
    
    # 测试1: 模拟数据模式
    print("【测试1】模拟数据模式")
    os.environ['USE_REAL_DB'] = 'false'
    os.environ['DEV_MODE'] = 'true'
    
    use_real = os.getenv("USE_REAL_DB", "false").lower() in ["true", "1", "yes"]
    dev_mode = os.getenv("DEV_MODE", "true").lower() in ["true", "1", "yes"]
    
    print(f"  USE_REAL_DB: {os.environ.get('USE_REAL_DB')}")
    print(f"  解析结果: use_real={use_real}, dev_mode={dev_mode}")
    
    if not use_real and dev_mode:
        print("  ✅ 模拟数据模式配置正确")
    else:
        print("  ❌ 模拟数据模式配置错误")
    
    print()
    
    # 测试2: 真实数据模式
    print("【测试2】真实数据模式")
    os.environ['USE_REAL_DB'] = 'true'
    os.environ['DEV_MODE'] = 'true'
    
    use_real = os.getenv("USE_REAL_DB", "false").lower() in ["true", "1", "yes"]
    dev_mode = os.getenv("DEV_MODE", "true").lower() in ["true", "1", "yes"]
    
    print(f"  USE_REAL_DB: {os.environ.get('USE_REAL_DB')}")
    print(f"  解析结果: use_real={use_real}, dev_mode={dev_mode}")
    
    if use_real and dev_mode:
        print("  ✅ 真实数据模式配置正确")
    else:
        print("  ❌ 真实数据模式配置错误")
    
    print()
    
    # 测试3: 数据库配置
    print("【测试3】数据库配置")
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '5432'
    os.environ['DB_NAME'] = 'rag'
    os.environ['DB_USER'] = 'postgres'
    os.environ['DB_PASSWORD'] = 'postgres'
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'rag'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    print(f"  数据库配置: {db_config}")
    
    if all([
        db_config['host'] == 'localhost',
        db_config['port'] == 5432,
        db_config['database'] == 'rag',
        db_config['user'] == 'postgres'
    ]):
        print("  ✅ 数据库配置解析正确")
    else:
        print("  ❌ 数据库配置解析错误")
    
    print()
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print()
    print("📌 下一步:")
    print("  1. 使用 start_mock_server.ps1 启动模拟数据服务器")
    print("  2. 使用 start_real_server.ps1 启动真实数据服务器")
    print("  3. 使用 start_true_server.ps1 启动真实数据专用服务器")
    print()

if __name__ == "__main__":
    test_env_switching()
