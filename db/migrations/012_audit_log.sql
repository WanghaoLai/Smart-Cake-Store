USE `cake_store`;
SET NAMES utf8mb4;

-- 操作审计：敏感操作（密码重置、账号增删、订单状态强制变更、知识库删除）
-- 落库可追溯："谁在何时从哪个 IP 改了什么"。
-- 审计为 best-effort 写入（业务成功后落记录，失败仅记日志不阻塞业务），
-- 因此与业务表无外键关联——审计行允许引用已删除的目标。
CREATE TABLE IF NOT EXISTS `audit_log` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `operator_role` VARCHAR(16) NOT NULL COMMENT '操作者角色：用户/管理员/系统',
    `operator_id` INT NOT NULL COMMENT '操作者主键（对应 user/admin 表）',
    `operator_name` VARCHAR(255) NULL COMMENT '操作者用户名（冗余，防账号删除后不可读）',
    `action` VARCHAR(64) NOT NULL COMMENT '动作标识，如 user.reset_password',
    `target_type` VARCHAR(32) NULL COMMENT '目标实体类型：user/admin/order/knowledge',
    `target_id` INT NULL COMMENT '目标主键',
    `detail` JSON NULL COMMENT '变更明细（旧值→新值摘要等）',
    `ip` VARCHAR(64) NULL COMMENT '来源 IP',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX `idx_audit_created` (`created_at`),
    INDEX `idx_audit_operator` (`operator_role`, `operator_id`, `created_at`),
    INDEX `idx_audit_target` (`target_type`, `target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='敏感操作审计日志';
