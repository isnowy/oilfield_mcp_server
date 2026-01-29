# LibreChat MCP Server 角色权限配置方案

## 问题分析

### stdio类型MCP Server的限制

1. **环境变量静态性**：stdio类型的MCP Server在LibreChat启动时加载，环境变量在整个生命周期内固定
2. **无法传递动态用户信息**：`{{LIBRECHAT_USER_ROLE}}`等占位符只对HTTP/SSE类型有效，对stdio类型不起作用
3. **所有用户共享同一进程**：stdio MCP Server是单例进程，不能基于不同用户动态切换角色

### LibreChat的MCP权限系统

LibreChat使用**Access Control List (ACL)**系统来管理MCP Server的访问权限，而不是通过yaml文件配置。

**权限模型**：
- 基于资源类型（ResourceType.MCPSERVER）
- 使用访问角色（AccessRoleIds: VIEWER, EDITOR, OWNER）
- 支持用户级和组级权限控制

## 解决方案

### 方案1: 创建角色特定的数据库MCP Server（推荐）

通过LibreChat UI或API创建多个MCP Server实例，并使用ACL控制访问权限。

#### 步骤

1. **通过UI创建MCP Server**
   - 登录LibreChat管理员账号
   - 进入Settings -> MCP Servers
   - 创建两个MCP Server配置：
     - "油田钻井数据服务 (管理员版)"
     - "油田钻井数据服务 (用户版)"

2. **配置MCP Server**

**管理员版配置**：
```json
{
  "command": "python",
  "args": ["d:/work/oilMCP/oilfield_mcp_server_with_permissions.py"],
  "env": {
    "DATABASE_URL": "sqlite:///d:/work/oilMCP/oilfield.db",
    "PYTHONIOENCODING": "utf-8",
    "LOG_LEVEL": "INFO",
    "LIBRECHAT_USER_ROLE": "ADMIN"
  }
}
```

**用户版配置**：
```json
{
  "command": "python",
  "args": ["d:/work/oilMCP/oilfield_mcp_server_with_permissions.py"],
  "env": {
    "DATABASE_URL": "sqlite:///d:/work/oilMCP/oilfield.db",
    "PYTHONIOENCODING": "utf-8",
    "LOG_LEVEL": "INFO",
    "LIBRECHAT_USER_ROLE": "USER"
  }
}
```

3. **配置访问权限**
   - 在MCP Server的访问控制设置中
   - 为管理员MCP Server只授予ADMIN角色用户访问权限
   - 为用户MCP Server只授予USER角色用户访问权限

### 方案2: 使用HTTP/SSE传输类型（最佳长期方案）

stdio类型的限制决定了无法真正传递动态用户信息。改用HTTP/SSE可以实现真正的per-request权限控制。

#### 优点
- ✅ 每个请求可以获取实际用户信息
- ✅ 可以使用`{{LIBRECHAT_USER_ROLE}}`占位符
- ✅ 不需要创建多个MCP Server实例
- ✅ 支持真正的动态权限控制

#### 实现步骤

1. **创建HTTP MCP Server**

```python
# oilfield_mcp_http_server.py
from fastapi import FastAPI, Header, HTTPException
from mcp.server import Server
from permissions import PermissionChecker, UserRole

app = FastAPI()
mcp_app = Server("oilfield-drilling-data")

@app.post("/mcp/call-tool")
async def call_tool(
    tool_name: str,
    arguments: dict,
    x_user_role: str = Header(None, alias="X-User-Role"),
    x_user_email: str = Header(None, alias="X-User-Email")
):
    # 从header获取用户角色
    user_role = UserRole(x_user_role) if x_user_role else UserRole.GUEST
    
    # 创建权限检查器
    checker = PermissionChecker(user_role, x_user_email)
    
    # 检查权限
    if not checker.has_permission(tool_name):
        raise HTTPException(
            status_code=403,
            detail=f"用户角色{user_role.value}无权访问工具{tool_name}"
        )
    
    # 执行工具
    result = await mcp_app.call_tool(tool_name, arguments)
    return result
```

2. **在librechat.yaml配置HTTP类型MCP Server**

```yaml
mcpServers:
  oilfield-drilling:
    type: sse  # 或 http
    url: "http://localhost:8080/mcp"
    headers:
      X-User-Role: "{{LIBRECHAT_USER_ROLE}}"
      X-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
    description: "油田钻井数据查询服务"
```

3. **启动HTTP服务器**

```bash
uvicorn oilfield_mcp_http_server:app --host 0.0.0.0 --port 8080
```

### 方案3: 在MCP Server内部实现动态权限查询

如果必须使用stdio类型，可以让MCP Server主动查询数据库获取用户权限。

#### 实现方式

```python
# oilfield_mcp_server_with_db_auth.py
import os
from pymongo import MongoClient
from permissions import PermissionChecker, UserRole

# 连接到LibreChat的数据库
mongo_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/librechat"))
db = mongo_client.librechat

def get_user_role_from_db(user_email: str) -> UserRole:
    """从LibreChat数据库查询用户角色"""
    if not user_email:
        return UserRole.GUEST
    
    user = db.users.find_one({"email": user_email})
    if not user:
        return UserRole.GUEST
    
    role_str = user.get("role", "USER")
    try:
        return UserRole(role_str)
    except ValueError:
        return UserRole.USER

@app.call_tool()
async def handle_tool_call(name: str, arguments: dict) -> Sequence[TextContent]:
    # 从环境变量获取用户email（这个可以传递）
    user_email = os.getenv("LIBRECHAT_USER_EMAIL")
    
    # 从数据库查询实际角色
    user_role = get_user_role_from_db(user_email)
    
    # 创建权限检查器
    checker = PermissionChecker(user_role, user_email)
    
    # 检查权限
    if not checker.has_permission(name):
        return [TextContent(
            type="text",
            text=f"权限不足：用户角色{user_role.value}无权访问工具{name}"
        )]
    
    # 执行工具逻辑
    # ...
```

**优点**：
- 可以继续使用stdio类型
- 获取真实的用户角色

**缺点**：
- 需要访问LibreChat的数据库
- 每次调用都要查询数据库（性能影响）
- 需要配置数据库连接信息

## 当前配置分析

### librechat.yaml中的配置

```yaml
mcpServers:
  oilfield-admin:
    command: python
    env:
      LIBRECHAT_USER_ROLE: "ADMIN"  # 硬编码
  
  oilfield-user:
    command: python
    env:
      LIBRECHAT_USER_ROLE: "USER"   # 硬编码
```

**问题**：
1. ❌ 所有用户都能看到两个MCP Server
2. ❌ 没有基于用户角色的访问控制
3. ❌ 用户可以选择使用任意一个MCP Server

**原因**：
yaml文件中定义的MCP Server是**全局配置**，不受ACL权限控制。

## 推荐实施步骤

### 阶段1: 快速解决（方案1）

1. 从librechat.yaml中删除两个MCP Server配置
2. 通过LibreChat UI创建数据库MCP Server
3. 使用ACL系统配置访问权限

### 阶段2: 长期优化（方案2）

1. 实现HTTP类型MCP Server
2. 支持动态用户上下文传递
3. 实现per-request权限验证

### 阶段3: 权限细化（如需要）

1. 基于用户组织架构配置访问权限
2. 实现基于资源的细粒度权限控制
3. 添加审计日志

## 测试验证

### 验证ACL权限

```bash
# 查看用户角色
node scripts/list-users-with-roles.js

# 查看用户可访问的MCP Servers
# 登录不同角色的用户，检查Settings -> MCP Servers中显示的服务器列表
```

### 验证工具权限

```bash
# 测试权限逻辑
cd d:\work\oilMCP
python test_permissions_quick.py
```

## 常见问题

### Q: 为什么{{LIBRECHAT_USER_ROLE}}没有被替换？

**A**: stdio类型MCP Server在启动时加载，环境变量是静态的。LibreChat的`processMCPEnv()`函数只处理HTTP/SSE类型的headers。

### Q: 如何让不同用户看到不同的MCP Server？

**A**: 
1. 使用数据库创建的MCP Server（通过UI或API）
2. 使用ACL系统配置访问权限
3. LibreChat会自动根据用户权限过滤可见的MCP Server

### Q: yaml中配置的MCP Server可以限制访问吗？

**A**: 不能。yaml中的配置是全局的，所有用户都可见。需要通过数据库创建MCP Server并使用ACL控制访问。

### Q: 如何迁移现有的yaml配置到数据库？

**A**: 
1. 登录管理员账号
2. 在Settings -> MCP Servers中手动创建相同配置
3. 配置访问权限
4. 从librechat.yaml中删除旧配置
5. 重启LibreChat

## 总结

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| 数据库MCP Server + ACL | 简单、可控、原生支持 | 需要手动配置 | ⭐⭐⭐⭐⭐ |
| HTTP/SSE类型 | 动态权限、灵活 | 需要额外服务器 | ⭐⭐⭐⭐ |
| 数据库查询权限 | 继续使用stdio | 性能影响、复杂度高 | ⭐⭐ |
| yaml配置多实例 | 无 | 不支持访问控制 | ❌ |

**最佳实践**：使用LibreChat的数据库MCP Server功能 + ACL权限系统
