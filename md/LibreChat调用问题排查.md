# LibreChat 调用问题排查与解决

## 🔍 问题现象

用户查询"DG-092的钻井日报"时：
- ❌ 工具被调用了多次（3-4次）
- ❌ 每次都返回"思考内容"
- ❌ 最后才返回正确结果
- ❌ 没有触发日期追问机制

## 🎯 根本原因

LibreChat 的 Claude 模型在调用 MCP 工具时，可能存在以下问题：

1. **工具描述不够清晰**：之前的描述"不填则查询最新"，导致 LLM 认为可以多次尝试
2. **参数是否必填不明确**：`date` 参数标记为必填，LLM 会尝试猜测值
3. **缺少明确的行为指导**：没有告诉 LLM"留空会返回可选日期"

## ✅ 解决方案

### 1. 已完成的优化

#### (1) 更新工具描述
```json
{
  "name": "get_daily_report",
  "description": "获取指定日期的钻井日报。重要：如果用户未指定具体日期，请将date留空，系统会列出可用日期供选择，避免重复调用。",
  "inputSchema": {
    "properties": {
      "well_id": {"type": "string", "description": "井号"},
      "date": {"type": "string", "description": "日期(YYYY-MM-DD)，如用户未明确指定则留空"}
    },
    "required": ["well_id"]  // 注意：date不是必填的
  }
}
```

**关键点**：
- ✅ `date` 参数改为**可选**（从 `required` 中移除）
- ✅ 明确说明"如用户未指定则留空"
- ✅ 强调"避免重复调用"

#### (2) 实现智能追问逻辑
```python
def get_daily_report(well_id: str, date_str: str = "", ...):
    # 如果日期为空，返回可用日期列表
    if not date_str or date_str.strip() == "":
        recent_reports = query_recent_5_reports(well_id)
        return f"""
### ℹ️ 请明确查询日期

您查询的是 **{well_id}** 的日报，但未指定具体日期。

以下是该井最近的日报记录：
- 2023-10-31 (井深: 5240.0m, 进尺: 100.0m)
- 2023-10-30 (井深: 5140.0m, 进尺: 100.0m)
...

**请明确指定日期**
"""
    
    # 如果有日期，返回具体日报
    return get_report_details(well_id, date_str)
```

#### (3) 添加查询缓存
```python
_daily_report_cache = {}
_cache_ttl = 60  # 60秒缓存

# 相同查询60秒内直接返回缓存，避免重复数据库查询
```

### 2. 需要重启服务

**重要**：修改后必须重启 HTTP 服务器才能生效！

```bash
# Windows PowerShell
cd d:\work\oilMCP
.\start_http_server.bat
```

### 3. 验证服务已更新

启动后检查日志，应该看到：
```
✅ Mock data seeded successfully.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

或者访问：http://localhost:8080/health

## 🧪 测试方法

### 测试1：未指定日期（触发追问）
```
用户输入："查询DG-092的日报"

预期行为：
1. LLM调用：get_daily_report(well_id="DG-092", date="")
2. 系统返回：可用日期列表（最近5条）
3. LLM向用户展示日期列表
4. 用户选择具体日期后再次查询
```

### 测试2：指定了日期
```
用户输入："查询DG-092在2023-10-31的日报"

预期行为：
1. LLM调用：get_daily_report(well_id="DG-092", date="2023-10-31")
2. 系统返回：完整日报内容
3. 只调用一次工具
```

### 测试3：使用相对时间
```
用户输入："查询DG-092昨天的日报"

预期行为：
1. LLM调用：get_daily_report(well_id="DG-092", date="昨天")
2. 系统自动归一化：昨天 → 2023-10-31
3. 返回日报内容
```

## 🐛 如果还是多次调用怎么办？

### 可能原因1：服务未重启
**解决**：确保重启了 HTTP 服务器

### 可能原因2：LibreChat 使用了错误的端点
**检查**：LibreChat 应该使用 `http://localhost:8080/sse`
```yaml
# librechat.yaml
mcpServers:
  oilfield-drilling:
    transport: "sse"
    url: "http://localhost:8080/sse"
    disabled: false
```

### 可能原因3：Claude 缓存了旧的工具定义
**解决**：
1. 在 LibreChat 中重新加载 MCP 服务
2. 或者重启 LibreChat

### 可能原因4：Claude 的推理行为
**观察日志**：
```bash
# 查看工具调用日志
tail -f logs/mcp_server.log

# 应该看到：
# ✅ [HTTP] 使用缓存数据: DG-092_2023-10-31_ADMIN
```

如果工具被调用多次但参数不同（如 date=""、date="今天"、date="2023-10-31"），说明 Claude 还在猜测。

**临时解决方案**：在 LibreChat 的 System Prompt 中添加：
```
在调用 get_daily_report 工具时：
- 如果用户未明确指定日期，请将 date 参数留空（传递空字符串 ""）
- 不要猜测日期，等待系统返回可用日期列表
- 只调用工具一次，不要重复调用
```

## 📊 预期效果对比

### 优化前
```
调用次数：4次
- get_daily_report(well_id="DG-092", date="")      → 思考内容
- get_daily_report(well_id="DG-092", date="今天")  → 思考内容
- get_daily_report(well_id="DG-092", date="today") → 思考内容
- get_daily_report(well_id="DG-092", date="2023-10-31") → 成功
```

### 优化后
```
调用次数：1次（未指定日期）或 1次（指定日期）

场景1（用户未指定）：
- get_daily_report(well_id="DG-092", date="") → 返回可用日期列表
- 用户看到列表后选择
- get_daily_report(well_id="DG-092", date="2023-10-31") → 成功

场景2（用户指定）：
- get_daily_report(well_id="DG-092", date="2023-10-31") → 直接成功
```

## 🔧 调试命令

### 查看当前工具定义
```bash
curl http://localhost:8080/mcp/tools | python -m json.tool
```

应该看到：
```json
{
  "tools": [
    {
      "name": "get_daily_report",
      "description": "获取指定日期的钻井日报。重要：如果用户未指定具体日期，请将date留空...",
      "inputSchema": {
        "required": ["well_id"]  // ← 注意 date 不在这里
      }
    }
  ]
}
```

### 手动测试工具调用
```python
# 运行测试脚本
python test_date_prompt.py

# 应该看到：
# 测试1：返回可用日期列表 ✅
# 测试2：返回具体日报 ✅
# 测试3：使用了缓存 ✅
```

## 📝 总结

优化的核心是：
1. ✅ **参数设计**：date 改为可选参数
2. ✅ **工具描述**：明确说明"留空会返回可选日期"
3. ✅ **行为引导**：在描述中加入"避免重复调用"
4. ✅ **缓存机制**：60秒内相同查询直接返回缓存
5. ✅ **智能追问**：date 为空时返回最近5条记录供选择

记得重启服务！🚀
