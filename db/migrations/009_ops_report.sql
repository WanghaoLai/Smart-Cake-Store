SET NAMES utf8mb4;

-- 运营日报持久化：每次生成落库，历史可回看。
CREATE TABLE IF NOT EXISTS `ops_report` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `days` INT NOT NULL DEFAULT 7 COMMENT '统计天数窗口',
    `summary` TEXT NULL COMMENT 'LLM 摘要（失败时为 NULL，仅存事实）',
    `facts` JSON NULL COMMENT '原始 SQL 事实快照（用于对比摘要准确性）',
    `model` VARCHAR(64) NULL COMMENT '生成模型',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_ops_report_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运营日报';
