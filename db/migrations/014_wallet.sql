-- 用户钱包：每个 DDL 步骤按 information_schema 判定，可从中断点安全重跑。
SET NAMES utf8mb4;
DROP PROCEDURE IF EXISTS `_cake_exec_ddl`;
DELIMITER //
CREATE PROCEDURE `_cake_exec_ddl`(IN needed BOOLEAN, IN statement_text TEXT)
BEGIN
  IF needed THEN
    SET @cake_ddl = statement_text;
    PREPARE cake_stmt FROM @cake_ddl;
    EXECUTE cake_stmt;
    DEALLOCATE PREPARE cake_stmt;
  END IF;
END//
DELIMITER ;
CALL `_cake_exec_ddl`(NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user' AND column_name='balance'), 'ALTER TABLE `user` ADD COLUMN `balance` DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER `token_version`');
CALL `_cake_exec_ddl`(NOT EXISTS(SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='user' AND constraint_name='ck_user_balance_nonnegative'), 'ALTER TABLE `user` ADD CONSTRAINT `ck_user_balance_nonnegative` CHECK (`balance` >= 0)');
CREATE TABLE IF NOT EXISTS `wallet_transaction` (
  `id` INT NOT NULL AUTO_INCREMENT, `user_id` INT NOT NULL, `type` VARCHAR(16) NOT NULL,
  `amount` DECIMAL(12,2) NOT NULL, `balance_after` DECIMAL(12,2) NOT NULL,
  `payment_method` VARCHAR(32) DEFAULT NULL, `status` VARCHAR(16) NOT NULL DEFAULT 'success',
  `order_id` INT DEFAULT NULL, `request_id` VARCHAR(64) NOT NULL, `remark` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wallet_request_id` (`request_id`), KEY `idx_wallet_user_created` (`user_id`, `created_at`),
  KEY `idx_wallet_order_type` (`order_id`, `type`), CONSTRAINT `ck_wallet_amount_nonzero` CHECK (`amount` <> 0),
  CONSTRAINT `ck_wallet_balance_nonnegative` CHECK (`balance_after` >= 0),
  CONSTRAINT `fk_wallet_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_wallet_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
DROP PROCEDURE `_cake_exec_ddl`;
