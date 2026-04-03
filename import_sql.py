"""
导入 SQL 文件到 PostgreSQL 数据库
使用 subprocess 调用 psql.exe，避免 GBK/UTF8 编码冲突
"""
import os
import sys
import subprocess

PSQL = r'C:\Program Files\PostgreSQL\18\bin\psql.exe'
SQL_FILE = r'C:\Users\10211\Desktop\q.sql'

HOST = '127.0.0.1'
PORT = '5432'
USER = 'postgres'
PASSWORD = '33123'
DB = 'rag'


def run_psql(database, sql, label=''):
    """执行一条 SQL，返回 (returncode, stdout, stderr)"""
    env = os.environ.copy()
    env['PGPASSWORD'] = PASSWORD

    result = subprocess.run(
        [PSQL, '-U', USER, '-h', HOST, '-p', PORT, '-d', database,
         '-c', sql, '-X', '-A', '-t'],
        env=env,
        capture_output=True,
    )
    stdout = result.stdout.decode('utf-8', errors='replace').strip()
    stderr = result.stderr.decode('gbk', errors='replace').strip()
    if label:
        if result.returncode != 0:
            print(f"  ❌ {label}: {stderr}")
        else:
            print(f"  ✅ {label}")
    return result.returncode, stdout, stderr


def run_psql_file(database, sql_file):
    """用 psql -f 执行整个 SQL 文件"""
    env = os.environ.copy()
    env['PGPASSWORD'] = PASSWORD

    result = subprocess.run(
        [PSQL, '-U', USER, '-h', HOST, '-p', PORT, '-d', database,
         '-f', sql_file, '-X',
         '--set', 'ON_ERROR_STOP=0',   # 遇到错误继续执行
         '-v', 'VERBOSITY=default'],
        env=env,
        capture_output=True,
    )
    stdout = result.stdout.decode('utf-8', errors='replace')
    stderr = result.stderr.decode('gbk', errors='replace')
    return result.returncode, stdout, stderr


def ensure_db_exists():
    rc, out, err = run_psql('postgres',
        "SELECT 1 FROM pg_database WHERE datname='rag'")
    if rc != 0:
        print(f"❌ 连接失败: {err}")
        sys.exit(1)
    if out.strip() == '1':
        print("✅ 数据库 rag 已存在")
    else:
        print("创建数据库 rag ...")
        rc2, _, err2 = run_psql('postgres',
            "CREATE DATABASE rag ENCODING 'UTF8' LC_COLLATE 'Chinese (Simplified)_China.936' LC_CTYPE 'Chinese (Simplified)_China.936' TEMPLATE template0",
            '创建 rag 数据库')
        if rc2 != 0:
            # 如果指定 locale 失败，尝试默认
            rc3, _, err3 = run_psql('postgres',
                "CREATE DATABASE rag ENCODING 'UTF8'", '创建 rag 数据库(默认locale)')
            if rc3 != 0:
                print(f"❌ 创建数据库失败: {err3}")
                sys.exit(1)


def ensure_vector_extension():
    rc, _, err = run_psql(DB,
        "CREATE EXTENSION IF NOT EXISTS vector", 'pgvector 扩展')
    if rc != 0:
        print(f"  ⚠️  pgvector 未安装，langchain_pg_embedding 表可能导入失败")
        print(f"     可手动安装: https://github.com/pgvector/pgvector")


def ensure_trigger_function():
    """确保 update_updated_at_column 函数存在"""
    sql = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
"""
    rc, _, err = run_psql(DB, sql, 'update_updated_at_column 函数')


if __name__ == '__main__':
    print("=" * 60)
    print("导入 SQL 文件到 PostgreSQL")
    print(f"文件: {SQL_FILE}")
    print(f"目标: {USER}@{HOST}:{PORT}/{DB}")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"❌ 文件不存在: {SQL_FILE}")
        sys.exit(1)

    if not os.path.exists(PSQL):
        print(f"❌ psql 不存在: {PSQL}")
        sys.exit(1)

    # 步骤1: 确保数据库存在
    ensure_db_exists()

    # 步骤2: 安装 pgvector 扩展（用于 langchain_pg_embedding）
    ensure_vector_extension()

    # 步骤3: 创建触发器函数（各表的触发器依赖它）
    ensure_trigger_function()

    # 步骤4: 导入 SQL 文件
    print(f"\n开始导入 {SQL_FILE} ...")
    rc, stdout, stderr = run_psql_file(DB, SQL_FILE)

    # 打印输出
    if stdout:
        print(stdout)
    if stderr:
        # 过滤掉 NOTICE 级别（仅打印警告和错误）
        lines = [l for l in stderr.splitlines()
                 if not l.startswith('NOTICE') and l.strip()]
        if lines:
            print('\n'.join(lines))

    print("\n" + "=" * 60)
    if rc == 0:
        print("✅ SQL 文件导入完成")
    else:
        print(f"⚠️  导入过程中有部分错误（退出码={rc}），请查看上方输出")
    print("=" * 60)

    # 步骤5: 验证结果
    print("\n验证导入结果:")
    tables = ['oil_wells', 'drilling_daily', 'key_well_daily',
              'workover_records', 'perforation_records', 'well_analysis',
              'wellbore_diagrams', 'wellbore_structure_sections',
              'drilling_pre_daily']
    for t in tables:
        rc2, out2, _ = run_psql(DB, f"SELECT COUNT(*) FROM {t}")
        status = f"{out2} 行" if rc2 == 0 else "❌ 不存在"
        print(f"  {t}: {status}")
