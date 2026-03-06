# MCP 服务器拆分方案

## 📋 项目概述

为了提升系统的可维护性、可扩展性和性能，将现有的单体 MCP 服务器按业务域拆分成多个独立的 MCP 服务器。

---

## 🎯 拆分原则

1. **按业务域划分**：每个 MCP 服务器负责一个明确的业务领域
2. **工具数量控制**：每个 MCP 包含 5-8 个工具，避免 LLM 选择困难
3. **独立部署**：每个 MCP 可以独立启动、更新和维护
4. **代码复用**：通过共享模块复用数据库连接、权限控制等通用功能
5. **向后兼容**：保持原有接口不变，便于平滑迁移

---

## 🏗️ 拆分架构

### **阶段一：2 个 MCP 服务器**（当前实施）

```
📦 oilMCP/
├── common/                          # 共享模块
│   ├── __init__.py
│   ├── db.py                        # 数据库连接
│   ├── permissions.py               # 权限控制
│   ├── utils.py                     # 工具函数
│   └── audit.py                     # 审计日志
│
├── oilfield_wells_mcp.py            # ✅ 油井基础数据 MCP
│   ├── search_wells                 # 搜索油井
│   ├── get_well_details             # 井详细信息
│   ├── get_wells_by_block           # 按区块查询
│   ├── get_wells_by_project         # 按项目查询
│   └── get_statistics               # 统计信息
│
└── oilfield_dailyreports_mcp.py    # ✅ 日报系统 MCP
    ├── get_drilling_daily           # 钻井工程日报
    ├── get_drilling_pre_daily       # 钻前工程日报
    └── get_key_well_daily           # 重点井试采日报
```

### **阶段二：4 个 MCP 服务器**（未来扩展）

```
📦 oilMCP/
├── common/                          # 共享模块
│
├── oilfield_wells_mcp.py            # 油井基础数据 MCP (5个工具)
├── oilfield_dailyreports_mcp.py    # 日报系统 MCP (3-6个工具)
│   ├── get_drilling_daily           # 钻井工程日报
│   ├── get_drilling_pre_daily       # 钻前工程日报
│   ├── get_key_well_daily           # 重点井试采日报
│   ├── get_drilling_geology_daily   # ⭐ 钻井地质日报（新增）
│   ├── get_test_oil_daily           # ⭐ 试油日报（新增）
│   └── get_formation_pressure_daily # ⭐ 地层压力日报（新增）
│
├── oilfield_reports_mcp.py          # 📊 统计报表 MCP (4-6个工具)
│   ├── generate_weekly_report       # 周报生成
│   ├── generate_monthly_report      # 月报生成
│   ├── generate_annual_report       # 年报生成
│   ├── get_performance_statistics   # 绩效统计
│   └── get_trend_analysis           # 趋势分析
│
└── oilfield_production_mcp.py       # ⚡ 生产动态 MCP (5-7个工具)
    ├── get_production_overview      # 生产概览
    ├── get_drilling_progress        # 钻井进度
    ├── get_test_oil_status          # 试油状态
    ├── get_rig_routes               # 钻机路线
    ├── get_well_map_data            # 井点地图数据
    └── get_real_time_status         # 实时状态监控
```

---

## 📊 对比分析

| 维度 | 单一 MCP | 多个 MCP（推荐） |
|------|----------|------------------|
| **工具发现** | ❌ 20+ 工具，LLM 容易混淆 | ✅ 每个 MCP 5-8 工具，清晰明确 |
| **性能** | ❌ 单点负载，启动慢 | ✅ 并行启动，响应快 |
| **维护性** | ❌ 3000+ 行代码，改动风险高 | ✅ 每个文件 800 行，易维护 |
| **权限控制** | ⚠️ 需要混合逻辑 | ✅ 按服务维度独立鉴权 |
| **LibreChat 配置** | ✅ 配置 1 个 | ⚠️ 配置 2-4 个（但更灵活） |
| **团队协作** | ❌ 容易冲突 | ✅ 按模块分工 |
| **版本管理** | ❌ 一个改动影响全局 | ✅ 独立更新部署 |
| **错误隔离** | ❌ 一个服务故障全挂 | ✅ 故障隔离，其他服务正常 |

---

## 🔧 共享模块设计

### **common/db.py** - 数据库连接管理
```python
def get_db_connection()           # 获取数据库连接
def test_db_connection()          # 测试连接
def execute_query(query, params)  # 执行查询
```

### **common/permissions.py** - 权限控制
```python
class PermissionService:
    check_well_access()           # 井级权限检查
    check_block_access()          # 区块级权限检查
    get_accessible_wells()        # 获取可访问井列表
    filter_wells_by_permission()  # 数据过滤
```

### **common/utils.py** - 工具函数
```python
df_to_markdown()                  # DataFrame转Markdown
normalize_well_id()               # 井号归一化
normalize_date()                  # 日期归一化
parse_date_range()                # 日期范围解析
```

### **common/audit.py** - 审计日志
```python
class AuditLog:
    @staticmethod
    def trace(tool_name)          # 装饰器：记录工具调用
```

---

## 📡 LibreChat 配置示例

### **方案 A：配置文件方式**（推荐）

```json
{
  "mcpServers": {
    "oilfield-wells": {
      "command": "python",
      "args": ["-m", "d:\\work\\oilMCP\\oilfield_wells_mcp"],
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
      "args": ["-m", "d:\\work\\oilMCP\\oilfield_dailyreports_mcp"],
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

### **方案 B：启动脚本方式**

**start_all_mcps.bat**
```batch
@echo off
echo Starting Oil Wells MCP...
start "Oil Wells MCP" python oilfield_wells_mcp.py

echo Starting Daily Reports MCP...
start "Daily Reports MCP" python oilfield_dailyreports_mcp.py

echo All MCP Servers started!
pause
```

---

## 🎯 用户体验

### **无感知访问**
用户在 LibreChat 中查询时，Claude 会根据工具描述自动选择正确的 MCP 服务器：

```
用户: "查询 ZT-102 的基本信息"
→ Claude 自动调用 oilfield-wells MCP 的 get_well_details

用户: "查询 DG-092 的钻井日报"
→ Claude 自动调用 oilfield-dailyreports MCP 的 get_drilling_daily

用户: "统计各区块的油井数量"
→ Claude 自动调用 oilfield-wells MCP 的 get_statistics
```

---

## 📝 实施步骤

### **阶段一：代码重构**（2个MCP）✅
1. ✅ 创建 `common/` 共享模块目录
2. ✅ 提取共用代码到 `common/`
3. ✅ 创建 `oilfield_wells_mcp.py`（5个工具）
4. ✅ 创建 `oilfield_dailyreports_mcp.py`（3个工具）
5. ✅ 更新启动脚本

### **阶段二：测试验证**
1. 单独测试每个 MCP 服务器
2. 测试权限控制功能
3. 在 LibreChat 中集成测试
4. 性能基准测试

### **阶段三：文档更新**
1. 更新部署文档
2. 更新 LibreChat 配置指南
3. 创建故障排查文档
4. 更新 README

### **阶段四：未来扩展**（4个MCP）
1. 添加新日报类型到 `dailyreports_mcp`
2. 创建 `reports_mcp` 处理周报/月报
3. 创建 `production_mcp` 处理实时监控
4. 地图数据和图表分析功能

---

## 🚀 优势总结

1. **开发效率提升**：模块独立，减少代码冲突
2. **维护成本降低**：单个模块代码量小，易于理解和修改
3. **性能优化**：按需启动，降低资源消耗
4. **扩展性强**：新增功能时创建新 MCP 即可
5. **故障隔离**：单个服务故障不影响其他服务
6. **权限细化**：可以给不同用户分配不同 MCP 的访问权限
7. **版本管理**：独立版本号，灵活升级

---

## 📚 相关文档

- [项目介绍和框架文档.md](./项目介绍和框架文档.md)
- [LibreChat调用问题排查.md](./LibreChat调用问题排查.md)
- [权限控制集成完成总结.md](./权限控制集成完成总结.md)
- [数据源切换指南.md](./数据源切换指南.md)

---

## 💡 注意事项

1. **环境变量**：确保所有 MCP 服务器共享相同的数据库配置
2. **端口管理**：每个 MCP HTTP 服务器需要不同端口（如 8081, 8082, 8083...）
3. **日志管理**：每个 MCP 使用独立的日志文件便于调试
4. **健康检查**：每个 MCP 都应提供 `/health` 端点
5. **版本兼容**：保持共享模块的 API 向后兼容

---

**最后更新**: 2026年3月5日
**文档版本**: v1.0
**作者**: GitHub Copilot
