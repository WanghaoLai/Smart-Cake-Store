-- 购物车：用户-商品-数量 + 持久化选中状态（跨端同步勾选）。
-- 非资金审计根（区别于订单）：用户注销/商品删除时级联清理，不保留孤儿行。
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS `cart` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` INT NOT NULL COMMENT '所属用户（user 表）',
    `goods_id` INT NOT NULL COMMENT '商品（goods 表）',
    `num` INT NOT NULL DEFAULT 1 COMMENT '数量',
    `selected` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '结算勾选状态（1 勾选 / 0 未选）',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cart_user_goods` (`user_id`, `goods_id`),
    CONSTRAINT `ck_cart_num_positive` CHECK (`num` > 0),
    CONSTRAINT `fk_cart_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cart_goods` FOREIGN KEY (`goods_id`) REFERENCES `goods` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='购物车';
