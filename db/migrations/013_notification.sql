USE `cake_store`;
SET NAMES utf8mb4;

-- 订单站内通知：状态变更（发货/取消）在业务事务内同步写行——
-- 通知即业务副产物，同事务保证"状态变了必有通知"，无需独立 outbox 表。
-- 轮询读取（分钟级实时性足够：蛋糕制作配送本身以小时计）。
CREATE TABLE IF NOT EXISTS `notification` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL COMMENT '接收者主键（user 表）',
    `owner_role` VARCHAR(16) NOT NULL DEFAULT '用户' COMMENT '接收者角色（User/Admin 独立建表，主键可能重叠）',
    `type` VARCHAR(32) NOT NULL COMMENT '通知类型：order.shipped / order.cancelled',
    `title` VARCHAR(128) NOT NULL,
    `content` VARCHAR(500) NULL,
    `is_read` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX `idx_notification_owner_read` (`owner_role`, `user_id`, `is_read`, `id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单站内通知';
