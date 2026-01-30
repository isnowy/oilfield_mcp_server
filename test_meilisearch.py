#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Meilisearch 连接和功能测试脚本
"""

try:
    import meilisearch
    print("✓ meilisearch 已安装")
except ImportError:
    print("✗ meilisearch 未安装")
    print("请运行: pip install meilisearch")
    exit(1)

import time
from datetime import datetime

def test_meilisearch():
    """测试 Meilisearch 连接和基本功能"""
    print("\n=== Meilisearch 连接测试 ===\n")
    
    try:
        # 连接 Meilisearch
        print("正在连接到 Meilisearch (http://localhost:7700)...")
        client = meilisearch.Client('http://localhost:7700')
        
        # 检查健康状态
        health = client.health()
        print(f"✓ Meilisearch 连接成功！状态: {health['status']}")
        
        # 获取版本信息
        version = client.get_version()
        print(f"\nMeilisearch 版本: {version['pkgVersion']}")
        
        # 列出现有索引
        print("\n当前索引列表:")
        indexes = client.get_indexes()
        if indexes['results']:
            for idx in indexes['results']:
                print(f"  - {idx.uid} ({idx.primary_key or 'no primary key'})")
        else:
            print("  (无索引)")
        
        # 测试创建索引和文档操作
        print("\n正在测试索引操作...")
        index_uid = 'test_oilfield'
        
        # 删除可能存在的旧测试索引
        try:
            client.delete_index(index_uid)
            time.sleep(0.5)
        except:
            pass
        
        # 创建新索引
        task = client.create_index(index_uid, {'primaryKey': 'id'})
        print(f"✓ 创建索引 '{index_uid}'")
        
        # 等待任务完成
        time.sleep(1)
        
        # 获取索引对象
        index = client.index(index_uid)
        
        # 准备测试文档
        documents = [
            {
                'id': 1,
                'well_name': 'A1井',
                'depth': 3500.5,
                'status': '钻进',
                'location': '渤海湾',
                'description': '油田A区块主力井，日产油量稳定'
            },
            {
                'id': 2,
                'well_name': 'B2井',
                'depth': 4200.8,
                'status': '完井',
                'location': '东海',
                'description': '深海探井，发现优质油层'
            },
            {
                'id': 3,
                'well_name': 'C3井',
                'depth': 2800.3,
                'status': '生产',
                'location': '塔里木',
                'description': '老井改造后恢复生产'
            }
        ]
        
        # 添加文档
        task = index.add_documents(documents)
        print(f"✓ 添加 {len(documents)} 个测试文档")
        
        # 等待索引完成
        time.sleep(2)
        
        # 配置可搜索属性
        index.update_searchable_attributes([
            'well_name', 'status', 'location', 'description'
        ])
        time.sleep(0.5)
        
        # 测试搜索
        print("\n测试搜索功能:")
        
        # 搜索 1: 按井名
        results = index.search('A1井')
        print(f"\n  搜索 'A1井': 找到 {results['estimatedTotalHits']} 个结果")
        if results['hits']:
            print(f"    → {results['hits'][0]['well_name']} - {results['hits'][0]['status']}")
        
        # 搜索 2: 按状态
        results = index.search('生产')
        print(f"\n  搜索 '生产': 找到 {results['estimatedTotalHits']} 个结果")
        for hit in results['hits']:
            print(f"    → {hit['well_name']} - {hit['status']}")
        
        # 搜索 3: 按描述内容
        results = index.search('油层')
        print(f"\n  搜索 '油层': 找到 {results['estimatedTotalHits']} 个结果")
        for hit in results['hits']:
            print(f"    → {hit['well_name']} - {hit['description']}")
        
        # 测试过滤
        print("\n测试过滤功能:")
        index.update_filterable_attributes(['status', 'depth'])
        time.sleep(0.5)
        
        results = index.search('', {
            'filter': 'depth > 3000'
        })
        print(f"\n  过滤 'depth > 3000': 找到 {len(results['hits'])} 个结果")
        for hit in results['hits']:
            print(f"    → {hit['well_name']} - 深度: {hit['depth']}m")
        
        # 获取统计信息
        print("\n索引统计:")
        stats = index.get_stats()
        print(f"  文档数量: {stats['numberOfDocuments']}")
        print(f"  索引中: {stats.get('isIndexing', False)}")
        
        # 清理测试数据
        print("\n清理测试数据...")
        client.delete_index(index_uid)
        print("✓ 已删除测试索引")
        
        print("\n=== 所有测试通过！===")
        print("Meilisearch 已准备就绪，可以在项目中使用。")
        
        return True
        
    except meilisearch.errors.MeilisearchCommunicationError as e:
        print(f"\n✗ 无法连接到 Meilisearch: {e}")
        print("\n请检查:")
        print("1. Meilisearch 是否正在运行")
        print("   启动命令: meilisearch --db-path=data.ms --http-addr=127.0.0.1:7700")
        print("2. 端口 7700 是否可访问")
        print("3. 防火墙设置")
        return False
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_meilisearch()
