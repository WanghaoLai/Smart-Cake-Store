-- 购买幂等、规格与地址快照；每一步可安全重跑。
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
CALL `_cake_exec_ddl`(NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='orders' AND column_name='shipping_snapshot'), 'ALTER TABLE `orders` ADD COLUMN `shipping_snapshot` JSON NULL');
CALL `_cake_exec_ddl`(NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='orders' AND column_name='spec'), 'ALTER TABLE `orders` ADD COLUMN `spec` VARCHAR(255) NOT NULL DEFAULT ''''');
UPDATE orders o LEFT JOIN address a ON a.id=o.address_id SET o.shipping_snapshot=JSON_OBJECT('name',a.name,'phone',a.phone,'address',a.address) WHERE o.shipping_snapshot IS NULL;
CALL `_cake_exec_ddl`(NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='cart' AND column_name='spec'), 'ALTER TABLE `cart` ADD COLUMN `spec` VARCHAR(255) NOT NULL DEFAULT ''''');
CALL `_cake_exec_ddl`(NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='cart' AND index_name='uk_cart_user_goods_spec'), 'ALTER TABLE `cart` ADD UNIQUE KEY `uk_cart_user_goods_spec` (`user_id`,`goods_id`,`spec`)');
CALL `_cake_exec_ddl`(EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='cart' AND index_name='uk_cart_user_goods'), 'ALTER TABLE `cart` DROP INDEX `uk_cart_user_goods`');
CREATE TABLE IF NOT EXISTS `purchase_request` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY, `user_id` INT NOT NULL,
  `request_id` VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `fingerprint` VARCHAR(64) NOT NULL, `response` JSON NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY `uk_purchase_user_request` (`user_id`,`request_id`),
  CONSTRAINT `fk_purchase_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
DROP PROCEDURE `_cake_exec_ddl`;
