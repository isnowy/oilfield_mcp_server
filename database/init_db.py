import sqlite3

conn = sqlite3.connect('d:/work/oilMCP/oilfield.db')
cursor = conn.cursor()

# 创建表
cursor.execute('''
    CREATE TABLE IF NOT EXISTS drilling_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        well_number TEXT NOT NULL,
        drilling_date TEXT NOT NULL,
        depth REAL NOT NULL,
        drilling_speed REAL,
        pressure REAL,
        temperature REAL
    )
''')

# 插入测试数据
test_data = [
    ('WELL-001', '2026-01-28', 1500.5, 25.3, 3200.0, 85.5),
    ('WELL-002', '2026-01-27', 2000.0, 30.1, 3500.0, 92.0),
    ('WELL-003', '2026-01-26', 1800.0, 28.5, 3300.0, 88.0),
]

cursor.executemany(
    'INSERT INTO drilling_data (well_number, drilling_date, depth, drilling_speed, pressure, temperature) VALUES (?, ?, ?, ?, ?, ?)',
    test_data
)

conn.commit()
print(f"✅ 数据库初始化完成，插入了 {len(test_data)} 条记录")
conn.close()
