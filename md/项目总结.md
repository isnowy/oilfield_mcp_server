# 油田钻井数据查询 MCP Server - 项目总结

## 🎯 项目概述

本项目是一个基于 **FastMCP** 框架开发的油田钻井数据智能查询服务，实现了完整的鉴权、数据查询、分析对比和报告生成功能，可直接部署到本地环境并与 Claude Desktop 集成使用。

## 📁 项目文件结构

```
gemini-ge/
├── oilfield_mcp_server.py      # 主服务器代码（核心文件）
├── requirements.txt             # Python依赖清单
├── config_example.json          # Claude Desktop配置示例
├── test_server.py              # 功能测试脚本
├── start_server.bat            # Windows启动脚本
├── run_test.bat                # Windows测试脚本
├── README_OILFIELD_MCP.md      # 完整使用文档
├── DEPLOY_GUIDE.md             # 部署指南
└── PROJECT_SUMMARY.md          # 本文档
```

## ✨ 核心功能

### 1. 鉴权系统（参考 auth-mcp.md）
- ✅ 基于角色的访问控制（RBAC）
- ✅ 支持 admin/engineer/viewer/default 四种角色
- ✅ 井级和区块级双重权限控制
- ✅ 工具调用前强制鉴权检查
- ✅ 完整的审计日志追踪（TraceID、执行时间、用户角色）

**实现要点：**
```python
class PermissionService:
    @staticmethod
    def check_well_access(user_role: str, well_id: str) -> bool
    
    @staticmethod
    def check_block_access(user_role: str, block_name: str) -> bool
```

### 2. 单井数据查询（参考 many-tool.md）
- ✅ 模糊搜索井号（支持中文井名归一化）
- ✅ 井基本信息概览（开钻日期、井型、钻机、队伍）
- ✅ 钻井日报查询（DDR）
- ✅ NPT（非生产时间）事故分析
- ✅ 井身结构/套管程序查询
- ✅ 泥浆参数追踪（密度、粘度、pH）

**工具列表：**
- `search_wells` - 井搜索
- `get_well_summary` - 井概览
- `get_well_casing` - 井身结构
- `get_daily_report` - 日报查询
- `analyze_npt_events` - NPT分析
- `track_mud_properties` - 泥浆追踪

### 3. 多井/邻井对比（参考 many-tool.md）
- ✅ 基本信息横向对比
- ✅ 钻井速度对比（ROP、日进尺、效率指标）
- ✅ NPT统计对比矩阵
- ✅ 标杆井识别
- ✅ 风险井预警

**工具列表：**
- `compare_wells_overview` - 基本对比
- `compare_drilling_pace` - 速度对比
- `compare_npt_statistics` - NPT对比

### 4. 日报总结成周报/月报（参考 read.md）
- ✅ 单井期间数据汇总（周报/月报素材）
- ✅ 区块级汇总报告（厂级报告）
- ✅ 自动计算核心指标（进尺、ROP、NPT、泥浆趋势）
- ✅ 每日作业时间轴生成
- ✅ 标杆井和问题井识别
- ✅ 钻井队绩效排名

**工具列表：**
- `get_period_drilling_summary` - 单井期间报告
- `get_block_period_summary` - 区块汇总报告

## 🏗️ 技术架构（参考 many-tool.md）

### 架构分层

```
┌─────────────────────────────────────────┐
│    LLM Client (Claude Desktop)          │
│    - 自然语言理解                        │
│    - 意图识别与改写                      │
│    - 工具调用决策                        │
└──────────────┬──────────────────────────┘
               │ MCP Protocol (stdio)
┌──────────────▼──────────────────────────┐
│    MCP Server (oilfield_mcp_server.py)  │
├─────────────────────────────────────────┤
│  鉴权层 (PermissionService)              │
│    - 角色权限检查                        │
│    - 井级/区块级控制                     │
├─────────────────────────────────────────┤
│  监控层 (AuditLog)                       │
│    - 调用日志                            │
│    - 性能监控                            │
│    - 异常追踪                            │
├─────────────────────────────────────────┤
│  业务层 (MCP Tools)                      │
│    - 11个查询工具                        │
│    - Pydantic参数校验                    │
│    - Markdown格式输出                    │
├─────────────────────────────────────────┤
│  数据层 (SQLAlchemy ORM)                 │
│    - Well / DailyReport                  │
│    - NPTEvent / CasingProgram            │
│    - 关系映射                            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Database (SQLite/PostgreSQL/MySQL)   │
│    - 井基本信息表                        │
│    - 钻井日报表                          │
│    - NPT事故表                           │
│    - 套管程序表                          │
└─────────────────────────────────────────┘
```

### 关键设计模式

1. **装饰器模式**（AuditLog）
   - 用于工具调用的横切关注点（日志、性能监控）
   - 不侵入业务逻辑

2. **策略模式**（PermissionService）
   - 不同角色对应不同权限策略
   - 易于扩展新角色

3. **适配器模式**（normalize_well_id）
   - 处理中文井号与标准ID的映射
   - 用户友好的输入接口

4. **聚合模式**（区块报告）
   - 服务端完成数据聚合
   - 减轻LLM的计算负担

## 📊 数据模型（参考 read.md）

### 核心表结构

```sql
-- 井基本信息
Wells (
    id, name, block, target_depth, spud_date, 
    status, well_type, team, rig
)

-- 钻井日报
DailyReports (
    id, well_id, report_date, report_no,
    current_depth, progress, avg_rop,
    mud_density, mud_viscosity, mud_ph,
    operation_summary, next_plan
)

-- NPT事故
NPTEvents (
    id, report_id, category, duration, 
    severity, description
)

-- 套管程序
CasingPrograms (
    id, well_id, run_number, run_date,
    size, shoe_depth, cement_top
)
```

### 关系设计

```
Well 1----* DailyReport 1----* NPTEvent
     1----* CasingProgram
```

## 🎯 核心特性实现

### 1. 意图识别增强（参考 many-tool.md）

**问题**：LLM 可能不理解钻井术语，导致工具选择错误。

**解决方案**：
- 详细的 docstring（场景化描述 + 关键词标签）
- System Prompt 中的术语映射表
- 参数使用 `Literal` 枚举限制选项

**示例**：
```python
@mcp.tool()
def analyze_npt_events(...) -> str:
    """
    [场景] 分析某井的所有非生产时间（NPT）事件和复杂情况。
    [关键词] 事故、复杂、井漏、溢流、NPT、非生产时间
    """
```

### 2. 数据聚合优化（参考 many-tool.md）

**问题**：如果让 LLM 循环调用单井工具，会导致Token消耗巨大。

**解决方案**：
- 服务端完成所有 SQL JOIN 和 GROUP BY 操作
- 只返回聚合后的统计结果
- 使用 Pandas 进行二次聚合

**示例**：
```python
# 区块报告中的聚合逻辑
df = pd.DataFrame(data)
well_stats = df.groupby(['well_id', 'well_name']).agg({
    'progress': 'sum',
    'npt': 'sum'
}).sort_values('总进尺(m)', ascending=False)
```

### 3. 权限防御编程（参考 auth-mcp.md）

**问题**：不能依赖 Prompt 来实现权限控制。

**解决方案**：
- 每个工具强制调用权限检查
- 失败返回友好的错误信息（不抛异常）
- 权限过滤在数据查询前完成

**示例**：
```python
if not PermissionService.check_well_access(user_role, well_id):
    return f"🚫 权限拒绝：用户角色 ({user_role}) 无权访问井号 {well_id}。"
```

### 4. Markdown 输出优化（参考 many-tool.md）

**问题**：JSON 输出 Token 消耗大，且 LLM 阅读困难。

**解决方案**：
- 使用 Markdown 表格（pandas.to_markdown）
- 添加 Emoji 图标增强可读性
- 结构化的章节标题

**对比**：
```
# JSON (占用更多Token)
{"wells": [{"id": "ZT-102", "depth": 3500}, ...]}

# Markdown (更易读，Token更少)
| 井号 | 井深(m) |
|------|---------|
| ZT-102 | 3500  |
```

## 🛠️ 部署方式

### 方式一：本地测试
```bash
python test_server.py
```

### 方式二：MCP Inspector 调试
```bash
npx @modelcontextprotocol/inspector python oilfield_mcp_server.py
```

### 方式三：Claude Desktop 集成
编辑 `%APPDATA%\Claude\claude_desktop_config.json`：
```json
{
  "mcpServers": {
    "oilfield-intel": {
      "command": "python",
      "args": ["D:/work/joyagent/gemini-ge/oilfield_mcp_server.py"]
    }
  }
}
```

## 📈 性能特性

### 1. 审计日志（参考 many-tool.md）
```python
@AuditLog.trace("tool_name")
def tool_function(...):
    # 自动记录：开始时间、结束时间、执行时长、异常
```

输出示例：
```json
{
  "event": "TOOL_SUCCESS",
  "trace_id": "a3b2c1d4",
  "tool": "search_wells",
  "duration_ms": 125.3
}
```

### 2. 异常处理
- 所有工具调用都被 try-except 包裹
- 返回友好的错误信息（不中断对话）
- TraceID 用于问题追踪

### 3. 数据降采样（参考 many-tool.md）
- 时间范围过大时自动聚合
- 避免返回超过1000行的原始数据
- 优先返回统计指标而非明细

## 🔒 安全特性

1. **SQL注入防护**：使用 SQLAlchemy 参数化查询
2. **权限隔离**：角色级访问控制
3. **审计追踪**：完整的调用日志
4. **错误脱敏**：不暴露内部堆栈给用户
5. **输入校验**：Pydantic 严格的类型检查

## 🚀 扩展指南

### 添加新工具
1. 定义函数，添加装饰器
2. 编写详细的 docstring
3. 添加权限检查
4. 使用 Pydantic Field 描述参数

### 连接真实数据库
1. 修改 `engine` 创建语句（第176行）
2. 注释掉 `seed_mock_data()`
3. 确保表结构匹配

### 自定义权限
1. 修改 `USER_PERMISSIONS` 字典
2. 添加新角色和对应的井号/区块列表

## 📚 参考文档

本项目的设计完全参考了以下文档：

1. **auth-mcp.md** - 鉴权设计方案
   - 权限服务设计
   - 工具层拦截机制
   - 审计日志实现

2. **many-tool.md** - 多工具设计原则
   - 按业务维度分层
   - 数据聚合优化
   - 意图识别增强

3. **read.md** - 完整代码参考
   - ORM 模型设计
   - 工具实现范例
   - 报表生成逻辑

## 🎉 项目亮点

1. **开箱即用**：内置模拟数据，无需配置数据库即可测试
2. **完整鉴权**：生产级的权限控制和审计
3. **智能聚合**：服务端完成数据处理，节省LLM Token
4. **中文友好**：支持中文井号识别和归一化
5. **易于扩展**：清晰的代码结构，详细的注释
6. **测试完备**：13个测试用例覆盖所有功能
7. **文档齐全**：README、部署指南、代码注释

## 📞 技术栈

- **框架**: FastMCP 0.2.0+
- **ORM**: SQLAlchemy 2.0+
- **数据处理**: Pandas 2.0+
- **参数校验**: Pydantic 2.0+
- **数据库**: SQLite（可切换至 PostgreSQL/MySQL/Oracle）
- **协议**: MCP (Model Context Protocol) stdio

## 🏆 最佳实践

1. **Tool 设计**：按用户意图分层，不按数据库表结构
2. **权限控制**：在代码层强制执行，不依赖 Prompt
3. **输出格式**：优先使用 Markdown，避免大量 JSON
4. **数据聚合**：服务端完成，只给 LLM 统计结果
5. **错误处理**：返回友好信息，不中断对话流
6. **日志审计**：记录所有调用，便于问题追踪

---

**项目状态：** ✅ 完成，可直接部署使用

**最后更新：** 2026-01-26
