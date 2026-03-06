# 数据库文件夹

本文件夹包含所有数据库相关的 schema 定义、数据导入脚本和初始化工具。

---

## 📁 文件说明

### **数据库 Schema 文件**

| 文件名 | 用途 |
|--------|------|
| `database_schema.sql` | 油井基础数据表结构定义 |
| `drilling_daily_schema.sql` | 钻井工程日报表结构定义 |
| `drilling_pre_daily_schema.sql` | 钻前工程日报表结构定义 |
| `key_well_daily_schema.sql` | 重点井试采日报表结构定义 |

### **数据库初始化脚本**

| 文件名 | 用途 |
|--------|------|
| `init_db.py` | 数据库初始化主脚本 |
| `setup_oil_wells_table.py` | 创建油井数据表 (Python) |
| `setup_oil_wells_table.bat` | 创建油井数据表 (批处理) |

### **数据导入脚本**

| 文件名 | 用途 |
|--------|------|
| `import_well_data.py` | 导入油井基础数据 |
| `import_drilling_daily.py` | 导入钻井工程日报数据 |
| `import_drilling_pre_daily.py` | 导入钻前工程日报数据 |
| `import_key_well_daily.py` | 导入重点井试采日报数据 |

---

## 🚀 使用方法

### 1. 初始化数据库结构

**方法一：使用 Python 脚本**
```bash
cd database
python init_db.py
```

**方法二：使用批处理文件**
```cmd
cd database
setup_oil_wells_table.bat
```

### 2. 导入数据

**导入油井基础数据：**
```bash
python import_well_data.py
```

**导入钻井工程日报：**
```bash
python import_drilling_daily.py
```

**导入钻前工程日报：**
```bash
python import_drilling_pre_daily.py
```

**导入重点井试采日报：**
```bash
python import_key_well_daily.py
```

---

## ⚙️ 配置说明

数据库连接配置通过环境变量设置：

```bash
DB_HOST=localhost      # 数据库主机
DB_PORT=5432          # 数据库端口
DB_NAME=rag           # 数据库名称
DB_USER=postgres      # 数据库用户
DB_PASSWORD=postgres  # 数据库密码
```

或在脚本中直接配置 `DB_CONFIG` 字典。

---

## 📊 数据表结构

### **oil_wells** - 油井基础数据表
包含油井的基本信息、设计参数、地理位置等。

### **drilling_daily** - 钻井工程日报表
记录每日钻井作业数据，包括进尺、钻速、泥浆参数等。

### **drilling_pre_daily** - 钻前工程日报表
记录钻前准备工作的时间节点和进度。

### **key_well_daily** - 重点井试采日报表
记录重点井的试采数据，包括产量、压力参数等。

---

## 🔧 维护与更新

### 添加新的数据表
1. 在此文件夹创建新的 `*_schema.sql` 文件
2. 在 `init_db.py` 中添加表创建逻辑
3. 创建对应的 `import_*.py` 导入脚本

### 修改现有表结构
1. 修改对应的 `*_schema.sql` 文件
2. 使用数据库迁移工具或手动执行 ALTER TABLE 语句
3. 更新相关的导入脚本

---

## 📝 注意事项

1. **数据备份**：在执行任何 schema 修改前，请先备份数据
2. **权限检查**：确保数据库用户有创建表和导入数据的权限
3. **数据清理**：导入脚本会自动处理 `is_deleted` 字段标记删除的数据
4. **字符编码**：所有脚本使用 UTF-8 编码，支持中文

---

## 🐛 常见问题

### 问题：连接数据库失败
**解决方案**：
1. 检查 PostgreSQL 服务是否启动
2. 验证数据库配置是否正确
3. 确认防火墙允许数据库端口

### 问题：导入数据失败
**解决方案**：
1. 确保表结构已创建（先运行 `init_db.py`）
2. 检查数据文件路径是否正确
3. 验证数据格式是否符合表结构

### 问题：中文显示乱码
**解决方案**：
1. 确保数据库使用 UTF-8 编码
2. 在 Windows 中设置 `chcp 65001`
3. 检查 Python 脚本文件编码

---

**创建日期**: 2026年3月5日  
**版本**: v1.0
