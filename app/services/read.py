from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session


def fetch_all(db: Session, sql: str, values: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), values or {}).mappings().all()]


def fetch_one(db: Session, sql: str, values: dict[str, Any] | None = None) -> dict[str, Any]:
    row = db.execute(text(sql), values or {}).mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "조회 결과가 없습니다."},
        )
    return dict(row)
