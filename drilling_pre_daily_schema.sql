-- 钻前工程日报数据表设计
-- 基于drilling_pre_daily.xlsx数据结构设计

CREATE TABLE IF NOT EXISTS drilling_pre_daily (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 基本信息
    ktxm VARCHAR(100),                     -- 勘探项目
    ssnd INTEGER,                          -- 实施年度
    jh VARCHAR(50),                        -- 井号（关联oil_wells.well_name）
    
    -- 各阶段时间节点
    jwzysj DATE,                           -- 井位论证时间
    jwtjxdsj DATE,                         -- 井位条件下达时间
    jwtclsj DATE,                          -- 井位测量时间
    tzxdsj DATE,                           -- 投资下达时间
    kjcgcwsj DATE,                         -- 勘界成果完成时间
    hpsbsj DATE,                           -- 环评上报时间
    ydsqsbsj DATE,                         -- 用地申请上报时间
    gcfatlsj DATE,                         -- 工程方案讨论时间
    zjdzsjspsj DATE,                       -- 钻井地质设计审批时间
    zjgcsjspsj DATE,                       -- 钻井工程设计审批时间
    hpxdsj DATE,                           -- 环评下达时间
    zdcwsj DATE,                           -- 征地完成时间
    tlsksj DATE,                           -- 探临开始时间
    tljssj DATE,                           -- 探临结束时间
    bjkssj DATE,                           -- 搬家安装开始时间
    bjjssj DATE,                           -- 搬家安装结束时间
    
    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_dpd_jh ON drilling_pre_daily(jh);
CREATE INDEX IF NOT EXISTS idx_dpd_ktxm ON drilling_pre_daily(ktxm);
CREATE INDEX IF NOT EXISTS idx_dpd_ssnd ON drilling_pre_daily(ssnd);
CREATE INDEX IF NOT EXISTS idx_dpd_created_at ON drilling_pre_daily(created_at);
CREATE INDEX IF NOT EXISTS idx_dpd_is_deleted ON drilling_pre_daily(is_deleted);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_dpd_ktxm_ssnd ON drilling_pre_daily(ktxm, ssnd);
CREATE INDEX IF NOT EXISTS idx_dpd_jh_ssnd ON drilling_pre_daily(jh, ssnd);

-- 添加注释
COMMENT ON TABLE drilling_pre_daily IS '钻前工程日报数据表';
COMMENT ON COLUMN drilling_pre_daily.ktxm IS '勘探项目';
COMMENT ON COLUMN drilling_pre_daily.ssnd IS '实施年度';
COMMENT ON COLUMN drilling_pre_daily.jh IS '井号（关联oil_wells.well_name）';
COMMENT ON COLUMN drilling_pre_daily.jwzysj IS '井位论证时间';
COMMENT ON COLUMN drilling_pre_daily.jwtjxdsj IS '井位条件下达时间';
COMMENT ON COLUMN drilling_pre_daily.jwtclsj IS '井位测量时间';
COMMENT ON COLUMN drilling_pre_daily.tzxdsj IS '投资下达时间';
COMMENT ON COLUMN drilling_pre_daily.kjcgcwsj IS '勘界成果完成时间';
COMMENT ON COLUMN drilling_pre_daily.hpsbsj IS '环评上报时间';
COMMENT ON COLUMN drilling_pre_daily.ydsqsbsj IS '用地申请上报时间';
COMMENT ON COLUMN drilling_pre_daily.gcfatlsj IS '工程方案讨论时间';
COMMENT ON COLUMN drilling_pre_daily.zjdzsjspsj IS '钻井地质设计审批时间';
COMMENT ON COLUMN drilling_pre_daily.zjgcsjspsj IS '钻井工程设计审批时间';
COMMENT ON COLUMN drilling_pre_daily.hpxdsj IS '环评下达时间';
COMMENT ON COLUMN drilling_pre_daily.zdcwsj IS '征地完成时间';
COMMENT ON COLUMN drilling_pre_daily.tlsksj IS '探临开始时间';
COMMENT ON COLUMN drilling_pre_daily.tljssj IS '探临结束时间';
COMMENT ON COLUMN drilling_pre_daily.bjkssj IS '搬家安装开始时间';
COMMENT ON COLUMN drilling_pre_daily.bjjssj IS '搬家安装结束时间';
