-- 订单状态字段迁移脚本
-- 适用：已有 cake_store 数据库，需要为 orders 表新增 status 字段
-- 用法：在 cake_store 库下执行本脚本
--
-- 新增字段：
--   status  订单状态（待发货/已发货/已签收/已评价/已取消），默认"待发货"
--
-- 设计原理：订单生命周期从用户和商家双边视角拆解
--   用户下单 -> 待发货 -> 已发货 -> 已签收 -> 已评价
--   待发货/已发货 态可由用户或管理员取消，库存恢复

-- 显式声明客户端字符集：否则 mysql CLI 默认 latin1，会把脚本里的中文常量
-- 按字节错误重编码后写入（HEX 会变成 C3A5C2BE… 双重编码），前端读到就是乱码。
SET NAMES utf8mb4;

ALTER TABLE `orders`
  ADD COLUMN `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '待发货' COMMENT '订单状态：待发货/已发货/已签收/已评价/已取消' AFTER `time`;

-- 旧订单统一视为"待发货"，避免历史数据状态为 NULL
UPDATE `orders` SET `status` = '待发货' WHERE `status` IS NULL;
