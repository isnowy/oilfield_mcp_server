"""
测试真实数据库MCP服务器
验证PostgreSQL数据库连接和数据查询
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rag',
    'user': 'postgres',
    'password': 'postgres'
}

def test_database_connection():
    """测试1: 数据库连接"""
    print("=" * 60)
    print("【测试1】数据库连接测试")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # 检查oil_wells表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'oil_wells'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ oil_wells表存在")
            
            # 查询数据量
            cursor.execute("SELECT COUNT(*) as count FROM oil_wells WHERE is_deleted = false")
            count = cursor.fetchone()['count']
            print(f"✅ 数据库连接成功")
            print(f"📊 当前有 {count} 口井的数据")
            
            if count == 0:
                print("\n⚠️  警告：数据库中没有数据！")
                print("   请先运行以下命令导入数据：")
                print("   1. python setup_oil_wells_table.py  # 创建表")
                print("   2. python import_well_data.py       # 导入数据")
                cursor.close()
                conn.close()
                return False
            
            # 显示部分数据样例
            cursor.execute("""
                SELECT well_name, qk, jx, sjjs 
                FROM oil_wells 
                WHERE is_deleted = false 
                LIMIT 5
            """)
            samples = cursor.fetchall()
            
            print("\n📝 数据样例（前5条）：")
            print("-" * 60)
            for row in samples:
                print(f"  井名: {row['well_name']:<15} 区块: {row['qk']:<10} "
                      f"井型: {row['jx']:<10} 设计井深: {row['sjjs']}")
            print("-" * 60)
            
        else:
            print("❌ oil_wells表不存在")
            print("   请先运行: python setup_oil_wells_table.py")
            cursor.close()
            conn.close()
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n可能的原因：")
        print("  1. PostgreSQL服务未启动")
        print("  2. 数据库配置不正确")
        print("  3. 数据库'rag'不存在")
        return False

def test_mcp_server(port, server_name):
    """测试MCP服务器HTTP端点"""
    print(f"\n{'=' * 60}")
    print(f"【测试2】{server_name} HTTP端点测试")
    print("=" * 60)
    
    base_url = f"http://localhost:{port}"
    
    # 测试根路径
    print(f"\n1️⃣ 测试根路径: {base_url}/")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 服务器运行正常")
            print(f"   服务: {data.get('service')}")
            print(f"   版本: {data.get('version')}")
            print(f"   状态: {data.get('status')}")
        else:
            print(f"⚠️  状态码: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务器")
        print(f"   请先启动服务器:")
        if port == 8080:
            print(f"   运行: .\\start_real_server.ps1 或 start_real_server.bat")
        else:
            print(f"   运行: .\\start_true_server.ps1 或 start_true_server.bat")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False
    
    # 测试健康检查
    print(f"\n2️⃣ 测试健康检查: {base_url}/health")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过")
            print(f"   状态: {data.get('status')}")
            print(f"   数据库: {data.get('database')}")
        else:
            print(f"⚠️  健康检查失败")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
    
    # 测试SSE端点
    print(f"\n3️⃣ 测试SSE端点: {base_url}/sse")
    try:
        response = requests.head(f"{base_url}/sse", timeout=5)
        if response.status_code == 200:
            print(f"✅ SSE端点可用")
        else:
            print(f"⚠️  SSE端点状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ SSE端点测试失败: {e}")
    
    return True

def test_mcp_tools(port, server_name):
    """测试MCP工具调用"""
    print(f"\n{'=' * 60}")
    print(f"【测试3】{server_name} 工具调用测试")
    print("=" * 60)
    
    base_url = f"http://localhost:{port}/sse"
    
    # 测试tools/list
    print(f"\n1️⃣ 测试工具列表")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Role": "ADMIN",
            "X-User-Email": "test@example.com",
            "X-User-ID": "test123"
        }
        
        response = requests.post(base_url, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'tools' in data['result']:
                tools = data['result']['tools']
                print(f"✅ 获取到 {len(tools)} 个工具:")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool['description'][:50]}...")
            else:
                print(f"⚠️  响应格式不正确: {data}")
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 工具列表测试失败: {e}")
        return False
    
    # 测试实际工具调用 - 搜索油井
    print(f"\n2️⃣ 测试工具调用 - 搜索油井")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search_wells" if port == 8080 else "search_wells",
                "arguments": {
                    "keyword": "",  # 空字符串获取所有井
                    "limit": 5
                }
            }
        }
        
        response = requests.post(base_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'content' in data['result']:
                content = data['result']['content'][0]['text']
                print(f"✅ 工具调用成功")
                print(f"\n返回内容（前500字符）：")
                print("-" * 60)
                print(content[:500])
                print("-" * 60)
            else:
                print(f"⚠️  响应格式不正确")
        else:
            print(f"❌ 工具调用失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 工具调用测试失败: {e}")
        return False
    
    return True

def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("🚀 真实数据库MCP服务器测试")
    print("=" * 60)
    print()
    
    # 步骤1: 测试数据库连接
    if not test_database_connection():
        print("\n❌ 数据库测试失败，请先解决数据库问题")
        return
    
    print("\n✅ 数据库测试通过！\n")
    input("按Enter继续测试MCP服务器（请确保服务器已启动）...")
    
    # 步骤2: 测试8080端口服务器（可选）
    print("\n是否测试8080端口服务器（主服务器真实数据模式）？")
    test_8080 = input("输入 y 测试，其他键跳过: ").lower() == 'y'
    
    if test_8080:
        if test_mcp_server(8080, "主服务器(8080)"):
            test_mcp_tools(8080, "主服务器(8080)")
    
    # 步骤3: 测试8081端口服务器
    print("\n是否测试8081端口服务器（真实数据专用服务器）？")
    test_8081 = input("输入 y 测试，其他键跳过: ").lower() == 'y'
    
    if test_8081:
        if test_mcp_server(8081, "真实数据专用服务器(8081)"):
            test_mcp_tools(8081, "真实数据专用服务器(8081)")
    
    # 测试总结
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print("\n📌 下一步：")
    print("  1. 在LibreChat中配置MCP服务器")
    print("  2. 使用以下URL:")
    print("     - 主服务器: http://localhost:8080/sse")
    print("     - 专用服务器: http://localhost:8081/sse")
    print("  3. 设置HTTP Headers:")
    print("     - X-User-Role: ADMIN")
    print("     - X-User-Email: your@email.com")
    print()

if __name__ == "__main__":
    main()
