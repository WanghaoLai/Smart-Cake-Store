USE `cake_store`;
SET NAMES utf8mb4;

-- AI 可观测性：把 LangChain 返回的 usage_metadata 与耗时落到 message 表。
-- 仅 assistant 消息有值；旧数据字段为 NULL，统计按 0 计并标注缺失。
ALTER TABLE `message` ADD COLUMN `prompt_tokens` INT NULL AFTER `content`;
ALTER TABLE `message` ADD COLUMN `completion_tokens` INT NULL AFTER `prompt_tokens`;
ALTER TABLE `message` ADD COLUMN `latency_ms` INT NULL AFTER `completion_tokens`;
ALTER TABLE `message` ADD COLUMN `model` VARCHAR(64) NULL AFTER `latency_ms`;
