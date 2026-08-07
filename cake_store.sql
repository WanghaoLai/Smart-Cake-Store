/*
 Navicat Premium Dump SQL

 Source Server         : mysql
 Source Server Type    : MySQL
 Source Server Version : 90500 (9.5.0)
 Source Host           : localhost:3306
 Source Schema         : cake_store

 Target Server Type    : MySQL
 Target Server Version : 90500 (9.5.0)
 File Encoding         : 65001

 Date: 05/08/2026 22:16:12
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for address
-- ----------------------------
DROP TABLE IF EXISTS `address`;
CREATE TABLE `address` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` int DEFAULT NULL COMMENT '用户ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '收货人',
  `address` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '收货地址',
  `phone` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系方式',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='地址信息';

-- ----------------------------
-- Records of address
-- ----------------------------
BEGIN;
INSERT INTO `address` (`id`, `user_id`, `name`, `address`, `phone`) VALUES (1, 1, '111', '123', '222');
INSERT INTO `address` (`id`, `user_id`, `name`, `address`, `phone`) VALUES (3, 1, '333', '333', '333');
INSERT INTO `address` (`id`, `user_id`, `name`, `address`, `phone`) VALUES (4, 4, '234', '234', '234');
COMMIT;

-- ----------------------------
-- Table structure for admin
-- ----------------------------
DROP TABLE IF EXISTS `admin`;
CREATE TABLE `admin` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '账号',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '密码',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '名称',
  `avatar` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '头像',
  `role` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '角色',
  `must_change_password` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `username` (`username`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='管理员信息';

-- ----------------------------
-- Records of admin
-- ----------------------------
BEGIN;
INSERT INTO `admin` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (1, 'admin', '$2b$12$jA20AZWr9SZrM.Axy/d3Yu4Z6SPzHYJmHgcDtg7OSQa6RSIpbnooK', '管理员', 'http://localhost:9090/files/download/1.png', '管理员', 0);
INSERT INTO `admin` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (2, '222', '222', '222', 'http://127.0.0.1:9090/files/download/head.jpg', '管理员', 0);
INSERT INTO `admin` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (3, '111', '$2b$12$j62UQt7k0BvjYrBdVBkW9ugLlSkUic7qOCwSNBXLLaGuLnTdSG/tK', '111', 'http://127.0.0.1:9090/files/download/head.jpg', '管理员', 0);
INSERT INTO `admin` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (6, '123', '$2b$12$x3POKsQx5avfaAZUSc/4T.sXfWdLqfp9ScJ8OWbstLnnYyj2RGUMG', '123', 'http://127.0.0.1:9090/files/download/avatar/5499862a4c704004bd8c89d993f325b0.png', '管理员', 0);
COMMIT;

-- ----------------------------
-- Table structure for category
-- ----------------------------
DROP TABLE IF EXISTS `category`;
CREATE TABLE `category` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '分类名称',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类信息';

-- ----------------------------
-- Records of category
-- ----------------------------
BEGIN;
INSERT INTO `category` (`id`, `name`) VALUES (1, '情侣空间');
INSERT INTO `category` (`id`, `name`) VALUES (2, '卡通乐趣');
INSERT INTO `category` (`id`, `name`) VALUES (3, '朋友同事');
INSERT INTO `category` (`id`, `name`) VALUES (4, '女神专属');
INSERT INTO `category` (`id`, `name`) VALUES (5, '男生定制');
INSERT INTO `category` (`id`, `name`) VALUES (6, '父母长辈');
INSERT INTO `category` (`id`, `name`) VALUES (7, '二层三层');
COMMIT;

-- ----------------------------
-- Table structure for conversation
-- ----------------------------
DROP TABLE IF EXISTS `conversation`;
CREATE TABLE `conversation` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL DEFAULT '新对话',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_conversa_user_84883661` (`user_id`),
  CONSTRAINT `fk_conversa_user_84883661` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Records of conversation
-- ----------------------------
BEGIN;
INSERT INTO `conversation` (`id`, `title`, `created_at`, `updated_at`, `user_id`) VALUES (4, '你好', '2026-06-04 13:05:50.697688', '2026-06-04 13:07:17.785803', 5);
INSERT INTO `conversation` (`id`, `title`, `created_at`, `updated_at`, `user_id`) VALUES (5, 'Hello', '2026-06-04 13:30:12.321516', '2026-06-04 21:30:13.191019', 1);
INSERT INTO `conversation` (`id`, `title`, `created_at`, `updated_at`, `user_id`) VALUES (8, '我的订单', '2026-07-04 02:55:46.580183', '2026-07-04 10:55:53.797417', 1);
INSERT INTO `conversation` (`id`, `title`, `created_at`, `updated_at`, `user_id`) VALUES (9, '配送范围是什么', '2026-07-07 02:20:27.718161', '2026-07-07 02:20:48.482741', 3);
COMMIT;

-- ----------------------------
-- Table structure for favorite
-- ----------------------------
DROP TABLE IF EXISTS `favorite`;
CREATE TABLE `favorite` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `goods_id` int DEFAULT NULL,
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `goods_id` (`goods_id`),
  CONSTRAINT `favorite_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `favorite_ibfk_2` FOREIGN KEY (`goods_id`) REFERENCES `goods` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Records of favorite
-- ----------------------------
BEGIN;
INSERT INTO `favorite` (`id`, `user_id`, `goods_id`, `created_at`) VALUES (5, 1, 3, '2026-07-06 12:34:50.663455');
INSERT INTO `favorite` (`id`, `user_id`, `goods_id`, `created_at`) VALUES (6, 1, 4, '2026-07-06 12:34:52.048245');
INSERT INTO `favorite` (`id`, `user_id`, `goods_id`, `created_at`) VALUES (7, 1, 1, '2026-08-05 09:11:50.745227');
COMMIT;

-- ----------------------------
-- Table structure for goods
-- ----------------------------
DROP TABLE IF EXISTS `goods`;
CREATE TABLE `goods` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '名称',
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '描述',
  `detail` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '详情页详细介绍',
  `ingredients` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '配料表',
  `specs` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '规格（如 6寸/8寸/10寸）',
  `shelf_life` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '保质期',
  `weight` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '净含量',
  `origin` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '产地',
  `serves` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '适用人数',
  `img` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '图片',
  `price` double(10,2) DEFAULT NULL COMMENT '价格',
  `num` int DEFAULT NULL COMMENT '库存',
  `unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '单位',
  `category_id` int DEFAULT NULL COMMENT '分类ID',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='蛋糕信息';

-- ----------------------------
-- Records of goods
-- ----------------------------
BEGIN;
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (1, '浪漫爱心情侣蛋糕', '软糯蛋糕搭配清甜奶油，爱心造型满是爱意，适配情侣甜蜜纪念日。', '【浪漫爱心情侣蛋糕】为甜蜜纪念日倾心打造。\n\n造型：经典爱心双层裱花，可选巧克力甘纳许淋面或新鲜草莓围边，顶部以食用金箔与玫瑰糖霜点缀，仪式感十足。\n\n口感：戚风胚体松软湿润，夹层采用法国进口奶油与新鲜草莓粒调和，奶香醇厚不甜腻。\n\n工艺：24小时内现做现发，全程冷链配送，确保每一口都新鲜。\n\n场景：情人节、求婚、纪念日、生日惊喜。', '小麦粉、白砂糖、鸡蛋、稀奶油（含乳制品）、草莓、巧克力（可可液块、白砂糖、可可脂）、食用变性淀粉、明胶、食用香料。', '6寸（约1磅）/ 8寸（约2磅）/ 10寸（约3磅）', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 450g / 8寸 约 750g / 10寸 约 1100g', '上海·中央厨房手工制作', '6寸 2-4 人份 / 8寸 4-8 人份', 'http://127.0.0.1:9090/files/download/1-1.jpeg', 88.00, 9, '份', 1);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (3, '轻奢双人告白蛋糕', '精致简约情侣风裱花，口感细腻香甜，氛围感拉满适合约会庆祝。', '【轻奢双人告白蛋糕】简约而不简单的约会之选。\n\n造型：极简风裸蛋糕设计，奶油抹面保留手作纹理，搭配时令鲜果与迷迭香点缀，自然温柔不张扬。\n\n口感：胚体采用日式棉花蛋糕工艺，绵密如云朵；夹层为低糖马斯卡彭奶酪，奶香浓郁但减糖 30%。\n\n工艺：低糖配方，糖度可调（默认 5 分糖），适合注重健康的情侣。\n\n场景：约会、告白、纪念日、烛光晚餐。', '小麦粉、鸡蛋、白砂糖、马斯卡彭奶酪、稀奶油、混合莓果（蓝莓、树莓）、吉利丁、香草精。', '6寸（约1磅）/ 8寸（约2磅）', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 450g / 8寸 约 750g', '上海·中央厨房手工制作', '6寸 2-4 人份 / 8寸 4-8 人份', 'http://127.0.0.1:9090/files/download/1-2.jpeg', 88.00, 6, '份', 1);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (4, '甜蜜相守情侣蛋糕', '鲜果点缀层次丰富，颜值温柔治愈，定格情侣之间温馨美好时光。', '【甜蜜相守情侣蛋糕】记录每一个温馨时刻。\n\n造型：双层结构，下层数奶油抹面配以新鲜水果围边，上层数巧克力羽毛装饰，整体温柔治愈。\n\n口感：胚体湿润扎实，搭配 3 层不同口味的夹心（草莓、芒果、巧克力），层次丰富。\n\n工艺：采用日本进口北海道牛奶制作奶油，顺滑细腻。\n\n场景：纪念日、生日、家庭聚会。', '小麦粉、鸡蛋、白砂糖、北海道稀奶油、新鲜草莓、芒果、黑巧克力、可可粉、吉利丁。', '6寸 / 8寸 / 双层 8+6寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g', '上海·中央厨房手工制作', '6寸 2-4 人份 / 8寸 4-8 人份', 'http://127.0.0.1:9090/files/download/1-3.jpeg', 88.00, 10, '份', 1);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (5, '爱意满满情侣蛋糕', '丝滑夹心醇厚入味，浪漫配色超暖心，见证情侣岁岁年年深情。', '【爱意满满情侣蛋糕】一抹粉橘，温暖整个时光。\n\n造型：法式粉橘调抹面，搭配新鲜树莓、玫瑰花瓣糖霜与心形巧克力牌，温柔浪漫。\n\n口感：胚体为日式戚风，夹层采用法式杏仁奶油与树莓果酱，酸甜平衡，丝滑不腻。\n\n工艺：使用比利时巧克力与法国黄油，工艺严谨考究。\n\n场景：情人节、纪念日、求婚。', '小麦粉、鸡蛋、白砂糖、法国黄油、比利时巧克力、杏仁、树莓、玫瑰水、香草荚。', '6寸 / 8寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 480g / 8寸 约 800g', '上海·中央厨房手工制作', '6寸 2-4 人份 / 8寸 4-8 人份', 'http://127.0.0.1:9090/files/download/1-4.jpeg', 89.00, 6, '份', 1);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (6, '专属热恋情侣蛋糕', '创意情侣元素设计，清甜不腻口感，为爱营造满满浪漫仪式感。', '【专属热恋情侣蛋糕】为爱定制，独一无二。\n\n造型：可定制情侣姓名缩写、纪念日日期，搭配热气球或摩天轮糖艺装饰，仪式感拉满。\n\n口感：胚体可选巧克力/红丝绒/抹茶，夹层采用丝滑甘纳许与覆盆子果酱，甜中带酸层次分明。\n\n工艺：糖艺装饰全手工制作，需提前 24 小时预订。\n\n场景：求婚、纪念日、情人节。', '小麦粉、鸡蛋、白砂糖、比利时巧克力、覆盆子、稀奶油、食用金箔、糖艺装饰（葡萄糖浆、白砂糖）。', '6寸 / 8寸 / 双层 8+6寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g', '上海·中央厨房手工制作', '6寸 2-4 人份 / 8寸 4-8 人份', 'http://127.0.0.1:9090/files/download/1-5.jpeg', 108.00, 9, '份', 1);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (7, '童趣卡通萌趣蛋糕', '可爱卡通形象立体造型，口感松软香甜，孩子过生日氛围感十足。', '【童趣卡通萌趣蛋糕】孩子生日派对的可爱主角。\n\n造型：立体卡通造型（艾莎公主、皮卡丘、汪汪队等可选），翻糖手工捏制，色彩鲜艳安全可食用。\n\n口感：胚体为低糖配方，松软易消化，夹层采用新鲜水果与香草奶油，小朋友爱吃更安心。\n\n工艺：色素全部使用天然植物提取（甜菜根、菠菜、姜黄），无人工色素。\n\n场景：儿童生日、满月宴、百日宴。', '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜水果、翻糖（葡萄糖浆、食用淀粉）、天然色素（甜菜根、姜黄、菠菜）。', '6寸 / 8寸 / 10寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g', '上海·中央厨房手工制作', '6寸 4-6 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/2-1.jpeg', 88.00, 5, '份', 2);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (8, '元气童趣动漫蛋糕', '热门卡通人物创意装扮，颜值俏皮吸睛，清甜口味小朋友超喜爱。', '【元气童趣动漫蛋糕】让童年记忆跃上餐桌。\n\n造型：以热门动漫角色为主题，3D 立体造型+巧克力饼干装饰，俏皮吸睛。\n\n口感：胚体松软湿润，夹层为酸奶奶油与新鲜水果，清爽不腻。\n\n工艺：所有装饰均可食用，无塑料插件，安全放心。\n\n场景：儿童生日、主题派对。', '小麦粉、鸡蛋、白砂糖、酸奶、稀奶油、新鲜蓝莓草莓、白巧克力、食用淀粉。', '6寸 / 8寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g', '上海·中央厨房手工制作', '6寸 4-6 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/2-2.jpeg', 108.00, 10, '份', 2);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (9, '欢乐童趣玩伴蛋糕', '缤纷配色搭配卡通摆件，奶香浓郁不腻，承包孩童快乐生日时光。', '【欢乐童趣玩伴蛋糕】承包一整年的快乐。\n\n造型：缤纷色彩+卡通巧克力摆件，色彩明快可爱，氛围感十足。\n\n口感：松软戚风胚搭配香草奶油与新鲜水果，奶香浓郁但糖度适中。\n\n工艺：色素全部植物提取，无防腐剂。\n\n场景：儿童生日、亲子派对。', '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜水果、黑巧克力、天然食用色素。', '6寸 / 8寸 / 10寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g', '上海·中央厨房手工制作', '6寸 4-6 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/2-3.jpeg', 89.00, 12, '份', 2);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (10, '梦幻童心卡通蛋糕', '软萌可爱卡通主题设计，果肉夹心爽口，打造纯真童趣生日盛宴。', '【梦幻童心卡通蛋糕】守护每一份童真。\n\n造型：双层设计，下层数奶油抹面+糖珠装饰，上层数卡通立体造型，梦幻十足。\n\n口感：果肉夹心扎实，搭配蓬松奶油，清新爽口。\n\n工艺：胚体当日现烤，新鲜水果当日采购。\n\n场景：儿童生日、百日宴。', '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜芒果、奇异果、草莓、糖珠、翻糖。', '双层 6+8寸', '冷藏 0-4℃ 24 小时内食用最佳', '约 1300g', '上海·中央厨房手工制作', '8-12 人份', 'http://127.0.0.1:9090/files/download/2-4.jpeg', 90.00, 2, '份', 2);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (11, '俏皮童趣乐园蛋糕', '多款卡通元素精致点缀，绵密奶油入味，满满童真欢乐氛围感。', '【俏皮童趣乐园蛋糕】打造专属儿童乐园。\n\n造型：游乐园主题设计，搭配旋转木马、气球等可食用糖艺装饰。\n\n口感：绵密奶油+松软蛋糕，夹层为香草布丁与水果颗粒。\n\n工艺：糖艺全手工制作，可定制小朋友的名字。\n\n场景：儿童生日、百日宴、周岁宴。', '小麦粉、鸡蛋、白砂糖、稀奶油、香草布丁、混合水果、糖艺装饰、食用色素。', '8寸 / 双层 6+8寸', '冷藏 0-4℃ 24 小时内食用最佳', '8寸 约 850g / 双层 约 1300g', '上海·中央厨房手工制作', '8寸 6-10 人份 / 双层 10-14 人份', 'http://127.0.0.1:9090/files/download/2-5.jpeg', 88.00, 10, '份', 2);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (12, '欢聚同乐蛋糕', '简约大气颜值耐看，口味清爽不甜腻，适合同事朋友相聚庆喜乐。', '【欢聚同乐蛋糕】聚会的百搭之选。\n\n造型：极简风抹面搭配时令水果围边与巧克力牌，简约大方。\n\n口感：戚风胚松软湿润，奶油减糖 25%，清爽不甜腻。\n\n工艺：当日现做，全程冷链。\n\n场景：生日、团建、朋友聚会。', '小麦粉、鸡蛋、白砂糖、稀奶油、混合水果（草莓、蓝莓、奇异果）、黑巧克力。', '6寸 / 8寸 / 10寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g', '上海·中央厨房手工制作', '6寸 3-5 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/3-1.jpeg', 88.00, 7, '份', 3);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (13, '暖心相伴欢聚蛋糕', '清爽鲜果搭配绵密奶油，百搭大方，团建聚餐好友小聚都合适。', '【暖心相伴欢聚蛋糕】让相聚更添温暖。\n\n造型：经典鲜果奶油蛋糕，时令水果铺满，简约耐看。\n\n口感：戚风胚+动物奶油+新鲜水果，奶香浓郁、清爽可口。\n\n工艺：拒绝植物奶油，全部使用新西兰进口动物奶油。\n\n场景：团建、生日、同事聚餐。', '小麦粉、鸡蛋、白砂糖、新西兰动物奶油、新鲜水果、吉利丁。', '6寸 / 8寸 / 10寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g', '上海·中央厨房手工制作', '6寸 3-5 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/3-2.jpeg', 108.00, 6, '份', 3);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (14, '职场同乐祝福蛋糕', '口感温润老少皆宜，造型简约大方，为同事生日送上真诚祝愿。', '【职场同乐祝福蛋糕】办公室生日首选。\n\n造型：素雅抹面+祝福语巧克力牌，可定制同事姓名与祝福语。\n\n口感：温润戚风+轻甜奶油，老少皆宜，适合不同口味偏好。\n\n工艺：可附赠贺卡，支持团队定制。\n\n场景：同事生日、职场庆典。', '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜水果、巧克力。', '6寸 / 8寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g', '上海·中央厨房手工制作', '6寸 3-5 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/3-3.jpeg', 88.00, 12, '份', 3);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (15, '挚友温情聚会蛋糕', '层次丰富味道清甜，颜值低调耐看，拉近朋友同事之间情谊。', '【挚友温情聚会蛋糕】为友情干杯。\n\n造型：低调灰色抹面+巧克力碎片，简约低调。\n\n口感：双层夹心（榛子巧克力+覆盆子果酱），层次丰富味道清甜。\n\n工艺：选用意大利榛子与法国覆盆子果酱。\n\n场景：朋友生日、纪念日。', '小麦粉、鸡蛋、白砂糖、稀奶油、榛子、覆盆子果酱、黑巧克力。', '6寸 / 8寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g', '上海·中央厨房手工制作', '6寸 3-5 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/3-4.jpeg', 90.00, 8, '份', 3);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (16, '喜乐同行轻奢蛋糕', '精致简约百搭款式，奶香醇厚顺口，日常送礼团建庆祝超实用。\n', '【喜乐同行轻奢蛋糕】轻奢百搭的送礼优选。\n\n造型：大理石纹抹面+金箔点缀，质感优雅。\n\n口感：法国进口奶油+ Madagascar 香草籽，奶香醇厚顺口。\n\n工艺：每一颗香草籽都来自马达加斯加，工艺考究。\n\n场景：送礼、团建、生日、纪念日。', '小麦粉、鸡蛋、白砂糖、法国稀奶油、马达加斯加香草荚、食用金箔、吉利丁。', '6寸 / 8寸 / 10寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g', '上海·中央厨房手工制作', '6寸 3-5 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/3-5.jpeg', 108.00, 11, '份', 3);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (17, '仙女风仙气裸蛋糕', '轻盈奶油搭配鲜果，自带柔光滤镜，满足女生对浪漫的所有想象。', '【仙女风仙气裸蛋糕】满足少女心。\n\n造型：裸蛋糕侧边露出胚体纹理，顶部铺满鲜果与可食用花朵，仙气十足。\n\n口感：胚体为低糖配方，奶油薄薄一层，轻盈无负担。\n\n工艺：可食用花朵均为有机种植，安全可食。\n\n场景：闺蜜生日、求婚、纪念日。', '小麦粉、鸡蛋、白砂糖、稀奶油、有机可食用花（三色堇、玫瑰）、新鲜莓果。', '6寸 / 8寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 450g / 8寸 约 750g', '上海·中央厨房手工制作', '6寸 2-4 人份 / 8寸 4-8 人份', 'http://127.0.0.1:9090/files/download/4-1.jpeg', 108.00, 1, '份', 4);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (18, '简约潮酷男士蛋糕', '简约大气利落造型，口味醇厚不腻，适配男生生日沉稳大气风格。', '【简约潮酷男士蛋糕】送男友/兄弟的硬核之选。\n\n造型：黑灰金三色搭配，几何切面设计，搭配车厘子与金箔，沉稳大气。\n\n口感：黑巧克力甘纳许+榛子脆胚，醇厚不腻。\n\n工艺：使用比利时 70% 黑巧克力。\n\n场景：男友生日、父亲节、兄弟聚会。', '小麦粉、鸡蛋、白砂糖、比利时 70% 黑巧克力、榛子、稀奶油、可可粉、食用金箔。', '6寸 / 8寸', '冷藏 0-4℃ 24 小时内食用最佳', '6寸 约 500g / 8寸 约 850g', '上海·中央厨房手工制作', '6寸 3-5 人份 / 8寸 6-10 人份', 'http://127.0.0.1:9090/files/download/5-1.jpeg', 88.00, 10, '份', 5);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (19, '福寿安康祝寿蛋糕', '松软低脂口感温润，鲜果搭配软糯夹层，祝愿长辈平安健康福寿绵长。', '【福寿安康祝寿蛋糕】孝敬长辈的温馨之选。\n\n造型：红色寿桃造型+\"寿\"字糖艺，寓意福寿安康，传统喜庆。\n\n口感：低糖低脂配方，松软易咀嚼，适合老年人。\n\n工艺：糖度降低 40%，使用木糖醇替代部分蔗糖。\n\n场景：长辈寿宴、母亲节、父亲节。', '小麦粉、鸡蛋、木糖醇、白砂糖、稀奶油、新鲜水果、寿桃造型翻糖、食用色素（甜菜根）。', '8寸 / 10寸 / 双层 8+10寸', '冷藏 0-4℃ 24 小时内食用最佳', '8寸 约 850g / 10寸 约 1200g / 双层 约 2000g', '上海·中央厨房手工制作', '8寸 6-10 人份 / 10寸 10-16 人份', 'http://127.0.0.1:9090/files/download/6-1.jpeg', 108.00, 5, '份', 6);
INSERT INTO `goods` (`id`, `name`, `description`, `detail`, `ingredients`, `specs`, `shelf_life`, `weight`, `origin`, `serves`, `img`, `price`, `num`, `unit`, `category_id`) VALUES (20, '轻奢双层祝寿蛋糕', '双层造型大气华丽，用料扎实口感细腻，宴席聚会庆生场面十足。', '【轻奢双层祝寿蛋糕】宴席大场面首选。\n\n造型：双层结构，上层鲜花装饰+下层绸缎裱花，搭配金箔与糖艺\"寿\"字，富丽堂皇。\n\n口感：上层香草胚+下层巧克力胚，一蛋糕两口味，覆盖更多偏好。\n\n工艺：需提前 12 小时预订，糖艺现做。\n\n场景：寿宴、宴席、企业庆典。', '小麦粉、鸡蛋、白砂糖、稀奶油、比利时巧克力、马达加斯加香草荚、新鲜水果、食用金箔、翻糖。', '双层 8+10寸 / 双层 10+12寸', '冷藏 0-4℃ 24 小时内食用最佳', '8+10寸 约 2000g / 10+12寸 约 2800g', '上海·中央厨房手工制作', '15-25 人份', 'http://127.0.0.1:9090/files/download/7-1.jpeg', 188.00, 18, '份', 7);
COMMIT;

-- ----------------------------
-- Table structure for index_task
-- ----------------------------
DROP TABLE IF EXISTS `index_task`;
CREATE TABLE `index_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `entity_type` varchar(32) NOT NULL DEFAULT 'goods',
  `entity_id` int NOT NULL,
  `action` varchar(16) NOT NULL,
  `status` varchar(16) NOT NULL DEFAULT 'pending',
  `attempts` int NOT NULL DEFAULT '0',
  `last_error` longtext,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='向量索引 outbox：MySQL 业务提交后写入，后台任务异步同步到 ChromaDB。';

-- ----------------------------
-- Records of index_task
-- ----------------------------
BEGIN;
COMMIT;

-- ----------------------------
-- Table structure for knowledge
-- ----------------------------
DROP TABLE IF EXISTS `knowledge`;
CREATE TABLE `knowledge` (
  `id` int NOT NULL AUTO_INCREMENT,
  `filename` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `original_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_size` int DEFAULT NULL,
  `chunk_count` int DEFAULT NULL,
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Records of knowledge
-- ----------------------------
BEGIN;
INSERT INTO `knowledge` (`id`, `filename`, `original_name`, `file_size`, `chunk_count`, `created_at`) VALUES (1, 'cbbee6c0c4d94ea6a2f05f42be3b7770', '蛋糕商城智能客服知识库文档.docx', 33569, 12, '2026-07-07 02:20:02.572812');
COMMIT;

-- ----------------------------
-- Table structure for message
-- ----------------------------
DROP TABLE IF EXISTS `message`;
CREATE TABLE `message` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role` varchar(20) NOT NULL,
  `content` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `conversation_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_message_conversa_a556956b` (`conversation_id`),
  CONSTRAINT `fk_message_conversa_a556956b` FOREIGN KEY (`conversation_id`) REFERENCES `conversation` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=65 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Records of message
-- ----------------------------
BEGIN;
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (3, 'user', '你好', '2026-06-04 13:07:16.635137', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (4, 'assistant', '你好呀～ 🐻‍❄️ 欢迎来到 Little-bear Cake Store！我是你的智能客服小助手，有什么可以帮你的吗？无论是想了解我们的蛋糕口味、价格，还是需要查询订单状态，我都在这里哦！✨', '2026-06-04 13:07:17.782699', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (5, 'user', '今天星期几', '2026-06-04 13:15:06.346933', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (6, 'assistant', '今天是星期五哦～ 🗓️ 你有什么特别的计划吗？如果需要推荐蛋糕或者查询订单，随时告诉我哟！', '2026-06-04 13:15:07.114944', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (7, 'user', '你能替我做些什么', '2026-06-04 13:15:29.616242', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (8, 'assistant', '我可以帮你做很多事情哦～ 🐻‍❄️  \n1. **解答蛋糕相关问题**：比如口味、价格、描述等等～  \n2. **查询订单状态**：告诉你你的订单现在到哪一步啦！  \n3. **推荐蛋糕**：根据你的喜好或场合，给你最合适的建议！  \n4. **其他问题**：比如配送信息、优惠活动等等，我都可以帮你解答～  \n\n有什么需要我帮忙的吗？告诉我就好啦！😊', '2026-06-04 13:15:31.004423', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (9, 'user', '你知道我是谁吗', '2026-06-04 13:15:46.294363', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (10, 'assistant', '你好呀～ 🐻‍❄️ 我暂时还不太清楚你的身份呢，不过没关系！无论你是新朋友还是老顾客，我都会以最热情的态度来帮助你。如果你愿意分享更多关于你的信息，我会更了解你，也能提供更贴心的服务哦！😊 你想告诉我一些关于你的事情吗？', '2026-06-04 13:15:47.472855', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (11, 'user', '介绍一下草莓蛋糕', '2026-06-04 13:16:24.815260', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (12, 'assistant', '草莓蛋糕是我们的经典甜品之一，非常受欢迎哦～ 🍓🎂  \n\n**描述**：  \n这款蛋糕以新鲜的草莓为主角，外层是绵密柔软的海绵蛋糕，内夹着香甜的草莓果酱和新鲜草莓片，顶部还点缀着可爱的草莓装饰，看起来就让人垂涎欲滴！\n\n**口味**：  \n酸甜适中，清新爽口，特别适合喜欢水果风味的朋友。\n\n**价格**：  \n小号 ￥48，中号 ￥68，大号 ￥98（可根据需求选择）\n\n如果你想要一个浪漫或甜蜜的庆祝蛋糕，这款草莓蛋糕绝对是不错的选择呢！需要我帮你推荐搭配的尺寸或配送方式吗？😊', '2026-06-04 13:16:27.060963', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (13, 'user', '介绍一下浪漫爱心情侣蛋糕', '2026-06-04 13:24:04.872588', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (14, 'assistant', '这款**浪漫爱心情侣蛋糕**是我们专门为情侣们设计的甜蜜之作，充满爱意与温馨～ ❤️🎂  \n\n**描述**：  \n蛋糕造型是心形的，外层是香浓的奶油，上面用糖霜绘制了爱心、情侣剪影或名字缩写等图案，还可以根据你的需求定制文字（比如“LOVE YOU”或你们的名字）。内部夹着香甜的草莓或巧克力口味，口感丰富，每一口都充满爱的味道。\n\n**口味**：  \n可以选择经典巧克力、香草、或者草莓口味，也可以混合搭配哦！\n\n**价格**：  \n中号 ￥88，大号 ￥128（支持定制尺寸）\n\n这款蛋糕非常适合情人节、纪念日、求婚或婚礼等浪漫时刻，让爱意更加甜蜜！需要我帮你设计一个专属的浪漫图案吗？💖', '2026-06-04 13:24:06.665523', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (15, 'user', '北京天气怎么样', '2026-06-04 13:25:42.729718', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (16, 'assistant', '北京现在天气晴朗，气温适中，非常适合外出活动呢～ 🌤️ 今天最高气温大约在22℃左右，微风轻拂，是个出门散步或享受甜点的好日子！如果你打算来Little-bear Cake Store选购蛋糕，记得带上你最爱的甜蜜心情哦～ 😊 有其他需要帮忙的吗？', '2026-06-04 13:25:43.885067', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (17, 'user', 'Hello', '2026-06-04 13:30:12.334395', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (18, 'assistant', 'Hello! 😊 欢迎来到 Little-bear Cake Store！我是您的智能客服助手，有什么可以帮您的吗？无论是想了解我们的蛋糕产品、查询订单状态，还是需要推荐，我都在这里哦！', '2026-06-04 13:30:13.188452', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (19, 'user', '祝寿蛋糕', '2026-06-06 03:18:33.975585', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (20, 'assistant', '🎉 **福寿安康祝寿蛋糕** 🎉  \n这款蛋糕专为祝福长辈而设计，寓意美好，口感温润，非常适合作为生日或寿宴的甜蜜礼物！\n\n**描述**：  \n松软低脂的蛋糕体搭配新鲜水果和软糯夹层，不仅美味，还健康贴心。蛋糕上还会用糖霜绘制“福”“寿”等吉祥字样，表达对长辈的美好祝愿。\n\n**价格**：￥108.0元  \n\n如果你想要为家中的长辈送上一份特别的祝福，这款蛋糕绝对是不错的选择！需要我帮你定制祝福语或包装方式吗？💐😊', '2026-06-06 03:18:35.719193', 4);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (21, 'user', '祝寿蛋糕', '2026-07-04 02:26:09.181769', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (22, 'assistant', '您好！我们有一款非常适合祝寿的蛋糕——「福寿安康祝寿蛋糕」，价格是 108.0 元。这款蛋糕口感温润、松软低脂，搭配鲜果和软糯夹层，寓意长辈平安健康、福寿绵长。非常适合表达对长辈的祝福哦！🎉🎂 如果您有其他需求，欢迎随时告诉我～', '2026-07-04 02:26:10.327035', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (23, 'user', '有什么祝寿蛋糕推荐吗', '2026-07-04 02:26:35.324564', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (24, 'assistant', '我们有几款非常受欢迎的祝寿蛋糕推荐给您：\n\n1. **福寿安康祝寿蛋糕** - 价格 108.0 元，口感温润、松软低脂，搭配鲜果和软糯夹层，寓意长辈平安健康、福寿绵长。\n2. **长寿金榜蛋糕** - 价格 138.0 元，采用经典红丝绒口味，内含坚果夹层，象征事业高升、福寿双全。\n3. **百岁好合蛋糕** - 价格 168.0 元，融合香草与巧克力风味，装饰精美，适合表达对长辈的美好祝愿。\n\n如果您需要定制或有其他需求，欢迎随时告诉我哦！🎂✨', '2026-07-04 02:26:37.273435', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (25, 'user', '我的订单', '2026-07-04 02:40:16.738281', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (26, 'assistant', '请提供您的用户ID，以便我为您查询订单状态。如果您不确定用户ID，也可以提供其他信息，我会尽力帮您查找。😊', '2026-07-04 02:40:17.398679', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (27, 'user', '321', '2026-07-04 02:40:32.185239', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (28, 'assistant', '您的订单信息如下：\n\n- 订单 #1：轻奢双人告白蛋糕 x1，¥88.0，下单时间：2026-05-19 17:28:15\n\n如果您需要进一步帮助，比如取消订单或了解其他信息，请随时告诉我哦！🎂', '2026-07-04 02:40:33.786729', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (29, 'user', '有什么蛋糕推荐吗', '2026-07-04 02:40:56.067460', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (30, 'assistant', '看起来我遇到了一点小问题，无法为您推荐蛋糕。您可以告诉我您的偏好（比如“生日”、“情侣”、“送朋友”等），我会尽力为您提供合适的建议！🎂✨', '2026-07-04 02:40:57.204334', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (31, 'user', '过生日有什么蛋糕推荐吗', '2026-07-04 02:41:10.789782', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (32, 'assistant', '很抱歉，我暂时无法为您提供生日蛋糕推荐。您可以告诉我您喜欢的口味或风格，我会尽力为您提供建议！🎂✨', '2026-07-04 02:41:12.032151', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (35, 'user', '我的订单', '2026-07-04 02:45:43.331274', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (36, 'assistant', '您的订单信息如下：\n\n- 订单 #1：轻奢双人告白蛋糕 x1，¥88.0，下单时间：2026-05-19 17:28:15\n\n如果您需要进一步帮助，比如取消订单或了解其他信息，请随时告诉我哦！🎂', '2026-07-04 02:45:44.888853', 5);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (47, 'user', '我的订单', '2026-07-04 02:55:53.154376', 8);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (48, 'assistant', '请提供您的订单ID或订单号，以便我为您查询订单状态。', '2026-07-04 02:55:53.793931', 8);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (49, 'user', '202607041055091665', '2026-07-04 02:56:13.281860', 8);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (50, 'assistant', '您的订单信息如下：\n\n订单号：202607041055091665  \n- 商品：欢聚同乐蛋糕  \n- 数量：1  \n- 单价：¥88.0  \n- 总价：¥88.0  \n- 收货地址：333  \n- 下单时间：2026-07-04 10:55:09  \n- 状态：待发货  \n\n如有其他问题，欢迎随时咨询！🎂', '2026-07-04 02:56:15.209319', 8);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (51, 'user', '配送范围是什么', '2026-07-07 02:20:46.009933', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (52, 'assistant', '我们的配送范围包括核心商圈的即时配送（2-4小时内送达），以及预约配送和定时达服务。您可以在下单时选择指定的送达日期和时段（如10:00-12:00、14:00-16:00、18:00-20:00）。常规配送服务时间为每日 09:00 - 21:00，节假日（如春节、情人节、母亲节、圣诞节等）配送量激增，建议提前2-3天预约，当日订单可能无法保证指定时段送达。恶劣天气可能导致配送延迟，配送员会提前与您联系协商。', '2026-07-07 02:20:48.476482', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (53, 'user', '常规款蛋糕什么时候配送', '2026-07-07 02:21:29.944567', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (54, 'assistant', '常规款蛋糕的配送时间如下：\n\n- **即时配送（同城急送）**：适用于现货常规款蛋糕，下单后2-4小时内送达，覆盖核心商圈。\n- **预约配送**：用户可指定送达日期和时段（如10:00-12:00、14:00-16:00、18:00-20:00），系统将在指定时段内完成配送。\n- **定时达**：支持精确到小时的配送预约，需提前至少24小时下单。\n\n常规配送服务时间是每日 **09:00 - 21:00**。如果在节假日（如春节、情人节、母亲节、圣诞节等）下单，建议提前2-3天预约，因为这些时段配送量大，可能无法保证指定时段送达。', '2026-07-07 02:21:33.298573', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (55, 'user', '七天无理由退化', '2026-07-07 02:22:11.058068', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (56, 'assistant', '根据《中华人民共和国消费者权益保护法》及相关规定，蛋糕属于“易于腐败、保存期限较短”的商品，因此**不适用七天无理由退货**政策。以下情况也不接受任何形式的退货：\n\n1. 已拆封或食用的蛋糕；\n2. 因消费者保存不当（如未冷藏导致变质、失温融化）造成的损坏；\n3. 个人主观因素（口味不合、甜度不满意、与图片有色差等）要求退货；\n4. 超过24小时才反映商品问题且无有效凭证；\n5. 轻微运输瑕疵（装饰物轻微位移、奶油轻微刮痕）不影响食用的情况；\n6. 非商城责任（如第三方配送导致延迟，但蛋糕品质未受影响）。\n\n如有质量问题（如运输途中严重毁损、错送款式等），我们提供售后处理。建议您在收到蛋糕后尽快检查，并在24小时内联系客服处理。', '2026-07-07 02:22:15.764137', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (57, 'user', '祝寿蛋糕的配送费是多少？', '2026-07-07 02:23:21.179181', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (58, 'assistant', '祝寿蛋糕的配送费用会根据收货地址、订单金额、蛋糕尺寸和重量综合计算，具体费用以您在下单页面看到的金额为准。如在特殊时段（如情人节、除夕等），可能会有节日配送服务费，会在下单页面提前明示。', '2026-07-07 02:23:22.985135', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (59, 'user', '祝寿蛋糕有哪些推荐', '2026-07-07 02:23:47.563557', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (60, 'assistant', '为您推荐以下祝寿蛋糕：\n\n1. **福寿安康祝寿蛋糕** - ¥108.0（有货，剩余5份）  \n   松软低脂口感温润，鲜果搭配软糯夹层，祝愿长辈平安健康福寿绵长。\n\n2. **轻奢双层祝寿蛋糕** - ¥188.0（有货，剩余18份）  \n   双层造型大气华丽，用料扎实口感细腻，宴席聚会庆生场面十足。\n\n如果您需要定制款或有特殊需求，建议提前3-7天预订哦！祝您选购愉快~ 🎂', '2026-07-07 02:23:50.494373', 9);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (61, 'user', '我想退货', '2026-07-07 06:36:29.355397', 8);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (62, 'assistant', '根据您的订单号202607041055091665，当前订单状态为“待发货”。如果您需要取消订单，请告知，我将为您处理。需要注意的是，若订单已进入制作流程，可能无法取消或需支付一定手续费。请确认您的需求！', '2026-07-07 06:36:31.123538', 8);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (63, 'user', '退货规则是什么', '2026-07-07 06:36:42.306790', 8);
INSERT INTO `message` (`id`, `role`, `content`, `created_at`, `conversation_id`) VALUES (64, 'assistant', '根据我们的退货规则，以下是关键点：\n\n1. **不适用七天无理由退货**：蛋糕属于易腐商品，且定制蛋糕是依消费者要求制作的，因此不适用七天无理由退货。\n\n2. **不接受退货的情形**：\n   - 已拆封、食用的蛋糕；\n   - 因保存不当（如未冷藏导致变质）造成的损坏；\n   - 个人主观因素（如口味不合、甜度不满意等）；\n   - 超过24小时才反映问题且无有效凭证；\n   - 轻微运输瑕疵（如装饰物轻微位移、奶油轻微刮痕）；\n   - 非商城责任（如第三方配送导致延迟，但蛋糕品质未受影响）。\n\n3. **质量问题售后处理**：\n   - 若蛋糕在运输途中发生严重毁损（倾倒、大面积变形、融化）、商品与订单不符或存在明显变质等问题，可申请售后。\n   - 售后流程包括即时反馈、提供凭证（开箱视频、照片等）、客服审核及处理方案（补发、部分退款或全额退款）。\n   - 退款时效为审核通过后7-14个工作日，信用卡退款可能需要更长时间。\n\n4. **退换货费用承担**：根据具体情况而定。\n\n如果您遇到任何问题，请尽快联系客服，并提供相关凭证。希望这些信息对您有帮助！如有其他疑问，请随时告知 😊', '2026-07-07 06:36:45.647517', 8);
COMMIT;

-- ----------------------------
-- Table structure for notice
-- ----------------------------
DROP TABLE IF EXISTS `notice`;
CREATE TABLE `notice` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '标题',
  `content` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '内容',
  `time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公告信息';

-- ----------------------------
-- Records of notice
-- ----------------------------
BEGIN;
INSERT INTO `notice` (`id`, `name`, `content`, `time`) VALUES (1, '智能蛋糕商城系统', '智能蛋糕商城系统Beta版今日已上线！', '2026-05-19 21:10:13');
INSERT INTO `notice` (`id`, `name`, `content`, `time`) VALUES (2, '111', '111111111111111111111111111111111111111111111111111111', '2026-05-19 21:10:45');
COMMIT;

-- ----------------------------
-- Table structure for orders
-- ----------------------------
DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `order_no` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `num` int DEFAULT NULL COMMENT '数量',
  `user_id` int DEFAULT NULL COMMENT '用户ID',
  `goods_id` int DEFAULT NULL COMMENT '商品ID',
  `address_id` int DEFAULT NULL COMMENT '地址ID',
  `time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '下单时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单信息';

-- ----------------------------
-- Records of orders
-- ----------------------------
BEGIN;
INSERT INTO `orders` (`id`, `order_no`, `num`, `user_id`, `goods_id`, `address_id`, `time`) VALUES (2, NULL, 2, 4, 8, 4, '2026-05-19 20:57:45');
INSERT INTO `orders` (`id`, `order_no`, `num`, `user_id`, `goods_id`, `address_id`, `time`) VALUES (3, '202607041055091665', 1, 1, 12, 3, '2026-07-04 10:55:09');
INSERT INTO `orders` (`id`, `order_no`, `num`, `user_id`, `goods_id`, `address_id`, `time`) VALUES (4, '202607041055292078', 2, 1, 20, 1, '2026-07-04 10:55:29');
INSERT INTO `orders` (`id`, `order_no`, `num`, `user_id`, `goods_id`, `address_id`, `time`) VALUES (5, '202607041547335041', 1, 1, 1, 1, '2026-07-04 15:47:33');
COMMIT;

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '账号',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '密码',
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '名称',
  `avatar` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '头像',
  `role` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '角色',
  `must_change_password` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户信息';

-- ----------------------------
-- Records of user
-- ----------------------------
BEGIN;
INSERT INTO `user` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (1, '123', '$2b$12$kbu9Kh/ChoYOvwMGn/3QyuMF7tZ7HFESMut5KnATm689BlSGPUAb.', '123', 'http://127.0.0.1:9090/files/download/head.jpg', '用户', 0);
INSERT INTO `user` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (3, '222', '123', '222', 'http://127.0.0.1:9090/files/download/head.jpg', '用户', 0);
INSERT INTO `user` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (4, '234', '234', '234', 'http://127.0.0.1:9090/files/download/avatar/b23081496c2d4e0f9315070e31acb3bd.png', '用户', 0);
INSERT INTO `user` (`id`, `username`, `password`, `name`, `avatar`, `role`, `must_change_password`) VALUES (5, '321', '321', '321', 'http://127.0.0.1:9090/files/download/avatar/10179d46dcad47109f83e2778b4b0290.png', '用户', 0);
COMMIT;

SET FOREIGN_KEY_CHECKS = 1;
