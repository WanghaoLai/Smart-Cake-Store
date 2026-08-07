-- Address 表结构化地址迁移脚本
-- 适用：已有 cake_store 数据库，需要为 address 表新增 省/市/区县 字段
--
-- 新增字段：
--   province_id     省 ID（关联 tb_province.id）
--   province_name   省名（冗余存储避免 join）
--   city_id         市 ID
--   city_name       市名
--   town_id         区县 ID
--   town_name       区县名
--   detail          详细地址（街道、门牌号）
-- 原 address 字段保留向后兼容；新增/更新时由 省+市+区+detail 自动拼接

USE `cake_store`;

ALTER TABLE `address`
  ADD COLUMN `province_id` int DEFAULT NULL COMMENT '省 ID' AFTER `phone`,
  ADD COLUMN `province_name` varchar(32) DEFAULT NULL COMMENT '省名称' AFTER `province_id`,
  ADD COLUMN `city_id` int DEFAULT NULL COMMENT '市 ID' AFTER `province_name`,
  ADD COLUMN `city_name` varchar(64) DEFAULT NULL COMMENT '市名称' AFTER `city_id`,
  ADD COLUMN `town_id` int DEFAULT NULL COMMENT '区县 ID' AFTER `city_name`,
  ADD COLUMN `town_name` varchar(64) DEFAULT NULL COMMENT '区县名称' AFTER `town_id`,
  ADD COLUMN `detail` varchar(255) DEFAULT NULL COMMENT '详细地址（街道、门牌号）' AFTER `town_name`,
  ADD COLUMN `is_default` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否默认地址（每用户最多 1 条）' AFTER `detail`,
  ADD KEY `idx_address_user` (`user_id`),
  ADD KEY `idx_address_region` (`province_id`, `city_id`, `town_id`),
  ADD KEY `idx_address_user_default` (`user_id`, `is_default`);
