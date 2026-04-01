-- 修井记录数据表

CREATE TABLE IF NOT EXISTS workover_records (
    id SERIAL PRIMARY KEY,

    -- 基本标识
    jh VARCHAR(50) NOT NULL,           -- 井号
    kssj DATE,                         -- 作业开始日期
    jssj DATE,                         -- 作业结束日期

    -- 作业信息
    azlx VARCHAR(100),                 -- 作业类型
    azmd TEXT,                         -- 作业目的
    sgnr TEXT,                         -- 施工内容
    sgsd NUMERIC(10, 2),               -- 作业深度 (m)
    azjg TEXT,                         -- 作业结果
    sgdw VARCHAR(100),                 -- 施工单位
    rgjd NUMERIC(10, 2),               -- 人工井底 (m)
    bsqzsd VARCHAR(100),               -- 泵深/气嘴深
    bjqzdx VARCHAR(100),               -- 泵径/气嘴大小
    ccyz VARCHAR(100),                 -- 冲程/油嘴
    cc VARCHAR(100),                   -- 冲次
    source_file VARCHAR(300),          -- 来源文件名
    source_sheet VARCHAR(100),         -- 来源工作表
    source_row_no INTEGER,             -- 来源行号
    bz TEXT,                           -- 备注

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_wr_jh ON workover_records(jh);
CREATE INDEX IF NOT EXISTS idx_wr_kssj ON workover_records(kssj);
CREATE INDEX IF NOT EXISTS idx_wr_azlx ON workover_records(azlx);
CREATE INDEX IF NOT EXISTS idx_wr_jh_kssj ON workover_records(jh, kssj);
CREATE INDEX IF NOT EXISTS idx_wr_source_file ON workover_records(source_file);
CREATE INDEX IF NOT EXISTS idx_wr_is_deleted ON workover_records(is_deleted);

-- 兼容已存在表：补充新增字段
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS rgjd NUMERIC(10, 2);
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS bsqzsd VARCHAR(100);
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS bjqzdx VARCHAR(100);
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS ccyz VARCHAR(100);
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS cc VARCHAR(100);
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS source_file VARCHAR(300);
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS source_sheet VARCHAR(100);
ALTER TABLE workover_records ADD COLUMN IF NOT EXISTS source_row_no INTEGER;

COMMENT ON TABLE workover_records IS '修井记录数据表';
COMMENT ON COLUMN workover_records.jh IS '井号';
COMMENT ON COLUMN workover_records.kssj IS '作业开始日期';
COMMENT ON COLUMN workover_records.jssj IS '作业结束日期';
COMMENT ON COLUMN workover_records.azlx IS '作业类型';
COMMENT ON COLUMN workover_records.azmd IS '作业目的';
COMMENT ON COLUMN workover_records.sgnr IS '施工内容';
COMMENT ON COLUMN workover_records.sgsd IS '作业深度 (m)';
COMMENT ON COLUMN workover_records.azjg IS '作业结果';
COMMENT ON COLUMN workover_records.sgdw IS '施工单位';
COMMENT ON COLUMN workover_records.rgjd IS '人工井底 (m)';
COMMENT ON COLUMN workover_records.bsqzsd IS '泵深/气嘴深';
COMMENT ON COLUMN workover_records.bjqzdx IS '泵径/气嘴大小';
COMMENT ON COLUMN workover_records.ccyz IS '冲程/油嘴';
COMMENT ON COLUMN workover_records.cc IS '冲次';
COMMENT ON COLUMN workover_records.source_file IS '来源文件名';
COMMENT ON COLUMN workover_records.source_sheet IS '来源工作表';
COMMENT ON COLUMN workover_records.source_row_no IS '来源行号';
COMMENT ON COLUMN workover_records.bz IS '备注';

DROP TRIGGER IF EXISTS update_workover_records_updated_at ON workover_records;
CREATE TRIGGER update_workover_records_updated_at
    BEFORE UPDATE ON workover_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
