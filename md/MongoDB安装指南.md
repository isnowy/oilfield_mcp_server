# MongoDB 安装指南

## Windows 系统安装 MongoDB

### 方法一：使用自动安装脚本（推荐）

运行项目根目录下的安装脚本：

```powershell
.\install_mongodb.ps1
```

### 方法二：使用 winget 命令行安装

在 PowerShell（管理员权限）中运行：

```powershell
winget install -e --id MongoDB.Server
```

### 方法三：手动下载安装

#### 1. 下载 MongoDB

访问官方下载页面：
```
https://www.mongodb.com/try/download/community
```

选择配置：
- **Version**: 当前稳定版本（推荐 7.0.x 或 6.0.x）
- **Platform**: Windows x64
- **Package**: MSI

#### 2. 安装 MongoDB

1. 双击下载的 `.msi` 文件启动安装程序
2. 选择 **"Complete"** 完整安装
3. 在 **Service Configuration** 步骤：
   - 勾选 ✅ **"Install MongoDB as a Service"**
   - Service Name: `MongoDB`
   - Data Directory: `C:\Program Files\MongoDB\Server\<version>\data`
   - Log Directory: `C:\Program Files\MongoDB\Server\<version>\log`
4. 可选：取消勾选 MongoDB Compass（图形化管理工具，如果不需要）
5. 点击 **Install** 开始安装

#### 3. 配置环境变量

安装完成后，将 MongoDB 的 bin 目录添加到系统 PATH：

1. 右键 **"此电脑"** → **"属性"**
2. 点击 **"高级系统设置"**
3. 点击 **"环境变量"**
4. 在 **"系统变量"** 中找到 `Path`，点击 **"编辑"**
5. 点击 **"新建"**，添加：
   ```
   C:\Program Files\MongoDB\Server\7.0\bin
   ```
   （根据实际安装版本调整路径）
6. 点击 **"确定"** 保存

#### 4. 创建数据目录

MongoDB 需要一个数据存储目录，默认为 `C:\data\db`：

```powershell
# 在 PowerShell 中运行
New-Item -ItemType Directory -Path "C:\data\db" -Force
```

或者使用 CMD：
```cmd
mkdir C:\data\db
```

#### 5. 验证安装

重新打开 PowerShell，运行：

```powershell
mongod --version
mongo --version  # 或 mongosh --version (新版本)
```

如果显示版本信息，说明安装成功！

### 启动 MongoDB

#### 作为 Windows 服务运行（推荐）

如果安装时选择了作为服务安装，MongoDB 会自动启动。

查看服务状态：
```powershell
Get-Service MongoDB
```

手动启动/停止服务：
```powershell
# 启动服务
Start-Service MongoDB

# 停止服务
Stop-Service MongoDB

# 重启服务
Restart-Service MongoDB
```

#### 手动启动

如果没有安装为服务，可以手动启动：

```powershell
# 启动 MongoDB 服务器
mongod --dbpath "C:\data\db"
```

### 连接 MongoDB

启动 MongoDB Shell：

```powershell
# MongoDB 6.0 及以上版本
mongosh

# 旧版本
mongo
```

### 配置文件示例

MongoDB 配置文件通常位于：
```
C:\Program Files\MongoDB\Server\7.0\bin\mongod.cfg
```

基本配置示例：
```yaml
systemLog:
  destination: file
  path: C:\Program Files\MongoDB\Server\7.0\log\mongod.log
  logAppend: true
storage:
  dbPath: C:\Program Files\MongoDB\Server\7.0\data
net:
  port: 27017
  bindIp: 127.0.0.1
```

### 本项目使用 MongoDB

安装完成后，确保在项目中安装 Python MongoDB 驱动：

```bash
pip install pymongo
```

在 `oilfield_mcp_server.py` 或相关配置文件中配置连接：

```python
from pymongo import MongoClient

# 连接本地 MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['oilfield_db']
```

### 常见问题

#### 1. 无法识别 mongod 命令

**解决方案**：
- 确认 MongoDB bin 目录已添加到系统 PATH
- 重启 PowerShell 或命令行窗口
- 使用完整路径运行：`"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --version`

#### 2. 服务启动失败

**检查事项**：
- 数据目录 `C:\data\db` 是否存在
- 查看日志文件：`C:\Program Files\MongoDB\Server\7.0\log\mongod.log`
- 检查端口 27017 是否被占用：`netstat -ano | findstr 27017`

#### 3. 权限问题

**解决方案**：
- 以管理员权限运行 PowerShell
- 确保数据目录有写入权限

### 卸载 MongoDB

使用 Windows 设置卸载：
1. **设置** → **应用** → **应用和功能**
2. 找到 **MongoDB**，点击 **卸载**

或使用 winget：
```powershell
winget uninstall MongoDB.Server
```

手动清理：
- 删除数据目录：`C:\data\db`
- 删除安装目录：`C:\Program Files\MongoDB`
- 从系统 PATH 中移除 MongoDB 路径

---

## 参考资料

- [MongoDB 官方文档](https://www.mongodb.com/docs/)
- [MongoDB Windows 安装指南](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/)
- [PyMongo 文档](https://pymongo.readthedocs.io/)
