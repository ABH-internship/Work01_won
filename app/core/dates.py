from datetime import date

from app.core.config import settings


def default_base_date() -> date:
    return settings.base_date
