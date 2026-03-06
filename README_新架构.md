# 油田 MCP 服务器 - 快速开始指南

## 📋 新架构概述

项目已从单一 MCP 服务器重构为**模块化的多 MCP 架构**，提升了可维护性、可扩展性和性能。

### 🏗️ 架构组成

```
📦 oilMCP/
├── common/                          # 共享模块
│   ├── db.py                        # 数据库连接
│   ├── permissions.py               # 权限控制
│   ├── utils.py                     # 工具函数
│   └── audit.py                     # 审计日志
│
├── oilfield_wells_mcp.py            # 油井基础数据 MCP (5个工具)
├── oilfield_dailyreports_mcp.py    # 日报系统 MCP (3个工具)
└── oilfield_mcp_true_server.py     # 原始服务器（已废弃，保留备份）
```

---

## 🚀 快速开始

### 1️⃣ 测试模块（可选）
```powershell
.\test_mcps.ps1
```

### 2️⃣ 启动所有服务
**Windows (推荐):**
```cmd
start_all_mcps.bat
```

**PowerShell:**
```powershell
.\start_all_mcps.ps1
```

### 3️⃣ 验证服务状态
```powershell
# 检查油井基础数据 MCP
Invoke-WebRequest http://localhost:8081/health

# 检查日报系统 MCP
Invoke-WebRequest http://localhost:8082/health
```

---

## 📡 LibreChat 集成

### 配置文件
将 `librechat_mcp_config.json` 的内容添加到 LibreChat 的 MCP 配置中：

```json
{
  "mcpServers": {
    "oilfield-wells": {
      "command": "python",
      "args": ["d:\\work\\oilMCP\\oilfield_wells_mcp.py"],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "rag",
        "DB_USER": "postgres",
        "DB_PASSWORD": "postgres",
        "DEV_MODE": "true"
      }
    },
    "oilfield-dailyreports": {
      "command": "python",
      "args": ["d:\\work\\oilMCP\\oilfield_dailyreports_mcp.py"],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "rag",
        "DB_USER": "postgres",
        "DB_PASSWORD": "postgres",
        "DEV_MODE": "true"
      }
    }
  }
}
```

### 测试查询
在 LibreChat 中测试以下查询：

1. **测试油井基础数据 MCP:**
   - "查询所有油井"
   - "查询 ZT-102 的详细信息"
   - "按区块统计油井数量"

2. **测试日报系统 MCP:**
   - "查询 DG-092 的钻井日报"
   - "查询重点井试采日报"
   - "查询钻前工程日报"

---

## 🔧 各 MCP 服务器详情

### **oilfield-wells** (端口 8081)
**功能**：油井基础数据查询和统计

| 工具名称 | 描述 |
|---------|------|
| `search_wells` | 搜索油井，支持批量查询 |
| `get_well_details` | 获取井的详细信息 |
| `get_wells_by_block` | 按区块查询油井 |
| `get_wells_by_project` | 按项目查询油井 |
| `get_statistics` | 统计分析（按区块/项目/井型） |

### **oilfield-dailyreports** (端口 8082)
**功能**：各类日报数据查询

| 工具名称 | 描述 |
|---------|------|
| `get_drilling_daily` | 钻井工程日报 |
| `get_drilling_pre_daily` | 钻前工程日报 |
| `get_key_well_daily` | 重点井试采日报 |

---

## 📊 优势对比

| 维度 | 单一 MCP | 多 MCP（新架构） |
|------|----------|------------------|
| 工具发现 | ❌ 8个工具混杂 | ✅ 5个 + 3个清晰分组 |
| 代码行数 | ❌ 1801行 | ✅ 最大约600行 |
| 维护性 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 扩展性 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 性能 | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 📝 开发指南

### 添加新工具
1. 在对应的 MCP 文件中添加工具定义
2. 在 `handle_list_tools()` 中注册工具
3. 在 `handle_call_tool()` 中添加路由
4. 实现业务逻辑函数

### 添加新 MCP 服务器
1. 复制现有 MCP 文件作为模板
2. 修改服务名称和端口
3. 添加工具定义和业务逻辑
4. 更新启动脚本和 LibreChat 配置

---

## 🐛 故障排查

### 问题：端口被占用
```powershell
# 查看端口占用
netstat -ano | findstr "8081"
netstat -ano | findstr "8082"

# 关闭占用进程
taskkill /PID <进程ID> /F
```

### 问题：数据库连接失败
1. 检查 PostgreSQL 是否启动
2. 验证数据库配置（DB_HOST、DB_PORT、DB_NAME）
3. 检查数据库用户权限

### 问题：模块导入失败
```powershell
# 验证 Python 路径
python -c "import sys; print('\n'.join(sys.path))"

# 测试共享模块
.\test_mcps.ps1
```

---

## 📚 相关文档

- [MCP服务器拆分方案.md](./md/MCP服务器拆分方案.md) - 详细的架构设计
- [MCP服务器重构完成总结.md](./md/MCP服务器重构完成总结.md) - 重构总结
- [项目介绍和框架文档.md](./md/项目介绍和框架文档.md) - 完整项目文档

---

## 🔄 未来扩展

### 阶段二计划（4个 MCP）
1. **oilfield_reports_mcp.py** - 统计报表（周报/月报/年报）
2. **oilfield_production_mcp.py** - 生产动态监控

### 新增日报类型（扩展现有 MCP）
- 钻井地质日报
- 试油工作日报
- 地层压力日报

---

**版本**: v1.0  
**最后更新**: 2026年3月5日  
**状态**: ✅ 生产就绪
