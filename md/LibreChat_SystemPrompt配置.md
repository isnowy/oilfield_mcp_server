# LibreChat System Prompt 配置建议

## 📋 问题说明

当用户查询"查看DG-088的钻井日报"这类请求时，LLM可能会：
- ❌ 猜测日期并填写 date 参数（如 "今天"、"最新"）
- ❌ 多次调用工具尝试不同日期
- ❌ 不触发日期追问机制

## ✅ 解决方案

在 LibreChat 的**自定义指令**或 **System Prompt** 中添加以下内容：

```markdown
## MCP 工具调用规则

### get_daily_report 工具使用规范

当用户查询钻井日报时，请严格遵守以下规则：

1. **判断用户是否明确指定日期**：
   - ✅ 明确日期："查询DG-088在2023-11-10的日报" → date="2023-11-10"
   - ✅ 相对时间："查询DG-088昨天的日报" → date="昨天"
   - ❌ 模糊表达："查询DG-088的日报" → date="" (留空)
   - ❌ 模糊词汇："查询DG-088最新的日报" → date="" (留空)

2. **date参数填写原则**：
   - 只有当用户**明确说出具体日期或相对时间**时才填写
   - 如果用户只是说"日报"、"最新日报"、"查看日报"，date参数**必须留空**
   - 留空后系统会自动返回可用日期列表供用户选择

3. **禁止行为**：
   - ❌ 不要猜测或推断日期
   - ❌ 不要多次调用工具尝试不同日期
   - ❌ 不要将"最新"、"当前"等词汇作为日期参数

4. **正确流程示例**：
   ```
   用户："查看DG-088的日报"
   ↓
   调用：get_daily_report(well_id="DG-088", date="")
   ↓
   系统返回：可用日期列表（2023-11-10, 2023-11-09...）
   ↓
   展示给用户：请选择具体日期
   ```

### 其他工具使用规范

对于所有 MCP 工具：
- 每个工具只调用一次，除非用户明确要求重试
- 如果工具返回"请明确..."之类的提示，将其展示给用户而不是重试
- 相信工具的返回结果，不要尝试"修正"或"优化"
```

## 🎯 配置位置

### LibreChat 设置路径
1. 打开 LibreChat
2. 点击右上角设置（齿轮图标）
3. 选择 **Custom Instructions** 或 **系统提示词**
4. 将上述内容粘贴进去
5. 保存

### 或者在 librechat.yaml 中配置

```yaml
endpoints:
  custom:
    - name: "Claude with MCP"
      apiKey: "${ANTHROPIC_API_KEY}"
      baseURL: "https://api.anthropic.com/v1"
      models:
        default: ["claude-3-5-sonnet-20241022"]
      systemPrompt: |
        你是一个专业的油田钻井数据助手。
        
        ## MCP 工具调用规则
        
        ### get_daily_report 工具使用规范
        
        当用户查询钻井日报时：
        1. 判断用户是否明确指定日期
        2. 只有明确日期时才填写 date 参数
        3. 否则留空，让系统返回可用日期列表
        4. 不要猜测日期或多次尝试
```

## 🧪 验证方法

配置后测试以下场景：

### 测试1：模糊查询
```
输入："查看DG-088的日报"

预期：
✅ 只调用工具1次，date参数为空
✅ 返回可用日期列表
✅ 提示用户选择具体日期
```

### 测试2：明确日期
```
输入："查看DG-088在2023-11-10的日报"

预期：
✅ 只调用工具1次，date="2023-11-10"
✅ 直接返回日报内容
```

### 测试3：相对时间
```
输入："查看DG-088昨天的日报"

预期：
✅ 只调用工具1次，date="昨天"
✅ 系统自动转换为标准日期
✅ 返回日报内容
```

## 📊 预期改进效果

### 优化前
- 工具调用次数：3-5次
- 响应时间：较慢
- 用户体验：需要等待多次尝试

### 优化后
- 工具调用次数：1次
- 响应时间：快速
- 用户体验：清晰的交互流程

## 🔍 如果还是有问题

### 检查清单
1. ☑ 已重启 HTTP 服务器
2. ☑ 已配置 System Prompt
3. ☑ 已重新加载 LibreChat 的 MCP 连接
4. ☑ 确认使用正确的端点 (http://localhost:8080/sse)

### 查看日志
```bash
# 实时查看 MCP 服务器日志
# 应该看到类似内容：
# {"event": "TOOL_START", "tool": "get_daily_report", "params": {}}
# {"event": "TOOL_SUCCESS", "duration_ms": 3.0, "result_length": 363}
```

如果看到工具被多次调用且参数不同，说明 Claude 还在尝试猜测，需要加强 System Prompt。

## 💡 额外技巧

### 更严格的 Prompt（如果上述方法还不够）

```markdown
## CRITICAL RULE for get_daily_report

BEFORE calling get_daily_report:
1. Ask yourself: "Did the user say a SPECIFIC date?"
   - YES: Use that date → date="2023-11-10" or date="昨天"
   - NO: Leave empty → date=""

2. NEVER assume or guess dates
3. NEVER call the tool multiple times
4. Trust the tool's response

Examples:
- "查询日报" → date="" ← EMPTY!
- "最新日报" → date="" ← EMPTY!
- "今天的日报" → date="今天" ← OK
- "2023-11-10的日报" → date="2023-11-10" ← OK
```

## 📚 相关文档
- [查询优化说明.md](./查询优化说明.md)
- [LibreChat调用问题排查.md](./LibreChat调用问题排查.md)
