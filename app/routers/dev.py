from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/reset", response_model=MessageResponse)
def reset_database(db: Session = Depends(get_db)) -> MessageResponse:
    if settings.app_env.lower() != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "개발 환경에서만 실행할 수 있습니다."},
        )

    try:
        db.execute(
            text(
                """
                TRUNCATE
                  events,
                  tests,
                  ai_inspections,
                  quote_materials,
                  order_materials,
                  inventories,
                  unit_processes,
                  units,
                  process_masters,
                  materials,
                  orders,
                  quotes,
                  customers
                RESTART IDENTITY CASCADE
                """
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return MessageResponse(code="RESET", message="개발 데이터가 초기화되었습니다.")
