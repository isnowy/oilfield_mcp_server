"""
在rag数据库中创建oil_wells表
直接使用Python连接PostgreSQL执行SQL脚本
"""

import psycopg2
import sys
import os
from pathlib import Path


def read_sql_file(file_path):
    """读取SQL文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 找不到文件: {file_path}")
        return None
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return None


def create_tables(db_config):
    """在rag数据库中创建oil_wells表"""
    
    print("=" * 50)
    print("在rag数据库中创建oil_wells表")
    print("=" * 50)
    print()
    
    # 读取SQL脚本
    sql_file = Path(__file__).parent / "database_schema.sql"
    print(f"📄 读取SQL脚本: {sql_file}")
    
    sql_content = read_sql_file(sql_file)
    if not sql_content:
        return False
    
    print("✓ SQL脚本读取成功")
    print()
    
    # 连接数据库
    print(f"🔌 正在连接到数据库: {db_config['database']}@{db_config['host']}:{db_config['port']}")
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("✓ 数据库连接成功")
        print()
        
        # 执行SQL脚本
        print("⚙️  正在创建表和索引...")
        cursor.execute(sql_content)
        conn.commit()
        
        print("✓ SQL脚本执行成功")
        print()
        
        # 验证表是否创建成功
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'oil_wells'
        """)
        
        if cursor.fetchone():
            print("=" * 50)
            print("✅ oil_wells表创建成功！")
            print("=" * 50)
            print()
            
            # 显示表结构信息
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'oil_wells'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            print(f"📊 表结构信息 (共{len(columns)}个字段):")
            print("-" * 50)
            for col in columns[:10]:  # 只显示前10个字段
                col_name, data_type, max_length, nullable = col
                length_info = f"({max_length})" if max_length else ""
                null_info = "NULL" if nullable == 'YES' else "NOT NULL"
                print(f"  • {col_name}: {data_type}{length_info} {null_info}")
            
            if len(columns) > 10:
                print(f"  ... (还有{len(columns) - 10}个字段)")
            print()
            
            # 检查索引
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'oil_wells'
            """)
            indexes = cursor.fetchall()
            print(f"🔍 索引数量: {len(indexes)}")
            print()
            
            return True
        else:
            print("❌ 表创建验证失败")
            return False
            
    except psycopg2.Error as e:
        print()
        print("=" * 50)
        print("❌ 数据库操作失败")
        print("=" * 50)
        print(f"错误信息: {e}")
        print()
        
        if "password authentication failed" in str(e):
            print("💡 提示: 数据库密码错误，请检查密码配置")
        elif "could not connect" in str(e):
            print("💡 提示: 无法连接到数据库，请检查：")
            print("   1. PostgreSQL服务是否正在运行")
            print("   2. 主机地址和端口是否正确")
            print("   3. 防火墙是否阻止连接")
        elif "database" in str(e) and "does not exist" in str(e):
            print("💡 提示: rag数据库不存在，请先创建数据库")
        
        return False
        
    except Exception as e:
        print()
        print(f"❌ 发生未知错误: {e}")
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("🔌 数据库连接已关闭")
            print()


def main():
    """主函数"""
    
    # 数据库配置
    print("请输入数据库连接信息 (直接按Enter使用默认值):")
    print()
    
    host = input("主机地址 [localhost]: ").strip() or "localhost"
    port = input("端口 [5432]: ").strip() or "5432"
    database = input("数据库名 [rag]: ").strip() or "rag"
    user = input("用户名 [postgres]: ").strip() or "postgres"
    
    # 密码输入
    try:
        import getpass
        password = getpass.getpass("密码: ")
    except:
        password = input("密码: ")
    
    print()
    
    db_config = {
        'host': host,
        'port': int(port),
        'database': database,
        'user': user,
        'password': password
    }
    
    # 执行建表
    success = create_tables(db_config)
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 程序异常: {e}")
        sys.exit(1)
