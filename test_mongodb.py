yun#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MongoDB 连接测试脚本
"""

try:
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi
    print("✓ pymongo 已安装")
except ImportError:
    print("✗ pymongo 未安装")
    print("请运行: pip install pymongo")
    exit(1)

def test_mongodb_connection():
    """测试 MongoDB 连接"""
    print("\n=== MongoDB 连接测试 ===\n")
    
    try:
        # 连接本地 MongoDB
        print("正在连接到 MongoDB (localhost:27017)...")
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        
        # 测试连接
        client.admin.command('ping')
        print("✓ MongoDB 连接成功！")
        
        # 获取服务器信息
        server_info = client.server_info()
        print(f"\nMongoDB 版本: {server_info['version']}")
        
        # 列出数据库
        print("\n当前数据库列表:")
        databases = client.list_database_names()
        for db in databases:
            print(f"  - {db}")
        
        # 测试创建数据库和集合
        print("\n正在测试数据库操作...")
        test_db = client['test_oilfield']
        test_collection = test_db['test_collection']
        
        # 插入测试文档
        test_doc = {"name": "test", "type": "connection_test", "timestamp": "2026-01-28"}
        result = test_collection.insert_one(test_doc)
        print(f"✓ 成功插入测试文档，ID: {result.inserted_id}")
        
        # 查询测试文档
        found_doc = test_collection.find_one({"_id": result.inserted_id})
        print(f"✓ 成功查询测试文档: {found_doc}")
        
        # 删除测试文档
        test_collection.delete_one({"_id": result.inserted_id})
        print("✓ 成功删除测试文档")
        
        # 删除测试数据库
        client.drop_database('test_oilfield')
        print("✓ 已清理测试数据库")
        
        print("\n=== 所有测试通过！===")
        print("MongoDB 已准备就绪，可以在项目中使用。")
        
        return True
        
    except Exception as e:
        print(f"\n✗ MongoDB 连接失败: {e}")
        print("\n请检查:")
        print("1. MongoDB 服务是否正在运行")
        print("   - 检查服务: Get-Service MongoDB")
        print("   - 启动服务: Start-Service MongoDB")
        print("2. 防火墙是否阻止了 27017 端口")
        print("3. MongoDB 配置文件是否正确")
        return False
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    test_mongodb_connection()
