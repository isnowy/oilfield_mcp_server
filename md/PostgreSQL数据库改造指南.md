# PostgreSQL 数据库改造指南

本文档详细说明如何将 `oilfield_mcp_server.py` 从内存SQLite数据库改造为使用真实的PostgreSQL数据库。

## 📋 目录

1. [改动概览](#改动概览)
2. [依赖配置修改](#依赖配置修改)
3. [数据库配置文件](#数据库配置文件)
4. [代码修改清单](#代码修改清单)
5. [数据迁移方案](#数据迁移方案)
6. [PostgreSQL数据库准备](#postgresql数据库准备)
7. [测试验证](#测试验证)
8. [生产部署注意事项](#生产部署注意事项)

---

## 改动概览

### 需要修改的文件

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `requirements.txt` | 新增依赖 | 添加PostgreSQL驱动 |
| `oilfield_mcp_server.py` | 核心修改 | 数据库连接、配置加载、数据初始化 |
| `db_config.json` | 新增文件 | 数据库连接配置（不提交到版本控制） |
| `.env` | 新增文件 | 数据库敏感信息（不提交到版本控制） |
| `.gitignore` | 更新 | 排除敏感配置文件 |
| `data_migration.py` | 新增文件（可选） | 将模拟数据导入真实数据库 |

---

## 依赖配置修改

### 1. 修改 `requirements.txt`

**当前内容：**

```txt
# Core framework
fastmcp>=0.2.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Database
sqlalchemy>=2.0.0

# Data processing
pandas>=2.0.0
tabulate>=0.9.0

# Logging and utilities
python-dateutil>=2.8.0
```

**需要添加的新依赖：**

```txt
# Core framework
fastmcp>=0.2.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0        # ← 新增：PostgreSQL驱动
python-dotenv>=1.0.0          # ← 新增：环境变量管理

# Data processing
pandas>=2.0.0
tabulate>=0.9.0

# Logging and utilities
python-dateutil>=2.8.0
```

**安装命令：**

```bash
pip install psycopg2-binary python-dotenv
```

---

## 数据库配置文件

### 2. 新建 `.env` 文件（根目录）

用于存储敏感的数据库连接信息，**不提交到版本控制**。

```env
# PostgreSQL 数据库连接配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=oilfield_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# 应用配置
DEV_MODE=false
LOG_LEVEL=INFO

# 连接池配置（可选）
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

### 3. 新建 `db_config.example.json`（示例配置）

用于团队参考，可以提交到版本控制。

```json
{
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "oilfield_db",
    "user": "postgres",
    "password": "使用 .env 文件配置",
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "echo_sql": false
  },
  "app": {
    "dev_mode": false,
    "log_level": "INFO"
  }
}
```

### 4. 更新 `.gitignore`

确保敏感配置不被提交到版本控制：

```gitignore
# 环境配置
.env
db_config.json

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
.venv/

# IDE
.vscode/
.idea/

# 数据库
*.db
*.sqlite
*.sqlite3
```

---

## 代码修改清单

### 5. 修改 `oilfield_mcp_server.py`

#### 5.1 添加配置加载功能（文件开头部分）

**位置：** 第 1-20 行附近，导入部分之后

**当前代码：**

```python
import os
import re
import time
import json
import logging
import functools
import pandas as pd
from typing import List, Optional, Literal, Dict, Any
from datetime import date, datetime, timedelta
from fastmcp import FastMCP, Context
from pydantic import Field
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
```

**修改为：**

```python
import os
import re
import time
import json
import logging
import functools
import pandas as pd
from typing import List, Optional, Literal, Dict, Any
from datetime import date, datetime, timedelta
from fastmcp import FastMCP, Context
from pydantic import Field
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv  # ← 新增

# 加载环境变量
load_dotenv()  # ← 新增
```

#### 5.2 添加数据库配置类

**位置：** 第 22-29 行附近，日志配置之后

**添加以下代码：**

```python
# ==========================================
# 数据库配置加载
# ==========================================

class DatabaseConfig:
    """数据库配置管理类"""
    
    @staticmethod
    def load_from_env() -> Dict[str, Any]:
        """从环境变量加载数据库配置"""
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "oilfield_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "echo_sql": os.getenv("DB_ECHO_SQL", "false").lower() == "true"
        }
    
    @staticmethod
    def build_connection_string(config: Dict[str, Any]) -> str:
        """构建PostgreSQL连接字符串"""
        return (
            f"postgresql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
```

#### 5.3 修改数据库连接部分

**位置：** 第 224-231 行，数据库初始化部分

**当前代码（第 228-231 行）：**

```python
# 使用内存数据库（生产环境替换为实际数据库连接）
engine = create_engine('sqlite:///:memory:', echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
```

**修改为：**

```python
# ==========================================
# 数据库连接初始化
# ==========================================

def init_database():
    """初始化数据库连接"""
    try:
        # 加载数据库配置
        db_config = DatabaseConfig.load_from_env()
        connection_string = DatabaseConfig.build_connection_string(db_config)
        
        logger.info(f"正在连接数据库: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # 创建数据库引擎
        global engine, Session
        engine = create_engine(
            connection_string,
            pool_size=db_config['pool_size'],
            max_overflow=db_config['max_overflow'],
            pool_timeout=db_config['pool_timeout'],
            echo=db_config['echo_sql'],
            pool_pre_ping=True,  # 连接前检查有效性
            pool_recycle=3600    # 每小时回收连接
        )
        
        # 创建会话工厂
        Session = sessionmaker(bind=engine)
        
        # 创建所有表（如果不存在）
        Base.metadata.create_all(engine)
        
        logger.info("✅ 数据库连接成功，表结构已初始化")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise

# 初始化数据库
init_database()
```

#### 5.4 修改模拟数据函数（可选）

**位置：** 第 233-371 行，`seed_mock_data()` 函数

**方案 A：保留用于开发环境**

```python
def seed_mock_data():
    """注入模拟数据（仅用于开发和测试环境）"""
    # 检查是否已有数据
    session = Session()
    try:
        existing_count = session.query(Well).count()
        if existing_count > 0:
            logger.info(f"数据库已有 {existing_count} 口井的数据，跳过模拟数据注入")
            return
        
        logger.info("开始注入模拟数据...")
        
        # 创建井信息
        wells = [
            Well(id="ZT-102", name="中塔-102", block="Block-A", target_depth=4500, 
                 spud_date=date(2023, 10, 1), status="Active", well_type="Horizontal",
                 team="Team-701", rig="Rig-50"),
            # ... 其他井数据保持不变 ...
        ]
        session.add_all(wells)
        
        # ... 其余模拟数据代码保持不变 ...
        
        session.commit()
        logger.info("✅ Mock data seeded successfully.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error seeding data: {e}")
        raise
    finally:
        session.close()


# 仅在开发模式下初始化模拟数据
if DEV_MODE:
    logger.info("🔓 开发模式：注入模拟数据")
    seed_mock_data()
else:
    logger.info("🔒 生产模式：使用真实数据库")
```

**方案 B：完全移除（生产环境推荐）**

```python
# 删除 seed_mock_data() 函数
# 删除第 371 行的 seed_mock_data() 调用
# 生产环境中数据由真实业务系统录入
```

#### 5.5 添加健康检查工具（可选但推荐）

**位置：** 在 MCP 工具定义部分（第 830 行之前）

**添加以下代码：**

```python
@mcp.tool()
@AuditLog.trace("database_health_check")
def database_health_check() -> str:
    """
    [场景] 检查数据库连接状态和数据概览
    [关键词] 健康检查、连接状态、系统状态
    """
    session = Session()
    try:
        # 测试连接
        session.execute("SELECT 1")
        
        # 统计数据
        well_count = session.query(Well).count()
        report_count = session.query(DailyReport).count()
        npt_count = session.query(NPTEvent).count()
        
        # 最新日报日期
        latest_report = session.query(DailyReport)\
            .order_by(DailyReport.report_date.desc())\
            .first()
        
        latest_date = latest_report.report_date if latest_report else "无数据"
        
        return f"""
### ✅ 数据库健康检查

**连接状态**: 正常

**数据统计**:
- 井数量: {well_count} 口
- 日报记录: {report_count} 条
- NPT事件: {npt_count} 条
- 最新日报日期: {latest_date}

**数据库信息**:
- 类型: PostgreSQL
- 连接池: {engine.pool.size()} / {engine.pool.overflow()}
"""
    except Exception as e:
        return f"❌ 数据库连接失败: {str(e)}"
    finally:
        session.close()
```

#### 5.6 改进错误处理（数据库连接相关）

在每个数据库操作的 `try-except` 块中，添加连接重试逻辑（可选）：

```python
from sqlalchemy.exc import OperationalError, DBAPIError

def with_retry(max_retries=3, delay=1):
    """数据库操作重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DBAPIError) as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"数据库操作失败，重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(delay * (attempt + 1))
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例：
@mcp.tool()
@AuditLog.trace("get_well_summary")
@with_retry(max_retries=3, delay=1)  # ← 添加重试逻辑
def get_well_summary(well_id: str, user_role: str = "default") -> str:
    # ... 原有代码 ...
```

---

## 数据迁移方案

### 6. 创建数据迁移脚本（可选）

如果需要将模拟数据导入PostgreSQL进行测试，创建 `data_migration.py`：

```python
"""
数据迁移脚本：将模拟数据导入 PostgreSQL 数据库
运行命令: python data_migration.py
"""

import os
from datetime import date, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 加载环境变量
load_dotenv()

# 导入数据模型
from oilfield_mcp_server import Base, Well, DailyReport, NPTEvent, CasingProgram

def migrate_data():
    """执行数据迁移"""
    # 构建连接字符串
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "oilfield_db")
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print(f"连接数据库: {db_host}:{db_port}/{db_name}")
    
    # 创建引擎
    engine = create_engine(connection_string, echo=False)
    Session = sessionmaker(bind=engine)
    
    # 创建表结构
    print("创建表结构...")
    Base.metadata.create_all(engine)
    
    session = Session()
    
    try:
        # 检查是否已有数据
        existing_count = session.query(Well).count()
        if existing_count > 0:
            print(f"⚠️  数据库已有 {existing_count} 口井的数据")
            response = input("是否清空并重新导入？(yes/no): ")
            if response.lower() != 'yes':
                print("取消迁移")
                return
            
            # 清空数据
            print("清空现有数据...")
            session.query(NPTEvent).delete()
            session.query(CasingProgram).delete()
            session.query(DailyReport).delete()
            session.query(Well).delete()
            session.commit()
        
        print("开始导入模拟数据...")
        
        # 创建井信息
        wells = [
            Well(id="ZT-102", name="中塔-102", block="Block-A", target_depth=4500, 
                 spud_date=date(2023, 10, 1), status="Active", well_type="Horizontal",
                 team="Team-701", rig="Rig-50"),
            Well(id="ZT-105", name="中塔-105", block="Block-A", target_depth=4200,
                 spud_date=date(2023, 10, 5), status="Active", well_type="Vertical",
                 team="Team-702", rig="Rig-51"),
            Well(id="ZT-108", name="中塔-108", block="Block-A", target_depth=5000,
                 spud_date=date(2023, 9, 20), status="Completed", well_type="Directional",
                 team="Team-701", rig="Rig-50"),
            Well(id="XY-009", name="新疆-009", block="Block-B", target_depth=5500,
                 spud_date=date(2023, 9, 15), status="Active", well_type="Horizontal",
                 team="Team-808", rig="Rig-88"),
        ]
        session.add_all(wells)
        print(f"✓ 导入 {len(wells)} 口井")
        
        # 创建日报数据
        base_date = date(2023, 11, 1)
        report_count = 0
        
        # ZT-102: 10天数据
        for i in range(10):
            report_date = base_date + timedelta(days=i)
            is_npt_day = (i == 5)
            
            progress = 50 if is_npt_day else 150
            current_depth = 3000 + sum([50 if j == 5 else 150 for j in range(i + 1)])
            
            r = DailyReport(
                well_id="ZT-102",
                report_date=report_date,
                report_no=25 + i,
                current_depth=current_depth,
                progress=progress,
                mud_density=1.25 if i < 5 else 1.28,
                mud_viscosity=55 + i * 0.5,
                mud_ph=9.5,
                avg_rop=25.0 if not is_npt_day else 8.0,
                bit_number=3 if i < 7 else 4,
                operation_summary=f"钻进8.5寸井段，{'遇井漏，循环压井' if is_npt_day else '作业正常'}。当前井深{current_depth}米。",
                next_plan="继续钻进" if not is_npt_day else "观察井况，准备处理井漏"
            )
            
            if is_npt_day:
                npt = NPTEvent(
                    category="Lost Circulation",
                    duration=12.5,
                    severity="High",
                    description="井深3750米处发生井漏，漏失速率15立方米/小时，泵注堵漏材料处理。"
                )
                r.npt_events.append(npt)
            
            session.add(r)
            report_count += 1
        
        # 其他井的数据...（省略，参考原 seed_mock_data 函数）
        
        # 套管数据
        casings = [
            CasingProgram(well_id="ZT-102", run_number=1, run_date=date(2023, 10, 5),
                         size=13.375, shoe_depth=800, cement_top=0),
            CasingProgram(well_id="ZT-102", run_number=2, run_date=date(2023, 10, 20),
                         size=9.625, shoe_depth=2500, cement_top=500),
            CasingProgram(well_id="ZT-105", run_number=1, run_date=date(2023, 10, 8),
                         size=13.375, shoe_depth=850, cement_top=0),
        ]
        session.add_all(casings)
        print(f"✓ 导入 {len(casings)} 条套管记录")
        
        session.commit()
        print(f"\n✅ 数据迁移完成！共导入 {report_count} 条日报记录")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ 迁移失败: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_data()
```

**运行方法：**

```bash
python data_migration.py
```

---

## PostgreSQL数据库准备

### 7. 创建PostgreSQL数据库

#### 方法 1：使用命令行

```bash
# 登录 PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE oilfield_db WITH ENCODING 'UTF8';

# 创建专用用户（推荐）
CREATE USER oilfield_user WITH PASSWORD 'secure_password';

# 授权
GRANT ALL PRIVILEGES ON DATABASE oilfield_db TO oilfield_user;

# 退出
\q
```

#### 方法 2：使用 pgAdmin

1. 打开 pgAdmin
2. 右键点击 "Databases" → "Create" → "Database"
3. 数据库名：`oilfield_db`
4. 编码：`UTF8`
5. 点击 "Save"

#### 方法 3：使用 Docker（推荐开发环境）

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: oilfield_postgres
    environment:
      POSTGRES_DB: oilfield_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
      POSTGRES_HOST_AUTH_METHOD: trust
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

启动数据库：

```bash
docker-compose up -d
```

### 8. 验证数据库连接

创建测试脚本 `test_db_connection.py`：

```python
"""测试 PostgreSQL 数据库连接"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def test_connection():
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "oilfield_db")
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    try:
        print(f"正在连接: {db_host}:{db_port}/{db_name}")
        engine = create_engine(connection_string, echo=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"\n✅ 连接成功！")
            print(f"PostgreSQL 版本: {version[0]}")
            
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")

if __name__ == "__main__":
    test_connection()
```

运行测试：

```bash
python test_db_connection.py
```

---

## 测试验证

### 9. 测试步骤

#### 9.1 环境准备

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（编辑 .env 文件）
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=oilfield_db
# DB_USER=postgres
# DB_PASSWORD=your_password

# 3. 测试数据库连接
python test_db_connection.py

# 4. 运行数据迁移（如果需要）
python data_migration.py
```

#### 9.2 启动服务测试

```bash
# 启动 MCP 服务
python oilfield_mcp_server.py
```

应该看到类似输出：

```
============================================================
🚀 油田钻井智能查询 MCP Server 已启动
============================================================

📌 系统功能：
  ✓ 鉴权管理（基于角色的权限控制）
  ✓ 单井数据查询（概览、日报、NPT分析）
  ✓ 多井对比分析（速度、事故、绩效）
  ✓ 周报/月报生成（单井和区块级别）
  ✓ 泥浆参数追踪（密度、粘度、pH）

🔒 权限模式：生产模式 (严格权限控制)
INFO:OilfieldMCP:正在连接数据库: localhost:5432/oilfield_db
INFO:OilfieldMCP:✅ 数据库连接成功，表结构已初始化
```

#### 9.3 功能测试（通过 Claude Desktop）

配置 Claude Desktop 的 `config_example.json`：

```json
{
  "mcpServers": {
    "oilfield-intel": {
      "command": "python",
      "args": [
        "d:/work/joyagent/gemini-ge/oilfield_mcp_server.py"
      ],
      "env": {
        "USER_ROLE": "admin",
        "DEV_MODE": "false"
      }
    }
  }
}
```

测试对话：

1. "检查数据库健康状态" → 调用 `database_health_check`
2. "查询ZT-102井的概况" → 调用 `get_well_summary`
3. "查询ZT-102井昨天的日报" → 调用 `get_daily_report`

---

## 生产部署注意事项

### 10. 安全最佳实践

#### 10.1 环境变量安全

```bash
# ❌ 错误：硬编码密码
DB_PASSWORD=admin123

# ✅ 正确：使用强密码
DB_PASSWORD=$(openssl rand -base64 32)

# 生产环境建议使用密钥管理服务（如 AWS Secrets Manager、Azure Key Vault）
```

#### 10.2 数据库连接安全

在生产环境的 `.env` 文件中：

```env
# 使用 SSL 连接
DB_SSLMODE=require
DB_SSLROOTCERT=/path/to/root.crt
DB_SSLCERT=/path/to/client.crt
DB_SSLKEY=/path/to/client.key

# 连接字符串示例（支持SSL）
# postgresql://user:password@host:port/dbname?sslmode=require
```

修改 `DatabaseConfig.build_connection_string()`:

```python
@staticmethod
def build_connection_string(config: Dict[str, Any]) -> str:
    """构建PostgreSQL连接字符串（支持SSL）"""
    connection_string = (
        f"postgresql://{config['user']}:{config['password']}@"
        f"{config['host']}:{config['port']}/{config['database']}"
    )
    
    # 添加SSL参数
    ssl_mode = os.getenv("DB_SSLMODE")
    if ssl_mode:
        connection_string += f"?sslmode={ssl_mode}"
    
    return connection_string
```

#### 10.3 权限管理

```sql
-- 创建只读用户（用于报表查询）
CREATE USER oilfield_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE oilfield_db TO oilfield_readonly;
GRANT USAGE ON SCHEMA public TO oilfield_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO oilfield_readonly;

-- 创建读写用户（用于应用程序）
CREATE USER oilfield_app WITH PASSWORD 'app_password';
GRANT CONNECT ON DATABASE oilfield_db TO oilfield_app;
GRANT USAGE ON SCHEMA public TO oilfield_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO oilfield_app;
```

#### 10.4 备份策略

```bash
# 自动备份脚本 (backup.sh)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/oilfield"
DB_NAME="oilfield_db"

pg_dump -U postgres -h localhost $DB_NAME | gzip > $BACKUP_DIR/oilfield_${DATE}.sql.gz

# 保留最近30天的备份
find $BACKUP_DIR -name "oilfield_*.sql.gz" -mtime +30 -delete
```

添加到 crontab：

```bash
# 每天凌晨2点自动备份
0 2 * * * /path/to/backup.sh
```

#### 10.5 监控和告警

添加数据库监控（可选）：

```python
# 在 oilfield_mcp_server.py 中添加
import psutil

@mcp.tool()
def system_monitor() -> str:
    """系统资源监控"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    session = Session()
    try:
        # 数据库连接池状态
        pool_size = engine.pool.size()
        pool_overflow = engine.pool.overflow()
        
        return f"""
### 📊 系统监控

**系统资源**:
- CPU 使用率: {cpu_percent}%
- 内存使用率: {memory.percent}%

**数据库连接池**:
- 当前连接数: {pool_size}
- 溢出连接数: {pool_overflow}
"""
    finally:
        session.close()
```

---

## 附录

### A. 完整的目录结构（改造后）

```
gemini-ge/
├── oilfield_mcp_server.py       # 主程序（已修改）
├── requirements.txt              # 依赖配置（已更新）
├── .env                          # 环境变量（新增，不提交）
├── .env.example                  # 环境变量示例（新增）
├── .gitignore                    # Git忽略配置（已更新）
├── db_config.example.json        # 数据库配置示例（新增）
├── data_migration.py             # 数据迁移脚本（新增）
├── test_db_connection.py         # 连接测试脚本（新增）
├── docker-compose.yml            # Docker配置（新增，可选）
├── config_example.json           # MCP配置示例
├── md/
│   ├── PostgreSQL数据库改造指南.md  # 本文档
│   ├── README.md
│   └── ...
└── venv/                         # 虚拟环境
```

### B. 快速检查清单

完成改造后，使用此清单验证：

- [ ] 已安装 `psycopg2-binary` 和 `python-dotenv`
- [ ] 已创建 `.env` 文件并配置数据库连接
- [ ] 已创建 PostgreSQL 数据库 `oilfield_db`
- [ ] 已修改 `oilfield_mcp_server.py` 的数据库连接代码
- [ ] 已测试数据库连接（运行 `test_db_connection.py`）
- [ ] 已创建数据库表结构（自动或手动）
- [ ] 已导入初始数据（如果需要）
- [ ] 已测试 MCP 服务启动
- [ ] 已通过 Claude Desktop 测试工具调用
- [ ] 已配置 `.gitignore` 排除敏感文件
- [ ] 已创建数据库备份策略（生产环境）

### C. 故障排查

#### 问题 1：连接失败 "could not connect to server"

**原因**：PostgreSQL 服务未启动或防火墙阻止

**解决**：

```bash
# Windows
net start postgresql-x64-15

# Linux
sudo systemctl start postgresql

# macOS
brew services start postgresql
```

#### 问题 2：认证失败 "password authentication failed"

**原因**：用户名或密码错误

**解决**：

```bash
# 重置 PostgreSQL 密码
psql -U postgres
ALTER USER postgres PASSWORD 'new_password';
```

#### 问题 3：数据库不存在 "database does not exist"

**原因**：数据库未创建

**解决**：

```sql
CREATE DATABASE oilfield_db;
```

#### 问题 4：表不存在 "relation does not exist"

**原因**：表结构未创建

**解决**：

运行迁移脚本或确保 `Base.metadata.create_all(engine)` 被执行。

---

## 总结

本文档详细说明了从 SQLite 内存数据库迁移到 PostgreSQL 的完整流程。关键改动点：

1. **依赖**: 添加 `psycopg2-binary` 和 `python-dotenv`
2. **配置**: 创建 `.env` 文件管理数据库连接
3. **代码**: 修改连接字符串和初始化逻辑
4. **数据**: 可选的数据迁移脚本
5. **安全**: 生产环境的安全最佳实践

完成改造后，系统将使用真实的 PostgreSQL 数据库，支持持久化存储和生产级别的并发访问。

---

**文档版本**: 1.0  
**创建日期**: 2026-01-27  
**维护者**: [你的名字]
