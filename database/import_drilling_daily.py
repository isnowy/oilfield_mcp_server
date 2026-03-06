"""
导入钻井工程日报数据（drilling_daily.xlsx）到PostgreSQL数据库
"""

import pandas as pd
import psycopg2
from psycopg2 import sql, extras
from pathlib import Path
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rag',
    'user': 'postgres',
    'password': 'postgres'
}

# Excel文件路径
EXCEL_FILE = "drilling_daily.xlsx"

# 字段映射：Excel列名 -> 数据库字段名
COLUMN_MAPPING = {
    'RQ': 'rq',           # 日期
    'JH': 'jh',           # 井号
    'KZRQ': 'kzrq',       # 开钻日期
    'DRJS': 'drjs',       # 当日井深
    'ZJRJC': 'zjrjc',     # 日进尺
    'ZTLX': 'ztlx',       # 钻头类型
    'ZTZJ': 'ztzj',       # 钻头直径
    'ZY': 'zy',           # 钻压
    'ZS': 'zs',           # 钻速
    'BYA': 'bya',         # 泵压
    'BPL': 'bpl',         # 排量
    'ZJYMD': 'zjymd',     # 钻井液密度
    'ZJYND': 'zjynd',     # 钻井液粘度
    'CZJLJSJ': 'czjljsj', # 纯钻进累计时间
    'BRZYGZ': 'brzygz',   # 本日主要工作
}


def read_excel_data(file_path):
    """读取Excel文件"""
    print(f"📄 读取Excel文件: {file_path}")
    
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return None
    
    try:
        # 第2行（索引1）作为表头
        df = pd.read_excel(file_path, header=1)
        
        # 去除列名空格
        df.columns = df.columns.str.strip()
        
        # 删除第一列（如果是Unnamed）
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])
        
        print(f"✓ 成功读取 {len(df)} 行数据")
        print(f"✓ 列名: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"❌ 读取Excel失败: {e}")
        return None


def clean_and_validate_data(df):
    """清洗和验证数据"""
    print("\n🧹 清洗和验证数据...")
    
    original_count = len(df)
    
    # 删除井号为空的行
    before_jh = len(df)
    df = df.dropna(subset=['JH'])
    if before_jh != len(df):
        print(f"  - 删除井号为空的行: {before_jh - len(df)} 行")
    
    # 删除日期为空的行（日期是必须的）
    before_rq = len(df)
    df = df.dropna(subset=['RQ'])
    if before_rq != len(df):
        print(f"  - 删除日期为空的行: {before_rq - len(df)} 行")
    
    # 处理日期格式
    try:
        df['RQ'] = pd.to_datetime(df['RQ'], errors='coerce')
        df['KZRQ'] = pd.to_datetime(df['KZRQ'], errors='coerce')
        
        # 删除日期转换失败的行
        before = len(df)
        df = df.dropna(subset=['RQ'])
        if before != len(df):
            print(f"  - 删除日期格式错误的行: {before - len(df)} 行")
        
        # 将KZRQ中的NaT转换为None（允许开钻日期为空）
        df['KZRQ'] = df['KZRQ'].replace({pd.NaT: None})
        
    except Exception as e:
        print(f"  ⚠️  日期处理警告: {e}")
    
    # 转换数值字段
    numeric_fields = ['DRJS', 'ZJRJC', 'ZTZJ', 'ZY', 'ZS', 'BYA', 'BPL', 'ZJYMD', 'ZJYND']
    for field in numeric_fields:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors='coerce')
    
    # 处理CZJLJSJ字段（可能是字符串或数值）
    if 'CZJLJSJ' in df.columns:
        df['CZJLJSJ'] = pd.to_numeric(df['CZJLJSJ'], errors='coerce')
    
    # 将NaN替换为None
    df = df.where(pd.notnull(df), None)
    
    print(f"✓ 数据清洗完成，有效数据: {len(df)} 行")
    
    return df


def create_table_if_not_exists(db_config):
    """如果表不存在则创建"""
    print("\n🔧 检查并创建数据表...")
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'drilling_daily'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("  表不存在，正在创建...")
            
            # 读取并执行建表SQL
            sql_file = Path(__file__).parent / "drilling_daily_schema.sql"
            if sql_file.exists():
                with open(sql_file, 'r', encoding='utf-8') as f:
                    create_sql = f.read()
                cursor.execute(create_sql)
                conn.commit()
                print("  ✓ 表创建成功")
            else:
                print(f"  ❌ 找不到建表SQL文件: {sql_file}")
                return False
        else:
            print("  ✓ 表已存在")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 检查/创建表失败: {e}")
        return False


def prepare_insert_data(df):
    """准备插入数据库的数据"""
    print("\n📦 准备插入数据...")
    
    # 重命名列为数据库字段名
    rename_map = {k: v for k, v in COLUMN_MAPPING.items() if k in df.columns}
    df = df.rename(columns=rename_map)
    
    # 只保留映射的字段
    db_columns = list(rename_map.values())
    df = df[db_columns]
    
    # 转换为字典列表
    data = df.to_dict('records')
    
    print(f"✓ 准备 {len(data)} 条数据待插入")
    
    return data, db_columns


def insert_data_to_db(data, columns, db_config):
    """将数据插入数据库"""
    print("\n💾 插入数据到数据库...")
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print(f"✓ 数据库连接成功")
        
        # 构建插入SQL
        insert_query = sql.SQL("""
            INSERT INTO drilling_daily ({})
            VALUES ({})
        """).format(
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(columns))
        )
        
        # 批量插入
        inserted_count = 0
        error_count = 0
        
        for record in data:
            try:
                values = [record.get(col) for col in columns]
                cursor.execute(insert_query, values)
                inserted_count += 1
                
                # 每1000条提交一次
                if inserted_count % 1000 == 0:
                    conn.commit()
                    print(f"  进度: {inserted_count}/{len(data)}")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 只打印前5个错误
                    print(f"  ⚠️  插入错误: {e} - 井号: {record.get('jh', 'N/A')}")
        
        conn.commit()
        
        print(f"✓ 成功插入 {inserted_count} 条数据")
        if error_count > 0:
            print(f"  ⚠️  失败 {error_count} 条数据")
        
        cursor.close()
        conn.close()
        
        return inserted_count
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
        return 0


def check_well_matching(db_config):
    """检查井号匹配情况"""
    print("\n🔍 检查井号与oil_wells表的匹配情况...")
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # 获取drilling_daily中的不同井号
        cursor.execute("""
            SELECT DISTINCT jh 
            FROM drilling_daily 
            WHERE jh IS NOT NULL
            ORDER BY jh
        """)
        drilling_wells = {row[0] for row in cursor.fetchall()}
        print(f"  ✓ drilling_daily表中不同井号: {len(drilling_wells)} 个")
        
        # 获取oil_wells中的well_name
        cursor.execute("""
            SELECT DISTINCT well_name 
            FROM oil_wells 
            WHERE well_name IS NOT NULL
            ORDER BY well_name
        """)
        oil_wells = {row[0] for row in cursor.fetchall()}
        print(f"  ✓ oil_wells表中不同well_name: {len(oil_wells)} 个")
        
        # 找出匹配的井号
        matched_wells = drilling_wells.intersection(oil_wells)
        unmatched_wells = drilling_wells - oil_wells
        
        print(f"\n  ✅ 匹配成功的井号: {len(matched_wells)} 个")
        print(f"  ⚠️  匹配失败的井号: {len(unmatched_wells)} 个")
        
        if unmatched_wells:
            print(f"\n  匹配失败的井号列表（前20个）:")
            for well in sorted(list(unmatched_wells))[:20]:
                # 统计该井号的记录数
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM drilling_daily 
                    WHERE jh = %s
                """, (well,))
                count = cursor.fetchone()[0]
                print(f"    - {well}: {count} 条记录")
            
            if len(unmatched_wells) > 20:
                print(f"    ... 还有 {len(unmatched_wells) - 20} 个")
        
        # 统计记录数匹配情况
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN EXISTS (
                    SELECT 1 FROM oil_wells WHERE oil_wells.well_name = drilling_daily.jh
                ) THEN 1 END) as matched,
                COUNT(CASE WHEN NOT EXISTS (
                    SELECT 1 FROM oil_wells WHERE oil_wells.well_name = drilling_daily.jh
                ) THEN 1 END) as unmatched
            FROM drilling_daily
            WHERE jh IS NOT NULL
        """)
        
        result = cursor.fetchone()
        total, matched_count, unmatched_count = result
        
        print(f"\n  📊 记录匹配统计:")
        print(f"    总记录数: {total:,} 条")
        print(f"    匹配成功: {matched_count:,} 条 ({matched_count/total*100:.1f}%)")
        print(f"    匹配失败: {unmatched_count:,} 条 ({unmatched_count/total*100:.1f}%)")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查匹配失败: {e}")


def main():
    """主函数"""
    print("=" * 70)
    print("钻井工程日报数据导入工具")
    print("=" * 70)
    print()
    
    # 检查Excel文件
    if not Path(EXCEL_FILE).exists():
        print(f"❌ 找不到Excel文件: {EXCEL_FILE}")
        return False
    
    # 创建表
    if not create_table_if_not_exists(DB_CONFIG):
        return False
    
    # 读取Excel
    df = read_excel_data(EXCEL_FILE)
    if df is None or len(df) == 0:
        print("❌ 没有数据可导入")
        return False
    
    # 清洗数据
    df = clean_and_validate_data(df)
    if len(df) == 0:
        print("❌ 清洗后没有有效数据")
        return False
    
    # 准备数据
    data, columns = prepare_insert_data(df)
    
    # 插入数据
    inserted = insert_data_to_db(data, columns, DB_CONFIG)
    
    # 检查井号匹配
    check_well_matching(DB_CONFIG)
    
    print("\n" + "=" * 70)
    if inserted > 0:
        print(f"✅ 导入完成！成功导入 {inserted} 条数据")
    else:
        print("❌ 导入失败")
    print("=" * 70)
    
    return inserted > 0


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
