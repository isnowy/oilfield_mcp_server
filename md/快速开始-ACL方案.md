# 数据库MCP Server + ACL权限 - 5分钟快速开始

## 一键执行流程

### 步骤1: 准备工作（1分钟）

```bash
# 1. 确保LibreChat正在运行
cd d:\work\librechat
docker-compose ps

# 2. 确认配置已启用MCP创建功能
# 编辑 librechat.yaml，确保：
#   interface.mcpServers.create: true

# 3. 重启LibreChat（如果修改了配置）
docker-compose restart
```

### 步骤2: 创建MCP Servers（2分钟）

```bash
cd d:\work\librechat

# 1. 创建管理员版MCP Server
node scripts\create-mcp-admin.js
# 输入JWT token（从浏览器F12获取）
# 记录返回的Server Name，例如：mcp_abc123xyz

# 2. 创建用户版MCP Server
node scripts\create-mcp-user.js
# 输入JWT token
# 记录返回的Server Name，例如：mcp_def456uvw
```

#### 如何获取JWT Token？

1. 使用管理员账号登录LibreChat
2. 按 `F12` 打开开发者工具
3. 切换到 `Network` 标签
4. 刷新页面
5. 找到任意API请求（如 `/api/user`）
6. 查看 `Request Headers` 中的 `Authorization`
7. 复制 `Bearer ` 后面的完整token

### 步骤3: 配置ACL权限（1分钟）

```bash
# 为管理员MCP Server配置权限
node scripts\configure-mcp-acl.js mcp_abc123xyz ADMIN

# 为用户MCP Server配置权限
node scripts\configure-mcp-acl.js mcp_def456uvw USER
```

### 步骤4: 清理yaml配置（30秒）

编辑 `librechat.yaml`，注释掉或删除全局MCP配置：

```yaml
# mcpServers:
#   oilfield-admin:
#     ...
#   oilfield-user:
#     ...
```

重启：

```bash
docker-compose restart
```

### 步骤5: 验证（30秒）

#### 管理员验证
1. 使用ADMIN账号登录
2. Settings → MCP Servers
3. 应该只看到 **"油田钻井数据服务(管理员)"**

#### 用户验证
1. 使用USER账号登录
2. Settings → MCP Servers
3. 应该只看到 **"油田钻井数据服务(普通用户)"**

## 完整命令序列

```bash
# 一键执行（需要手动输入token两次）
cd d:\work\librechat

# 创建
node scripts\create-mcp-admin.js    # 输入token，记录server name
node scripts\create-mcp-user.js     # 输入token，记录server name

# 配置权限（替换server name）
node scripts\configure-mcp-acl.js mcp_abc123xyz ADMIN
node scripts\configure-mcp-acl.js mcp_def456uvw USER

# 重启
docker-compose restart
```

## 预期结果

### 管理员用户体验

- 登录后看到1个MCP Server：**油田钻井数据服务(管理员)**
- 可以使用所有15个工具：
  - ✅ 基础查询（4个）
  - ✅ 数据修改（2个）
  - ✅ 数据删除（2个）
  - ✅ 系统管理（7个）

### 普通用户体验

- 登录后看到1个MCP Server：**油田钻井数据服务(普通用户)**
- 只能使用8个基础工具：
  - ✅ 基础查询（4个）
  - ✅ 数据修改（2个）
  - ✅ 基础分析（2个）
  - ❌ 无法访问删除和管理工具

## 故障排除

### Q: 创建MCP Server时返回401错误

**A**: Token过期或无效
- 重新从浏览器获取token
- 确保复制了完整的token（不包括"Bearer "前缀）

### Q: 返回403 Forbidden

**A**: 权限不足
```bash
# 确认当前用户是ADMIN角色
node scripts\list-users-with-roles.js

# 如果不是，设置为ADMIN
node scripts\set-user-role.js your-email@example.com ADMIN
```

### Q: 创建成功但用户看不到MCP Server

**A**: ACL权限未配置或配置错误
```bash
# 检查用户角色
node scripts\list-users-with-roles.js

# 重新配置ACL
node scripts\configure-mcp-acl.js <server-name> <role>

# 清除缓存并重启
node scripts\flush-cache.js
docker-compose restart
```

### Q: MCP Server启动失败

**A**: 检查Python环境和脚本路径
```bash
# 测试Python和MCP模块
cd d:\work\oilMCP
python -c "import mcp; print('OK')"

# 测试脚本独立运行
python oilfield_mcp_server_with_permissions.py

# 查看LibreChat日志
cd d:\work\librechat
docker-compose logs api | grep -i mcp
```

## 下一步

### 添加更多用户

```bash
# 创建新用户
node scripts\create-user.js

# 设置角色
node scripts\set-user-role.js newuser@example.com USER

# 无需额外操作，ACL已配置为给所有该角色用户授权
```

### 修改权限级别

编辑 `configure-mcp-acl.js`，修改第90行：

```javascript
accessRoleId: 'mcpServer_viewer',  // 可改为: mcpServer_editor, mcpServer_owner
```

### 撤销权限

```bash
# 进入MongoDB
docker-compose exec mongodb mongosh librechat

# 查看权限
db.permissions.find({ resourceType: 'mcpServer' })

# 删除特定用户的权限
db.permissions.deleteOne({
  principalType: 'user',
  principalId: ObjectId('用户ID'),
  resourceType: 'mcpServer',
  resourceId: ObjectId('MCP Server ID')
})
```

## 总结

你现在已经成功配置了：

✅ **基于数据库的MCP Server** - 替代yaml全局配置
✅ **ACL权限控制** - 不同角色看到不同的MCP Server
✅ **角色隔离** - ADMIN有15个工具，USER有8个工具
✅ **动态管理** - 无需修改yaml，可通过脚本管理

这是使用stdio类型MCP Server的**最佳实践方案**。
