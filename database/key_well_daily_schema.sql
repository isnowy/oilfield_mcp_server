-- 重点井试采日报数据表设计
-- 基于key_well_daily.xlsx数据结构设计

CREATE TABLE IF NOT EXISTS key_well_daily (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 井基本信息（井号关联oil_wells表）
    jh VARCHAR(50) NOT NULL,  -- 井号
    qk VARCHAR(50),            -- 区块
    cw VARCHAR(50),            -- 层位
    cxh VARCHAR(50),           -- 层序号
    
    -- 深度信息
    djsd1 DECIMAL(10, 2),      -- 顶界深度1
    djsd2 DECIMAL(10, 2),      -- 底界深度2
    
    -- 日报基本信息
    rq DATE NOT NULL,          -- 日期
    zt VARCHAR(50),            -- 状态
    cyfs VARCHAR(50),          -- 采油方式
    yz VARCHAR(50),            -- 油嘴
    
    -- 工作信息
    gzsj VARCHAR(100),         -- 工作时间
    gzzd VARCHAR(50),          -- 工作制度
    rcql DECIMAL(10, 2),       -- 日产气量（万方）
    hs DECIMAL(10, 2),         -- 含水（%）
    
    -- 压力信息 - 油压
    yysx DECIMAL(10, 4),       -- 油压上限（兆帕）
    yyxx DECIMAL(10, 4),       -- 油压下限（兆帕）
    
    -- 压力信息 - 套压
    tysx DECIMAL(10, 4),       -- 套压上限（兆帕）
    tyxx DECIMAL(10, 4),       -- 套压下限（兆帕）
    
    -- 压力信息 - 回压
    hysx DECIMAL(10, 4),       -- 回压上限（兆帕）
    hyxx DECIMAL(10, 4),       -- 回压下限（兆帕）
    
    -- 其他压力信息
    d_ly DECIMAL(10, 4),       -- 流压
    d_jy DECIMAL(10, 4),       -- 静压
    
    -- 备注
    d_bz TEXT,                 -- 施工内容/备注
    
    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_kwd_jh ON key_well_daily(jh);
CREATE INDEX IF NOT EXISTS idx_kwd_rq ON key_well_daily(rq);
CREATE INDEX IF NOT EXISTS idx_kwd_qk ON key_well_daily(qk);
CREATE INDEX IF NOT EXISTS idx_kwd_zt ON key_well_daily(zt);
CREATE INDEX IF NOT EXISTS idx_kwd_created_at ON key_well_daily(created_at);
CREATE INDEX IF NOT EXISTS idx_kwd_is_deleted ON key_well_daily(is_deleted);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_kwd_jh_rq ON key_well_daily(jh, rq);
CREATE INDEX IF NOT EXISTS idx_kwd_qk_rq ON key_well_daily(qk, rq);

-- 添加列注释
COMMENT ON TABLE key_well_daily IS '重点井试采日报数据表 - 存储重点井每日生产数据';
COMMENT ON COLUMN key_well_daily.id IS '主键ID';
COMMENT ON COLUMN key_well_daily.jh IS '井号（关联oil_wells表）';
COMMENT ON COLUMN key_well_daily.qk IS '区块';
COMMENT ON COLUMN key_well_daily.cw IS '层位';
COMMENT ON COLUMN key_well_daily.cxh IS '层序号';
COMMENT ON COLUMN key_well_daily.djsd1 IS '顶界深度1';
COMMENT ON COLUMN key_well_daily.djsd2 IS '底界深度2';
COMMENT ON COLUMN key_well_daily.rq IS '日期';
COMMENT ON COLUMN key_well_daily.zt IS '状态';
COMMENT ON COLUMN key_well_daily.cyfs IS '采油方式';
COMMENT ON COLUMN key_well_daily.yz IS '油嘴';
COMMENT ON COLUMN key_well_daily.gzsj IS '工作时间';
COMMENT ON COLUMN key_well_daily.gzzd IS '工作制度';
COMMENT ON COLUMN key_well_daily.rcql IS '日产气量（万方）';
COMMENT ON COLUMN key_well_daily.hs IS '含水（%）';
COMMENT ON COLUMN key_well_daily.yysx IS '油压上限（兆帕）';
COMMENT ON COLUMN key_well_daily.yyxx IS '油压下限（兆帕）';
COMMENT ON COLUMN key_well_daily.tysx IS '套压上限（兆帕）';
COMMENT ON COLUMN key_well_daily.tyxx IS '套压下限（兆帕）';
COMMENT ON COLUMN key_well_daily.hysx IS '回压上限（兆帕）';
COMMENT ON COLUMN key_well_daily.hyxx IS '回压下限（兆帕）';
COMMENT ON COLUMN key_well_daily.d_ly IS '流压';
COMMENT ON COLUMN key_well_daily.d_jy IS '静压';
COMMENT ON COLUMN key_well_daily.d_bz IS '施工内容/备注';
COMMENT ON COLUMN key_well_daily.created_at IS '创建时间';
COMMENT ON COLUMN key_well_daily.updated_at IS '更新时间';
COMMENT ON COLUMN key_well_daily.is_deleted IS '软删除标记';

-- 创建更新时间触发器
DROP TRIGGER IF EXISTS update_key_well_daily_updated_at ON key_well_daily;
CREATE TRIGGER update_key_well_daily_updated_at 
    BEFORE UPDATE ON key_well_daily 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
