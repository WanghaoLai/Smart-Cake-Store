-- 用户钱包：余额 + 不可变资金流水。
SET NAMES utf8mb4;

ALTER TABLE `user`
  ADD COLUMN `balance` DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER `token_version`,
  ADD CONSTRAINT `ck_user_balance_nonnegative` CHECK (`balance` >= 0);

CREATE TABLE `wallet_transaction` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `type` VARCHAR(16) NOT NULL COMMENT 'recharge/payment/refund',
  `amount` DECIMAL(12,2) NOT NULL COMMENT '正数入账，负数出账',
  `balance_after` DECIMAL(12,2) NOT NULL,
  `payment_method` VARCHAR(32) DEFAULT NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'success',
  `order_id` INT DEFAULT NULL,
  `request_id` VARCHAR(64) NOT NULL,
  `remark` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wallet_request_id` (`request_id`),
  KEY `idx_wallet_user_created` (`user_id`, `created_at`),
  KEY `idx_wallet_order_type` (`order_id`, `type`),
  CONSTRAINT `ck_wallet_amount_nonzero` CHECK (`amount` <> 0),
  CONSTRAINT `ck_wallet_balance_nonnegative` CHECK (`balance_after` >= 0),
  CONSTRAINT `fk_wallet_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_wallet_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='钱包资金流水';
