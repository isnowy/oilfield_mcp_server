-- 钻井工程日报数据表设计
-- 基于drilling_daily.xlsx数据结构设计

CREATE TABLE IF NOT EXISTS drilling_daily (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 基本信息
    rq DATE NOT NULL,                      -- 日期
    jh VARCHAR(50),                        -- 井号（关联oil_wells.well_name，允许为空）
    kzrq DATE,                             -- 开钻日期
    
    -- 钻井参数
    drjs DECIMAL(10, 2),                   -- 当日井深（米）
    zjrjc DECIMAL(10, 2),                  -- 日进尺（米）
    
    -- 钻头信息
    ztlx VARCHAR(50),                      -- 钻头类型
    ztzj DECIMAL(10, 2),                   -- 钻头直径（毫米）
    
    -- 钻井工艺参数
    zy DECIMAL(10, 2),                     -- 钻压（千牛）
    zs DECIMAL(10, 2),                     -- 钻速（米/小时）
    bya DECIMAL(10, 2),                    -- 泵压（兆帕）
    bpl DECIMAL(10, 2),                    -- 排量（升/秒）
    
    -- 钻井液参数
    zjymd DECIMAL(10, 2),                  -- 钻井液密度（克/立方厘米）
    zjynd DECIMAL(10, 2),                  -- 钻井液粘度（秒）
    
    -- 工作时间与内容
    czjljsj DECIMAL(10, 2),                -- 纯钻进累计时间（小时）
    brzygz TEXT,                           -- 本日主要工作
    
    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_dd_jh ON drilling_daily(jh);
CREATE INDEX IF NOT EXISTS idx_dd_rq ON drilling_daily(rq);
CREATE INDEX IF NOT EXISTS idx_dd_kzrq ON drilling_daily(kzrq);
CREATE INDEX IF NOT EXISTS idx_dd_created_at ON drilling_daily(created_at);
CREATE INDEX IF NOT EXISTS idx_dd_is_deleted ON drilling_daily(is_deleted);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_dd_jh_rq ON drilling_daily(jh, rq);

-- 添加列注释
COMMENT ON TABLE drilling_daily IS '钻井工程日报数据表 - 存储钻井每日作业数据';
COMMENT ON COLUMN drilling_daily.id IS '主键ID';
COMMENT ON COLUMN drilling_daily.rq IS '日期';
COMMENT ON COLUMN drilling_daily.jh IS '井号（关联oil_wells.well_name）';
COMMENT ON COLUMN drilling_daily.kzrq IS '开钻日期';
COMMENT ON COLUMN drilling_daily.drjs IS '当日井深（米）';
COMMENT ON COLUMN drilling_daily.zjrjc IS '日进尺（米）';
COMMENT ON COLUMN drilling_daily.ztlx IS '钻头类型';
COMMENT ON COLUMN drilling_daily.ztzj IS '钻头直径（毫米）';
COMMENT ON COLUMN drilling_daily.zy IS '钻压（千牛）';
COMMENT ON COLUMN drilling_daily.zs IS '钻速（米/小时）';
COMMENT ON COLUMN drilling_daily.bya IS '泵压（兆帕）';
COMMENT ON COLUMN drilling_daily.bpl IS '排量（升/秒）';
COMMENT ON COLUMN drilling_daily.zjymd IS '钻井液密度（克/立方厘米）';
COMMENT ON COLUMN drilling_daily.zjynd IS '钻井液粘度（秒）';
COMMENT ON COLUMN drilling_daily.czjljsj IS '纯钻进累计时间（小时）';
COMMENT ON COLUMN drilling_daily.brzygz IS '本日主要工作';
COMMENT ON COLUMN drilling_daily.created_at IS '创建时间';
COMMENT ON COLUMN drilling_daily.updated_at IS '更新时间';
COMMENT ON COLUMN drilling_daily.is_deleted IS '软删除标记';

-- 创建更新时间触发器
DROP TRIGGER IF EXISTS update_drilling_daily_updated_at ON drilling_daily;
CREATE TRIGGER update_drilling_daily_updated_at 
    BEFORE UPDATE ON drilling_daily 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
