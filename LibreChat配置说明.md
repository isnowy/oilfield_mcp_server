# LibreChat MCP 集成配置说明

## 📋 两种配置方式

### ✅ 方式一：HTTP/SSE 方式（推荐）

**优点：**
- ✅ 配置文件中**不暴露数据库信息**
- ✅ 支持动态用户权限控制
- ✅ 多个 LibreChat 实例可共享一个 MCP 服务器
- ✅ 服务独立部署和维护
- ✅ 更好的性能和扩展性

**配置文件：** `librechat_mcp_config.json`

```yaml
mcpServers:
  oilfield-wells:
    type: http
    url: "http://localhost:8081/sse"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    title: "Oilfield Wells Data Service"
    description: "Oil well search, details query, and statistical analysis"
  
  oilfield-dailyreports:
    type: http
    url: "http://localhost:8082/sse"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    title: "Oilfield Daily Reports Service"
    description: "Drilling reports and key well production data"
```

**使用步骤：**

1. **启动 MCP 服务器**（在 oilMCP 项目目录）
   ```cmd
   start_all_mcps.bat
   ```

2. **配置数据库环境变量**（在启动脚本中已设置）
   ```powershell
   $env:DB_HOST = "localhost"
   $env:DB_PORT = "5432"
   $env:DB_NAME = "rag"
   $env:DB_USER = "postgres"
   $env:DB_PASSWORD = "postgres"
   $env:DEV_MODE = "true"
   ```

3. **将配置添加到 LibreChat**
   - 将 `librechat_mcp_config.json` 的内容添加到 LibreChat 配置文件中

4. **重启 LibreChat**
   ```bash
   # 重启 LibreChat 使配置生效
   docker-compose restart librechat
   ```

---

### ⚠️ 方式二：stdio 方式（备选）

**优点：**
- ✅ LibreChat 直接管理 MCP 进程
- ✅ 配置简单

**缺点：**
- ❌ 配置文件中需要包含数据库密码
- ❌ 每个用户会话都启动独立进程（资源占用高）
- ❌ 不支持多 LibreChat 实例共享

**配置文件：** `librechat_mcp_config_stdio.json`

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

**使用步骤：**

1. **配置 LibreChat**
   - 将配置添加到 LibreChat 的 MCP 配置文件
   - 修改数据库连接信息

2. **重启 LibreChat**
   - LibreChat 会自动启动 MCP 进程

---

## 🔄 从旧架构迁移

### 旧配置（单一 MCP）
```yaml
mcpServers:
  oilfield-drilling:
    type: http
    url: "http://localhost:8081/sse"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    title: "Oilfield Drilling Data Service"
```

### 新配置（多 MCP - 推荐）
```yaml
mcpServers:
  oilfield-wells:
    type: http
    url: "http://localhost:8081/sse"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    title: "Oilfield Wells Data Service"
  
  oilfield-dailyreports:
    type: http
    url: "http://localhost:8082/sse"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    title: "Oilfield Daily Reports Service"
```

**变化说明：**
- ✅ 从 1 个服务拆分为 2 个服务
- ✅ `oilfield-wells` (8081) - 油井基础数据（5个工具）
- ✅ `oilfield-dailyreports` (8082) - 日报系统（3个工具）
- ✅ 工具更清晰，LLM 选择更精准
- ✅ 服务可以独立升级和维护

---

## 🔒 权限控制说明

### 动态权限传递
LibreChat 会通过 HTTP headers 传递用户信息：

```yaml
headers:
  X-User-Role: "{{LIBRECHAT_USER_ROLE}}"      # 用户角色
  X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"    # 用户邮箱
  X-User-ID: "{{LIBRECHAT_USER_ID}}"          # 用户ID
```

### 支持的角色
MCP 服务器根据角色控制访问权限：

| 角色 | 权限 |
|------|------|
| `ADMIN` | 所有油井的完全访问权限 |
| `ENGINEER` | 指定区块的油井 + 公共数据 |
| `VIEWER` | 指定油井的只读访问 |
| `USER` / `GUEST` | 仅公共数据 |

### 开发模式
在启动脚本中设置 `DEV_MODE=true` 可以跳过权限检查（仅用于开发测试）：

```powershell
$env:DEV_MODE = "true"  # 开发模式
$env:DEV_MODE = "false" # 生产模式
```

---

## 🧪 验证配置

### 1. 检查服务状态
```powershell
# 检查油井基础数据服务
Invoke-WebRequest http://localhost:8081/health

# 检查日报系统服务
Invoke-WebRequest http://localhost:8082/health
```

### 2. 测试工具调用
在 LibreChat 中测试：

**油井基础数据:**
- "查询所有油井"
- "查询 ZT-102 的详细信息"
- "统计各区块的油井数量"

**日报系统:**
- "查询 DG-092 的钻井日报"
- "查询重点井试采日报"
- "查询钻前工程日报"

### 3. 测试权限控制
使用不同角色的用户测试：
- ADMIN 用户应能查看所有数据
- ENGINEER 用户只能查看授权的井
- GUEST 用户只能查看公共数据

---

## 🐛 常见问题

### 问题 1：无法连接到 MCP 服务器
**解决方案：**
1. 确认 MCP 服务器已启动（`start_all_mcps.bat`）
2. 检查端口是否被占用（8081, 8082）
3. 查看服务健康状态（访问 /health 端点）

### 问题 2：数据库连接失败
**解决方案：**
1. 检查 PostgreSQL 是否启动
2. 验证启动脚本中的数据库配置
3. 检查数据库用户权限

### 问题 3：权限控制不生效
**解决方案：**
1. 确认 `DEV_MODE=false`（生产模式）
2. 检查 LibreChat 是否正确传递用户信息
3. 查看 MCP 服务器日志确认接收到的角色信息

### 问题 4：配置中数据库密码安全问题
**解决方案：**
- **推荐使用 HTTP 方式**，数据库配置在启动脚本中设置
- 启动脚本可以从 `.env` 文件或环境变量读取敏感信息
- 不要将敏感配置提交到 git 仓库

---

## 📚 相关文档

- [README_新架构.md](./README_新架构.md) - 快速开始指南
- [项目结构说明.md](./项目结构说明.md) - 完整结构说明
- [md/MCP服务器拆分方案.md](./md/MCP服务器拆分方案.md) - 架构设计
- [md/迁移指南.md](./md/迁移指南.md) - 从旧版迁移

---

## 🎯 推荐配置总结

对于生产环境，推荐使用 **HTTP/SSE 方式**：

```yaml
# ✅ 推荐配置
mcpServers:
  oilfield-wells:
    type: http
    url: "http://localhost:8081/sse"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
  
  oilfield-dailyreports:
    type: http
    url: "http://localhost:8082/sse"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
```

**优势：**
- ✅ 安全（不暴露数据库信息）
- ✅ 高性能（单实例服务多用户）
- ✅ 易维护（独立部署和升级）
- ✅ 可扩展（支持负载均衡）

---

**最后更新**: 2026年3月5日  
**版本**: v2.0
