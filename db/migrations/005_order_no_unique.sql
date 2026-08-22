USE `cake_store`;
SET NAMES utf8mb4;

-- 订单号防碰撞：秒级时间戳 + 4 位随机的旧方案同秒有 1/9000 碰撞概率，
-- 且无唯一约束兜底。本迁移：1) 存量去重（保留每组最小 id，其余追加 -id 后缀）
-- 2) 加唯一索引，把唯一性交给数据库保证。

UPDATE `orders` o
JOIN (
    SELECT `order_no` FROM `orders`
    WHERE `order_no` IS NOT NULL
    GROUP BY `order_no` HAVING COUNT(*) > 1
) d ON o.`order_no` = d.`order_no`
SET o.`order_no` = CONCAT(o.`order_no`, '-', o.`id`)
WHERE o.`id` NOT IN (
    SELECT keep_id FROM (
        SELECT MIN(`id`) AS keep_id FROM `orders`
        WHERE `order_no` IS NOT NULL
        GROUP BY `order_no`
    ) t
);

ALTER TABLE `orders` ADD UNIQUE INDEX `uk_orders_order_no` (`order_no`);
