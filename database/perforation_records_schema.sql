-- 射孔记录数据表

CREATE TABLE IF NOT EXISTS perforation_records (
    id SERIAL PRIMARY KEY,

    -- 基本标识
    jh VARCHAR(50) NOT NULL,           -- 井号
    sksj DATE,                         -- 射孔日期
    cw VARCHAR(50),                    -- 层位

    -- 射孔参数
    sk_top NUMERIC(10, 2),             -- 射孔顶深 (m)
    sk_bot NUMERIC(10, 2),             -- 射孔底深 (m)
    skhs NUMERIC(10, 2),               -- 射孔厚度 (m)
    skqx VARCHAR(50),                  -- 射孔枪型
    skmd NUMERIC(8, 2),                -- 射孔密度 (孔/m)
    kj NUMERIC(8, 2),                  -- 孔径 (mm)
    skfs VARCHAR(50),                  -- 射孔方式
    zccs_rq DATE,                      -- 增产措施日期
    zccs_cw VARCHAR(100),              -- 增产措施层位
    ylfs VARCHAR(100),                 -- 压裂方式
    ylmc VARCHAR(200),                 -- 液名称
    zylq_nql VARCHAR(100),             -- 总液量/氮气量
    sl_ss VARCHAR(100),                -- 砂量/瞬时
    bl_tbyl VARCHAR(100),              -- 破裂/停泵压力
    zccs_bz TEXT,                      -- 增产措施备注
    source_file VARCHAR(300),          -- 来源文件名
    source_sheet VARCHAR(100),         -- 来源工作表
    source_row_no INTEGER,             -- 来源行号
    bz TEXT,                           -- 备注

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_pr_jh ON perforation_records(jh);
CREATE INDEX IF NOT EXISTS idx_pr_sksj ON perforation_records(sksj);
CREATE INDEX IF NOT EXISTS idx_pr_cw ON perforation_records(cw);
CREATE INDEX IF NOT EXISTS idx_pr_jh_sksj ON perforation_records(jh, sksj);
CREATE INDEX IF NOT EXISTS idx_pr_zccs_rq ON perforation_records(zccs_rq);
CREATE INDEX IF NOT EXISTS idx_pr_source_file ON perforation_records(source_file);
CREATE INDEX IF NOT EXISTS idx_pr_is_deleted ON perforation_records(is_deleted);

-- 兼容已存在表：补充新增字段
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS zccs_rq DATE;
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS zccs_cw VARCHAR(100);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS ylfs VARCHAR(100);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS ylmc VARCHAR(200);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS zylq_nql VARCHAR(100);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS sl_ss VARCHAR(100);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS bl_tbyl VARCHAR(100);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS zccs_bz TEXT;
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS source_file VARCHAR(300);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS source_sheet VARCHAR(100);
ALTER TABLE perforation_records ADD COLUMN IF NOT EXISTS source_row_no INTEGER;

COMMENT ON TABLE perforation_records IS '射孔记录数据表';
COMMENT ON COLUMN perforation_records.jh IS '井号';
COMMENT ON COLUMN perforation_records.sksj IS '射孔日期';
COMMENT ON COLUMN perforation_records.cw IS '层位';
COMMENT ON COLUMN perforation_records.sk_top IS '射孔顶深 (m)';
COMMENT ON COLUMN perforation_records.sk_bot IS '射孔底深 (m)';
COMMENT ON COLUMN perforation_records.skhs IS '射孔厚度 (m)';
COMMENT ON COLUMN perforation_records.skqx IS '射孔枪型';
COMMENT ON COLUMN perforation_records.skmd IS '射孔密度 (孔/m)';
COMMENT ON COLUMN perforation_records.kj IS '孔径 (mm)';
COMMENT ON COLUMN perforation_records.skfs IS '射孔方式';
COMMENT ON COLUMN perforation_records.zccs_rq IS '增产措施日期';
COMMENT ON COLUMN perforation_records.zccs_cw IS '增产措施层位';
COMMENT ON COLUMN perforation_records.ylfs IS '压裂方式';
COMMENT ON COLUMN perforation_records.ylmc IS '液名称';
COMMENT ON COLUMN perforation_records.zylq_nql IS '总液量/氮气量';
COMMENT ON COLUMN perforation_records.sl_ss IS '砂量/瞬时';
COMMENT ON COLUMN perforation_records.bl_tbyl IS '破裂/停泵压力';
COMMENT ON COLUMN perforation_records.zccs_bz IS '增产措施备注';
COMMENT ON COLUMN perforation_records.source_file IS '来源文件名';
COMMENT ON COLUMN perforation_records.source_sheet IS '来源工作表';
COMMENT ON COLUMN perforation_records.source_row_no IS '来源行号';
COMMENT ON COLUMN perforation_records.bz IS '备注';

DROP TRIGGER IF EXISTS update_perforation_records_updated_at ON perforation_records;
CREATE TRIGGER update_perforation_records_updated_at
    BEFORE UPDATE ON perforation_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
