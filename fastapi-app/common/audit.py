"""敏感操作审计。

资金和权限变更使用 ``record_audit_required``，由调用方传入业务事务连接，
保证业务结果与审计记录同时提交或同时回滚。非关键操作可继续使用
``record_audit``：审计失败只记录服务器日志，不阻塞主体业务。"""
import logging
from typing import Any

from fastapi import Request

from models import AuditLog
from settings import TRUST_PROXY_HEADERS

logger = logging.getLogger(__name__)


def client_ip(request: Request | None) -> str | None:
    """不盲信 X-Forwarded-For：只有在反向代理层明确覆盖该头时才应使用。"""
    if request is None:
        return None
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else None


async def record_audit(
    operator: dict,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    """记录一条审计日志。任何异常只进 logger，不影响调用方返回值。"""
    try:
        await AuditLog.create(
            operator_role=operator.get("role", "系统"),
            operator_id=operator.get("user_id", 0),
            operator_name=operator.get("username"),
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            ip=ip,
        )
    except Exception:
        logger.exception(
            "audit write failed action=%s operator=%s target=%s/%s",
            action, operator.get("username"), target_type, target_id,
        )


async def record_audit_required(
    operator: dict,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
    ip: str | None = None,
    *,
    using_db: Any = None,
) -> None:
    """写入必须完整留痕的审计记录；失败时交由业务事务统一回滚。"""
    await AuditLog.create(
        operator_role=operator.get("role", "系统"),
        operator_id=operator.get("user_id", 0),
        operator_name=operator.get("username"),
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip=ip,
        using_db=using_db,
    )
