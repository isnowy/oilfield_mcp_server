"""
导入钻前工程日报数据（drilling_pre_daily.xlsx）到PostgreSQL数据库
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
EXCEL_FILE = "drilling_pre_daily.xlsx"

# 字段映射：Excel列名 -> 数据库字段名
# 第0行是中文名，第1行是英文名（作为列名）
COLUMN_MAPPING = {
    'KTXM': 'ktxm',           # 勘探项目
    'SSND': 'ssnd',           # 实施年度
    'JH': 'jh',               # 井号
    'JWZYSJ': 'jwzysj',       # 井位论证时间
    'JWTJXDSJ': 'jwtjxdsj',   # 井位条件下达时间
    'JWTCLSJ': 'jwtclsj',     # 井位测量时间
    'TZXDSJ': 'tzxdsj',       # 投资下达时间
    'KJCGCWSJ': 'kjcgcwsj',   # 勘界成果完成时间
    'HPSBSJ': 'hpsbsj',       # 环评上报时间
    'YDSQSBSJ': 'ydsqsbsj',   # 用地申请上报时间
    'GCFATLSJ': 'gcfatlsj',   # 工程方案讨论时间
    'ZJDZSJSPSJ': 'zjdzsjspsj', # 钻井地质设计审批时间
    'ZJGCSJSPSJ': 'zjgcsjspsj', # 钻井工程设计审批时间
    'HPXDSJ': 'hpxdsj',       # 环评下达时间
    'ZDCWSJ': 'zdcwsj',       # 征地完成时间
    'TLSKSJ': 'tlsksj',       # 探临开始时间
    'TLJSSJ': 'tljssj',       # 探临结束时间
    'BJKSSJ': 'bjkssj',       # 搬家安装开始时间
    'BJJSSJ': 'bjjssj',       # 搬家安装结束时间
}


def read_excel_data(file_path):
    """读取Excel文件"""
    print(f"📄 读取Excel文件: {file_path}")
    
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return None
    
    try:
        # 第1行（索引1）作为表头（英文列名）
        df = pd.read_excel(file_path, header=1)
        
        # 去除列名空格
        df.columns = df.columns.str.strip()
        
        # 删除第一列（如果是Unnamed或NaN）
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])
        
        # 如果第一列全是NaN，删除
        if df.columns[0] and pd.isna(df.columns[0]):
            df = df.iloc[:, 1:]
        
        print(f"✓ 成功读取 {len(df)} 行数据")
        print(f"✓ 列名: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"❌ 读取Excel失败: {e}")
        import traceback
        traceback.print_exc()
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
    
    # 删除井号前后空格
    df['JH'] = df['JH'].astype(str).str.strip()
    
    # 处理年度字段
    if 'SSND' in df.columns:
        df['SSND'] = pd.to_numeric(df['SSND'], errors='coerce')
    
    # 处理所有日期字段
    date_columns = [col for col in df.columns if col in COLUMN_MAPPING and col.endswith('SJ')]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    print(f"✓ 清洗后保留 {len(df)} 行数据（删除了 {original_count - len(df)} 行）")
    
    return df


def create_table(conn):
    """创建数据表"""
    print("\n📋 创建数据表...")
    
    try:
        with conn.cursor() as cur:
            # 读取并执行schema文件
            schema_file = Path("drilling_pre_daily_schema.sql")
            if schema_file.exists():
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                cur.execute(schema_sql)
                conn.commit()
                print("✓ 数据表创建成功")
            else:
                print("❌ Schema文件不存在")
                return False
                
    except Exception as e:
        print(f"❌ 创建数据表失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def clear_table(conn):
    """清空表数据（可选）"""
    print("\n🗑️  清空现有数据...")
    
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM drilling_pre_daily")
            conn.commit()
            print("✓ 表数据已清空")
    except Exception as e:
        print(f"❌ 清空表数据失败: {e}")
        return False
    
    return True


def import_data(conn, df):
    """导入数据到数据库"""
    print(f"\n📥 导入数据到数据库...")
    
    try:
        # 准备插入数据
        records = []
        for idx, row in df.iterrows():
            record = {}
            for excel_col, db_col in COLUMN_MAPPING.items():
                if excel_col in df.columns:
                    value = row[excel_col]
                    # 处理NaN值
                    if pd.isna(value):
                        record[db_col] = None
                    # 处理Timestamp类型
                    elif isinstance(value, pd.Timestamp):
                        record[db_col] = value.to_pydatetime()
                    else:
                        record[db_col] = value
            records.append(record)
        
        # 构建插入SQL
        if records:
            columns = list(records[0].keys())
            insert_query = sql.SQL(
                "INSERT INTO drilling_pre_daily ({}) VALUES ({})"
            ).format(
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(columns))
            )
            
            # 批量插入
            with conn.cursor() as cur:
                for record in records:
                    values = [record[col] for col in columns]
                    cur.execute(insert_query, values)
            
            conn.commit()
            print(f"✓ 成功导入 {len(records)} 条记录")
            return len(records)
        else:
            print("⚠️  没有数据可导入")
            return 0
            
    except Exception as e:
        conn.rollback()
        print(f"❌ 导入数据失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def check_unmatched_wells(conn):
    """检查哪些井号在oil_wells表中不存在"""
    print("\n🔍 检查井号匹配情况...")
    
    try:
        with conn.cursor() as cur:
            # 查询drilling_pre_daily中不在oil_wells中的井号
            query = """
                SELECT DISTINCT dpd.jh
                FROM drilling_pre_daily dpd
                LEFT JOIN oil_wells ow ON dpd.jh = ow.well_name
                WHERE ow.well_name IS NULL AND dpd.jh IS NOT NULL
                ORDER BY dpd.jh
            """
            cur.execute(query)
            unmatched_wells = cur.fetchall()
            
            if unmatched_wells:
                print(f"\n❌ 发现 {len(unmatched_wells)} 个井号在oil_wells表中不存在:")
                print("=" * 60)
                for idx, (well_name,) in enumerate(unmatched_wells, 1):
                    print(f"{idx:3d}. {well_name}")
                print("=" * 60)
            else:
                print("✅ 所有井号都在oil_wells表中存在！")
            
            # 统计总数
            cur.execute("SELECT COUNT(DISTINCT jh) FROM drilling_pre_daily WHERE jh IS NOT NULL")
            total_wells = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM drilling_pre_daily")
            total_records = cur.fetchone()[0]
            
            print(f"\n📊 统计信息:")
            print(f"  - drilling_pre_daily 总记录数: {total_records}")
            print(f"  - drilling_pre_daily 不同井号数: {total_wells}")
            print(f"  - 未匹配井号数: {len(unmatched_wells)}")
            print(f"  - 匹配率: {(total_wells - len(unmatched_wells)) / total_wells * 100:.2f}%")
            
            return unmatched_wells
            
    except Exception as e:
        print(f"❌ 检查井号匹配失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("=" * 80)
    print("钻前工程日报数据导入工具")
    print("=" * 80)
    
    # 1. 读取Excel数据
    df = read_excel_data(EXCEL_FILE)
    if df is None:
        return
    
    # 2. 清洗和验证数据
    df = clean_and_validate_data(df)
    if df is None or len(df) == 0:
        print("❌ 没有有效数据可导入")
        return
    
    # 3. 连接数据库
    print("\n🔌 连接数据库...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    try:
        # 4. 创建数据表
        if not create_table(conn):
            return
        
        # 5. 清空现有数据（可选）
        user_input = input("\n是否清空现有数据？(y/n, 默认y): ").strip().lower()
        if user_input != 'n':
            if not clear_table(conn):
                return
        
        # 6. 导入数据
        imported_count = import_data(conn, df)
        
        if imported_count > 0:
            # 7. 检查井号匹配情况
            check_unmatched_wells(conn)
        
        print("\n" + "=" * 80)
        print("✅ 导入完成！")
        print("=" * 80)
        
    finally:
        conn.close()
        print("\n🔒 数据库连接已关闭")


if __name__ == "__main__":
    main()
