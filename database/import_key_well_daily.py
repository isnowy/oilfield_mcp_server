"""
导入重点井试采日报数据（key_well_daily.xlsx）到PostgreSQL数据库
支持Excel数据格式：第一行中文名，第二行英文名，第三行开始为数据
"""

import pandas as pd
import psycopg2
from psycopg2 import sql, extras
import sys
import os
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
EXCEL_FILE = "key_well_daily.xlsx"

# 字段映射：Excel列名（英文）-> 数据库字段名
COLUMN_MAPPING = {
    'JH': 'jh',           # 井号
    'QK': 'qk',           # 区块
    'CW': 'cw',           # 层位
    'CXH': 'cxh',         # 层序号
    'DJSD1': 'djsd1',     # 顶界深度1
    'DJSD2': 'djsd2',     # 底界深度2
    'RQ': 'rq',           # 日期
    'ZT': 'zt',           # 状态
    'CYFS': 'cyfs',       # 采油方式
    'YZ': 'yz',           # 油嘴
    'GZSJ': 'gzsj',       # 工作时间
    'GZZD': 'gzzd',       # 工作制度
    'RCQL': 'rcql',       # 日产气量
    'HS': 'hs',           # 含水
    'YYSX': 'yysx',       # 油压上限
    'YYXX': 'yyxx',       # 油压下限
    'TYSX': 'tysx',       # 套压上限
    'TYXX': 'tyxx',       # 套压下限
    'HYSX': 'hysx',       # 回压上限
    'HYXX': 'hyxx',       # 回压下限
    'D.LY': 'd_ly',       # 流压
    'D.JY': 'd_jy',       # 静压
    'D.BZ': 'd_bz',       # 备注
}


def read_excel_with_dual_headers(file_path):
    """
    读取Excel文件，处理双行表头（第1行中文，第2行英文）
    返回使用英文表头的DataFrame
    """
    print(f"📄 读取Excel文件: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return None
    
    try:
        # 读取Excel，指定第2行（索引1）作为表头
        df = pd.read_excel(file_path, header=1)
        
        # 去除列名的空格
        df.columns = df.columns.str.strip()
        
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
    df = df.dropna(subset=['JH'])
    print(f"  - 删除井号为空的行: {original_count - len(df)} 行")
    
    # 删除日期为空的行
    df = df.dropna(subset=['RQ'])
    print(f"  - 删除日期为空的行: {original_count - len(df)} 行")
    
    # 处理日期格式
    try:
        df['RQ'] = pd.to_datetime(df['RQ'], errors='coerce')
        # 删除日期转换失败的行
        before = len(df)
        df = df.dropna(subset=['RQ'])
        if before != len(df):
            print(f"  - 删除日期格式错误的行: {before - len(df)} 行")
    except Exception as e:
        print(f"  ⚠️  日期处理警告: {e}")
    
    # 转换数值字段
    numeric_fields = ['DJSD1', 'DJSD2', 'RCQL', 'HS', 'YYSX', 'YYXX', 
                     'TYSX', 'TYXX', 'HYSX', 'HYXX', 'D_LY', 'D_JY']
    
    for field in numeric_fields:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors='coerce')
    
    print(f"✓ 数据清洗完成，有效数据: {len(df)} 行")
    
    return df


def check_well_exists(cursor, jh):
    """检查井号是否存在于oil_wells表中"""
    cursor.execute("SELECT jh FROM oil_wells WHERE jh = %s", (jh,))
    return cursor.fetchone() is not None


def validate_well_numbers(df, cursor):
    """验证井号是否存在于oil_wells表中"""
    print("\n🔍 验证井号...")
    
    unique_wells = df['JH'].unique()
    valid_wells = []
    invalid_wells = []
    
    for jh in unique_wells:
        if check_well_exists(cursor, jh):
            valid_wells.append(jh)
        else:
            invalid_wells.append(jh)
    
    print(f"  ✓ 有效井号: {len(valid_wells)} 个")
    
    if invalid_wells:
        print(f"  ⚠️  无效井号: {len(invalid_wells)} 个")
        print(f"     {invalid_wells[:10]}" + (" ..." if len(invalid_wells) > 10 else ""))
        
        # 过滤掉无效井号的数据
        before = len(df)
        df = df[df['JH'].isin(valid_wells)]
        print(f"  - 删除无效井号的数据: {before - len(df)} 行")
    
    return df


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
            INSERT INTO key_well_daily ({})
            VALUES ({})
            ON CONFLICT DO NOTHING
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
            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 只打印前5个错误
                    print(f"  ⚠️  插入错误: {e} - 数据: {record.get('jh', 'N/A')}")
        
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
                AND table_name = 'key_well_daily'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("  表不存在，正在创建...")
            
            # 读取并执行建表SQL
            sql_file = Path(__file__).parent / "key_well_daily_schema.sql"
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


def main():
    """主函数"""
    print("=" * 60)
    print("重点井试采日报数据导入工具")
    print("=" * 60)
    print()
    
    # 检查Excel文件是否存在
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ 找不到Excel文件: {EXCEL_FILE}")
        print(f"   请确保文件在当前目录: {os.getcwd()}")
        return False
    
    # 创建表（如果不存在）
    if not create_table_if_not_exists(DB_CONFIG):
        return False
    
    # 读取Excel数据
    df = read_excel_with_dual_headers(EXCEL_FILE)
    if df is None or len(df) == 0:
        print("❌ 没有数据可导入")
        return False
    
    # 清洗数据
    df = clean_and_validate_data(df)
    if len(df) == 0:
        print("❌ 清洗后没有有效数据")
        return False
    
    # 注意：井号不验证是否存在于oil_wells表，因为可能使用不同的编号体系
    print("\n⚠️  提示: 井号不验证外键关联，将直接导入所有数据")
    
    # 准备数据
    data, columns = prepare_insert_data(df)
    
    # 插入数据
    inserted = insert_data_to_db(data, columns, DB_CONFIG)
    
    print("\n" + "=" * 60)
    if inserted > 0:
        print(f"✅ 导入完成！成功导入 {inserted} 条数据")
    else:
        print("❌ 导入失败")
    print("=" * 60)
    
    return inserted > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
