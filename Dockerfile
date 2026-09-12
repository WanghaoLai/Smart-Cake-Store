# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm AS wheels

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY fastapi-app/requirements.txt /tmp/requirements.txt
RUN python -m pip wheel --wheel-dir=/wheels -r /tmp/requirements.txt


FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    XDG_CACHE_HOME=/tmp/.cache \
    PATH=/home/app/.local/bin:${PATH}

# tzdata: common/time.py 与 agents/tools/business.py 在 import 时调用
# ZoneInfo(APP_TIMEZONE)，镜像缺时区数据库会导致 API 启动即崩
RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 tini tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY --from=wheels /wheels /wheels
COPY fastapi-app/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-index --find-links=/wheels -r /tmp/requirements.txt \
    && rm -rf /wheels /tmp/requirements.txt

WORKDIR /app
COPY --chown=app:app fastapi-app/ /app/

# files/ contains versioned seed images and runtime uploads. A new named volume
# mounted here is populated from this directory by Docker on first use.
RUN rm -rf /app/.env /app/.venv /app/chroma_db \
    && mkdir -p /app/files/review /app/chroma_db \
    && chown -R app:app /app/files /app/chroma_db

USER app
EXPOSE 9090

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9090/health/db', timeout=3)"]

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9090", "--workers", "1"]


# The migration target is deliberately separate so the API image does not
# carry a MySQL CLI. Compose runs this target once before starting the API.
FROM runtime AS migrator

USER root
RUN apt-get update \
    && apt-get install --no-install-recommends -y default-mysql-client \
    && rm -rf /var/lib/apt/lists/*
COPY --chown=app:app db/ /workspace/db/
RUN chmod 0755 /workspace/db/migrate.sh
WORKDIR /workspace
USER app
HEALTHCHECK NONE
ENTRYPOINT ["tini", "--"]
CMD ["/workspace/db/migrate.sh"]
