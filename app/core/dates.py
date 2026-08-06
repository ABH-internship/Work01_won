from datetime import date, datetime

from app.core.config import settings


def default_base_date() -> date:
    return settings.base_date


def default_base_datetime() -> datetime:
    return datetime.combine(settings.base_date, datetime.now().time().replace(microsecond=0))
