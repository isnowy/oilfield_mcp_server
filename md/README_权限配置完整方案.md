# 🔐 LibreChat MCP Server 角色权限配置完整方案

## 📋 目录

1. [概述](#概述)
2. [架构说明](#架构说明)
3. [配置步骤](#配置步骤)
4. [权限体系](#权限体系)
5. [测试验证](#测试验证)
6. [实际应用](#实际应用)
7. [常见问题](#常见问题)

---

## 概述

本方案为LibreChat系统的MCP Server实现了完整的角色权限控制,实现了:

✅ **用户信息传递** - LibreChat通过环境变量自动传递用户上下文  
✅ **角色权限检查** - MCP Server根据用户角色检查工具访问权限  
✅ **细粒度控制** - 支持READ、WRITE、DELETE、ADMIN四级权限  
✅ **开发模式** - 支持开发环境跳过权限检查  
✅ **审计日志** - 记录所有权限检查和工具调用

---

## 架构说明

### 工作流程

```
┌─────────────┐
│   用户      │
└──────┬──────┘
       │ 1. 调用MCP工具
       ↓
┌─────────────────────────────────────┐
│         LibreChat                   │
│  ┌──────────────────────────────┐   │
│  │ • 检查interface.mcpServers   │   │
│  │   USE权限                    │   │
│  │ • 准备用户上下文             │   │
│  └──────────────────────────────┘   │
└──────┬──────────────────────────────┘
       │ 2. 传递用户信息(env)
       │    - LIBRECHAT_USER_ID
       │    - LIBRECHAT_USER_EMAIL
       │    - LIBRECHAT_USER_ROLE
       │    - LIBRECHAT_USER_USERNAME
       ↓
┌─────────────────────────────────────┐
│      MCP Server (Python)            │
│  ┌──────────────────────────────┐   │
│  │  PermissionChecker           │   │
│  │  ┌─────────────────────────┐ │   │
│  │  │ 1. 解析用户角色         │ │   │
│  │  │ 2. 检查工具权限要求     │ │   │
│  │  │ 3. 验证权限匹配         │ │   │
│  │  │ 4. 记录审计日志         │ │   │
│  │  └─────────────────────────┘ │   │
│  └──────────────────────────────┘   │
│               │                     │
│               ├─ 权限允许 ──────────┼─→ 执行工具
│               │                     │
│               └─ 权限拒绝 ──────────┼─→ 返回错误
│                                     │
└─────────────────────────────────────┘
       │
       │ 3. 返回结果
       ↓
┌─────────────┐
│   用户      │
└─────────────┘
```

---

## 配置步骤

### 步骤1: 修改 librechat.yaml

```yaml
# 接口级别MCP权限控制
interface:
  mcpServers:
    use: true      # 允许使用MCP服务器
    create: false  # 不允许创建MCP配置
    share: false   # 不允许分享
    public: false  # 不允许公开

# MCP Server配置
mcpServers:
  oilfield-data:
    command: python
    args:
      - "d:/work/oilMCP/oilfield_mcp_server_with_permissions.py"
    env:
      # 数据库配置
      DATABASE_URL: "sqlite:///d:/work/oilMCP/oilfield.db"
      PYTHONIOENCODING: "utf-8"
      LOG_LEVEL: "INFO"
      
      # 用户上下文变量(自动注入)
      LIBRECHAT_USER_ID: "{{LIBRECHAT_USER_ID}}"
      LIBRECHAT_USER_EMAIL: "{{LIBRECHAT_USER_EMAIL}}"
      LIBRECHAT_USER_ROLE: "{{LIBRECHAT_USER_ROLE}}"
      LIBRECHAT_USER_USERNAME: "{{LIBRECHAT_USER_USERNAME}}"
      
      # 权限控制开关
      DEV_MODE: "false"  # 生产环境必须设为false
    
    description: "油田钻井数据查询服务(带权限控制)"
    disabled: false
    timeout: 60000
```

### 步骤2: 部署权限模块

将以下文件放到MCP Server目录(`d:/work/oilMCP/`):

1. **permissions.py** - 权限检查核心模块
2. **oilfield_mcp_server_with_permissions.py** - 集成权限的MCP Server
3. **test_permissions_quick.py** - 权限测试脚本

### 步骤3: 配置权限映射

在 `permissions.py` 中配置:

```python
# 角色权限映射
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.ADMIN
    ],
    UserRole.USER: [
        Permission.READ,
        Permission.WRITE
    ],
    UserRole.GUEST: [
        Permission.READ
    ]
}

# 工具权限要求
TOOL_PERMISSIONS = {
    "query_drilling_data": [Permission.READ],
    "add_drilling_record": [Permission.WRITE],
    "delete_drilling_record": [Permission.DELETE],
    "export_all_data": [Permission.ADMIN],
}
```

### 步骤4: 启动LibreChat

```bash
cd d:\work\libreChat

# Docker方式
docker-compose up -d

# 或开发模式
npm run backend:dev
```

---

## 权限体系

### LibreChat用户角色

| 角色 | 说明 | MCP_SERVERS权限 |
|-----|------|-----------------|
| **ADMIN** | 系统管理员 | USE, CREATE, SHARE, SHARE_PUBLIC |
| **USER** | 普通用户 | USE (默认) |

### MCP Server自定义权限

| 权限 | 说明 | 适用角色 |
|-----|------|----------|
| **READ** | 查询数据 | ADMIN, USER, GUEST |
| **WRITE** | 创建/更新数据 | ADMIN, USER |
| **DELETE** | 删除数据 | ADMIN |
| **ADMIN** | 管理操作 | ADMIN |

### 权限测试结果

根据实际测试,不同角色的工具访问权限:

| 角色 | 可用工具数 | 访问率 | 说明 |
|-----|----------|--------|------|
| **ADMIN** | 15/15 | 100% | 完全访问 |
| **USER** | 8/15 | 53.3% | 读写权限 |
| **GUEST** | 4/15 | 26.7% | 只读权限 |

#### 详细权限对比

| 工具分类 | 示例工具 | ADMIN | USER | GUEST |
|---------|---------|-------|------|-------|
| **查询类** | query_drilling_data | ✅ | ✅ | ✅ |
| **写入类** | add_drilling_record | ✅ | ✅ | ❌ |
| **删除类** | delete_drilling_record | ✅ | ❌ | ❌ |
| **管理类** | export_all_data | ✅ | ❌ | ❌ |

---

## 测试验证

### 快速测试

```bash
cd d:/work/oilMCP

# 测试所有角色
python test_permissions_quick.py all

# 对比权限差异
python test_permissions_quick.py compare

# 测试特定角色
python test_permissions_quick.py admin
python test_permissions_quick.py user

# 测试开发模式
python test_permissions_quick.py dev
```

### 预期输出

**ADMIN角色测试:**
```
🧪 测试角色: ADMIN
📧 用户邮箱: admin@oilfield.com
🔐 角色 'ADMIN' 拥有的权限:
   ✅ read
   ✅ write
   ✅ delete
   ✅ admin
📈 统计:
   允许使用: 15/15 个工具
   访问率: 100.0%
```

**USER角色测试:**
```
🧪 测试角色: USER
🔐 角色 'USER' 拥有的权限:
   ✅ read
   ✅ write
📈 统计:
   允许使用: 8/15 个工具
   访问率: 53.3%
```

### 在LibreChat中测试

1. 以不同用户角色登录LibreChat
2. 在对话中调用MCP工具
3. 观察权限检查结果:
   - ✅ 有权限: 正常返回结果
   - ❌ 无权限: 返回权限拒绝消息

---

## 实际应用

### 使用示例1: 普通用户查询数据

**对话:**
```
用户: 帮我查询井A-001的钻井数据

助手: 好的,我来查询...
[调用 query_drilling_data 工具]

✅ 钻井数据查询成功
井名: 井A-001
...
```

**日志:**
```
INFO: 🔍 Permission check - User: user@oilfield.com, Role: USER, Tool: query_drilling_data
INFO: ✅ Permission granted for user@oilfield.com to use query_drilling_data
```

### 使用示例2: 普通用户尝试删除数据

**对话:**
```
用户: 帮我删除记录ID 12345

助手: 抱歉,你没有权限执行此操作
[调用 delete_drilling_record 工具]

❌ 权限被拒绝
权限不足: 用户角色 'USER' 缺少以下权限: delete。
```

**日志:**
```
WARNING: ❌ Permission denied for tool: delete_drilling_record
WARNING: ❌ Access Log - User: user@oilfield.com, Tool: delete_drilling_record, Success: False
```

### 使用示例3: 管理员导出数据

**对话:**
```
用户: 帮我导出所有钻井数据

助手: 好的,正在导出...
[调用 export_all_data 工具]

✅ 数据导出成功
格式: json
文件名: oilfield_data_20240129_153000.json
```

**日志:**
```
INFO: ✅ Permission granted for admin@oilfield.com to use export_all_data
INFO: ✅ Access Log - User: admin@oilfield.com, Tool: export_all_data, Success: True
```

---

## 常见问题

### Q1: 用户上下文变量没有传递?

**问题:** MCP Server中获取不到用户信息

**解决:**
1. 检查 `librechat.yaml` 中是否正确配置了环境变量:
   ```yaml
   env:
     LIBRECHAT_USER_ROLE: "{{LIBRECHAT_USER_ROLE}}"
     LIBRECHAT_USER_EMAIL: "{{LIBRECHAT_USER_EMAIL}}"
   ```

2. 确认占位符格式正确(双花括号)

3. 重启LibreChat服务使配置生效

### Q2: 权限检查不生效?

**问题:** 所有工具都能访问,没有权限限制

**解决:**
1. 检查 `DEV_MODE` 是否设置为 `"false"`:
   ```yaml
   env:
     DEV_MODE: "false"  # 必须是字符串 "false"
   ```

2. 查看MCP Server启动日志,确认权限检查已启用:
   ```
   ✅ Production mode - permission checks enabled
   ```

3. 如果显示开发模式,检查环境变量设置

### Q3: 如何添加新的权限级别?

**步骤:**
1. 在 `permissions.py` 的 `Permission` 枚举中添加新权限:
   ```python
   class Permission(Enum):
       READ = "read"
       WRITE = "write"
       DELETE = "delete"
       ADMIN = "admin"
       EXPORT = "export"  # 新增
   ```

2. 更新角色权限映射:
   ```python
   ROLE_PERMISSIONS = {
       UserRole.ADMIN: [Permission.READ, Permission.WRITE, 
                        Permission.DELETE, Permission.ADMIN, Permission.EXPORT],
       UserRole.USER: [Permission.READ, Permission.WRITE],
   }
   ```

3. 在工具权限映射中使用:
   ```python
   TOOL_PERMISSIONS = {
       "export_to_excel": [Permission.EXPORT],
   }
   ```

### Q4: 如何基于用户邮箱域名控制权限?

**实现:**

在 `permissions.py` 的 `PermissionChecker` 类中添加自定义逻辑:

```python
def has_permission(self, tool_name: str) -> tuple[bool, Optional[str]]:
    user_context = self.get_user_context()
    email = user_context['email']
    
    # 管理员域名白名单
    admin_domains = ['admin.oilfield.com', 'manager.oilfield.com']
    
    if any(email.endswith(f"@{domain}") for domain in admin_domains):
        logger.info(f"Admin domain detected for {email}, granting access")
        return True, None
    
    # 继续正常权限检查
    return self._check_role_permission(tool_name)
```

### Q5: 如何记录详细的审计日志?

**方案:**

1. 扩展 `log_access` 方法:
   ```python
   def log_access(self, tool_name: str, success: bool, 
                  arguments: dict = None, error: Optional[str] = None):
       user_context = self.get_user_context()
       
       log_data = {
           "timestamp": datetime.now().isoformat(),
           "user_id": user_context['user_id'],
           "email": user_context['email'],
           "role": user_context['role'],
           "tool": tool_name,
           "arguments": arguments,
           "success": success,
           "error": error
       }
       
       # 写入审计日志文件
       with open("audit.log", "a") as f:
           f.write(json.dumps(log_data) + "\n")
   ```

2. 在工具调用时记录参数:
   ```python
   @app.call_tool()
   async def call_tool(name: str, arguments: dict):
       has_permission, error = permission_checker.has_permission(name)
       permission_checker.log_access(name, has_permission, arguments, error)
       # ...
   ```

### Q6: 开发环境和生产环境如何切换?

**配置:**

在 `librechat.yaml` 中使用环境变量:

```yaml
mcpServers:
  oilfield-data:
    env:
      # 开发环境
      # DEV_MODE: "true"
      
      # 生产环境
      DEV_MODE: "false"
```

或者通过环境变量传递:

```bash
# 开发环境
export DEV_MODE=true
docker-compose up

# 生产环境
export DEV_MODE=false
docker-compose up -d
```

### Q7: 如何自定义权限错误消息?

**方案:**

在 `permissions.py` 中自定义错误消息:

```python
ERROR_MESSAGES = {
    "zh-CN": {
        "no_permission": "您没有权限执行此操作",
        "need_admin": "此操作需要管理员权限",
        "need_write": "此操作需要写入权限",
    },
    "en": {
        "no_permission": "You don't have permission for this operation",
        "need_admin": "This operation requires admin privileges",
        "need_write": "This operation requires write permission",
    }
}

def get_error_message(permission: Permission, locale="zh-CN") -> str:
    messages = ERROR_MESSAGES.get(locale, ERROR_MESSAGES["en"])
    # 根据权限类型返回相应消息
    ...
```

---

## 文件清单

```
d:/work/librechat/
├── librechat.yaml                    # LibreChat配置(已修改)
├── docs/
│   └── MCP权限配置指南.md            # 详细配置指南
└── ...

d:/work/oilMCP/
├── permissions.py                    # ✅ 权限检查核心模块
├── oilfield_mcp_server_with_permissions.py  # ✅ 带权限的MCP Server
├── test_permissions_quick.py         # ✅ 权限测试脚本
├── oilfield.db                       # 数据库文件
└── requirements.txt                  # Python依赖
```

---

## 安全建议

1. ✅ **生产环境禁用DEV_MODE**
   ```yaml
   DEV_MODE: "false"  # 必须
   ```

2. ✅ **最小权限原则**
   - 默认USER角色只给READ+WRITE
   - 敏感操作限制为ADMIN角色

3. ✅ **启用审计日志**
   ```python
   permission_checker.log_access(tool_name, success, error)
   ```

4. ✅ **定期审查权限配置**
   - 检查 `TOOL_PERMISSIONS` 映射
   - 验证 `ROLE_PERMISSIONS` 设置
   - 审查访问日志

5. ✅ **错误信息不泄露敏感数据**
   ```python
   # ❌ 不好
   return f"用户{user_id}无权访问{database_table}"
   
   # ✅ 好
   return "权限不足,无法执行此操作"
   ```

---

## 总结

本方案实现了LibreChat MCP Server的完整角色权限控制,具有以下特点:

✅ **无缝集成** - 利用LibreChat内置的用户上下文传递机制  
✅ **灵活配置** - 支持自定义角色权限和工具权限映射  
✅ **开发友好** - 支持开发模式跳过权限检查  
✅ **生产就绪** - 完整的权限检查和审计日志  
✅ **易于扩展** - 可以方便地添加新权限和新工具

通过这个方案,你可以实现:
- 🔒 保护敏感数据和操作
- 👥 区分不同用户的访问权限
- 📊 记录详细的操作审计日志
- 🛡️ 防止未授权访问

---

## 参考资料

- [LibreChat MCP文档](https://github.com/danny-avila/LibreChat/blob/main/MCP_QUICKSTART.md)
- [LibreChat权限系统](https://github.com/danny-avila/LibreChat/tree/main/packages/data-provider/src)
- [MCP Protocol规范](https://modelcontextprotocol.io/)

---

**版本:** 1.0  
**更新日期:** 2026-01-29  
**作者:** LibreChat MCP Team
