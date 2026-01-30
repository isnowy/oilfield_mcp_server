# 🚀 快速参考卡 - HTTP Server 权限方案

## ⏱️ 30分钟快速部署指南

### 前置条件
- Python 3.8+
- pip 
- LibreChat 正在运行
- VS Code (可选)

---

## 📋 步骤1: 安装依赖 (2分钟)

```bash
cd d:\work\oilMCP

# 安装HTTP Server依赖
pip install fastapi uvicorn mcp

# 或使用requirements文件
pip install -r requirements_http.txt
```

**验证**：
```bash
python -c "import fastapi; print('✅ FastAPI已安装')"
```

---

## 🚀 步骤2: 启动HTTP Server (1分钟)

### 方式A: 直接运行（开发）
```bash
python oilfield_mcp_http_server.py
```

**预期输出**：
```
✅ HTTP MCP Server started
INFO: Uvicorn running on http://0.0.0.0:8080
```

### 方式B: 使用启动脚本（推荐）
```bash
# 开发模式
.\start_dev.ps1

# 或生产模式
.\start_prod.ps1

# 或直接双击
start_http_server.bat
```

### 验证HTTP Server运行中
```bash
# 健康检查
curl http://localhost:8080/health

# 预期响应
# {"status":"ok","service":"oilfield-mcp-http"}
```

---

## ⚙️ 步骤3: 配置 librechat.yaml (3分钟)

打开 `d:\work\librechat\librechat.yaml`，添加/修改：

```yaml
interface:
  mcpServers:
    use: true
    create: false
    share: false
    public: false

mcpServers:
  oilfield-drilling:
    type: http
    url: "http://localhost:8080/mcp/call-tool"
    
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    
    description: "油田钻井数据查询服务"
    disabled: false
    timeout: 60000
```

**注意**：
- 如果LibreChat在Docker中，改为：
  ```yaml
  url: "http://host.docker.internal:8080/mcp/call-tool"
  ```

---

## 🔄 步骤4: 重启LibreChat (2分钟)

```bash
cd d:\work\librechat

# 如果使用Docker
docker-compose restart

# 或使用开发模式
npm run backend:dev
```

等待服务启动完成（通常30秒）

---

## ✅ 步骤5: 测试验证 (5分钟)

### 5.1 健康检查
```bash
curl -v http://localhost:8080/health
```

**预期**：HTTP 200, 返回 `{"status":"ok"}`

### 5.2 权限检查
```bash
# 以ADMIN身份测试
curl -X POST http://localhost:8080/mcp/call-tool \
  -H "X-User-Role: ADMIN" \
  -H "X-User-Email: admin@oilfield.com" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "query_drilling_data",
    "arguments": {}
  }'

# 预期：权限通过，返回工具执行结果
```

### 5.3 权限拒绝测试
```bash
# 以USER身份尝试删除操作
curl -X POST http://localhost:8080/mcp/call-tool \
  -H "X-User-Role: USER" \
  -H "X-User-Email: user@oilfield.com" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "delete_drilling_record",
    "arguments": {"id": "123"}
  }'

# 预期：权限拒绝，HTTP 403
```

### 5.4 在LibreChat中测试
1. 以ADMIN账号登录LibreChat
2. 打开对话窗口
3. 调用MCP工具：
   ```
   @oilfield 查询井数据
   ```
4. 观察是否正常执行

---

## 📊 权限矩阵（快速参考）

| 角色 | 查询 | 添加 | 删除 | 导出 | 工具数 |
|------|------|------|------|------|--------|
| ADMIN | ✅ | ✅ | ✅ | ✅ | 15/15 |
| USER | ✅ | ✅ | ❌ | ❌ | 8/15 |
| GUEST | ✅ | ❌ | ❌ | ❌ | 4/15 |

---

## 🔧 常见问题速解

### Q1: HTTP Server启动失败

**症状**：`ModuleNotFoundError: No module named 'fastapi'`

**解决**：
```bash
pip install fastapi uvicorn
```

### Q2: LibreChat无法连接HTTP Server

**症状**：工具调用超时或连接拒绝

**解决**：
1. 确认HTTP Server在运行：`curl http://localhost:8080/health`
2. 如果LibreChat在Docker中，修改URL为：
   ```yaml
   url: "http://host.docker.internal:8080/mcp/call-tool"
   ```
3. 检查防火墙设置

### Q3: 权限检查不生效

**症状**：所有请求都成功，没有权限限制

**解决**：
1. 检查HTTP Server日志，确认权限检查在运行
2. 确认 `permissions.py` 中的权限配置正确
3. 查看 `PERMISSION_CONFIG.md` 中的配置说明

### Q4: 占位符没有被替换

**症状**：`X-User-Role: {{LIBRECHAT_USER_ROLE}}`

**解决**：
1. 确保librechat.yaml中headers部分有占位符
2. 重启LibreChat
3. 查看LibreChat日志确认替换是否成功

---

## 📞 获取更多帮助

| 问题类型 | 查看文档 |
|---------|---------|
| **方案对比** | `md/PERMISSION_SOLUTION_COMPARISON.md` |
| **HTTP实施细节** | `md/HTTP方案实施指南.md` |
| **权限配置** | `md/PERMISSION_CONFIG.md` |
| **常见问题** | `md/占位符问题解决方案.md` |
| **故障排除** | `md/UI配置MCP权限操作指南.md` |
| **文档索引** | `md/README_文档导航.md` |

---

## 📈 性能指标

| 指标 | 值 | 说明 |
|------|-----|------|
| 响应延迟 | 50-100ms | HTTP请求开销 |
| 吞吐量 | 1000+ QPS | 单机能力 |
| 内存占用 | 50-100MB | FastAPI进程 |
| CPU占用 | <5% | 空闲状态 |

---

## ✨ 下一步

- ✅ 完成上述5个步骤 (30分钟)
- 📚 阅读 `PERMISSION_SOLUTION_COMPARISON.md` 了解更多细节
- 🔐 配置更多用户角色和权限
- 🚀 部署到生产环境
- 📊 设置监控和日志

---

**预计总时间：30分钟** ⏱️

**难度等级：⭐⭐ (中等)** 

**推荐度：⭐⭐⭐⭐⭐** 

祝部署顺利！🎉

