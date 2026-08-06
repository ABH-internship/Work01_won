from datetime import date
from random import uniform

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dates import default_base_date, default_base_datetime
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.screens import (
    AiInspectionItem,
    AiInspectionSummary,
    MockAiInspectionData,
    MockAiInspectionInput,
    MockAiInspectionResponse,
    TestRecordItem,
    TraceResponse,
)
from app.services.insert import insert_id
from app.services.read import fetch_all, fetch_one

router = APIRouter(tags=["quality"])


@router.get("/ai-inspections/summary", response_model=AiInspectionSummary)
def get_ai_inspection_summary(
    base_date: date = Query(default_factory=default_base_date),
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
          ROUND(AVG(confidence) FILTER (WHERE CAST(inspected_at AS date) = CAST(:base_date AS date)), 2) AS average_confidence,
          COALESCE(
            ROUND(AVG(read_seconds) FILTER (WHERE CAST(inspected_at AS date) = CAST(:base_date AS date)), 2),
            0
          ) AS average_read_seconds
        FROM ai_inspections
        """,
        {"base_date": base_date},
    )


@router.post("/ai-inspections/mock", status_code=status.HTTP_201_CREATED, response_model=MockAiInspectionResponse)
def run_mock_ai_inspection(payload: MockAiInspectionInput, db: Session = Depends(get_db)) -> MockAiInspectionResponse:
    unit = fetch_one(db, "SELECT id FROM units WHERE unit_no = :unit_no", {"unit_no": payload.unit_no})
    read_seconds = round(uniform(1.5, 2.0), 1)
    response = insert_id(
        db,
        """
        INSERT INTO ai_inspections (unit_id, inspection_type, result, confidence, finding, read_seconds, inspected_at)
        VALUES (:unit_id, :inspection_type, :result, :confidence, :finding, :read_seconds, :inspected_at)
        RETURNING id
        """,
        {
            "unit_id": unit["id"],
            "inspection_type": payload.inspection_type,
            "result": payload.result,
            "confidence": payload.confidence,
            "finding": payload.finding,
            "read_seconds": read_seconds,
            "inspected_at": default_base_datetime(),
        },
        "Mock AI 검사 결과가 저장되었습니다.",
    )
    return MockAiInspectionResponse(
        code=response.code,
        message=response.message,
        data=MockAiInspectionData(id=response.data.id, read_seconds=read_seconds),
    )


@router.get("/ai-inspections/units/{unit_no}", response_model=list[AiInspectionItem])
def get_unit_ai_inspections(unit_no: str, db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT
          ai.id,
          u.unit_no,
          ai.inspection_type,
          ai.result,
          ai.confidence,
          ai.finding,
          ai.read_seconds,
          ai.inspected_at
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


def build_unit_trace(unit_no: str, db: Session) -> dict:
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
    base["timeline"] = fetch_all(
        db,
        """
        SELECT occurred_at, event_type, title, message, severity, status_label
        FROM (
          SELECT
            COALESCE(
              (
                SELECT MIN(up.started_at) - INTERVAL '2 days'
                FROM unit_processes up
                JOIN units ux ON ux.id = up.unit_id
                WHERE ux.unit_no = :unit_no
              ),
              o.created_at
            ) AS occurred_at,
            '수주' AS event_type,
            '수주 등록' AS title,
            o.item_name || ' ' || o.quantity || '면 · 납기 ' || o.due_date AS message,
            'info' AS severity,
            '등록' AS status_label
          FROM units u
          JOIN orders o ON o.id = u.order_id
          WHERE u.unit_no = :unit_no

          UNION ALL

          SELECT
            COALESCE(
              (
                SELECT MIN(up.started_at) - INTERVAL '1 day'
                FROM unit_processes up
                JOIN units ux ON ux.id = up.unit_id
                WHERE ux.unit_no = :unit_no
              ),
              u.created_at
            ) AS occurred_at,
            '호기' AS event_type,
            '호기 등록' AS title,
            u.unit_no || COALESCE(' · ' || u.item_detail, '') AS message,
            'info' AS severity,
            '등록' AS status_label
          FROM units u
          WHERE u.unit_no = :unit_no

          UNION ALL

          SELECT
            COALESCE(
              (
                SELECT MIN(up.started_at) - INTERVAL '12 hours'
                FROM unit_processes up
                JOIN units ux ON ux.id = up.unit_id
                WHERE ux.unit_no = :unit_no
              ),
              o.created_at
            ) AS occurred_at,
            '자재' AS event_type,
            '자재 LOT 배정' AS title,
            m.name || ' ' || om.required_quantity || m.unit || COALESCE(' · LOT ' || i.lot_no, '') AS message,
            'info' AS severity,
            '배정' AS status_label
          FROM order_materials om
          JOIN units u ON u.order_id = om.order_id
          JOIN orders o ON o.id = u.order_id
          JOIN materials m ON m.id = om.material_id
          LEFT JOIN inventories i ON i.id = om.inventory_id
          WHERE u.unit_no = :unit_no

          UNION ALL

          SELECT
            up.started_at AS occurred_at,
            '공정' AS event_type,
            pm.name || ' 시작' AS title,
            u.unit_no || ' · ' || pm.name || ' 공정 시작' AS message,
            CASE WHEN up.status = '지연주의' THEN 'warning' ELSE 'info' END AS severity,
            CASE WHEN up.status = '지연주의' THEN '지연' ELSE '진행중' END AS status_label
          FROM unit_processes up
          JOIN units u ON u.id = up.unit_id
          JOIN process_masters pm ON pm.id = up.process_master_id
          WHERE u.unit_no = :unit_no
            AND up.started_at IS NOT NULL

          UNION ALL

          SELECT
            up.completed_at AS occurred_at,
            '공정' AS event_type,
            pm.name || ' 완료' AS title,
            pm.name || ' 완료' || COALESCE(' · 실적 ' || up.result_quantity, '') AS message,
            CASE WHEN up.is_rework THEN 'warning' ELSE 'info' END AS severity,
            CASE WHEN up.is_rework THEN '재작업' ELSE '완료' END AS status_label
          FROM unit_processes up
          JOIN units u ON u.id = up.unit_id
          JOIN process_masters pm ON pm.id = up.process_master_id
          WHERE u.unit_no = :unit_no
            AND up.completed_at IS NOT NULL

          UNION ALL

          SELECT
            ai.inspected_at AS occurred_at,
            '검사' AS event_type,
            'AI ' || ai.inspection_type || ' ' || ai.result AS title,
            COALESCE(ai.finding, '특이사항 없음') AS message,
            CASE WHEN ai.result = 'FAIL' THEN 'error' ELSE 'info' END AS severity,
            ai.result AS status_label
          FROM ai_inspections ai
          JOIN units u ON u.id = ai.unit_id
          WHERE u.unit_no = :unit_no

          UNION ALL

          SELECT
            t.tested_at AS occurred_at,
            '시험' AS event_type,
            t.test_item || ' ' || t.result AS title,
            t.measured_value || ' · 기준 ' || t.criteria || ' · 시험자 ' || t.tester AS message,
            CASE WHEN t.result = 'FAIL' THEN 'error' ELSE 'info' END AS severity,
            t.result AS status_label
          FROM tests t
          JOIN units u ON u.id = t.unit_id
          WHERE u.unit_no = :unit_no

          UNION ALL

          SELECT
            e.occurred_at AS occurred_at,
            e.event_type,
            e.event_type AS title,
            e.message,
            e.severity,
            CASE
              WHEN e.severity = 'error' THEN '실패'
              WHEN e.severity = 'warning' THEN '지연'
              ELSE '완료'
            END AS status_label
          FROM events e
          JOIN units u ON u.id = e.unit_id
          WHERE u.unit_no = :unit_no
        ) timeline
        WHERE occurred_at IS NOT NULL
        ORDER BY occurred_at, event_type, title
        """,
        params,
    )
    del base["unit_id"]
    return base


@router.get("/trace/{unit_no}", response_model=TraceResponse)
def get_trace(unit_no: str, db: Session = Depends(get_db)) -> dict:
    return build_unit_trace(unit_no, db)


@router.get("/trace/orders/{order_id}", response_model=list[TraceResponse])
def get_order_trace(order_id: int, db: Session = Depends(get_db)) -> list[dict]:
    units = fetch_all(
        db,
        """
        SELECT unit_no
        FROM units
        WHERE order_id = :order_id
        ORDER BY unit_no
        """,
        {"order_id": order_id},
    )
    return [build_unit_trace(row["unit_no"], db) for row in units]
