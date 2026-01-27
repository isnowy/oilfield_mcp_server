# 油田钻井数据查询 MCP Server

基于 FastMCP 开发的油田钻井数据智能查询服务，支持鉴权、单井查询、多井对比、日报分析、周报月报生成等功能。

## 📋 功能特性

### 1. 权限管理（鉴权）
- ✅ 基于角色的访问控制（RBAC）
- ✅ 支持 admin/engineer/viewer 三种角色
- ✅ 井级和区块级权限控制
- ✅ 完整的审计日志追踪

### 2. 单井数据查询
- 🔍 模糊搜索井号（支持中文井名）
- 📊 井基本信息概览
- 📋 钻井日报查询（DDR）
- ⚠️ NPT（非生产时间）事故分析
- 🏗️ 井身结构/套管程序查询

### 3. 多井对比分析
- 📊 基本信息对比
- 🏎️ 钻井速度对比（ROP、日进尺）
- ⚠️ NPT统计对比
- 🎯 标杆井识别

### 4. 周报/月报生成
- 📄 单井期间报告（周报/月报素材）
- 🏭 区块汇总报告（厂级报告）
- 📈 关键指标自动统计
- 🕐 每日作业时间轴

### 5. 工程参数追踪
- 🧪 泥浆密度变化趋势
- 💧 泥浆粘度监测
- 🔬 pH值追踪

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装 Python 3.8+
python --version

# 安装依赖
pip install -r requirements.txt
```

### 2. 本地测试运行

```bash
# 直接运行服务器
python oilfield_mcp_server.py
```

运行后会看到类似输出：

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

⏳ 等待客户端连接...
```

### 3. 使用 MCP Inspector 调试

MCP Inspector 是官方提供的调试工具：

```bash
# 安装 Inspector
npm install -g @modelcontextprotocol/inspector

# 启动调试
npx @modelcontextprotocol/inspector python oilfield_mcp_server.py
```

浏览器会自动打开调试界面，可以测试所有工具。

### 4. 配置到 Claude Desktop

#### Windows 配置

配置文件位置：
```
%APPDATA%\Claude\claude_desktop_config.json
```

配置内容（参考 `config_example.json`）：

```json
{
  "mcpServers": {
    "oilfield-intel": {
      "command": "python",
      "args": [
        "D:/work/joyagent/gemini-ge/oilfield_mcp_server.py"
      ],
      "env": {
        "USER_ROLE": "admin"
      }
    }
  }
}
```

**注意事项：**
- 使用绝对路径
- Windows 路径使用正斜杠 `/` 或双反斜杠 `\\`
- 如果使用虚拟环境，`command` 指向虚拟环境的 Python

#### macOS/Linux 配置

配置文件位置：
```
~/Library/Application Support/Claude/claude_desktop_config.json  # macOS
~/.config/claude/claude_desktop_config.json                      # Linux
```

### 5. 重启 Claude Desktop

配置完成后，完全退出并重启 Claude Desktop。

## 📖 使用示例

### 基础查询

```
用户: 帮我查一下Block-A区块有哪些活跃的井？
AI: [调用 search_wells 工具]

用户: ZT-102井的基本情况是什么？
AI: [调用 get_well_summary 工具]

用户: 查询ZT-102井在2023-11-05的日报
AI: [调用 get_daily_report 工具]
```

### 多井对比

```
用户: 对比一下ZT-102和ZT-105谁钻得快？
AI: [调用 compare_drilling_pace 工具]

用户: 这两口井的事故情况对比
AI: [调用 compare_npt_statistics 工具]
```

### 报告生成

```
用户: 生成ZT-102井上周的钻井周报
AI: [调用 get_period_drilling_summary，然后基于数据撰写周报]

用户: 给我Block-A区块11月份的生产总结报告
AI: [调用 get_block_period_summary，生成区块级汇总]
```

### 工程分析

```
用户: ZT-102的泥浆密度最近有什么变化？
AI: [调用 track_mud_properties 工具]

用户: 分析一下ZT-102井有哪些复杂情况
AI: [调用 analyze_npt_events 工具]
```

## 🔐 权限配置

### 默认权限角色

服务器内置了以下权限配置（在代码中的 `USER_PERMISSIONS` 字典）：

```python
USER_PERMISSIONS = {
    "admin": {
        "wells": "*",           # 所有井
        "blocks": "*",          # 所有区块
        "role": "admin"
    },
    "engineer": {
        "wells": ["ZT-102", "ZT-105"],     # 指定井
        "blocks": ["Block-A"],              # 指定区块
        "role": "engineer"
    },
    "viewer": {
        "wells": ["ZT-102"],                # 只读一口井
        "blocks": ["Block-A"],
        "role": "viewer"
    },
    "default": {
        "wells": [],                         # 无权限
        "blocks": [],
        "role": "guest"
    }
}
```

### 修改权限

1. **修改代码中的权限配置**（第34-39行）
2. **通过环境变量传递用户角色**：
   ```json
   {
     "env": {
       "USER_ROLE": "engineer"
     }
   }
   ```

### 权限检查机制

每个工具都会在执行前检查权限：

```python
if not PermissionService.check_well_access(user_role, well_id):
    return f"🚫 权限拒绝：用户角色 ({user_role}) 无权访问井号 {well_id}。"
```

## 🗄️ 数据库配置

### 当前：内存数据库（演示用）

代码默认使用 SQLite 内存数据库，适合测试：

```python
engine = create_engine('sqlite:///:memory:', echo=False)
```

### 切换到生产数据库

修改 `oilfield_mcp_server.py` 第176行：

#### PostgreSQL
```python
engine = create_engine(
    'postgresql://username:password@localhost:5432/oilfield_db'
)
```

#### MySQL/MariaDB
```python
engine = create_engine(
    'mysql+pymysql://username:password@localhost:3306/oilfield_db'
)
```

#### SQL Server
```python
engine = create_engine(
    'mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server'
)
```

#### Oracle
```python
engine = create_engine(
    'oracle+cx_oracle://username:password@host:1521/?service_name=orcl'
)
```

**注意：** 切换数据库后需要：
1. 删除 `seed_mock_data()` 调用（第194行）
2. 确保数据库中已有对应的表和数据
3. 或者修改 `seed_mock_data()` 函数以从现有数据源导入

## 📊 数据模型

系统包含4个核心数据表：

### 1. Well (井基本信息)
- `id`: 井号（主键）
- `name`: 井名
- `block`: 区块
- `target_depth`: 设计井深
- `spud_date`: 开钻日期
- `status`: 状态（Active/Completed/Suspended）
- `well_type`: 井型（Vertical/Horizontal/Directional）
- `team`: 钻井队
- `rig`: 钻机

### 2. DailyReport (钻井日报)
- `id`: 主键
- `well_id`: 井号（外键）
- `report_date`: 日期
- `report_no`: 报告编号
- `current_depth`: 当前井深
- `progress`: 日进尺
- `mud_density`: 泥浆密度
- `mud_viscosity`: 泥浆粘度
- `mud_ph`: 泥浆pH
- `operation_summary`: 作业摘要
- `next_plan`: 下步计划
- `avg_rop`: 平均机械钻速
- `bit_number`: 钻头编号

### 3. NPTEvent (非生产时间事故)
- `id`: 主键
- `report_id`: 日报ID（外键）
- `category`: 事故类别（Lost Circulation/Kick/Equipment Failure等）
- `duration`: 损失时间（小时）
- `severity`: 严重程度（Low/Medium/High）
- `description`: 详细描述

### 4. CasingProgram (套管程序)
- `id`: 主键
- `well_id`: 井号（外键）
- `run_number`: 趟次
- `run_date`: 下入日期
- `size`: 套管尺寸（英寸）
- `shoe_depth`: 鞋深（米）
- `cement_top`: 水泥返高（米）

## 🛠️ 工具列表

| 工具名称 | 功能描述 | 使用场景 | 新增/增强 |
|---------|---------|---------|----------|
| `plan_data_retrieval` ⭐ | 意图规划与分类 | 复杂查询时先规划 | 🆕 新增 |
| `search_wells` | 模糊搜索井号 | 不知道准确井号时 | - |
| `get_well_summary` | 获取井概览 | 查看井基本信息 | ✨ 支持中文井号 |
| `get_well_casing` | 查询井身结构 | 查看套管程序 | ✨ 支持中文井号 |
| `get_daily_report` | 查询日报 | 查看某天的作业情况 | ✨ 支持模糊日期 |
| `analyze_npt_events` | NPT分析 | 分析事故和复杂情况 | ✨ 支持中文井号 |
| `compare_wells_overview` | 多井基本对比 | 对比井的基本信息 | ✨ 支持中文井号 |
| `compare_drilling_pace` | 钻井速度对比 | 识别提速标杆井 | ✨ 支持中文井号 |
| `compare_npt_statistics` | NPT对比 | 识别风险井 | ✨ 支持中文井号 |
| `get_period_drilling_summary` | 单井期间报告 | 生成周报/月报素材 | ✨ 支持模糊日期范围 |
| `get_block_period_summary` | 区块汇总报告 | 生成厂级报告 | ✨ 支持模糊日期范围 |
| `track_mud_properties` | 泥浆参数追踪 | 监测泥浆性能变化 | ✨ 支持中文井号 |

### 🆕 新增功能说明

#### 1. 意图规划工具 (`plan_data_retrieval`)

当用户的查询比较复杂、涉及多个步骤时，可以先调用此工具进行规划。

**示例**：
```
用户："我想了解Block-A区块本月的整体情况，包括每口井的表现和事故统计"

LLM 先调用：plan_data_retrieval(
    intent_category="historical_report",
    entities=["Block-A"],
    time_range="本月"
)

返回规划建议 → LLM 按步骤执行
```

#### 2. 模糊输入支持

**中文井号识别**：
- "中102" → "ZT-102"
- "102井" → "ZT-102"
- "新疆009" → "XY-009"

**模糊日期识别**：
- "昨天"、"yesterday" → 自动计算日期
- "上周"、"last_week" → 计算日期范围
- "本月"、"this_month" → 本月1号到今天
- "最近7天" → 7天前到今天

## 📝 System Prompt 配置

### 方式一：使用完整配置文件（推荐）⭐

项目提供了完整的 `system_prompt.md` 配置文件，包含：
- ✅ 详细的实体归一化规则
- ✅ 完整的术语映射表
- ✅ Few-Shot Learning 示例
- ✅ 工具选择决策树
- ✅ 报告生成最佳实践

**使用方法**：
1. 打开 `system_prompt.md` 文件
2. 将内容复制到 Claude Desktop 的自定义指令中
3. 或在对话开始时告诉 Claude："请按照 system_prompt.md 中的规则与我交互"

### 方式二：简化版配置

如果需要简化版本，可以使用以下 System Prompt：

```
你是一个专业的油田钻井数据助手。你连接了一个 MCP 数据服务。

## 核心规则

1. **模糊输入支持**：
   - 中文井号："中102" 自动识别为 "ZT-102"
   - 模糊日期："昨天"、"上周" 自动计算具体日期
   - 系统已支持，可直接传递模糊输入

2. **意图映射**：
   - "谁钻得快"、"提速" → compare_drilling_pace
   - "有什么事故"、"井漏" → analyze_npt_events
   - "套管"、"井身结构" → get_well_casing
   - "周报"、"月报" → get_period_drilling_summary

3. **复杂查询**：
   - 涉及多个步骤时，先调用 plan_data_retrieval 工具规划

4. **默认行为**：
   - user_role 默认使用 "admin"
   - 未提供日期时使用 "today"
```

### 术语映射速查表

| 用户可能说的 | 标准术语 | 对应工具 |
|------------|---------|---------|
| 提速、钻得快 | ROP、机械钻速 | compare_drilling_pace |
| 井漏、溢流、卡钻 | NPT、复杂情况 | analyze_npt_events |
| 泥浆、密度、粘度 | 泥浆性能 | track_mud_properties |
| 套管、井身结构 | 套管程序 | get_well_casing |
| 周报、月报 | 期间报告 | get_period_drilling_summary |

## 🔍 调试与日志

### 查看运行日志

服务器会输出结构化的 JSON 日志，包含：
- 工具调用开始/成功/失败
- TraceID（用于追踪）
- 执行时间（毫秒）
- 用户角色和参数

示例日志：
```json
{
  "event": "TOOL_START",
  "trace_id": "a3b2c1d4",
  "tool": "search_wells",
  "user": "admin",
  "params": {"keyword": "ZT", "status": "All"}
}
```

### 常见问题

#### 1. 权限拒绝
```
🚫 权限拒绝：用户角色 (engineer) 无权访问井号 XY-009。
```
**解决**：检查 `USER_PERMISSIONS` 配置，确保用户角色有对应井号的权限。

#### 2. 未找到数据
```
❌ 未找到井号 'ZT-999'。
```
**解决**：确认井号正确，或者检查数据库中是否有该井的数据。

#### 3. Claude Desktop 未识别 Server
**解决**：
1. 检查 `claude_desktop_config.json` 路径是否正确
2. 确保 Python 路径使用绝对路径
3. 完全重启 Claude Desktop
4. 检查依赖是否安装完整

## 🚧 扩展开发

### 添加新的工具

1. 在 `oilfield_mcp_server.py` 中定义新函数
2. 使用 `@mcp.tool()` 和 `@AuditLog.trace()` 装饰器
3. 添加详细的 docstring（LLM会读取）
4. 添加权限检查逻辑

示例：
```python
@mcp.tool()
@AuditLog.trace("your_new_tool")
def your_new_tool(
    param1: str = Field(..., description="参数描述"),
    user_role: str = Field("default", description="当前用户角色")
) -> str:
    """
    [场景] 这个工具用于...
    [关键词] 关键词1、关键词2
    """
    # 权限检查
    if not PermissionService.check_well_access(user_role, param1):
        return "🚫 权限拒绝。"
    
    # 业务逻辑
    session = Session()
    try:
        # ... 数据库查询 ...
        return "结果"
    finally:
        session.close()
```

### 添加新的数据表

1. 在 `Part 2` 中定义新的 SQLAlchemy 模型
2. 在 `seed_mock_data()` 中添加模拟数据
3. 创建对应的查询工具

## 📄 许可证

本项目代码仅供学习和参考使用。

## 🤝 支持

如有问题或建议，请通过以下方式联系：
- 查看代码注释
- 参考 FastMCP 官方文档：https://github.com/jlowin/fastmcp
- 参考 MCP 协议文档：https://modelcontextprotocol.io

---

**祝您使用愉快！** 🎉
