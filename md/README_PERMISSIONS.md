# 权限控制使用指南

## ✨ 新特性

您的 MCP 服务器现在支持**灵活的权限控制模式**：

- 🔓 **开发模式**：方便测试，所有用户自动拥有全部权限
- 🔒 **生产模式**：严格控制，基于角色的权限管理

## 🚀 快速开始

### 方式 1: 使用启动脚本（推荐）

#### 开发/测试环境
```powershell
.\start_dev.ps1
```

#### 生产环境
```powershell
.\start_prod.ps1
```

### 方式 2: 手动设置环境变量

#### 开发模式
```powershell
$env:DEV_MODE="true"
python oilfield_mcp_server.py
```

#### 生产模式
```powershell
$env:DEV_MODE="false"
python oilfield_mcp_server.py
```

## 🧪 测试权限配置

运行测试脚本验证权限配置：

```powershell
# 测试开发模式
python test_permissions.py

# 测试生产模式
$env:DEV_MODE="false"
python test_permissions.py
```

## 📊 两种模式对比

| 特性 | 开发模式 | 生产模式 |
|-----|---------|---------|
| **环境变量** | `DEV_MODE=true` | `DEV_MODE=false` |
| **权限检查** | 跳过 | 严格执行 |
| **default 角色** | 全部权限 | 无权限 |
| **适用场景** | 本地开发、测试 | 正式部署 |
| **安全性** | 低（仅测试用） | 高 |

## 📁 文件说明

| 文件 | 说明 |
|-----|------|
| `oilfield_mcp_server.py` | MCP 服务器主程序（已添加开发模式支持） |
| `start_dev.ps1` | 开发模式启动脚本 |
| `start_prod.ps1` | 生产模式启动脚本 |
| `test_permissions.py` | 权限测试脚本 |
| `PERMISSION_CONFIG.md` | 详细权限配置文档 |
| `librechat.yaml` | LibreChat 配置文件 |

## 🎯 使用场景

### 场景 1: 本地开发

```powershell
# 使用开发模式，无需关心权限
.\start_dev.ps1

# 或
$env:DEV_MODE="true"
python oilfield_mcp_server.py
```

**特点**：
- ✅ 快速测试所有功能
- ✅ 无需配置用户角色
- ✅ 所有查询都能返回数据

### 场景 2: 功能演示

```powershell
# 开发模式，展示全部功能
.\start_dev.ps1
```

**特点**：
- ✅ 演示所有井和区块的数据
- ✅ 无权限限制

### 场景 3: 生产部署

```powershell
# 生产模式，启用严格权限
.\start_prod.ps1
```

**特点**：
- ✅ 严格的基于角色的访问控制
- ✅ 不同用户看到不同数据
- ✅ 符合安全规范

### 场景 4: 权限测试

```powershell
# 测试不同角色的权限
python test_permissions.py

# 切换到生产模式测试
$env:DEV_MODE="false"
python test_permissions.py
```

## 👥 生产模式权限说明

在生产模式（`DEV_MODE=false`）下：

| 角色 | 可访问的井 | 可访问的区块 |
|------|-----------|-------------|
| **admin** | 所有井 | 所有区块 |
| **engineer** | ZT-102, ZT-105 | Block-A |
| **viewer** | ZT-102 | Block-A |
| **default** | 无 | 无 |

## ⚙️ 配置到 LibreChat

编辑 `librechat.yaml`：

```yaml
mcpServers:
  oilfield-data:
    command: python
    args:
      - "d:/work/joyagent/gemini-ge/oilfield_mcp_server.py"
    env:
      DEV_MODE: "true"  # 开发：true，生产：false
```

## 🔧 自定义权限

编辑 `oilfield_mcp_server.py` 中的 `USER_PERMISSIONS`：

```python
USER_PERMISSIONS = {
    "admin": {
        "wells": "*",                           # 所有井
        "blocks": "*",                          # 所有区块
        "role": "admin"
    },
    "custom_role": {
        "wells": ["ZT-102", "ZT-105"],          # 指定井
        "blocks": ["Block-A", "Block-B"],       # 指定区块
        "role": "custom"
    },
}
```

## 💡 最佳实践

### ✅ 推荐做法

1. **开发阶段**：使用 `start_dev.ps1` 或 `DEV_MODE=true`
2. **生产部署**：使用 `start_prod.ps1` 或 `DEV_MODE=false`
3. **测试权限**：部署前运行 `test_permissions.py` 验证
4. **环境隔离**：不同环境使用不同配置文件

### ❌ 避免做法

1. ❌ 生产环境使用 `DEV_MODE=true`
2. ❌ 硬编码敏感信息
3. ❌ 在代码中直接修改权限后不测试

## 📚 更多文档

- `PERMISSION_CONFIG.md` - 完整权限配置文档
- `QUICKSTART.md` - 快速开始指南
- `DEPLOY_GUIDE.md` - 部署指南

## 🎉 总结

现在您的 MCP 服务器支持：

✅ **灵活切换**：开发模式 ↔️ 生产模式  
✅ **保留权限代码**：完整的 RBAC 实现  
✅ **方便测试**：一键启动开发模式  
✅ **安全部署**：生产环境严格控制  
✅ **快速验证**：测试脚本验证权限

开始使用：`.\start_dev.ps1` 🚀
