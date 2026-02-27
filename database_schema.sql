-- 油井基础信息表设计 - 针对rag数据库
-- 基于实际Excel数据结构设计
-- 注意：不会影响数据库中已有的表和vector扩展

CREATE TABLE IF NOT EXISTS oil_wells (
    -- 主键和基本标识
    id SERIAL PRIMARY KEY,
    well_name VARCHAR(100) NOT NULL,
    
    -- 项目分类信息
    ktxmlb VARCHAR(100),
    ktxm VARCHAR(100),
    ktzxm VARCHAR(100),
    
    -- 区块信息
    qk VARCHAR(50),
    qkdm VARCHAR(50),
    
    -- 井基本属性
    cw VARCHAR(50),
    jx VARCHAR(20),
    jb VARCHAR(20),
    jh VARCHAR(50),
    sfzdj VARCHAR(10),
    
    -- 设计参数
    sjrq DATE,
    sjjs NUMERIC(10, 2),
    sjzzbx NUMERIC(12, 2),
    sjhzby NUMERIC(12, 2),
    sjmdc VARCHAR(100),
    sjwzcw VARCHAR(100),
    
    -- 钻探信息
    ztmd TEXT,
    wzyz VARCHAR(200),
    
    -- 地理位置信息
    dmhb NUMERIC(10, 2),
    ss VARCHAR(50),
    sywz VARCHAR(100),
    
    -- 井旁地质测线
    jpdzcx1 VARCHAR(100),
    jpdzcx2 VARCHAR(100),
    
    -- 桩号和距离
    zh1 NUMERIC(10, 2),
    zh2 NUMERIC(10, 2),
    dcxjl1 NUMERIC(10, 2),
    dcxjl2 NUMERIC(10, 2),
    
    -- 合同和管理信息
    htqh VARCHAR(100),
    czr VARCHAR(50),
    lrr VARCHAR(50),
    bz TEXT,
    
    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_well_name ON oil_wells(well_name);
CREATE INDEX IF NOT EXISTS idx_qk ON oil_wells(qk);
CREATE INDEX IF NOT EXISTS idx_qkdm ON oil_wells(qkdm);
CREATE INDEX IF NOT EXISTS idx_sjrq ON oil_wells(sjrq);
CREATE INDEX IF NOT EXISTS idx_jx ON oil_wells(jx);
CREATE INDEX IF NOT EXISTS idx_ktxm ON oil_wells(ktxm);
CREATE INDEX IF NOT EXISTS idx_created_at ON oil_wells(created_at);
CREATE INDEX IF NOT EXISTS idx_is_deleted ON oil_wells(is_deleted);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_qk_jx ON oil_wells(qk, jx);
CREATE INDEX IF NOT EXISTS idx_ktxm_ktzxm ON oil_wells(ktxm, ktzxm);

-- 添加列注释
COMMENT ON TABLE oil_wells IS '油井基础信息表 - 存储油井的完整勘探和设计数据';
COMMENT ON COLUMN oil_wells.id IS '主键ID';
COMMENT ON COLUMN oil_wells.well_name IS '井名';
COMMENT ON COLUMN oil_wells.ktxmlb IS '勘探项目类别';
COMMENT ON COLUMN oil_wells.ktxm IS '勘探项目';
COMMENT ON COLUMN oil_wells.ktzxm IS '勘探子项目';
COMMENT ON COLUMN oil_wells.qk IS '区块';
COMMENT ON COLUMN oil_wells.qkdm IS '区块代码';
COMMENT ON COLUMN oil_wells.cw IS '层位';
COMMENT ON COLUMN oil_wells.jx IS '井型 (直井/预探井等)';
COMMENT ON COLUMN oil_wells.jb IS '井别';
COMMENT ON COLUMN oil_wells.jh IS '井号';
COMMENT ON COLUMN oil_wells.sfzdj IS '是否重点井';
COMMENT ON COLUMN oil_wells.sjrq IS '设计日期';
COMMENT ON COLUMN oil_wells.sjjs IS '设计井深 (米)';
COMMENT ON COLUMN oil_wells.sjzzbx IS '设计钻至标高';
COMMENT ON COLUMN oil_wells.sjhzby IS '设计海拔标高';
COMMENT ON COLUMN oil_wells.sjmdc IS '设计目的层';
COMMENT ON COLUMN oil_wells.sjwzcw IS '设计完钻层位';
COMMENT ON COLUMN oil_wells.ztmd IS '钻探目的';
COMMENT ON COLUMN oil_wells.wzyz IS '完钻原则';
COMMENT ON COLUMN oil_wells.dmhb IS '地面海拔';
COMMENT ON COLUMN oil_wells.ss IS '失矢';
COMMENT ON COLUMN oil_wells.sywz IS '水域位置';
COMMENT ON COLUMN oil_wells.jpdzcx1 IS '井旁地质测线1';
COMMENT ON COLUMN oil_wells.jpdzcx2 IS '井旁地质测线2';
COMMENT ON COLUMN oil_wells.zh1 IS '桩号1';
COMMENT ON COLUMN oil_wells.zh2 IS '桩号2';
COMMENT ON COLUMN oil_wells.dcxjl1 IS '到测线距离1';
COMMENT ON COLUMN oil_wells.dcxjl2 IS '到测线距离2';
COMMENT ON COLUMN oil_wells.htqh IS '合同区号';
COMMENT ON COLUMN oil_wells.czr IS '操作人';
COMMENT ON COLUMN oil_wells.lrr IS '录入人';
COMMENT ON COLUMN oil_wells.bz IS '备注';
COMMENT ON COLUMN oil_wells.created_at IS '创建时间';
COMMENT ON COLUMN oil_wells.updated_at IS '更新时间';
COMMENT ON COLUMN oil_wells.is_deleted IS '软删除标记';


-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_oil_wells_updated_at ON oil_wells;
CREATE TRIGGER update_oil_wells_updated_at 
    BEFORE UPDATE ON oil_wells 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
