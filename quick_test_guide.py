"""
快速测试真实数据服务器
简化版测试脚本
"""
import os
import sys

print("=" * 60)
print("快速测试指南：使用真实数据")
print("=" * 60)
print()

print("📋 测试步骤：")
print()

print("1️⃣  确保PostgreSQL服务运行")
print("   命令: Get-Service -Name postgresql*")
print("   或: Start-Service postgresql-x64-15")
print()

print("2️⃣  确保数据已导入")
print("   命令: python verify_imported_data.py")
print("   如果没有数据，运行:")
print("     python setup_oil_wells_table.py  # 创建表")
print("     python import_well_data.py       # 导入数据")
print()

print("3️⃣  启动MCP服务器")
print("   选择一种方式:")
print()
print("   方式A: 主服务器(8080) + 真实数据")
print("     PowerShell: .\\start_real_server.ps1")
print("     批处理:     start_real_server.bat")
print()
print("   方式B: 真实数据专用服务器(8081)")
print("     PowerShell: .\\start_true_server.ps1")
print("     批处理:     start_true_server.bat")
print()

print("4️⃣  验证服务器运行")
print("   在新终端窗口运行:")
print("     curl http://localhost:8080/health  # 如果用方式A")
print("     curl http://localhost:8081/health  # 如果用方式B")
print()
print("   预期输出:")
print('     {"status":"healthy","database":"connected",...}')
print()

print("5️⃣  完整测试（可选）")
print("   命令: python test_real_data.py")
print("   注意: 需要先启动服务器")
print()

print("=" * 60)
print("💡 提示")
print("=" * 60)
print()
print("- 如果PostgreSQL未安装，请先使用模拟数据:")
print("  运行: .\\start_mock_server.ps1 或 start_mock_server.bat")
print()
print("- 模拟数据模式无需任何配置，立即可用")
print()
print("- 真实数据和模拟数据的功能基本相同")
print("  区别在于数据来源（真实 vs 模拟）")
print()

# 检查是否想要立即测试
print("=" * 60)
choice = input("\n是否现在测试数据库连接？(y/n): ").lower()

if choice == 'y':
    print("\n正在测试数据库连接...")
    print("-" * 60)
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        DB_CONFIG = {
            'host': 'localhost',
            'port': 5432,
            'database': 'rag',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM oil_wells WHERE is_deleted = false")
        count = cursor.fetchone()['count']
        
        print(f"✅ 数据库连接成功！")
        print(f"📊 当前有 {count} 口井的数据")
        
        if count > 0:
            cursor.execute("""
                SELECT well_name, qk, jx 
                FROM oil_wells 
                WHERE is_deleted = false 
                LIMIT 3
            """)
            samples = cursor.fetchall()
            
            print(f"\n数据样例:")
            for row in samples:
                print(f"  - {row['well_name']} ({row['qk']}, {row['jx']})")
            
            print(f"\n✅ 可以启动真实数据服务器了！")
            print(f"   运行: .\\start_true_server.ps1")
        else:
            print(f"\n⚠️  数据库中没有数据")
            print(f"   请运行: python import_well_data.py")
        
        cursor.close()
        conn.close()
        
    except ImportError:
        print("❌ psycopg2未安装")
        print("   安装: pip install psycopg2-binary")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print(f"\n建议:")
        print(f"  1. 检查PostgreSQL是否运行")
        print(f"  2. 使用模拟数据模式: .\\start_mock_server.ps1")
else:
    print("\n📚 详细测试指南: md\\真实数据测试指南.md")

print()
