-- [已废弃] 商品详情页字段迁移脚本
-- 废弃原因：cake_store.sql 最新 dump 已包含这些字段，新部署无需再执行
-- 保留在 archive/ 仅作历史参考。migrate.sh 不会扫描 archive/ 子目录。
--
-- 历史新增字段：
--   detail       详情页详细介绍（长文本）
--   ingredients  配料表（过敏原提示）
--   specs        规格（如 6寸/8寸/10寸）
--   shelf_life   保质期
--   weight       净含量
--   origin       产地
--   serves       适用人数

USE `cake_store`;

-- 显式声明客户端字符集：避免 mysql CLI 默认 latin1 导致中文常量双重编码
SET NAMES utf8mb4;

ALTER TABLE `goods`
  ADD COLUMN `detail` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT '详情页详细介绍' AFTER `description`,
  ADD COLUMN `ingredients` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '配料表' AFTER `detail`,
  ADD COLUMN `specs` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '规格' AFTER `ingredients`,
  ADD COLUMN `shelf_life` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '保质期' AFTER `specs`,
  ADD COLUMN `weight` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '净含量' AFTER `shelf_life`,
  ADD COLUMN `origin` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '产地' AFTER `weight`,
  ADD COLUMN `serves` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '适用人数' AFTER `origin`;

-- 为已有商品填充详情字段示例（保持与 cake_store.sql 同步）
UPDATE `goods` SET
  `detail` = '【浪漫爱心情侣蛋糕】为甜蜜纪念日倾心打造。\n\n造型：经典爱心双层裱花，可选巧克力甘纳许淋面或新鲜草莓围边，顶部以食用金箔与玫瑰糖霜点缀，仪式感十足。\n\n口感：戚风胚体松软湿润，夹层采用法国进口奶油与新鲜草莓粒调和，奶香醇厚不甜腻。\n\n工艺：24小时内现做现发，全程冷链配送，确保每一口都新鲜。\n\n场景：情人节、求婚、纪念日、生日惊喜。',
  `ingredients` = '小麦粉、白砂糖、鸡蛋、稀奶油（含乳制品）、草莓、巧克力（可可液块、白砂糖、可可脂）、食用变性淀粉、明胶、食用香料。',
  `specs` = '6寸（约1磅）/ 8寸（约2磅）/ 10寸（约3磅）',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 450g / 8寸 约 750g / 10寸 约 1100g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 2-4 人份 / 8寸 4-8 人份'
WHERE `id` = 1;

UPDATE `goods` SET
  `detail` = '【轻奢双人告白蛋糕】简约而不简单的约会之选。\n\n造型：极简风裸蛋糕设计，奶油抹面保留手作纹理，搭配时令鲜果与迷迭香点缀，自然温柔不张扬。\n\n口感：胚体采用日式棉花蛋糕工艺，绵密如云朵；夹层为低糖马斯卡彭奶酪，奶香浓郁但减糖 30%。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、马斯卡彭奶酪、稀奶油、混合莓果（蓝莓、树莓）、吉利丁、香草精。',
  `specs` = '6寸（约1磅）/ 8寸（约2磅）',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 450g / 8寸 约 750g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 2-4 人份 / 8寸 4-8 人份'
WHERE `id` = 3;

UPDATE `goods` SET
  `detail` = '【甜蜜相守情侣蛋糕】记录每一个温馨时刻。\n\n造型：双层结构，下层数奶油抹面配以新鲜水果围边，上层数巧克力羽毛装饰，整体温柔治愈。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、北海道稀奶油、新鲜草莓、芒果、黑巧克力、可可粉、吉利丁。',
  `specs` = '6寸 / 8寸 / 双层 8+6寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 2-4 人份 / 8寸 4-8 人份'
WHERE `id` = 4;

UPDATE `goods` SET
  `detail` = '【爱意满满情侣蛋糕】一抹粉橘，温暖整个时光。\n\n造型：法式粉橘调抹面，搭配新鲜树莓、玫瑰花瓣糖霜与心形巧克力牌，温柔浪漫。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、法国黄油、比利时巧克力、杏仁、树莓、玫瑰水、香草荚。',
  `specs` = '6寸 / 8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 480g / 8寸 约 800g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 2-4 人份 / 8寸 4-8 人份'
WHERE `id` = 5;

UPDATE `goods` SET
  `detail` = '【专属热恋情侣蛋糕】为爱定制，独一无二。\n\n造型：可定制情侣姓名缩写、纪念日日期，搭配热气球或摩天轮糖艺装饰，仪式感拉满。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、比利时巧克力、覆盆子、稀奶油、食用金箔、糖艺装饰（葡萄糖浆、白砂糖）。',
  `specs` = '6寸 / 8寸 / 双层 8+6寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 2-4 人份 / 8寸 4-8 人份'
WHERE `id` = 6;

UPDATE `goods` SET
  `detail` = '【童趣卡通萌趣蛋糕】孩子生日派对的可爱主角。\n\n造型：立体卡通造型（艾莎公主、皮卡丘、汪汪队等可选），翻糖手工捏制，色彩鲜艳安全可食用。\n\n色素全部使用天然植物提取（甜菜根、菠菜、姜黄），无人工色素。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜水果、翻糖（葡萄糖浆、食用淀粉）、天然色素（甜菜根、姜黄、菠菜）。',
  `specs` = '6寸 / 8寸 / 10寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 4-6 人份 / 8寸 6-10 人份'
WHERE `id` = 7;

UPDATE `goods` SET
  `detail` = '【元气童趣动漫蛋糕】让童年记忆跃上餐桌。\n\n造型：以热门动漫角色为主题，3D 立体造型+巧克力饼干装饰，俏皮吸睛。\n\n所有装饰均可食用，无塑料插件，安全放心。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、酸奶、稀奶油、新鲜蓝莓草莓、白巧克力、食用淀粉。',
  `specs` = '6寸 / 8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 4-6 人份 / 8寸 6-10 人份'
WHERE `id` = 8;

UPDATE `goods` SET
  `detail` = '【欢乐童趣玩伴蛋糕】承包一整年的快乐。\n\n造型：缤纷色彩+卡通巧克力摆件，色彩明快可爱，氛围感十足。\n\n色素全部植物提取，无防腐剂。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜水果、黑巧克力、天然食用色素。',
  `specs` = '6寸 / 8寸 / 10寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 4-6 人份 / 8寸 6-10 人份'
WHERE `id` = 9;

UPDATE `goods` SET
  `detail` = '【梦幻童心卡通蛋糕】守护每一份童真。\n\n造型：双层设计，下层数奶油抹面+糖珠装饰，上层数卡通立体造型，梦幻十足。\n\n胚体当日现烤，新鲜水果当日采购。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜芒果、奇异果、草莓、糖珠、翻糖。',
  `specs` = '双层 6+8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '约 1300g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '8-12 人份'
WHERE `id` = 10;

UPDATE `goods` SET
  `detail` = '【俏皮童趣乐园蛋糕】打造专属儿童乐园。\n\n造型：游乐园主题设计，搭配旋转木马、气球等可食用糖艺装饰。\n\n糖艺全手工制作，可定制小朋友的名字。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、香草布丁、混合水果、糖艺装饰、食用色素。',
  `specs` = '8寸 / 双层 6+8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '8寸 约 850g / 双层 约 1300g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '8寸 6-10 人份 / 双层 10-14 人份'
WHERE `id` = 11;

UPDATE `goods` SET
  `detail` = '【欢聚同乐蛋糕】聚会的百搭之选。\n\n造型：极简风抹面搭配时令水果围边与巧克力牌，简约大方。\n\n戚风胚松软湿润，奶油减糖 25%，清爽不甜腻。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、混合水果（草莓、蓝莓、奇异果）、黑巧克力。',
  `specs` = '6寸 / 8寸 / 10寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 3-5 人份 / 8寸 6-10 人份'
WHERE `id` = 12;

UPDATE `goods` SET
  `detail` = '【暖心相伴欢聚蛋糕】让相聚更添温暖。\n\n造型：经典鲜果奶油蛋糕，时令水果铺满，简约耐看。\n\n拒绝植物奶油，全部使用新西兰进口动物奶油。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、新西兰动物奶油、新鲜水果、吉利丁。',
  `specs` = '6寸 / 8寸 / 10寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 3-5 人份 / 8寸 6-10 人份'
WHERE `id` = 13;

UPDATE `goods` SET
  `detail` = '【职场同乐祝福蛋糕】办公室生日首选。\n\n造型：素雅抹面+祝福语巧克力牌，可定制同事姓名与祝福语。\n\n口感：温润戚风+轻甜奶油，老少皆宜，适合不同口味偏好。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、新鲜水果、巧克力。',
  `specs` = '6寸 / 8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 3-5 人份 / 8寸 6-10 人份'
WHERE `id` = 14;

UPDATE `goods` SET
  `detail` = '【挚友温情聚会蛋糕】为友情干杯。\n\n造型：低调灰色抹面+巧克力碎片，简约低调。\n\n双层夹心（榛子巧克力+覆盆子果酱），层次丰富味道清甜。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、榛子、覆盆子果酱、黑巧克力。',
  `specs` = '6寸 / 8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 3-5 人份 / 8寸 6-10 人份'
WHERE `id` = 15;

UPDATE `goods` SET
  `detail` = '【喜乐同行轻奢蛋糕】轻奢百搭的送礼优选。\n\n造型：大理石纹抹面+金箔点缀，质感优雅。\n\n法国进口奶油+ Madagascar 香草籽，奶香醇厚顺口。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、法国稀奶油、马达加斯加香草荚、食用金箔、吉利丁。',
  `specs` = '6寸 / 8寸 / 10寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g / 10寸 约 1200g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 3-5 人份 / 8寸 6-10 人份'
WHERE `id` = 16;

UPDATE `goods` SET
  `detail` = '【仙女风仙气裸蛋糕】满足少女心。\n\n造型：裸蛋糕侧边露出胚体纹理，顶部铺满鲜果与可食用花朵，仙气十足。\n\n可食用花朵均为有机种植，安全可食。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、有机可食用花（三色堇、玫瑰）、新鲜莓果。',
  `specs` = '6寸 / 8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 450g / 8寸 约 750g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 2-4 人份 / 8寸 4-8 人份'
WHERE `id` = 17;

UPDATE `goods` SET
  `detail` = '【简约潮酷男士蛋糕】送男友/兄弟的硬核之选。\n\n造型：黑灰金三色搭配，几何切面设计，搭配车厘子与金箔，沉稳大气。\n\n使用比利时 70% 黑巧克力。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、比利时 70% 黑巧克力、榛子、稀奶油、可可粉、食用金箔。',
  `specs` = '6寸 / 8寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '6寸 约 500g / 8寸 约 850g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '6寸 3-5 人份 / 8寸 6-10 人份'
WHERE `id` = 18;

UPDATE `goods` SET
  `detail` = '【福寿安康祝寿蛋糕】孝敬长辈的温馨之选。\n\n造型：红色寿桃造型+"寿"字糖艺，寓意福寿安康，传统喜庆。\n\n低糖低脂配方，糖度降低 40%，使用木糖醇替代部分蔗糖。',
  `ingredients` = '小麦粉、鸡蛋、木糖醇、白砂糖、稀奶油、新鲜水果、寿桃造型翻糖、食用色素（甜菜根）。',
  `specs` = '8寸 / 10寸 / 双层 8+10寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '8寸 约 850g / 10寸 约 1200g / 双层 约 2000g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '8寸 6-10 人份 / 10寸 10-16 人份'
WHERE `id` = 19;

UPDATE `goods` SET
  `detail` = '【轻奢双层祝寿蛋糕】宴席大场面首选。\n\n造型：双层结构，上层鲜花装饰+下层绸缎裱花，搭配金箔与糖艺"寿"字，富丽堂皇。\n\n上层香草胚+下层巧克力胚，一蛋糕两口味，覆盖更多偏好。',
  `ingredients` = '小麦粉、鸡蛋、白砂糖、稀奶油、比利时巧克力、马达加斯加香草荚、新鲜水果、食用金箔、翻糖。',
  `specs` = '双层 8+10寸 / 双层 10+12寸',
  `shelf_life` = '冷藏 0-4℃ 24 小时内食用最佳',
  `weight` = '8+10寸 约 2000g / 10+12寸 约 2800g',
  `origin` = '上海·中央厨房手工制作',
  `serves` = '15-25 人份'
WHERE `id` = 20;
