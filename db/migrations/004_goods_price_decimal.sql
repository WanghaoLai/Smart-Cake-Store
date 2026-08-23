SET NAMES utf8mb4;

-- 金额精度修复：浮点无法精确表示十进制小数，销售额/订单总价等聚合会累积误差。
-- 与开发方案 6.3 节"金额字段统一使用 DECIMAL(10,2)"对齐。
-- 存量 float 值（如 98.00）转 DECIMAL 无损，MySQL 自动四舍五入到 2 位小数。
ALTER TABLE `goods` MODIFY `price` DECIMAL(10,2) NULL;
