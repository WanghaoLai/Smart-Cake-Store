-- 代码审查“建议项”：商品写约束、outbox 领取租约、UTC 时间语义。
SET NAMES utf8mb4;

-- 核心商品事实不允许为空；若存量库存在脏数据，ALTER 明确失败并要求人工修复。
ALTER TABLE `goods`
  MODIFY COLUMN `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '名称',
  MODIFY COLUMN `price` decimal(10,2) NOT NULL,
  MODIFY COLUMN `num` int NOT NULL COMMENT '库存',
  DROP CHECK `ck_goods_price_nonnegative`,
  DROP CHECK `ck_goods_stock_nonnegative`,
  ADD CONSTRAINT `ck_goods_price_nonnegative` CHECK (`price` >= 0),
  ADD CONSTRAINT `ck_goods_stock_nonnegative` CHECK (`num` >= 0);

-- 原子领取需要租约令牌，避免后台回调和管理员重试同时处理同一任务。
ALTER TABLE `index_task`
  ADD COLUMN `claim_token` varchar(36) DEFAULT NULL AFTER `last_error`,
  ADD COLUMN `processing_started_at` datetime(6) DEFAULT NULL AFTER `claim_token`,
  ADD KEY `idx_index_task_claim` (`status`, `processing_started_at`, `id`);

-- DDL 非事务化；步骤标记确保迁移中断后重跑不会再次减 8 小时。
CREATE TABLE IF NOT EXISTS `_migration_011_state` (
  `step` varchar(64) NOT NULL,
  `completed_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`step`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE `orders` MODIFY COLUMN `time` datetime(6) NULL COMMENT 'UTC 下单时间';
UPDATE `orders`
SET `time` = DATE_SUB(`time`, INTERVAL 8 HOUR)
WHERE `time` IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM `_migration_011_state` WHERE `step` = 'orders_time_utc');
INSERT IGNORE INTO `_migration_011_state` (`step`) VALUES ('orders_time_utc');
ALTER TABLE `orders` MODIFY COLUMN `time` datetime(6) NOT NULL COMMENT 'UTC 下单时间';

ALTER TABLE `review`
  MODIFY COLUMN `time` datetime(6) NULL COMMENT 'UTC 评价时间',
  MODIFY COLUMN `reply_time` datetime(6) NULL COMMENT 'UTC 回复时间';
UPDATE `review`
SET `time` = DATE_SUB(`time`, INTERVAL 8 HOUR),
    `reply_time` = CASE WHEN `reply_time` IS NULL THEN NULL ELSE DATE_SUB(`reply_time`, INTERVAL 8 HOUR) END
WHERE NOT EXISTS (SELECT 1 FROM `_migration_011_state` WHERE `step` = 'review_time_utc');
INSERT IGNORE INTO `_migration_011_state` (`step`) VALUES ('review_time_utc');
ALTER TABLE `review` MODIFY COLUMN `time` datetime(6) NOT NULL COMMENT 'UTC 评价时间';

ALTER TABLE `notice` MODIFY COLUMN `time` datetime(6) NULL COMMENT 'UTC 时间';
UPDATE `notice`
SET `time` = DATE_SUB(`time`, INTERVAL 8 HOUR)
WHERE `time` IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM `_migration_011_state` WHERE `step` = 'notice_time_utc');
INSERT IGNORE INTO `_migration_011_state` (`step`) VALUES ('notice_time_utc');
ALTER TABLE `notice` MODIFY COLUMN `time` datetime(6) NOT NULL COMMENT 'UTC 时间';
