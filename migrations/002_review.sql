-- 商品评价系统迁移脚本
-- 适用：已有 cake_store 数据库，需要新增 review 表 + 把 orders 历史"已签收"合并为"待评价"
-- 用法：在 cake_store 库下执行本脚本
--
-- 设计原理：
--   1. 评价独立成表：以 goods_id 为公开查询维度，避免 join orders + user 才能展示商品评价
--   2. order_id 唯一约束：1 订单 1 评价，DB 层防重复
--   3. "已签收"合并为"待评价"：签收的本质就是"等用户评价"，去除冗余状态
--   4. images 存 JSON 字符串：避免引入图片子表，前端直接 JSON.parse

USE `cake_store`;

-- 显式声明客户端字符集：否则 mysql CLI 默认会把脚本里的中文常量
-- 按字节错误重编码后写入（HEX 会变成 C3A5C2BE… 双重编码），前端读到就是乱码。
SET NAMES utf8mb4;

-- ----------------------------
-- 1. 评价表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `review` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `goods_id` int DEFAULT NULL COMMENT '商品ID',
  `user_id` int DEFAULT NULL COMMENT '评价用户ID',
  `order_id` int DEFAULT NULL COMMENT '订单ID（唯一，1单1评）',
  `rating` int DEFAULT NULL COMMENT '星级 1-5',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '评价正文',
  `images` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '评价图片 URL JSON 数组',
  `reply` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '管理员回复',
  `reply_time` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '回复时间',
  `time` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '评价时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order` (`order_id`),
  KEY `idx_goods` (`goods_id`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品评价';

-- ----------------------------
-- 2. 历史"已签收"订单合并为"待评价"
--    签收语义上就是"等用户评价"，新流程不再使用"已签收"状态
-- ----------------------------
UPDATE `orders` SET `status` = '待评价' WHERE `status` = '已签收';
