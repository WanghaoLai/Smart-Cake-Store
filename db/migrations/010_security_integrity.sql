-- 认证撤销、业务唯一性、审计外键与高频查询索引。
-- 本脚本故意不自动删除孤儿订单/评价：若现有数据违反外键，
-- ALTER TABLE 会失败并迫使运维人员先审计修复，避免迁移静默丢数据。
SET NAMES utf8mb4;

ALTER TABLE `admin`
  ADD COLUMN `token_version` INT NOT NULL DEFAULT 0 AFTER `must_change_password`;

ALTER TABLE `user`
  ADD COLUMN `token_version` INT NOT NULL DEFAULT 0 AFTER `must_change_password`,
  ADD UNIQUE KEY `uk_user_username` (`username`);

-- 仅在账号仍使用仓库历史演示哈希时替换；用户已自行改密则不覆盖。
UPDATE `admin`
SET `password` = '$2b$12$rfj6TAsthdiU8ufcO1qvVOT27DlmyqtsbLwJEzSy6eMvngUmvmc0.',
    `must_change_password` = 1,
    `token_version` = `token_version` + 1
WHERE `username` = '222'
  AND `password` = '$2b$12$fQR4RZU6e3aIz57EP2TkJuAg8RKLoptlCTLkVR9lZSGZc4h7h7pTq';

UPDATE `user`
SET `password` = '$2b$12$1l.HLJWA3WdbIE..Hokbo.6oSe0mfCweiDYr5UmNhX4wf4PZWaBxq',
    `must_change_password` = 1,
    `token_version` = `token_version` + 1
WHERE `username` = '234'
  AND `password` = '$2b$12$k3GFKLnZ9jVdmCAVnBRq1u5/KUf99u0uYVgqI0ZewR9vMyxU/Pb4i';

-- 收藏重复行无独立业务语义，保留最早一条后建立并发唯一约束。
DELETE newer
FROM `favorite` AS newer
JOIN `favorite` AS older
  ON newer.`user_id` = older.`user_id`
 AND newer.`goods_id` = older.`goods_id`
 AND newer.`id` > older.`id`;

ALTER TABLE `favorite`
  ADD UNIQUE KEY `uk_favorite_user_goods` (`user_id`, `goods_id`);

ALTER TABLE `address`
  ADD COLUMN `default_user_id` INT
    GENERATED ALWAYS AS (CASE WHEN `is_default` = 1 THEN `user_id` ELSE NULL END) STORED,
  ADD UNIQUE KEY `uk_address_one_default` (`default_user_id`),
  ADD CONSTRAINT `fk_address_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_address_province` FOREIGN KEY (`province_id`) REFERENCES `tb_province` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_address_city` FOREIGN KEY (`city_id`) REFERENCES `tb_city` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_address_town` FOREIGN KEY (`town_id`) REFERENCES `tb_town` (`id`) ON DELETE RESTRICT;

ALTER TABLE `goods`
  ADD KEY `idx_goods_category` (`category_id`),
  ADD CONSTRAINT `ck_goods_price_nonnegative` CHECK (`price` IS NULL OR `price` >= 0),
  ADD CONSTRAINT `ck_goods_stock_nonnegative` CHECK (`num` IS NULL OR `num` >= 0),
  ADD CONSTRAINT `fk_goods_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`) ON DELETE SET NULL;

ALTER TABLE `orders`
  ADD KEY `idx_orders_user_id_id` (`user_id`, `id`),
  ADD KEY `idx_orders_goods_time` (`goods_id`, `time`),
  ADD KEY `idx_orders_status_time` (`status`, `time`),
  ADD KEY `idx_orders_address` (`address_id`),
  ADD CONSTRAINT `ck_orders_num_positive` CHECK (`num` IS NULL OR `num` > 0),
  ADD CONSTRAINT `ck_orders_total_nonnegative` CHECK (`total_price` IS NULL OR `total_price` >= 0),
  ADD CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_orders_goods` FOREIGN KEY (`goods_id`) REFERENCES `goods` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_orders_address` FOREIGN KEY (`address_id`) REFERENCES `address` (`id`) ON DELETE RESTRICT;

ALTER TABLE `review`
  ADD CONSTRAINT `ck_review_rating` CHECK (`rating` IS NULL OR (`rating` >= 1 AND `rating` <= 5)),
  ADD CONSTRAINT `fk_review_goods` FOREIGN KEY (`goods_id`) REFERENCES `goods` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_review_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_review_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE RESTRICT;
