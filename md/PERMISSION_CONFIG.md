# 权限配置说明文档

## 🎯 概述

油田钻井数据查询 MCP 服务器支持**基于角色的权限控制**（RBAC），并提供**开发模式**方便测试。

## 🔓 开发模式 vs 🔒 生产模式

### 开发模式（默认）

- **用途**：本地开发、测试、演示
- **特点**：所有用户自动拥有 admin 权限，无需配置
- **启用方式**：设置环境变量 `DEV_MODE=true`（默认）

```yaml
# librechat.yaml 配置示例
env:
  DEV_MODE: "true"  # 开发模式
```

### 生产模式

- **用途**：正式部署、多用户环境
- **特点**：严格的基于角色的权限控制
- **启用方式**：设置环境变量 `DEV_MODE=false`

```yaml
# librechat.yaml 配置示例
env:
  DEV_MODE: "false"  # 生产模式
```

## 👥 权限角色说明

在**生产模式**下，系统支持以下角色：

| 角色 | 权限范围 | 可访问的井 | 可访问的区块 | 典型用途 |
|------|---------|-----------|-------------|---------|
| **admin** | 全部权限 | 所有井 | 所有区块 | 系统管理员 |
| **engineer** | 部分权限 | ZT-102, ZT-105 | Block-A | 工程师 |
| **viewer** | 只读权限 | ZT-102 | Block-A | 只读访客 |
| **default** | 受限访问 | 无 | 无 | 未授权用户 |

## ⚙️ 配置方式

### 方式 1: 环境变量（推荐）

```bash
# Windows PowerShell
$env:DEV_MODE="true"    # 开发模式
$env:DEV_MODE="false"   # 生产模式

# Linux/Mac
export DEV_MODE=true    # 开发模式
export DEV_MODE=false   # 生产模式
```

### 方式 2: LibreChat 配置文件

编辑 `librechat.yaml`：

```yaml
mcpServers:
  oilfield-data:
    command: python
    args:
      - "d:/work/joyagent/gemini-ge/oilfield_mcp_server.py"
    env:
      DEV_MODE: "true"  # 改为 "false" 启用生产模式
```

### 方式 3: Claude Desktop 配置

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "oilfield-data": {
      "command": "python",
      "args": ["d:/work/joyagent/gemini-ge/oilfield_mcp_server.py"],
      "env": {
        "DEV_MODE": "true"
      }
    }
  }
}
```

## 🛠️ 自定义权限配置

如需修改权限配置，编辑 `oilfield_mcp_server.py` 中的 `USER_PERMISSIONS`：

```python
USER_PERMISSIONS = {
    "admin": {
        "wells": "*",              # "*" 表示所有井
        "blocks": "*",             # "*" 表示所有区块
        "role": "admin"
    },
    "engineer": {
        "wells": ["ZT-102", "ZT-105", "ZT-108"],  # 指定可访问的井
        "blocks": ["Block-A"],                    # 指定可访问的区块
        "role": "engineer"
    },
    "viewer": {
        "wells": ["ZT-102"],
        "blocks": ["Block-A"],
        "role": "viewer"
    },
    "default": {
        "wells": [],               # 空列表表示无权限
        "blocks": [],
        "role": "guest"
    }
}
```

## 📊 权限检查逻辑

### 开发模式（DEV_MODE=true）

```python
# 所有权限检查都返回 True
check_well_access("default", "ZT-102")  # ✅ 返回 True
check_block_access("default", "Block-A") # ✅ 返回 True
get_accessible_wells("default")         # ✅ 返回 "*" (所有井)
```

### 生产模式（DEV_MODE=false）

```python
# 严格按照角色权限检查
check_well_access("engineer", "ZT-102")  # ✅ 返回 True (有权限)
check_well_access("engineer", "XY-009")  # ❌ 返回 False (无权限)
check_well_access("admin", "XY-009")     # ✅ 返回 True (admin全部权限)
```

## 🧪 测试不同模式

### 测试开发模式

1. 设置环境变量：
   ```bash
   $env:DEV_MODE="true"
   ```

2. 启动服务：
   ```bash
   python oilfield_mcp_server.py
   ```

3. 查看启动信息：
   ```
   🔓 权限模式：开发模式 (所有用户拥有 admin 权限)
      提示：生产环境请设置环境变量 DEV_MODE=false
   ```

4. 测试查询（任何角色都能访问所有数据）：
   ```
   查询所有油井  # ✅ 成功
   搜索 Block-B 的井  # ✅ 成功
   ```

### 测试生产模式

1. 设置环境变量：
   ```bash
   $env:DEV_MODE="false"
   ```

2. 启动服务：
   ```bash
   python oilfield_mcp_server.py
   ```

3. 查看启动信息：
   ```
   🔒 权限模式：生产模式 (严格权限控制)
   
   📌 权限角色：
     • admin   - 全部权限
     • engineer - Block-A的部分井
     • viewer  - ZT-102只读
     • default - 受限访问
   ```

4. 测试查询（根据角色限制）：
   ```
   # 使用 default 角色
   查询所有油井  # ❌ 无权限，返回空
   
   # 使用 admin 角色
   查询所有油井  # ✅ 成功
   ```

## 🎯 推荐实践

### 开发/测试阶段

```yaml
env:
  DEV_MODE: "true"  # 方便快速测试所有功能
```

### 生产部署

```yaml
env:
  DEV_MODE: "false"  # 启用严格权限控制
  # 其他生产环境配置...
```

### 多环境配置

创建不同的配置文件：

```bash
# 开发环境
librechat.dev.yaml    (DEV_MODE=true)

# 测试环境
librechat.test.yaml   (DEV_MODE=true)

# 生产环境
librechat.prod.yaml   (DEV_MODE=false)
```

## ⚠️ 安全提示

1. **生产环境务必设置 `DEV_MODE=false`**
2. **定期审查权限配置**
3. **使用环境变量而非硬编码密钥**
4. **记录所有权限变更**
5. **测试完成后删除临时权限**

## 📝 常见问题

### Q1: 为什么查询不到数据？

**A**: 检查以下几点：
1. 是否在生产模式（DEV_MODE=false）下使用了 `default` 角色
2. 当前角色是否有权限访问目标井或区块
3. 数据库中是否有数据

### Q2: 如何快速切换模式？

**A**: 修改环境变量后重启服务即可：
```bash
# 切换到开发模式
$env:DEV_MODE="true"
python oilfield_mcp_server.py

# 切换到生产模式  
$env:DEV_MODE="false"
python oilfield_mcp_server.py
```

### Q3: 可以在运行时切换模式吗？

**A**: 不可以。权限模式在服务启动时确定，需要重启服务才能切换。

### Q4: 如何为新用户添加权限？

**A**: 编辑 `USER_PERMISSIONS` 字典，添加新的角色配置，然后重启服务。

## 🔗 相关文档

- `QUICKSTART.md` - 快速开始指南
- `DEPLOY_GUIDE.md` - 部署指南
- `librechat.yaml` - LibreChat 配置文件
- `oilfield_mcp_server.py` - MCP 服务器源码
