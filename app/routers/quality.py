from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.screens import (
    AiInspectionItem,
    AiInspectionSummary,
    MockAiInspectionInput,
    TestRecordItem,
    TraceResponse,
)
from app.services.insert import insert_id
from app.services.read import fetch_all, fetch_one

router = APIRouter(tags=["quality"])


@router.get("/ai-inspections/summary", response_model=AiInspectionSummary)
def get_ai_inspection_summary(
    base_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> dict:
    return fetch_one(
        db,
        """
        SELECT
          CAST(COUNT(*) FILTER (WHERE CAST(inspected_at AS date) = CAST(:base_date AS date)) AS integer) AS today_count,
          CAST(COUNT(*) FILTER (
            WHERE CAST(inspected_at AS date) = CAST(:base_date AS date) AND result = 'FAIL'
          ) AS integer) AS detection_count,
          ROUND(AVG(confidence) FILTER (WHERE CAST(inspected_at AS date) = CAST(:base_date AS date)), 2) AS average_confidence
        FROM ai_inspections
        """,
        {"base_date": base_date},
    )


@router.post("/ai-inspections/mock", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def run_mock_ai_inspection(payload: MockAiInspectionInput, db: Session = Depends(get_db)) -> ApiResponse:
    unit = fetch_one(db, "SELECT id FROM units WHERE unit_no = :unit_no", {"unit_no": payload.unit_no})
    return insert_id(
        db,
        """
        INSERT INTO ai_inspections (unit_id, inspection_type, result, confidence, finding)
        VALUES (:unit_id, :inspection_type, :result, :confidence, :finding)
        RETURNING id
        """,
        {
            "unit_id": unit["id"],
            "inspection_type": payload.inspection_type,
            "result": payload.result,
            "confidence": payload.confidence,
            "finding": payload.finding,
        },
        "Mock AI 검사 결과가 저장되었습니다.",
    )


@router.get("/ai-inspections/units/{unit_no}", response_model=list[AiInspectionItem])
def get_unit_ai_inspections(unit_no: str, db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT ai.id, u.unit_no, ai.inspection_type, ai.result, ai.confidence, ai.finding, ai.inspected_at
        FROM ai_inspections ai
        JOIN units u ON u.id = ai.unit_id
        WHERE u.unit_no = :unit_no
        ORDER BY ai.inspected_at DESC
        """,
        {"unit_no": unit_no},
    )


@router.get("/tests", response_model=list[TestRecordItem])
def get_tests(limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT t.id, u.unit_no, t.test_item, t.measured_value, t.criteria, t.result, t.tester, t.tested_at
        FROM tests t
        JOIN units u ON u.id = t.unit_id
        ORDER BY t.tested_at DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


@router.get("/tests/units/{unit_no}", response_model=list[TestRecordItem])
def get_unit_tests(unit_no: str, db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT t.id, u.unit_no, t.test_item, t.measured_value, t.criteria, t.result, t.tester, t.tested_at
        FROM tests t
        JOIN units u ON u.id = t.unit_id
        WHERE u.unit_no = :unit_no
        ORDER BY t.tested_at DESC
        """,
        {"unit_no": unit_no},
    )


@router.get("/trace/{unit_no}", response_model=TraceResponse)
def get_trace(unit_no: str, db: Session = Depends(get_db)) -> dict:
    base = fetch_one(
        db,
        """
        SELECT u.id AS unit_id, u.unit_no, o.item_name, c.name AS customer_name, o.due_date
        FROM units u
        JOIN orders o ON o.id = u.order_id
        JOIN customers c ON c.id = o.customer_id
        WHERE u.unit_no = :unit_no
        """,
        {"unit_no": unit_no},
    )

    params = {"unit_no": unit_no}
    base["processes"] = fetch_all(
        db,
        """
        SELECT pm.name AS process_name, up.status, up.started_at, up.completed_at
        FROM unit_processes up
        JOIN units u ON u.id = up.unit_id
        JOIN process_masters pm ON pm.id = up.process_master_id
        WHERE u.unit_no = :unit_no
        ORDER BY pm.sequence
        """,
        params,
    )
    base["materials"] = fetch_all(
        db,
        """
        SELECT m.name AS material_name, om.required_quantity, m.unit, i.lot_no
        FROM order_materials om
        JOIN units u ON u.order_id = om.order_id
        JOIN materials m ON m.id = om.material_id
        LEFT JOIN inventories i ON i.id = om.inventory_id
        WHERE u.unit_no = :unit_no
        ORDER BY m.name
        """,
        params,
    )
    base["inspections"] = get_unit_ai_inspections(unit_no, db)
    base["tests"] = get_unit_tests(unit_no, db)
    del base["unit_id"]
    return base
