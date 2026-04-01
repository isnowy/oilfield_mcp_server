-- 分析化验数据表
-- 气样和水样共用一张表，yplx 字段区分类型

CREATE TABLE IF NOT EXISTS well_analysis (
    id SERIAL PRIMARY KEY,

    -- 基本标识
    jh VARCHAR(50) NOT NULL,           -- 井号
    qyrq DATE,                         -- 取样日期
    yplx VARCHAR(20),                  -- 样品类型（气样/水样）
    cw VARCHAR(50),                    -- 层位
    bgbh VARCHAR(100),                 -- 报告编号
    ypbh VARCHAR(100),                 -- 样品编号
    ypmc VARCHAR(100),                 -- 样品名称
    qydd VARCHAR(100),                 -- 取样地点
    qyr VARCHAR(100),                  -- 取样人
    cyrq DATE,                         -- 采样日期

    -- 气样组分 (mol%)
    ch4 NUMERIC(10, 4),                -- 甲烷
    c2h6 NUMERIC(10, 4),               -- 乙烷
    c3h8 NUMERIC(10, 4),               -- 丙烷
    c4h10 NUMERIC(10, 4),              -- 丁烷
    c5h12 NUMERIC(10, 4),              -- 戊烷
    ic4h10 NUMERIC(10, 4),             -- 异丁烷
    nc4h10 NUMERIC(10, 4),             -- 正丁烷
    ic5h12 NUMERIC(10, 4),             -- 异戊烷
    nc5h12 NUMERIC(10, 4),             -- 正戊烷
    c6_plus NUMERIC(10, 4),            -- C6+
    co2 NUMERIC(10, 4),                -- 二氧化碳
    n2 NUMERIC(10, 4),                 -- 氮气
    h2s NUMERIC(10, 4),                -- 硫化氢
    h2 NUMERIC(10, 4),                 -- 氢气
    co NUMERIC(10, 4),                 -- 一氧化碳
    o2 NUMERIC(10, 4),                 -- 氧气

    -- 气样物性
    molecular_weight NUMERIC(10, 4),   -- 计算分子量
    standard_density NUMERIC(12, 4),   -- 标准密度 (kg/m3)
    relative_density NUMERIC(12, 4),   -- 相对密度
    high_calorific_value NUMERIC(14, 2), -- 高位发热量 (kJ/m3)
    low_calorific_value NUMERIC(14, 2),  -- 低位发热量 (kJ/m3)
    compressibility_factor NUMERIC(10, 4), -- 压缩因子

    -- 水样离子 (mg/L)
    ph NUMERIC(6, 2),                  -- pH 值
    tds NUMERIC(12, 2),                -- 总溶解固体 (mg/L)
    cl_ion NUMERIC(12, 2),             -- 氯离子 Cl⁻
    so4_ion NUMERIC(12, 2),            -- 硫酸根 SO₄²⁻
    hco3_ion NUMERIC(12, 2),           -- 碳酸氢根 HCO₃⁻
    co3_ion NUMERIC(12, 2),            -- 碳酸根 CO₃²⁻
    ca_ion NUMERIC(12, 2),             -- 钙离子 Ca²⁺
    mg_ion NUMERIC(12, 2),             -- 镁离子 Mg²⁺
    na_k_ion NUMERIC(12, 2),           -- 钠钾离子 Na⁺+K⁺
    oh_ion NUMERIC(12, 2),             -- 氢氧根 OH⁻
    mineralization NUMERIC(12, 2),     -- 矿化度 (mg/L)
    total_hardness NUMERIC(12, 2),     -- 总硬度(以CaCO3计) (mg/L)
    total_alkalinity NUMERIC(12, 2),   -- 总碱度(以CaCO3计) (mg/L)

    -- 公共字段
    hyj VARCHAR(100),                  -- 化验机构
    bz TEXT,                           -- 备注

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_wa_jh ON well_analysis(jh);
CREATE INDEX IF NOT EXISTS idx_wa_qyrq ON well_analysis(qyrq);
CREATE INDEX IF NOT EXISTS idx_wa_yplx ON well_analysis(yplx);
CREATE INDEX IF NOT EXISTS idx_wa_jh_qyrq ON well_analysis(jh, qyrq);
CREATE INDEX IF NOT EXISTS idx_wa_is_deleted ON well_analysis(is_deleted);

-- 兼容已存在表：补充新增字段
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS bgbh VARCHAR(100);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS ypbh VARCHAR(100);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS ypmc VARCHAR(100);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS qydd VARCHAR(100);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS qyr VARCHAR(100);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS cyrq DATE;
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS ic4h10 NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS nc4h10 NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS ic5h12 NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS nc5h12 NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS c6_plus NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS h2 NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS co NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS o2 NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS molecular_weight NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS standard_density NUMERIC(12, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS relative_density NUMERIC(12, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS high_calorific_value NUMERIC(14, 2);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS low_calorific_value NUMERIC(14, 2);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS compressibility_factor NUMERIC(10, 4);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS oh_ion NUMERIC(12, 2);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS mineralization NUMERIC(12, 2);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS total_hardness NUMERIC(12, 2);
ALTER TABLE well_analysis ADD COLUMN IF NOT EXISTS total_alkalinity NUMERIC(12, 2);

COMMENT ON TABLE well_analysis IS '分析化验数据表 - 气样和水样共用，yplx 字段区分';
COMMENT ON COLUMN well_analysis.jh IS '井号';
COMMENT ON COLUMN well_analysis.qyrq IS '取样日期';
COMMENT ON COLUMN well_analysis.yplx IS '样品类型（气样/水样）';
COMMENT ON COLUMN well_analysis.cw IS '层位';
COMMENT ON COLUMN well_analysis.bgbh IS '报告编号';
COMMENT ON COLUMN well_analysis.ypbh IS '样品编号';
COMMENT ON COLUMN well_analysis.ypmc IS '样品名称';
COMMENT ON COLUMN well_analysis.qydd IS '取样地点';
COMMENT ON COLUMN well_analysis.qyr IS '取样人';
COMMENT ON COLUMN well_analysis.cyrq IS '采样日期';
COMMENT ON COLUMN well_analysis.ch4 IS '甲烷 (mol%)';
COMMENT ON COLUMN well_analysis.c2h6 IS '乙烷 (mol%)';
COMMENT ON COLUMN well_analysis.c3h8 IS '丙烷 (mol%)';
COMMENT ON COLUMN well_analysis.c4h10 IS '丁烷 (mol%)';
COMMENT ON COLUMN well_analysis.c5h12 IS '戊烷 (mol%)';
COMMENT ON COLUMN well_analysis.ic4h10 IS '异丁烷 (mol%)';
COMMENT ON COLUMN well_analysis.nc4h10 IS '正丁烷 (mol%)';
COMMENT ON COLUMN well_analysis.ic5h12 IS '异戊烷 (mol%)';
COMMENT ON COLUMN well_analysis.nc5h12 IS '正戊烷 (mol%)';
COMMENT ON COLUMN well_analysis.c6_plus IS 'C6+ (mol%)';
COMMENT ON COLUMN well_analysis.co2 IS '二氧化碳 (mol%)';
COMMENT ON COLUMN well_analysis.n2 IS '氮气 (mol%)';
COMMENT ON COLUMN well_analysis.h2s IS '硫化氢 (mol%)';
COMMENT ON COLUMN well_analysis.h2 IS '氢气 (mol%)';
COMMENT ON COLUMN well_analysis.co IS '一氧化碳 (mol%)';
COMMENT ON COLUMN well_analysis.o2 IS '氧气 (mol%)';
COMMENT ON COLUMN well_analysis.molecular_weight IS '计算分子量';
COMMENT ON COLUMN well_analysis.standard_density IS '标准密度 (kg/m3)';
COMMENT ON COLUMN well_analysis.relative_density IS '相对密度';
COMMENT ON COLUMN well_analysis.high_calorific_value IS '高位发热量 (kJ/m3)';
COMMENT ON COLUMN well_analysis.low_calorific_value IS '低位发热量 (kJ/m3)';
COMMENT ON COLUMN well_analysis.compressibility_factor IS '压缩因子';
COMMENT ON COLUMN well_analysis.ph IS 'pH 值';
COMMENT ON COLUMN well_analysis.tds IS '总溶解固体 (mg/L)';
COMMENT ON COLUMN well_analysis.cl_ion IS '氯离子 (mg/L)';
COMMENT ON COLUMN well_analysis.so4_ion IS '硫酸根 (mg/L)';
COMMENT ON COLUMN well_analysis.hco3_ion IS '碳酸氢根 (mg/L)';
COMMENT ON COLUMN well_analysis.co3_ion IS '碳酸根 (mg/L)';
COMMENT ON COLUMN well_analysis.ca_ion IS '钙离子 (mg/L)';
COMMENT ON COLUMN well_analysis.mg_ion IS '镁离子 (mg/L)';
COMMENT ON COLUMN well_analysis.na_k_ion IS '钠钾离子 (mg/L)';
COMMENT ON COLUMN well_analysis.oh_ion IS '氢氧根 (mg/L)';
COMMENT ON COLUMN well_analysis.mineralization IS '矿化度 (mg/L)';
COMMENT ON COLUMN well_analysis.total_hardness IS '总硬度(以CaCO3计) (mg/L)';
COMMENT ON COLUMN well_analysis.total_alkalinity IS '总碱度(以CaCO3计) (mg/L)';
COMMENT ON COLUMN well_analysis.hyj IS '化验机构';
COMMENT ON COLUMN well_analysis.bz IS '备注';

DROP TRIGGER IF EXISTS update_well_analysis_updated_at ON well_analysis;
CREATE TRIGGER update_well_analysis_updated_at
    BEFORE UPDATE ON well_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
