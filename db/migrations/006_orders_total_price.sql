USE `cake_store`;
SET NAMES utf8mb4;

-- 订单价格快照：金额原本在查询时用 goods.price*num 现算，管理员改价会
-- 让历史订单与报表数字漂移。本迁移：
-- 1) orders 增加 total_price DECIMAL(10,2)
-- 2) 用当前商品价 × 数量回填存量（商品已删除的订单保持 NULL，统计按 0 计）

ALTER TABLE `orders` ADD COLUMN `total_price` DECIMAL(10,2) NULL AFTER `status`;

UPDATE `orders` o
JOIN `goods` g ON o.`goods_id` = g.`id`
SET o.`total_price` = g.`price` * o.`num`
WHERE o.`total_price` IS NULL;
