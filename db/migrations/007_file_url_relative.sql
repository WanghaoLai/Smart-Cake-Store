SET NAMES utf8mb4;

-- 文件 URL 相对化：历史数据把 request.base_url 拼出的绝对地址入库，
-- localhost:9090 与 127.0.0.1:9090 混存；域名/端口一变全部失效。
-- 统一清洗为 files/download/... 相对路径（绝对地址由前端按环境拼接）。
-- 仅匹配指向本服务 /files/download/ 的 URL，外部图床/CDN 地址不受影响。

UPDATE `goods`
SET `img` = REGEXP_REPLACE(`img`, 'https?://[^/]+/(files/download/)', '$1')
WHERE `img` REGEXP 'https?://[^/]+/files/download/';

UPDATE `user`
SET `avatar` = REGEXP_REPLACE(`avatar`, 'https?://[^/]+/(files/download/)', '$1')
WHERE `avatar` REGEXP 'https?://[^/]+/files/download/';

UPDATE `admin`
SET `avatar` = REGEXP_REPLACE(`avatar`, 'https?://[^/]+/(files/download/)', '$1')
WHERE `avatar` REGEXP 'https?://[^/]+/files/download/';

-- review.images 是 JSON 数组字符串，REGEXP_REPLACE 全局替换数组内每个元素
UPDATE `review`
SET `images` = REGEXP_REPLACE(`images`, 'https?://[^/]+/(files/download/)', '$1')
WHERE `images` REGEXP 'https?://[^/]+/files/download/';
