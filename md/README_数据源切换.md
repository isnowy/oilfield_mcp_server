# 快速开始：数据源切换

## 三种启动方式

### 1️⃣ 模拟数据模式（推荐测试使用）
```powershell
# PowerShell
.\start_mock_server.ps1

# 或批处理
start_mock_server.bat
```
- ✅ 无需配置数据库
- ✅ 启动快速
- ✅ 适合开发测试
- 端口：8080

### 2️⃣ 真实数据模式（主服务器）
```powershell
# PowerShell
.\start_real_server.ps1

# 或批处理
start_real_server.bat
```
- ✅ 使用PostgreSQL真实数据
- ✅ 功能完整（日报、对比、周报等）
- ⚠️ 需要先导入数据
- 端口：8080

### 3️⃣ 真实数据专用服务器
```powershell
# PowerShell
.\start_true_server.ps1

# 或批处理
start_true_server.bat
```
- ✅ 专门优化的真实数据查询
- ✅ 提供额外的统计功能
- ⚠️ 需要先导入数据
- 端口：8081

## 准备真实数据（首次使用）

```powershell
# 1. 创建数据库表
python setup_oil_wells_table.py

# 2. 导入Excel数据
python import_well_data.py

# 3. 验证数据
python verify_imported_data.py
```

## 快速测试

```powershell
# 测试配置是否正确
python test_data_switching.py
```

## 环境变量说明

| 变量 | 值 | 说明 |
|------|----|----|
| USE_REAL_DB | true/false | 是否使用真实数据库 |
| DEV_MODE | true/false | 是否跳过权限检查 |
| DB_HOST | localhost | 数据库主机 |
| DB_PORT | 5432 | 数据库端口 |
| DB_NAME | rag | 数据库名称 |
| DB_USER | postgres | 数据库用户 |
| DB_PASSWORD | postgres | 数据库密码 |

## 选择指南

| 场景 | 推荐方式 |
|------|---------|
| 开发调试 | 模拟数据模式 |
| 功能演示 | 模拟数据模式 |
| 真实数据查询 | 真实数据模式 |
| 生产环境 | 真实数据专用服务器 |
| 同时使用两种数据 | 同时启动方式2和3 |

## 更多信息

详细文档请查看：[数据源切换指南.md](./数据源切换指南.md)
