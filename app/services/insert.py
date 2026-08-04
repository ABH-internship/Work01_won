from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemas.common import ApiResponse, IdData


def integrity_error_response(error: IntegrityError) -> HTTPException:
    sqlstate = getattr(error.orig, "sqlstate", None)

    if sqlstate == "23505":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_VALUE", "message": "이미 등록된 값입니다."},
        )

    if sqlstate in {"23503", "23514"}:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "입력값의 관계 또는 범위를 확인해 주세요."},
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "INVALID_INPUT", "message": "입력값을 확인해 주세요."},
    )


def insert_id(db: Session, sql: str, values: dict[str, Any], message: str) -> ApiResponse:
    try:
        result = db.execute(text(sql), values).one()
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise integrity_error_response(error) from error

    return ApiResponse(code="CREATED", message=message, data=IdData(id=result.id))


def validate_order_material_inventory(db: Session, values: dict[str, Any]) -> None:
    inventory_id = values.get("inventory_id")
    if inventory_id is None:
        return

    row = db.execute(
        text("SELECT material_id FROM inventories WHERE id = :inventory_id"),
        {"inventory_id": inventory_id},
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "존재하지 않는 재고입니다."},
        )

    if row["material_id"] != values["material_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "선택한 재고의 자재가 요청 자재와 일치하지 않습니다."},
        )
