# Smart Cake Store Docker 部署指南

本方案覆盖仓库中的 Vue 3 前端、FastAPI 后端、MySQL 8.4、ChromaDB 本地向量索引、上传文件和版本化 Agent profile。默认适合单机 Docker Compose 部署；公网生产环境应在 `web` 前再放置负责 TLS 的反向代理或负载均衡器。

## 1. 部署结构

```text
浏览器 :8080
    |
    v
Nginx + Vue 静态文件 (web)
    | /api/*，SSE 禁用缓冲
    v
FastAPI :9090 (api, 单 worker)
    |                         |
    v                         v
MySQL 8.4 (db)       ChromaDB + 上传文件（本地卷）
    ^
    |
一次性迁移容器 (migrate)
```

Compose 的启动门禁为 `db healthy -> migrate 成功退出 -> api healthy -> web`。迁移失败时 API 不会带着错误或过期的 schema 启动。

项目中的 Agent 配置 `fastapi-app/agents/config/*.json` 是应用版本的一部分，默认只读地烘焙进 API 镜像。这样 profile、工具白名单和代码保持同版本。运行环境只用环境变量调整允许覆盖的模型参数，不应把整个开发目录挂进生产容器。

## 2. 文件说明与构建实践

- `Dockerfile` 的 `wheels` 阶段安装编译工具并构建 Python wheels；`runtime` 阶段只保留 wheels 安装结果、`libgomp1` 和 `tini`，不包含编译器、测试依赖或 MySQL CLI。
- 同一 Dockerfile 的 `migrator` target 只给一次性迁移容器增加 MySQL 客户端和 `db/`，避免放大长期运行的 API 镜像和攻击面。
- API 使用 UID/GID `10001` 的非 root 用户，根文件系统只读，只允许 `/tmp`、`/app/files` 和 `/app/chroma_db` 写入。
- Uvicorn 固定一个 worker。当前上传配额、限流器和本地 ChromaDB 都有进程内/单写者假设；直接增加 workers 或 API 副本会使限流不一致，并可能竞争 SQLite/本地文件。横向扩容前需要把限流迁到 Redis、上传迁到对象存储、向量库迁到独立服务。
- `Dockerfile.frontend` 使用 `npm ci` 严格依据 `package-lock.json` 构建，再把 `dist/` 复制到 Nginx，不携带 Node.js 和源码。
- 前端构建参数固定为 `VITE_BASE_URL=/api`。Nginx 将 `/api/*` 转发给 API，因此浏览器不用知道 Docker 内部服务名，也没有跨域问题。
- `.dockerignore` 排除密钥、虚拟环境、依赖缓存、测试、开发态 Chroma 索引和运行时评价图片，缩小构建上下文并避免密钥进入镜像层。

当前 `requirements.txt` 主要使用 `~=`，可重建性是“锁定 major.minor，允许 patch 更新”，还不是完全可复现。正式发布建议在经过 CI 测试后生成带哈希的锁文件（如 `pip-compile --generate-hashes`），Docker 构建只安装该锁文件；同时将基础镜像从浮动标签升级为经过漏洞扫描的 digest，并由依赖机器人定期更新。

## 3. 首次配置

在项目根目录执行：

```bash
cp .env.docker.example .env.docker
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

编辑 `.env.docker`，至少替换：

- `DB_PASSWORD`：应用专用 MySQL 用户口令；
- `MYSQL_ROOT_PASSWORD`：不同于应用口令的 root 口令；
- `JWT_SECRET_KEY`：粘贴上面生成的随机值，生产环境至少 32 字符；
- `CORS_ORIGINS`：公网前端的完整来源，例如 `https://cake.example.com`；
- `DASHSCOPE_API_KEY`：需要智能客服、Embedding 和 AI 运营分析时填写。

`.env.docker` 已加入 `.gitignore`。它仍是明文文件，应设置最小权限：

```bash
chmod 600 .env.docker
```

Compose 的 `--env-file` 主要负责变量插值，只有显式列在服务 `environment` 中的变量会进入对应容器；MySQL root 密码不会进入 API 容器。更严格的平台部署应改用 Docker secrets 或云密钥管理服务，并让应用支持从 secret 文件读取。

不要复用 `fastapi-app/.env`：该文件的本机默认 `DB_HOST=localhost` 在容器内会指向 API 容器自身，而 Compose 中必须连接服务名 `db`。

## 4. 构建与启动

先校验最终配置（会展开环境变量，输出可能包含秘密，不要把结果贴到工单或日志）：

```bash
docker compose --env-file .env.docker config --quiet
```

构建全部镜像：

```bash
docker compose --env-file .env.docker build --pull
```

启动并后台运行：

```bash
docker compose --env-file .env.docker up -d
docker compose --env-file .env.docker ps
```

首次启动会创建三个命名卷并导入基础 schema、种子数据及全部增量迁移。查看启动链路：

```bash
docker compose --env-file .env.docker logs -f db migrate api web
```

`migrate` 正常状态是退出码 `0`，不是长期 `Up`。后续发布重复执行 `up -d` 时，幂等迁移脚本会跳过 `_schema_migrations` 中已记录的文件。

只重建并更新应用：

```bash
docker compose --env-file .env.docker build api migrate web
docker compose --env-file .env.docker up -d
```

普通停止与再次启动不会删除数据：

```bash
docker compose --env-file .env.docker stop
docker compose --env-file .env.docker start
```

删除容器和网络但保留卷：

```bash
docker compose --env-file .env.docker down
```

不要在有价值数据的环境运行 `docker compose down -v`，它会删除 MySQL、上传文件和 ChromaDB 三个卷。

## 5. 数据卷与备份

| 卷 | 容器路径 | 内容 | 恢复策略 |
|---|---|---|---|
| `mysql_data` | `/var/lib/mysql` | 业务数据、会话、迁移记录 | 定期逻辑备份 + 恢复演练 |
| `app_files` | `/app/files` | 种子图片、头像、商品图、评价图 | 文件级备份；必须与 DB 同一恢复时间点 |
| `chroma_data` | `/app/chroma_db` | 知识库和商品向量索引 | 可备份，也可依据 MySQL/知识文档重建 |

查看实际卷名：

```bash
docker volume ls --filter label=com.docker.compose.project=smart-cake-store
```

数据库逻辑备份示例（输出文件创建在宿主机当前目录）：

```bash
docker compose --env-file .env.docker exec -T db \
  sh -c 'exec mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" \
  --single-transaction --routines --triggers "$MYSQL_DATABASE"' > cake_store.sql
```

为避免口令进入 shell 历史，更推荐从安全的备份脚本/密钥存储注入，或交互式执行。备份不能只复制正在运行的 MySQL 数据目录；直接复制活跃 InnoDB 文件可能不一致。

`app_files` 与数据库中的相对 URL 有对应关系，二者应在同一维护窗口备份。ChromaDB 是可重建派生数据，但重建会调用 Embedding API 并产生时间/费用。

## 6. 部署后验证

### 6.1 基础健康检查

```bash
curl -fsS http://127.0.0.1:8080/nginx-health
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/health/db
```

预期依次返回 `ok`、FastAPI 的 `status: ok`、数据库 `connected`。API 端口只绑定宿主机回环地址，也可本机直查：

```bash
curl -fsS http://127.0.0.1:9090/health
```

### 6.2 容器与迁移状态

```bash
docker compose --env-file .env.docker ps -a
docker compose --env-file .env.docker logs migrate
docker compose --env-file .env.docker exec db \
  mysql -u cake_app -p cake_store -e "SELECT filename, applied_at FROM _schema_migrations ORDER BY filename;"
```

最后一条会交互式询问应用数据库密码。确认 `migrate` 为 `Exited (0)`，其余三个长期服务为 healthy。

### 6.3 功能冒烟测试

1. 打开 `http://localhost:8080`，确认 Vue 路由刷新不会 404。
2. 使用种子账号登录，或注册新用户；首次登录按项目规则修改密码。
3. 查看商品图片，上传一张评价图片，然后重启 API，确认图片仍可访问。
4. 配置 DashScope 后进行语义搜索、发送一条客服 SSE 消息，并在管理端检查知识库/索引状态。
5. 执行 `docker compose ... restart api` 后复查数据库、图片和向量索引，确认卷持久化有效。

## 7. Agent 配置的发布方式

默认发布流程是修改并评审 `fastapi-app/agents/config/customer_service.json` 或 `ops_assistant.json`，重建 API 镜像，再滚动更新。这能保证工具白名单、prompt 和执行器同步。

如确实需要紧急外置客服 profile，可只挂载一个经过审计的文件，并显式指定路径：

```yaml
services:
  api:
    environment:
      AGENT_CONFIG_PATH: /run/agent/customer_service.json
    volumes:
      - ./deploy/customer_service.json:/run/agent/customer_service.json:ro
```

不要把整个 `fastapi-app/agents` 目录覆盖到镜像中；这会造成代码/profile 版本漂移。运营分析 profile 当前由代码定位到镜像内固定路径，外置它需要先增加对应的受控配置项。

## 8. 常见问题排查

### `JWT_SECRET_KEY` 未配置或过短

API 日志会在导入 settings 时直接报错。生产环境必须使用至少 32 字符随机值；修改 `.env.docker` 后要重建容器环境：

```bash
docker compose --env-file .env.docker up -d --force-recreate api
```

### API 报数据库连接失败

- 容器内 `DB_HOST` 必须是 `db`，不是 `localhost`。
- 检查 `docker compose ... ps` 中 MySQL 是否 healthy。
- 查看 `db` 和 `migrate` 日志，确认应用用户、数据库名和密码一致。
- MySQL 命名卷初始化后，修改 `MYSQL_USER`/密码不会自动修改库内已有账号；应在 MySQL 中安全地执行 `ALTER USER`，或在确认无数据时重建卷。

### `migrate` 退出非零，API 一直不启动

```bash
docker compose --env-file .env.docker logs --tail=200 migrate db
docker compose --env-file .env.docker run --rm migrate
```

迁移脚本把 `orders` 是否存在作为基础库判断。`cake_store.sql` 含 `DROP TABLE`，不要绕过脚本手工重放；对“已有部分表但缺少 orders”的异常库，先备份并人工确认再处理。

### 前端页面正常但 API 404/502

- 浏览器请求应以 `/api/` 开头；若仍指向旧 Render 地址，需清理旧前端镜像并以 `VITE_BASE_URL=/api` 重新构建。
- `502` 通常表示 API 未 healthy 或正在重启，查看 `web` 和 `api` 日志。
- Nginx `proxy_pass` 末尾的 `/` 不能随意删除，否则 FastAPI 会收到不存在的 `/api/...` 路由。

### 聊天 SSE 一次性返回、超时或中断

确认请求经过 `location /api/`，其中 `proxy_buffering off` 且读取超时为 300 秒。再检查 DashScope Key、出口网络、`LLM_TIMEOUT_SECONDS` 和 API 日志。CDN/上层代理也必须关闭该路径的响应缓冲。

### 图片上传后重启丢失或权限错误

确认 `app_files:/app/files` 存在且 API 以 UID 10001 对卷可写。新命名卷会从镜像中的种子图片初始化；已有空卷不会在后续构建时自动补入新种子图片。需要同步新种子资源时，应使用一次性复制任务，不能删除含用户上传的卷。

### ChromaDB `readonly database`、锁冲突或索引缺失

确认 `chroma_data` 挂到 `/app/chroma_db`，不要同时启动多个写同一个本地卷的 API 实例。索引缺失时通过应用的索引重建接口恢复；先确认 DashScope Embedding 可用。

### 镜像过大或构建很慢

ChromaDB、LangChain、ONNX 等依赖本身较大。确认 BuildKit 缓存可用、`.dockerignore` 生效，且没有把 `.venv`、`node_modules`、本地 ChromaDB 或日志送入构建上下文。CI 可使用 registry cache；不要为了缩小镜像删除运行时实际需要的 `libgomp1`。

### 修改环境变量后没有生效

`restart` 不会重建容器环境，使用：

```bash
docker compose --env-file .env.docker up -d --force-recreate api web
```

`VITE_BASE_URL` 属于前端构建时变量，修改它必须重新 `build web`，仅重启无效。

## 9. 公网生产加固清单

- 在上层反向代理启用 HTTPS、HSTS、证书自动续期和合理的请求体/超时限制；只公开 80/443，不公开 MySQL 和 API 调试端口。
- 将 Compose 中 API 的 `ports` 删除，仅保留内部网络访问；当前回环映射主要用于本机运维验证。
- 使用云数据库时删除 `db` 服务和 `mysql_data`，把 `DB_HOST` 指向私网地址，并要求 TLS 连接（需要相应扩展当前 Tortoise 配置）。
- 备份 MySQL 与文件卷，配置异机保存、保留周期、加密和定期恢复演练。
- 在 CI 中运行后端测试、`npm ci && npm run build`、镜像漏洞扫描、SBOM 生成和镜像签名。
- 使用不可变版本号或 digest，不在生产直接依赖 `local`、浮动基础标签或未测试的 patch 更新。
- 将密钥迁到 secret manager，轮换数据库、JWT 和 DashScope 凭据；JWT 密钥轮换会使现有 token 失效，应安排维护窗口。
- 监控 `/health`、`/health/db`、容器重启次数、磁盘/卷容量、MySQL 连接数、LLM 延迟和错误率，并为日志设置外部采集与脱敏。
- 未接入真实支付网关前保持 `WALLET_RECHARGE_MODE=disabled`。
