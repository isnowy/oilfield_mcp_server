# PostgreSQL油井数据库设计文档

## 概述
根据提供的Excel数据表，设计了完整的油井信息存储方案。

## 数据库表结构

### 主表：oil_wells (油井基础信息表)

#### 字段说明

| 字段名 | 数据类型 | 说明 | 备注 |
|--------|---------|------|------|
| **id** | SERIAL | 主键 | 自增ID |
| **well_name** | VARCHAR(100) | 井名 | 唯一约束，对应Excel中的"D阱" |
| **ktxmlb** | VARCHAR(100) | 勘探项目类别 | 如"预探勘项目类别" |
| **ktxm** | VARCHAR(100) | 勘探项目 | 如"预探勘项目" |
| **ktzxm** | VARCHAR(100) | 勘探子项目 | 如"吐哈北部增储" |
| **qk** | VARCHAR(50) | 区块 | 如"北31" |
| **qkdm** | VARCHAR(50) | 区块代码 | 10位数字编码 |
| **cw** | VARCHAR(50) | 层位 | 如"H3/o" |
| **jx** | VARCHAR(20) | 井型 | 如"直井"、"预探井" |
| **jb** | VARCHAR(20) | 井别 | 如"预探井" |
| **jh** | VARCHAR(50) | 井号 | 井的编号 |
| **sfzdj** | VARCHAR(10) | 是否重点井 | "是"或其他值 |
| **sjrq** | DATE | 设计日期 | 井的设计时间 |
| **sjjs** | NUMERIC(10,2) | 设计井深 | 单位：米 |
| **sjzzbx** | NUMERIC(12,2) | 设计钻至标高 | 钻探终点标高 |
| **sjhzby** | NUMERIC(12,2) | 设计海拔标高 | 地面海拔 |
| **sjmdc** | VARCHAR(100) | 设计目的层 | 目标地层 |
| **sjwzcw** | VARCHAR(100) | 设计完钻层位 | 完成钻探的层位 |
| **ztmd** | TEXT | 钻探目的 | 钻探的详细目标描述 |
| **wzyz** | VARCHAR(200) | 完钻原则 | 完成钻探的判断原则 |
| **dmhb** | NUMERIC(10,2) | 地面海拔 | 井口地面高程 |
| **ss** | VARCHAR(50) | 失矢 | 测量相关 |
| **sywz** | VARCHAR(100) | 水域位置 | 是否在水域及具体位置 |
| **jpdzcx1** | VARCHAR(100) | 井旁地质测线1 | 第一条测线编号 |
| **jpdzcx2** | VARCHAR(100) | 井旁地质测线2 | 第二条测线编号 |
| **zh1** | NUMERIC(10,2) | 桩号1 | 第一个桩号 |
| **zh2** | NUMERIC(10,2) | 桩号2 | 第二个桩号 |
| **dcxjl1** | NUMERIC(10,2) | 到测线距离1 | 到第一条测线的距离 |
| **dcxjl2** | NUMERIC(10,2) | 到测线距离2 | 到第二条测线的距离 |
| **htqh** | VARCHAR(100) | 合同区号 | 合同标识 |
| **czr** | VARCHAR(50) | 操作人 | 数据操作人员 |
| **lrr** | VARCHAR(50) | 录入人 | 数据录入人员 |
| **bz** | TEXT | 备注 | 其他说明信息 |
| **created_at** | TIMESTAMP | 创建时间 | 自动生成 |
| **updated_at** | TIMESTAMP | 更新时间 | 自动更新 |
| **is_deleted** | BOOLEAN | 软删除标记 | 默认false |

## 索引设计

### 单列索引
- `idx_well_name`: 井名索引（最常用查询）
- `idx_qk`: 区块索引
- `idx_qkdm`: 区块代码索引
- `idx_sjrq`: 设计日期索引（时间范围查询）
- `idx_jx`: 井型索引
- `idx_ktxm`: 勘探项目索引
- `idx_created_at`: 创建时间索引
- `idx_is_deleted`: 软删除标记索引

### 复合索引
- `idx_qk_jx`: 区块+井型组合查询
- `idx_ktxm_ktzxm`: 项目+子项目组合查询

## 数据类型选择说明

1. **VARCHAR vs TEXT**
   - 固定长度且需要索引的用VARCHAR
   - 长文本描述用TEXT

2. **NUMERIC**
   - 用于需要精确计算的数值（深度、距离等）
   - 避免浮点数精度问题

3. **DATE vs TIMESTAMP**
   - 业务日期用DATE
   - 系统时间戳用TIMESTAMP

## 使用说明

### 1. 创建油井表（在现有rag数据库中）

```bash
# 方法1：使用批处理脚本（Windows）
setup_oil_wells_table.bat

# 方法2：手动执行SQL脚本
psql -U postgres -d rag -f database_schema.sql

# 方法3：在psql命令行中
psql -U postgres -d rag
\i database_schema.sql
```

**注意**：脚本已配置为使用`rag`数据库，不会影响数据库中已有的表和vector扩展。

### 2. 导入Excel数据

```bash
# 安装依赖
pip install pandas openpyxl psycopg2-binary

# 修改import_well_data.py中的配置
# - 数据库连接信息
# - Excel文件路径

# 运行导入脚本
python import_well_data.py
```

### 3. 常用查询示例

```sql
-- 查询某个区块的所有井
SELECT * FROM oil_wells WHERE qk = '北31' AND is_deleted = false;

-- 查询某个时间段的井
SELECT * FROM oil_wells 
WHERE sjrq BETWEEN '1989-01-01' AND '1989-12-31'
AND is_deleted = false;

-- 查询重点井
SELECT well_name, qk, sjrq, sjjs 
FROM oil_wells 
WHERE sfzdj = '是' AND is_deleted = false;

-- 按区块统计井数
SELECT qk, COUNT(*) as well_count
FROM oil_wells
WHERE is_deleted = false
GROUP BY qk
ORDER BY well_count DESC;

-- 查询井深大于3000米的井
SELECT well_name, qk, sjjs
FROM oil_wells
WHERE sjjs > 3000 AND is_deleted = false
ORDER BY sjjs DESC;
```

## 扩展建议

### 1. 如果需要分表，可以按以下维度：
- **按时间分区**：每年一个分区
- **按区块分区**：主要区块独立分区

### 2. 可以增加的关联表：
- **oil_well_production**：生产数据表
- **oil_well_maintenance**：维护记录表
- **oil_well_inspection**：检测记录表
- **oil_well_documents**：文档附件表

### 3. 性能优化建议：
- 定期VACUUM和ANALYZE
- 根据实际查询模式调整索引
- 考虑使用物化视图加速复杂统计查询

## 备份和恢复

```bash
# 备份rag数据库
pg_dump -U postgres rag > rag_backup.sql

# 仅备份oil_wells表
pg_dump -U postgres -t oil_wells rag > oil_wells_backup.sql

# 恢复数据库
psql -U postgres rag < rag_backup.sql

# 仅备份数据（不含结构）
pg_dump -U postgres --data-only -t oil_wells rag > oil_wells_data.sql
```

## 注意事项

1. **数据一致性**：well_name字段设置了唯一约束，确保井名不重复
2. **软删除**：使用is_deleted标记而非物理删除，保留历史数据
3. **自动时间戳**：created_at和updated_at自动维护
4. **事务处理**：批量导入时使用事务确保数据完整性
5. **字符编码**：确保数据库使用UTF-8编码支持中文
