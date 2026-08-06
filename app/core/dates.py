from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

KST = ZoneInfo("Asia/Seoul")


def default_base_date() -> date:
    return settings.base_date


def default_base_datetime() -> datetime:
    now = datetime.now(KST)
    return datetime.combine(settings.base_date, now.time().replace(microsecond=0), tzinfo=KST)
