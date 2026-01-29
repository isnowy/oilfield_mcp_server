# stdio vs HTTP/SSE方案 - 完整对比

## 快速决策表

| 如果你... | 推荐方案 |
|---------|---------|
| 需要最简单的配置 | HTTP/SSE ✅ |
| 需要灵活的权限控制 | HTTP/SSE ✅ |
| 已有stdio MCP Server | stdio + ACL |
| 不想额外部署HTTP服务 | stdio + ACL |
| 计划添加多个角色 | HTTP/SSE ✅ |
| 需要真正的per-request验证 | HTTP/SSE ✅ |
| 资源受限（内存/CPU） | HTTP/SSE ✅ |

## 详细对比

### 1. 架构对比

#### stdio + ACL方案

```
LibreChat启动
    ↓
启动多个stdio MCP进程
    ├─ oilfield-admin (ROLE=ADMIN, 独立进程)
    ├─ oilfield-user  (ROLE=USER, 独立进程)
    └─ oilfield-guest (ROLE=GUEST, 独立进程)
    ↓
用户登录
    ↓
ACL检查 → 返回该用户有权限的MCP Servers
    ↓
ADMIN用户看到: oilfield-admin
USER用户看到: oilfield-user
```

**特点**：
- 每个角色一个进程
- 环境变量静态（启动时固定）
- 通过ACL控制可见性

#### HTTP/SSE方案

```
LibreChat启动
    ↓
单个HTTP MCP Server (监听8080端口)
    ↓
用户登录 → 发起工具调用
    ↓
LibreChat发送HTTP请求
    headers:
      X-User-Role: ADMIN
      X-User-Email: admin@example.com
    ↓
HTTP Server接收请求
    ↓
从headers提取用户信息
    ↓
权限检查 (每次请求)
    ↓
执行工具 或 返回403
```

**特点**：
- 单个进程服务所有用户
- 用户信息动态传递（headers）
- 每次请求独立验证

### 2. 配置复杂度对比

#### stdio + ACL方案

**librechat.yaml (复杂)**:
```yaml
interface:
  mcpServers:
    create: true  # 需要启用创建功能

# 留空，通过API创建
mcpServers: {}
```

**需要执行的脚本**:
```bash
# 1. 创建MCP Server (需要JWT token)
node scripts/create-mcp-admin.js
node scripts/create-mcp-user.js

# 2. 配置ACL权限
node scripts/configure-mcp-acl.js mcp_xxx ADMIN
node scripts/configure-mcp-acl.js mcp_yyy USER

# 3. 重启
docker-compose restart
```

**配置文件**: 3个
- librechat.yaml
- create-mcp-admin.js
- configure-mcp-acl.js

**步骤数**: ~8步

#### HTTP/SSE方案

**librechat.yaml (简单)**:
```yaml
mcpServers:
  oilfield-drilling:
    type: sse
    url: "http://localhost:8080/mcp/call-tool"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
    title: "油田钻井数据服务"
```

**需要执行的脚本**:
```bash
# 1. 安装依赖
pip install -r requirements_http.txt

# 2. 启动HTTP Server
python oilfield_mcp_http_server.py

# 3. 重启LibreChat
docker-compose restart
```

**配置文件**: 1个
- librechat.yaml

**步骤数**: ~3步

### 3. 资源占用对比

假设有3个角色（ADMIN, USER, GUEST）：

#### stdio + ACL方案

| 资源 | 用量 |
|-----|------|
| 进程数 | 3个 (每角色一个) |
| 内存 | ~150-300MB (50-100MB × 3) |
| CPU | 低 (空闲时) |
| 启动时间 | ~6-15秒 (2-5秒 × 3) |

#### HTTP/SSE方案

| 资源 | 用量 |
|-----|------|
| 进程数 | 1个 |
| 内存 | ~80-120MB |
| CPU | 低 (空闲时) |
| 启动时间 | ~2-3秒 |

**节省**：
- 内存: 50-60%
- 启动时间: 66%

### 4. 扩展性对比

#### 添加新角色（如OPERATOR）

**stdio + ACL方案**:
```bash
# 1. 创建新的MCP Server实例
node scripts/create-mcp-operator.js  # 需要新脚本

# 2. 配置ACL
node scripts/configure-mcp-acl.js mcp_zzz OPERATOR

# 3. 重启LibreChat
docker-compose restart
```

**资源影响**: +1个进程 (+50-100MB内存)

**HTTP/SSE方案**:
```yaml
# librechat.yaml 无需修改
# permissions.py 添加新角色
class UserRole(Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    OPERATOR = "OPERATOR"  # 新角色
    GUEST = "GUEST"

# 配置权限映射
ROLE_PERMISSIONS = {
    UserRole.OPERATOR: [Permission.READ, Permission.WRITE],
    # ...
}

# 重启HTTP Server
python oilfield_mcp_http_server.py
```

**资源影响**: 无额外开销

### 5. 权限变更响应时间

#### 修改用户角色

**stdio + ACL方案**:
```bash
# 1. 修改数据库中的角色
node scripts/set-user-role.js user@example.com ADMIN

# 2. 删除旧权限
# (MongoDB操作)

# 3. 配置新权限
node scripts/configure-mcp-acl.js mcp_admin ADMIN

# 4. 重启LibreChat
docker-compose restart

# 生效时间: ~30秒
```

**HTTP/SSE方案**:
```bash
# 1. 修改数据库中的角色
node scripts/set-user-role.js user@example.com ADMIN

# 2. 用户重新登录

# 生效时间: 立即（下次请求）
```

### 6. 调试和监控对比

#### stdio + ACL方案

**查看日志**:
```bash
# LibreChat日志（混合所有MCP Server）
docker-compose logs api | grep mcp

# 难以区分不同进程的日志
```

**权限调试**:
```bash
# 需要检查ACL数据库
docker-compose exec mongodb mongosh librechat
db.permissions.find({resourceType: 'mcpServer'})

# 需要检查用户角色
db.users.find({}, {email: 1, role: 1})

# 复杂，多步骤
```

#### HTTP/SSE方案

**查看日志**:
```bash
# 直接查看HTTP Server控制台
# 清晰显示每个请求的用户信息和权限检查结果

📥 接收到用户上下文:
  Role: ADMIN
  Email: admin@example.com
🔧 工具调用: export_all_data
🔐 权限检查: export_all_data
  用户角色: ADMIN
  是否允许: ✓
✓ 执行成功
```

**权限调试**:
```bash
# 使用curl直接测试
curl -X POST http://localhost:8080/mcp/call-tool \
  -H "X-User-Role: USER" \
  -d '{"name":"export_all_data","arguments":{}}'

# 立即看到结果
# 简单，一步完成
```

### 7. 生产部署对比

#### stdio + ACL方案

**部署清单**:
- LibreChat容器
- MongoDB容器
- 3个Python MCP进程（内嵌在LibreChat中）
- 配置ACL权限脚本
- 用户管理脚本

**高可用**:
- 需要LibreChat高可用
- MCP进程随LibreChat重启
- 难以独立扩展

#### HTTP/SSE方案

**部署清单**:
- LibreChat容器
- MongoDB容器
- HTTP MCP Server（独立部署）
  - 可以用Docker
  - 可以用Systemd
  - 可以用Kubernetes

**高可用**:
- MCP Server可独立扩展
- 可以部署多个实例 + 负载均衡
- 独立监控和告警
- 零停机更新（滚动重启）

**示例（Kubernetes）**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oilfield-mcp
spec:
  replicas: 3  # 3个实例
  selector:
    matchLabels:
      app: oilfield-mcp
  template:
    spec:
      containers:
      - name: mcp-server
        image: oilfield-mcp:latest
        ports:
        - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: oilfield-mcp
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
```

### 8. 维护成本对比

#### stdio + ACL方案

**日常维护**:
- 监控3个进程
- 管理ACL数据库
- 处理权限同步问题
- 添加用户需要配置ACL

**升级MCP Server**:
```bash
# 1. 停止所有MCP Servers
# (通过删除数据库记录或禁用)

# 2. 更新代码
git pull

# 3. 重新创建所有MCP Servers
node scripts/create-mcp-admin.js
node scripts/create-mcp-user.js
node scripts/create-mcp-guest.js

# 4. 重新配置ACL
node scripts/configure-mcp-acl.js ...

# 5. 重启LibreChat
docker-compose restart
```

**估计时间**: 15-30分钟

#### HTTP/SSE方案

**日常维护**:
- 监控1个HTTP服务
- 无需管理ACL
- 添加用户自动生效

**升级MCP Server**:
```bash
# 1. 更新代码
git pull

# 2. 重启HTTP Server
# Ctrl+C
python oilfield_mcp_http_server.py

# 或使用systemd
sudo systemctl restart oilfield-mcp

# LibreChat无需重启
```

**估计时间**: 1-2分钟

### 9. 实际案例对比

#### 场景1: 新增一个工具

**stdio + ACL方案**:
1. 在Python代码中添加工具
2. 测试工具
3. 提交代码
4. 重新创建所有MCP Server实例
5. 重启LibreChat
6. 验证所有用户可见

**时间**: 20-30分钟

**HTTP/SSE方案**:
1. 在Python代码中添加工具
2. 测试工具
3. 提交代码
4. 重启HTTP Server
5. 刷新LibreChat页面

**时间**: 3-5分钟

#### 场景2: 修改权限规则

**stdio + ACL方案**:
1. 修改permissions.py
2. 需要重新创建所有MCP Server
3. 重启LibreChat
4. 验证

**时间**: 15-20分钟

**HTTP/SSE方案**:
1. 修改permissions.py
2. 重启HTTP Server
3. 下次请求立即生效

**时间**: 2-3分钟

#### 场景3: 临时授予用户特殊权限

**stdio + ACL方案**:
1. 修改数据库角色
2. 配置新的ACL权限
3. 可能需要创建新的MCP Server实例
4. 重启LibreChat

**时间**: 10-15分钟

**HTTP/SSE方案**:
1. 修改数据库角色
2. 用户重新登录
3. 立即生效

**时间**: 1分钟

## 总结建议

### 选择stdio + ACL方案，如果：

✅ 你已经有stdio MCP Server运行中
✅ 不想额外部署HTTP服务
✅ 用户角色非常固定，几乎不变
✅ 不需要频繁添加新工具
✅ 团队熟悉LibreChat的ACL系统

### 选择HTTP/SSE方案，如果：

✅ 刚开始配置权限系统
✅ 需要灵活的权限控制
✅ 计划添加更多角色
✅ 需要频繁更新工具
✅ 需要生产级别的部署
✅ 需要独立扩展MCP Server
✅ 团队熟悉HTTP/REST API

## 迁移指南

### 从stdio迁移到HTTP/SSE

如果你已经部署了stdio + ACL方案，可以这样迁移：

```bash
# 1. 部署HTTP Server（不影响现有系统）
pip install -r requirements_http.txt
python oilfield_mcp_http_server.py &

# 2. 测试HTTP Server
python test_http_server.py

# 3. 在librechat.yaml中添加HTTP MCP配置
# 保留现有stdio配置，新增HTTP配置

# 4. 重启LibreChat
docker-compose restart

# 5. 验证HTTP版本工作正常

# 6. 从librechat.yaml移除stdio配置

# 7. 清理数据库中的旧MCP Servers
docker-compose exec mongodb mongosh librechat
db.mcpservers.deleteMany({serverName: /^mcp_/})

# 8. 重启LibreChat
docker-compose restart
```

## 推荐方案

🏆 **HTTP/SSE方案**

**原因**：
1. 更简单的配置和维护
2. 更好的资源利用率
3. 更快的迭代速度
4. 更适合生产环境
5. 更容易扩展和监控

**除非**你有特殊原因必须使用stdio，否则HTTP/SSE是更好的选择。
