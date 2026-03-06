"""
数据库连接管理模块
提供统一的数据库连接和查询接口
"""
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# 数据库配置 - 从环境变量读取
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'rag'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def get_db_connection():
    """获取PostgreSQL数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def test_db_connection():
    """测试数据库连接"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM oil_wells")
        result = cursor.fetchone()
        count = result['count']
        cursor.close()
        conn.close()
        logger.info(f"✅ 数据库连接成功，共有 {count} 口井")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接测试失败: {e}")
        return False

def execute_query(query: str, params: tuple = None):
    """
    执行数据库查询
    
    Args:
        query: SQL查询语句
        params: 查询参数
        
    Returns:
        查询结果列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        return [dict(row) for row in results]
    finally:
        cursor.close()
        conn.close()
