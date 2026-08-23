"""UTC persistence and explicit store-time presentation helpers."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from settings import APP_TIMEZONE


STORE_TIMEZONE = ZoneInfo(APP_TIMEZONE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_store_time(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(STORE_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


__all__ = ["STORE_TIMEZONE", "format_store_time", "utc_now"]
