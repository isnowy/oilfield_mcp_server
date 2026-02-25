"""
Excel数据导入PostgreSQL脚本
用于将油井Excel数据批量导入到数据库
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WellDataImporter:
    """油井数据导入器"""
    
    def __init__(self, db_config):
        """
        初始化数据库连接
        
        Args:
            db_config: 数据库配置字典
                {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'rag',
                    'user': 'postgres',
                    'password': 'postgres'
                }
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def read_excel(self, file_path, sheet_name=0):
        """
        读取Excel文件
        
        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称或索引
            
        Returns:
            DataFrame: 读取的数据
        """
        try:
            # 定义字段映射 (Excel列名 -> 数据库字段名)
            # JH（井号）作为well_name使用，因为它是唯一标识
            column_mapping = {
                'JH': 'well_name',  # 井号作为井名/唯一标识
                'KTXMLB': 'ktxmlb',
                'KTXM': 'ktxm',
                'KTZXM': 'ktzxm',
                'QK': 'qk',
                'QKDM': 'qkdm',
                'CW': 'cw',
                'JX': 'jx',
                'JB': 'jb',
                'SFZDJ': 'sfzdj',
                'SJRQ': 'sjrq',
                'SJJS': 'sjjs',
                'SJZZBX': 'sjzzbx',
                'SJHZBY': 'sjhzby',
                'SJMDC': 'sjmdc',
                'SJWZCW': 'sjwzcw',
                'ZTMD': 'ztmd',
                'WZYZ': 'wzyz',
                'DMHB': 'dmhb',
                'SS': 'ss',
                'SYWZ': 'sywz',
                'JPDZCX1': 'jpdzcx1',
                'JPDZCX2': 'jpdzcx2',
                'ZH1': 'zh1',
                'ZH2': 'zh2',
                'DCXJL1': 'dcxjl1',
                'DCXJL2': 'dcxjl2',
                'HTQH': 'htqh',
                'CZR': 'czr',
                'LRR': 'lrr',
                'BZ': 'bz'
            }
            
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=0, skiprows=[1])
            
            # 重命名列
            df = df.rename(columns=column_mapping)
            
            # 只保留映射后的列
            available_columns = [col for col in column_mapping.values() if col in df.columns]
            df = df[available_columns]
            
            # 移除第一列（Unnamed:0）如果存在
            if 'Unnamed: 0' in df.columns:
                df = df.drop(columns=['Unnamed: 0'])
            
            logger.info(f"成功读取Excel文件，共 {len(df)} 行有效数据")
            return df
            
        except Exception as e:
            logger.error(f"读取Excel文件失败: {e}")
            raise
    
    def clean_data(self, df):
        """
        清洗数据
        
        Args:
            df: 原始DataFrame
            
        Returns:
            DataFrame: 清洗后的数据
        """
        # 处理日期格式
        if 'sjrq' in df.columns:
            df['sjrq'] = pd.to_datetime(df['sjrq'], errors='coerce')
        
        # 确保数值字段为正确类型
        numeric_fields = ['sjjs', 'sjzzbx', 'sjhzby', 'dmhb', 'zh1', 'zh2', 'dcxjl1', 'dcxjl2']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')
        
        # 将所有NaN和NaT替换为None（关键步骤）
        df = df.astype(object).where(pd.notnull(df), None)
        
        # 再次过滤：移除well_name为None或空字符串的行
        if 'well_name' in df.columns:
            original_count = len(df)
            df = df[df['well_name'].notna()]
            df = df[df['well_name'] != '']
            df = df[df['well_name'] != None]
            removed_count = original_count - len(df)
            if removed_count > 0:
                logger.info(f"过滤掉 {removed_count} 行无效数据（well_name为空）")
        logger.info(f"数据清洗完成，剩余 {len(df)} 行有效数据")
        return df
    
    def insert_data(self, df):
        """
        批量插入数据到数据库
        
        Args:
            df: 要插入的DataFrame
        """
        try:
            # 准备插入语句
            columns = df.columns.tolist()
            
            # 构建SQL语句（无ON CONFLICT，允许重复井号）
            insert_query = f"""
                INSERT INTO oil_wells ({', '.join(columns)})
                VALUES %s
            """
            
            # 准备数据
            values = [tuple(row) for row in df.values]
            
            # 批量插入
            execute_values(self.cursor, insert_query, values)
            self.conn.commit()
            
            logger.info(f"成功插入/更新 {len(df)} 条数据")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"数据插入失败: {e}")
            raise
    
    def import_from_excel(self, excel_path, sheet_name=0):
        """
        从Excel导入数据的完整流程
        
        Args:
            excel_path: Excel文件路径
            sheet_name: 工作表名称或索引
        """
        try:
            self.connect()
            
            # 读取数据
            df = self.read_excel(excel_path, sheet_name)
            
            # 清洗数据
            df = self.clean_data(df)
            
            # 插入数据
            self.insert_data(df)
            
            logger.info("数据导入完成！")
            
        except Exception as e:
            logger.error(f"数据导入过程出错: {e}")
            raise
        finally:
            self.close()


def main():
    """主函数示例"""
    
    # 数据库配置 - 连接到rag数据库
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'rag',
        'user': 'postgres',
        'password': 'postgres'
    }
    
    # Excel文件路径
    excel_path = r'D:\work\oilMCP\well_data.xlsx'
    
    # 创建导入器并执行导入
    importer = WellDataImporter(db_config)
    importer.import_from_excel(excel_path, sheet_name=0)


if __name__ == '__main__':
    main()
