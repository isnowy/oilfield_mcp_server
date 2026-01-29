# HTTP/SSE方案实施指南 - 完整操作流程

## 方案优势

与stdio方案相比：

| 特性 | stdio方案 | HTTP/SSE方案 ✅ |
|-----|----------|----------------|
| MCP Server实例数 | 每个角色一个 | 单个实例服务所有用户 |
| 用户信息传递 | ❌ 静态环境变量 | ✅ 动态HTTP headers |
| 权限验证时机 | 启动时固定 | 每次请求时验证 |
| 资源占用 | 多进程 | 单进程 |
| 扩展性 | ❌ 需要创建新实例 | ✅ 自动适配新角色 |
| 配置复杂度 | 高（需要ACL） | 低（只需配置headers） |

## 前置条件

1. ✅ Python 3.8+
2. ✅ LibreChat支持HTTP/SSE类型MCP Server
3. ✅ 权限系统已实现（permissions.py）
4. ✅ 数据库已准备好

## 实施步骤

### 步骤1: 安装依赖（2分钟）

```bash
cd d:\work\oilMCP

# 安装HTTP相关依赖
pip install -r requirements_http.txt

# 或手动安装
pip install fastapi uvicorn[standard] pydantic mcp
```

### 步骤2: 测试HTTP Server（2分钟）

```bash
# 启动HTTP MCP Server
python oilfield_mcp_http_server.py
```

应该看到：

```
============================================================
油田钻井数据MCP Server - HTTP/SSE版本
============================================================
数据库: d:/work/oilMCP/oilfield.db
端口: 8080

🚀 油田钻井数据MCP Server (HTTP/SSE) 启动中...
📍 监听地址: http://0.0.0.0:8080
INFO:     Uvicorn running on http://0.0.0.0:8080
```

保持这个窗口打开，Server需要持续运行。

### 步骤3: 验证Server运行（1分钟）

打开新的PowerShell窗口：

```powershell
# 健康检查
curl http://localhost:8080/health

# 应该返回：
# {
#   "status": "healthy",
#   "database": "connected",
#   "total_records": N
# }

# 查看可用工具
curl http://localhost:8080/mcp/tools

# 测试工具调用（管理员权限）
curl -X POST http://localhost:8080/mcp/call-tool `
  -H "Content-Type: application/json" `
  -H "X-User-Role: ADMIN" `
  -H "X-User-Email: admin@test.com" `
  -d '{\"name\":\"query_drilling_data\",\"arguments\":{\"limit\":5}}'

# 测试权限拒绝（用户尝试删除）
curl -X POST http://localhost:8080/mcp/call-tool `
  -H "Content-Type: application/json" `
  -H "X-User-Role: USER" `
  -H "X-User-Email: user@test.com" `
  -d '{\"name\":\"delete_drilling_record\",\"arguments\":{\"record_id\":1}}'

# 应该返回 403 Forbidden
```

### 步骤4: 配置LibreChat（3分钟）

编辑 `d:\work\librechat\librechat.yaml`：

```yaml
version: 1.3.1
cache: true

interface:
  mcpServers:
    use: true
    create: false  # HTTP方案不需要通过UI创建
    share: false
    public: false

mcpServers:
  # 单个HTTP MCP Server，服务所有用户
  oilfield-drilling:
    type: sse  # 或 streamable-http
    url: "http://localhost:8080/mcp/call-tool"
    
    # ⭐ 关键：通过headers传递用户信息
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    
    title: "油田钻井数据服务"
    description: "提供油田钻井数据查询、管理和分析功能，权限基于用户角色动态控制"
    
    timeout: 60000
    disabled: false

# DeepSeek和Qwen配置保持不变
endpoints:
  custom:
    - name: "DeepSeek"
      apiKey: "${DEEPSEEK_API_KEY}"
      baseURL: "https://api.deepseek.com/v1"
      models:
        default:
          - "deepseek-chat"
      # ... 其他配置
```

### 步骤5: 设置用户角色（1分钟）

```bash
cd d:\work\librechat

# 确认现有用户角色
node scripts\list-users-with-roles.js

# 设置管理员
node scripts\set-user-role.js 18202727050@163.com ADMIN

# 设置普通用户（如果有）
node scripts\set-user-role.js user@example.com USER
```

### 步骤6: 清理旧配置（1分钟）

如果之前使用了stdio + ACL方案：

```bash
# 可选：删除数据库中的旧MCP Server记录
# 进入MongoDB
docker-compose exec mongodb mongosh librechat

# 查看现有MCP Servers
db.mcpservers.find()

# 删除旧的stdio MCP Servers
db.mcpservers.deleteMany({ "config.type": "stdio" })

# 删除相关权限
db.permissions.deleteMany({ resourceType: "mcpServer" })
```

### 步骤7: 重启LibreChat（1分钟）

```bash
cd d:\work\librechat
docker-compose restart
```

等待服务完全启动（约30秒）。

### 步骤8: 验证功能（3分钟）

#### 验证1: 管理员用户

1. 使用ADMIN账号登录（18202727050@163.com）
2. 创建新对话
3. 在MCP Servers中应该看到 **"油田钻井数据服务"**
4. 测试调用工具：

```
查询最近10条钻井数据
```

5. 测试管理员专用工具：

```
导出所有钻井数据
```

应该成功执行。

6. 查看Server日志（HTTP Server窗口），应该看到：

```
📥 接收到用户上下文:
  Role: ADMIN
  Email: 18202727050@163.com
  User ID: xxx

🔧 工具调用: export_all_data
🔐 权限检查: export_all_data
  用户角色: ADMIN
  是否允许: ✓
✓ 执行成功
```

#### 验证2: 普通用户

1. 使用USER账号登录
2. 创建新对话
3. 测试基础工具（应该成功）：

```
查询井号为W001的钻井数据
```

4. 尝试调用管理员工具（应该被拒绝）：

```
导出所有钻井数据
```

应该收到错误消息：**"权限不足：用户角色 USER 无权访问工具 export_all_data"**

5. Server日志应该显示：

```
📥 接收到用户上下文:
  Role: USER
  Email: user@example.com

🔧 工具调用: export_all_data
🔐 权限检查: export_all_data
  用户角色: USER
  是否允许: ✗
```

## 生产部署

### 使用Systemd（Linux）

创建 `/etc/systemd/system/oilfield-mcp.service`：

```ini
[Unit]
Description=油田钻井数据MCP Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/oilMCP
Environment="DATABASE_URL=sqlite:////opt/oilMCP/oilfield.db"
ExecStart=/usr/bin/python3 /opt/oilMCP/oilfield_mcp_http_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable oilfield-mcp
sudo systemctl start oilfield-mcp
sudo systemctl status oilfield-mcp
```

### 使用Docker

创建 `Dockerfile.mcp`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements_http.txt .
RUN pip install --no-cache-dir -r requirements_http.txt

COPY oilfield_mcp_http_server.py .
COPY permissions.py .

ENV DATABASE_URL=sqlite:////data/oilfield.db

EXPOSE 8080

CMD ["python", "oilfield_mcp_http_server.py"]
```

构建和运行：

```bash
# 构建镜像
docker build -f Dockerfile.mcp -t oilfield-mcp:latest .

# 运行容器
docker run -d \
  --name oilfield-mcp \
  -p 8080:8080 \
  -v /path/to/data:/data \
  oilfield-mcp:latest
```

### 使用Nginx反向代理

```nginx
server {
    listen 443 ssl;
    server_name mcp.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 保留MCP headers
        proxy_pass_request_headers on;
    }
}
```

然后在librechat.yaml中使用HTTPS URL：

```yaml
mcpServers:
  oilfield-drilling:
    type: sse
    url: "https://mcp.yourdomain.com/mcp/call-tool"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
```

## 添加更多工具

编辑 `oilfield_mcp_http_server.py`：

```python
# 1. 在 list_tools() 中添加工具定义
@mcp_app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        # ... 现有工具
        Tool(
            name="new_tool_name",
            description="新工具描述（需要XXX权限）",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        ),
    ]

# 2. 在 call_tool() 中添加处理逻辑
@app.post("/mcp/call-tool")
async def call_tool(request: ToolCallRequest, ...):
    # ...
    elif tool_name == "new_tool_name":
        result = handle_new_tool(arguments)
    # ...

# 3. 实现工具函数
def handle_new_tool(args: Dict) -> Dict:
    # 工具逻辑
    return {"result": "..."}
```

重启Server：

```bash
# 按 Ctrl+C 停止
python oilfield_mcp_http_server.py
```

无需重启LibreChat，新工具会自动可用。

## 监控和日志

### 查看实时日志

```bash
# HTTP Server控制台会显示所有请求
# 包括用户信息、工具调用、权限检查结果
```

### 添加日志记录

编辑 `oilfield_mcp_http_server.py`，添加：

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 在关键位置添加日志
logger.info(f"Tool called: {tool_name} by {user_context.email}")
logger.warning(f"Permission denied: {tool_name} for {user_context.role}")
```

### 性能监控

添加Prometheus指标：

```python
from prometheus_client import Counter, Histogram, generate_latest

# 定义指标
tool_calls = Counter('mcp_tool_calls_total', 'Total tool calls', ['tool_name', 'role'])
permission_denials = Counter('mcp_permission_denials_total', 'Permission denials', ['tool_name', 'role'])
request_duration = Histogram('mcp_request_duration_seconds', 'Request duration')

# 在call_tool中记录
tool_calls.labels(tool_name=tool_name, role=user_context.role).inc()

# 添加指标端点
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 故障排除

### 问题1: LibreChat无法连接到HTTP Server

**检查**：

```bash
# 1. 确认Server正在运行
curl http://localhost:8080/health

# 2. 检查防火墙
netsh advfirewall firewall add rule name="MCP Server" dir=in action=allow protocol=TCP localport=8080

# 3. 查看LibreChat日志
docker-compose logs api | grep -i mcp
```

### 问题2: Headers未传递

**检查librechat.yaml配置**：

```yaml
headers:
  X-User-Role: "{{LIBRECHAT_USER_ROLE}}"  # 确保大括号正确
```

**查看Server日志**，应该看到headers值：

```
📥 接收到用户上下文:
  Role: ADMIN  # 如果显示为 {{LIBRECHAT_USER_ROLE}}，说明占位符未替换
```

### 问题3: 权限检查不生效

**验证permissions.py**：

```bash
cd d:\work\oilMCP
python test_permissions_quick.py
```

**检查角色映射**：

```python
# 在 oilfield_mcp_http_server.py 中添加调试
print(f"原始角色: {user_context.role}")
print(f"映射后角色: {user_role}")
print(f"权限配置: {checker.get_user_context()}")
```

### 问题4: Server崩溃或重启

**查看错误日志**：

```bash
# 如果使用systemd
sudo journalctl -u oilfield-mcp -n 100

# 如果使用Docker
docker logs oilfield-mcp
```

**常见原因**：
- 数据库文件损坏
- 内存不足
- 未处理的异常

**添加错误处理**：

```python
@app.post("/mcp/call-tool")
async def call_tool(...):
    try:
        # ... 工具逻辑
    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

## 对比总结

### stdio + ACL方案

**适用场景**：
- 需要使用现有stdio MCP Server
- 不想额外部署HTTP服务
- 用户角色固定，不常变化

**缺点**：
- 每个角色需要独立进程
- 需要配置ACL权限
- 添加新角色需要创建新Server

### HTTP/SSE方案（✅推荐）

**适用场景**：
- 需要灵活的权限控制
- 用户角色可能变化
- 需要真正的per-request验证
- 计划添加更多角色

**优点**：
- 单个Server实例
- 动态权限验证
- 易于扩展和维护
- 更好的性能和资源利用

## 下一步

1. ✅ 按照本指南完成HTTP/SSE方案部署
2. ✅ 验证所有功能正常
3. ✅ 配置生产环境部署（Systemd/Docker）
4. ✅ 设置监控和日志
5. ✅ 根据需要添加更多工具

HTTP/SSE方案是更现代、更灵活的选择，强烈推荐用于生产环境！
