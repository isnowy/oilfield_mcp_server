-- 井身结构（套管）明细表
-- 用于结构化存储“套管信息”表格数据，与井身结构图文件引用分离

CREATE TABLE IF NOT EXISTS wellbore_structure_sections (
    id SERIAL PRIMARY KEY,

    -- 基本标识
    jh VARCHAR(50) NOT NULL,               -- 井号
    casing_type VARCHAR(100),              -- 套管分类
    section_order INTEGER,                 -- 段次序号

    -- 套管参数
    od_mm NUMERIC(10, 2),                  -- 套管外径 (mm)
    steel_grade VARCHAR(50),               -- 套管钢级
    wall_thickness_mm NUMERIC(10, 2),      -- 套管壁厚 (mm)
    burst_pressure_mpa NUMERIC(10, 2),     -- 套管抗内压 (MPa)
    id_mm NUMERIC(10, 2),                  -- 套管内径 (mm)
    run_depth_m NUMERIC(10, 2),            -- 下入深度 (m)
    cement_return_depth_m NUMERIC(10, 2),  -- 水泥返深 (m)
    cement_quality VARCHAR(100),           -- 固井质量

    -- 地面设备
    wellhead_model VARCHAR(100),           -- 井口
    pumping_unit_model VARCHAR(100),       -- 抽油机
    metering_transport_system VARCHAR(200), -- 计量、输油系统

    -- 来源追溯
    source_file VARCHAR(300),              -- 来源文件名
    source_sheet VARCHAR(100),             -- 来源工作表
    source_row_no INTEGER,                 -- 来源行号
    bz TEXT,                               -- 备注

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_wss_jh ON wellbore_structure_sections(jh);
CREATE INDEX IF NOT EXISTS idx_wss_casing_type ON wellbore_structure_sections(casing_type);
CREATE INDEX IF NOT EXISTS idx_wss_run_depth_m ON wellbore_structure_sections(run_depth_m);
CREATE INDEX IF NOT EXISTS idx_wss_source_file ON wellbore_structure_sections(source_file);
CREATE INDEX IF NOT EXISTS idx_wss_is_deleted ON wellbore_structure_sections(is_deleted);

COMMENT ON TABLE wellbore_structure_sections IS '井身结构（套管）明细表 - 结构化存储井史卡片中的套管信息';
COMMENT ON COLUMN wellbore_structure_sections.jh IS '井号';
COMMENT ON COLUMN wellbore_structure_sections.casing_type IS '套管分类';
COMMENT ON COLUMN wellbore_structure_sections.section_order IS '段次序号';
COMMENT ON COLUMN wellbore_structure_sections.od_mm IS '套管外径 (mm)';
COMMENT ON COLUMN wellbore_structure_sections.steel_grade IS '套管钢级';
COMMENT ON COLUMN wellbore_structure_sections.wall_thickness_mm IS '套管壁厚 (mm)';
COMMENT ON COLUMN wellbore_structure_sections.burst_pressure_mpa IS '套管抗内压 (MPa)';
COMMENT ON COLUMN wellbore_structure_sections.id_mm IS '套管内径 (mm)';
COMMENT ON COLUMN wellbore_structure_sections.run_depth_m IS '下入深度 (m)';
COMMENT ON COLUMN wellbore_structure_sections.cement_return_depth_m IS '水泥返深 (m)';
COMMENT ON COLUMN wellbore_structure_sections.cement_quality IS '固井质量';
COMMENT ON COLUMN wellbore_structure_sections.wellhead_model IS '井口';
COMMENT ON COLUMN wellbore_structure_sections.pumping_unit_model IS '抽油机';
COMMENT ON COLUMN wellbore_structure_sections.metering_transport_system IS '计量、输油系统';
COMMENT ON COLUMN wellbore_structure_sections.source_file IS '来源文件名';
COMMENT ON COLUMN wellbore_structure_sections.source_sheet IS '来源工作表';
COMMENT ON COLUMN wellbore_structure_sections.source_row_no IS '来源行号';
COMMENT ON COLUMN wellbore_structure_sections.bz IS '备注';

DROP TRIGGER IF EXISTS update_wellbore_structure_sections_updated_at ON wellbore_structure_sections;
CREATE TRIGGER update_wellbore_structure_sections_updated_at
    BEFORE UPDATE ON wellbore_structure_sections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
