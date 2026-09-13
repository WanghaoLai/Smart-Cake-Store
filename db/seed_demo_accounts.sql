-- Development only. migrate.sh requires APP_ENV=development and SEED_DEMO_ACCOUNTS=1.
SET NAMES utf8mb4;
INSERT IGNORE INTO `admin` (`id`, `username`, `password`, `name`, `role`, `must_change_password`) VALUES
(1, '222', '$2b$12$rfj6TAsthdiU8ufcO1qvVOT27DlmyqtsbLwJEzSy6eMvngUmvmc0.', '演示管理员', '管理员', 1);

INSERT IGNORE INTO `user` (`id`, `username`, `password`, `name`, `role`, `must_change_password`) VALUES
(1, '234', '$2b$12$1l.HLJWA3WdbIE..Hokbo.6oSe0mfCweiDYr5UmNhX4wf4PZWaBxq', '演示用户', '用户', 1);

