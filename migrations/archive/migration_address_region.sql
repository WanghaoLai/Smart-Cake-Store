-- [已废弃] Address 表结构化地址迁移脚本
-- 废弃原因：cake_store.sql 最新 dump 已包含这些字段，新部署无需再执行
-- 保留在 archive/ 仅作历史参考。migrate.sh 不会扫描 archive/ 子目录。
--
-- 历史新增字段：
--   province_id     省 ID（关联 tb_province.id）
--   province_name   省名（冗余存储避免 join）
--   city_id         市 ID
--   city_name       市名
--   town_id         区县 ID
--   town_name       区县名
--   detail          详细地址（街道、门牌号）
-- 原 address 字段保留向后兼容；新增/更新时由 省+市+区+detail 自动拼接

USE `cake_store`;

-- 显式声明客户端字符集：避免 mysql CLI 默认 latin1 导致中文常量双重编码
SET NAMES utf8mb4;

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
