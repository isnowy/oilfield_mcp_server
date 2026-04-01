-- 井身结构图文件引用表
-- 不存储图片二进制，仅存储 LibreChat 文件系统的引用

CREATE TABLE IF NOT EXISTS wellbore_diagrams (
    id SERIAL PRIMARY KEY,

    -- 关联信息
    jh VARCHAR(50) NOT NULL,           -- 井号
    file_id VARCHAR(200) NOT NULL,     -- LibreChat 文件 ID

    -- 文件元数据
    file_name VARCHAR(300),            -- 原始文件名
    file_url TEXT,                     -- 可访问 URL
    diagram_type VARCHAR(50),          -- 图件类型（井身结构图/套管程序图/完井图等）
    image_ref_id VARCHAR(120),         -- 图像引用ID（如 Excel DISPIMG ID）
    source_file VARCHAR(300),          -- 来源文件名
    source_sheet VARCHAR(100),         -- 来源工作表
    source_cell VARCHAR(30),           -- 来源单元格位置
    image_seq INTEGER,                 -- 图像序号
    scsj DATE,                         -- 上传/编制日期
    ms TEXT,                           -- 描述/备注

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_wd_jh ON wellbore_diagrams(jh);
CREATE INDEX IF NOT EXISTS idx_wd_file_id ON wellbore_diagrams(file_id);
CREATE INDEX IF NOT EXISTS idx_wd_diagram_type ON wellbore_diagrams(diagram_type);
CREATE INDEX IF NOT EXISTS idx_wd_image_ref_id ON wellbore_diagrams(image_ref_id);
CREATE INDEX IF NOT EXISTS idx_wd_is_deleted ON wellbore_diagrams(is_deleted);

-- 兼容已存在表：补充新增字段
ALTER TABLE wellbore_diagrams ADD COLUMN IF NOT EXISTS image_ref_id VARCHAR(120);
ALTER TABLE wellbore_diagrams ADD COLUMN IF NOT EXISTS source_file VARCHAR(300);
ALTER TABLE wellbore_diagrams ADD COLUMN IF NOT EXISTS source_sheet VARCHAR(100);
ALTER TABLE wellbore_diagrams ADD COLUMN IF NOT EXISTS source_cell VARCHAR(30);
ALTER TABLE wellbore_diagrams ADD COLUMN IF NOT EXISTS image_seq INTEGER;

COMMENT ON TABLE wellbore_diagrams IS '井身结构图文件引用表 - 存储 LibreChat 文件 ID 及元数据，供其他系统页面按井号查询调用';
COMMENT ON COLUMN wellbore_diagrams.jh IS '井号';
COMMENT ON COLUMN wellbore_diagrams.file_id IS 'LibreChat 文件 ID';
COMMENT ON COLUMN wellbore_diagrams.file_name IS '原始文件名';
COMMENT ON COLUMN wellbore_diagrams.file_url IS '可访问 URL';
COMMENT ON COLUMN wellbore_diagrams.diagram_type IS '图件类型（井身结构图/套管程序图/完井图等）';
COMMENT ON COLUMN wellbore_diagrams.image_ref_id IS '图像引用ID（如 Excel DISPIMG ID）';
COMMENT ON COLUMN wellbore_diagrams.source_file IS '来源文件名';
COMMENT ON COLUMN wellbore_diagrams.source_sheet IS '来源工作表';
COMMENT ON COLUMN wellbore_diagrams.source_cell IS '来源单元格位置';
COMMENT ON COLUMN wellbore_diagrams.image_seq IS '图像序号';
COMMENT ON COLUMN wellbore_diagrams.scsj IS '上传/编制日期';
COMMENT ON COLUMN wellbore_diagrams.ms IS '描述/备注';

DROP TRIGGER IF EXISTS update_wellbore_diagrams_updated_at ON wellbore_diagrams;
CREATE TRIGGER update_wellbore_diagrams_updated_at
    BEFORE UPDATE ON wellbore_diagrams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
