SET NAMES utf8mb4;

-- User 与 Admin 位于独立表且主键可能重叠，不能使用只指向 user(id) 的外键
-- 表示两类会话所有者。现有记录均来自旧版普通用户入口，默认标记为“用户”。
SET @conversation_fk = (
  SELECT CONSTRAINT_NAME
  FROM information_schema.KEY_COLUMN_USAGE
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'conversation'
    AND COLUMN_NAME = 'user_id'
    AND REFERENCED_TABLE_NAME IS NOT NULL
  LIMIT 1
);
SET @drop_fk_sql = IF(
  @conversation_fk IS NULL,
  'SELECT 1',
  CONCAT('ALTER TABLE `conversation` DROP FOREIGN KEY `', @conversation_fk, '`')
);
PREPARE drop_fk_stmt FROM @drop_fk_sql;
EXECUTE drop_fk_stmt;
DEALLOCATE PREPARE drop_fk_stmt;

ALTER TABLE `conversation`
  ADD COLUMN `owner_role` varchar(32) NOT NULL DEFAULT '用户' AFTER `user_id`,
  ADD INDEX `idx_conversation_owner` (`owner_role`, `user_id`);
