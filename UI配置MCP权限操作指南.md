# LibreChat数据库MCP Server + ACL权限系统 - 完整实施指南

## 概述

本指南将手把手教你如何通过**API方式**创建LibreChat数据库MCP Server，并使用**ACL权限系统**实现基于角色的访问控制。

## 为什么使用这个方案

### yaml配置 vs 数据库配置

| 特性 | yaml配置 | 数据库配置（本方案） |
|-----|---------|---------------------|
| 访问控制 | ❌ 所有用户可见 | ✅ 支持ACL权限控制 |
| 角色隔离 | ❌ 无法实现 | ✅ 不同角色看不同Server |
| 动态管理 | ❌ 需要重启 | ✅ 无需重启 |
| 适用场景 | 开发测试 | 生产环境 |

### 架构说明

```
用户登录 → LibreChat检查ACL权限 → 只返回用户有权限的MCP Servers
                                  ↓
                          ADMIN看到：管理员版MCP（15个工具）
                          USER看到：用户版MCP（8个工具）
```

## 前提条置

### 1. 启用MCP功能

确保librechat.yaml中启用了MCP：

```yaml
interface:
  mcpServers:
    use: true     # 允许使用MCP服务器
    create: true  # 允许创建MCP服务器（重要！）
    share: false  
    public: false
```

### 2. 确认用户角色

```bash
# 查看所有用户及角色
cd d:\work\librechat
node scripts/list-users-with-roles.js

# 设置管理员角色
node scripts/set-user-role.js 18202727050@163.com ADMIN
```

### 3. 重启LibreChat

```bash
docker-compose restart
# 或
docker-compose down
docker-compose up -d
```

## 操作步骤

### 步骤1: 登录管理员账号

使用ADMIN角色的账号登录LibreChat（如 18202727050@163.com）

### 步骤2: 进入MCP设置

1. 点击右上角用户头像
2. 选择 **Settings** (设置)
3. 在左侧菜单中找到 **MCP Servers** 或 **工具** 选项

### 步骤3: 创建管理员MCP Server

点击 **"+ New MCP Server"** 或 **"创建新服务器"**

#### 基本信息
- **Server Name**: `oilfield-admin`
- **Display Name**: `油田钻井数据服务(管理员)`
- **Description**: `提供油田钻井数据的完整管理功能，包括查询、添加、修改、删除和系统管理`

#### 连接配置
- **Transport Type**: `stdio`
- **Command**: `python`
- **Args**: 
  ```
  d:/work/oilMCP/oilfield_mcp_server_with_permissions.py
  ```

#### 环境变量
添加以下环境变量：

| 变量名 | 值 |
|-------|-----|
| DATABASE_URL | `sqlite:///d:/work/oilMCP/oilfield.db` |
| PYTHONIOENCODING | `utf-8` |
| LOG_LEVEL | `INFO` |
| LIBRECHAT_USER_ROLE | `ADMIN` |
| DEV_MODE | `false` |

#### 权限设置（关键！）

在 **Access Control** 或 **访问控制** 部分：

1. **Visibility**: `Private` (私有)
2. **Shared with**: 
   - 点击 **"Add users"** 或 **"添加用户"**
   - 选择所有ADMIN角色的用户
   - 或者选择 **"Share with role"** -> 选择 **ADMIN**

3. **Access Level**: 
   - 选择 **"Owner"** 或 **"Viewer"**（根据需要）

点击 **"Create"** 或 **"创建"** 保存

### 步骤4: 创建普通用户MCP Server

重复步骤3，使用以下配置：

#### 基本信息
- **Server Name**: `oilfield-user`
- **Display Name**: `油田钻井数据服务(用户)`
- **Description**: `提供油田钻井数据的基本查询和录入功能`

#### 连接配置
- 与管理员版相同

#### 环境变量
- 与管理员版相同，但将 `LIBRECHAT_USER_ROLE` 设置为 `USER`

| 变量名 | 值 |
|-------|-----|
| LIBRECHAT_USER_ROLE | `USER` |

#### 权限设置
- **Visibility**: `Private`
- **Shared with**: 选择所有USER角色的用户或 **"Share with role"** -> **USER**

### 步骤5: 从yaml中移除全局配置

编辑 `d:\work\librechat\librechat.yaml`，移除或注释掉之前的MCP配置：

```yaml
# mcpServers:
#   oilfield-admin:
#     # ...
#   oilfield-user:
#     # ...
```

保留空的 `mcpServers:` 部分或完全删除该部分。

### 步骤6: 重启LibreChat

```bash
cd d:\work\librechat
docker-compose restart
```

## 验证步骤

### 验证1: 管理员用户

1. 使用ADMIN角色账号登录
2. 进入Settings -> MCP Servers
3. 应该能看到 **"油田钻井数据服务(管理员)"**
4. 创建新对话，选择该MCP Server
5. 测试调用管理员工具（如 `export_all_data`）

### 验证2: 普通用户

1. 使用USER角色账号登录
2. 进入Settings -> MCP Servers
3. 应该只能看到 **"油田钻井数据服务(用户)"**
4. 不应该看到管理员版MCP Server
5. 测试调用基础工具（如 `query_drilling_data`）
6. 尝试调用管理员工具应该被拒绝

### 验证3: 权限隔离

管理员账号测试所有15个工具：

```
- query_drilling_data ✓
- query_by_well_number ✓
- query_by_date_range ✓
- get_statistics ✓
- add_drilling_record ✓
- update_drilling_record ✓
- delete_drilling_record ✓
- batch_delete_records ✓
- export_all_data ✓
- reset_database ✓
- backup_database ✓
- get_system_info ✓
- query_well_info ✓
- get_performance_metrics ✓
- analyze_drilling_efficiency ✓
```

普通用户账号应该只能访问8个工具：

```
- query_drilling_data ✓
- query_by_well_number ✓
- query_by_date_range ✓
- get_statistics ✓
- add_drilling_record ✓
- update_drilling_record ✓
- query_well_info ✓
- get_performance_metrics ✓
```

## 故障排除

### 问题1: 找不到MCP Servers菜单

**可能原因**：
- LibreChat版本不支持MCP功能
- interface配置中未启用MCP

**解决方法**：
```bash
# 检查版本
docker-compose exec api cat package.json | grep version

# 确保版本 >= 0.8.0
# 检查librechat.yaml中的interface.mcpServers.use是否为true
```

### 问题2: 无法创建MCP Server

**可能原因**：
- 当前用户不是ADMIN角色
- interface.mcpServers.create设置为false

**解决方法**：
```bash
# 确认用户角色
node scripts/list-users-with-roles.js

# 如果不是ADMIN，设置为ADMIN
node scripts/set-user-role.js your-email@example.com ADMIN
```

### 问题3: 创建后所有用户都能看到

**可能原因**：
- 权限设置为Public或Shared
- 未正确配置Access Control

**解决方法**：
1. 编辑MCP Server配置
2. 在Access Control中设置为Private
3. 明确指定可访问的用户或角色

### 问题4: MCP Server启动失败

**检查方法**：
```bash
# 查看日志
docker-compose logs -f api

# 查找MCP相关错误
docker-compose logs api | grep -i mcp
```

**常见错误**：
- Python路径错误
- 脚本路径不正确
- 环境变量配置错误
- 数据库连接失败

## API方式创建（高级）

如果UI方式不可行，可以使用API创建：

```bash
# 获取access token
TOKEN="your-jwt-token"

# 创建MCP Server
curl -X POST http://localhost:3080/api/mcp/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "serverName": "oilfield-admin",
    "displayName": "油田钻井数据服务(管理员)",
    "description": "管理员权限MCP服务器",
    "config": {
      "command": "python",
      "args": ["d:/work/oilMCP/oilfield_mcp_server_with_permissions.py"],
      "env": {
        "DATABASE_URL": "sqlite:///d:/work/oilMCP/oilfield.db",
        "PYTHONIOENCODING": "utf-8",
        "LOG_LEVEL": "INFO",
        "LIBRECHAT_USER_ROLE": "ADMIN",
        "DEV_MODE": "false"
      }
    }
  }'
```

## 替代方案：通过脚本批量创建

如果有多个用户需要配置，可以创建脚本：

```javascript
// scripts/create-mcp-servers.js
const { MCPServer } = require('~/models');
const connect = require('./connect');

async function createMCPServers() {
  await connect();
  
  // 创建管理员MCP Server
  const adminServer = new MCPServer({
    serverName: 'oilfield-admin',
    displayName: '油田钻井数据服务(管理员)',
    config: {
      command: 'python',
      args: ['d:/work/oilMCP/oilfield_mcp_server_with_permissions.py'],
      env: {
        DATABASE_URL: 'sqlite:///d:/work/oilMCP/oilfield.db',
        LIBRECHAT_USER_ROLE: 'ADMIN'
      }
    },
    author: 'admin-user-id',
    visibility: 'private'
  });
  
  await adminServer.save();
  console.log('管理员MCP Server已创建');
  
  // 配置ACL权限
  // ...
  
  process.exit(0);
}

createMCPServers();
```

## 总结

通过LibreChat UI配置MCP Server并使用ACL权限系统是实现角色权限控制的**正确方式**。这比yaml配置更灵活，支持：

- ✅ 细粒度访问控制
- ✅ 动态权限管理
- ✅ 用户级和角色级权限
- ✅ 审计和日志记录

yaml配置应该只用于**全局共享**的MCP Server，如官方提供的公共服务。
