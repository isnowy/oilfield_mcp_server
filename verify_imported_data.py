"""验证导入的数据"""
import psycopg2

db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rag',
    'user': 'postgres',
    'password': 'postgres'
}

try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # 统计总数
    cursor.execute("SELECT COUNT(*) FROM oil_wells WHERE is_deleted = false")
    total = cursor.fetchone()[0]
    print(f"✓ 总井数: {total}")
    
    # 按区块统计
    cursor.execute("""
        SELECT qk, COUNT(*) as count 
        FROM oil_wells 
        WHERE is_deleted = false AND qk IS NOT NULL
        GROUP BY qk 
        ORDER BY count DESC 
        LIMIT 10
    """)
    print("\n📊 前10个区块井数统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}口井")
    
    # 按井型统计
    cursor.execute("""
        SELECT jx, COUNT(*) as count 
        FROM oil_wells 
        WHERE is_deleted = false AND jx IS NOT NULL
        GROUP BY jx 
        ORDER BY count DESC
    """)
    print("\n🔧 井型统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}口井")
    
    # 查看几条示例数据
    cursor.execute("""
        SELECT well_name, qk, jx, sjrq, sjjs 
        FROM oil_wells 
        WHERE is_deleted = false 
        LIMIT 5
    """)
    print("\n📝 示例数据:")
    for row in cursor.fetchall():
        print(f"  井名:{row[0]}, 区块:{row[1]}, 井型:{row[2]}, 设计日期:{row[3]}, 设计井深:{row[4]}米")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 验证失败: {e}")
