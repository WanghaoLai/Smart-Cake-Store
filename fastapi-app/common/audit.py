"""敏感操作审计：best-effort 落库，失败仅记日志、绝不阻塞业务。

设计权衡（roadmap 改进项 4）：审计与业务同事务可保证强一致，但任何
审计写入异常都会回滚业务操作——对"重置密码成功却报错给管理员"这种
体验损伤，换取的是一条大概率永不缺失的日志。选择业务成功后独立写入：
两者都是简单 INSERT，失败概率极低；审计万一缺失时有服务器日志兜底。"""
import logging

from fastapi import Request

from models import AuditLog

logger = logging.getLogger(__name__)


def client_ip(request: Request | None) -> str | None:
    """不盲信 X-Forwarded-For：只有在反向代理层明确覆盖该头时才应使用。"""
    if request is None:
        return None
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
