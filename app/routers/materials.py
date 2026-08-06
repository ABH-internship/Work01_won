from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dates import default_base_date
from app.db.session import get_db
from app.schemas.screens import InventoryItem, MaterialRequirementItem
from app.services.read import fetch_all

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("/requirements", response_model=list[MaterialRequirementItem])
def get_material_requirements(
    base_date: date = Query(default_factory=default_base_date),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = fetch_all(
        db,
        """
        WITH stock AS (
          SELECT material_id, COALESCE(SUM(current_quantity), 0) AS current_quantity
          FROM inventories
          GROUP BY material_id
        ),
        required AS (
          SELECT
            material_id,
            SUM(confirmed_quantity) AS confirmed_required_quantity,
            SUM(forecast_quantity) AS forecast_required_quantity,
            SUM(confirmed_quantity + forecast_quantity) AS required_quantity_2weeks
          FROM (
            SELECT
              om.material_id,
              om.required_quantity AS confirmed_quantity,
              0::numeric AS forecast_quantity
            FROM order_materials om
            JOIN orders o ON o.id = om.order_id
            WHERE o.status <> '완료'
              AND o.due_date BETWEEN CAST(:base_date AS date) AND CAST(:base_date AS date) + INTERVAL '14 days'

            UNION ALL

            SELECT
              qm.material_id,
              0::numeric AS confirmed_quantity,
              qm.required_quantity * q.probability AS forecast_quantity
            FROM quote_materials qm
            JOIN quotes q ON q.id = qm.quote_id
            WHERE q.status = '진행중'
              AND q.expected_due_date BETWEEN CAST(:base_date AS date) AND CAST(:base_date AS date) + INTERVAL '14 days'
              AND NOT EXISTS (
                SELECT 1 FROM orders o WHERE o.quote_id = q.id
              )
          ) forecast
          GROUP BY material_id
        )
        SELECT
          m.id AS material_id,
          m.name AS material_name,
          m.unit,
          COALESCE(s.current_quantity, 0) AS current_quantity,
          COALESCE(r.required_quantity_2weeks, 0) AS required_quantity_2weeks,
          GREATEST(COALESCE(r.required_quantity_2weeks, 0) - COALESCE(s.current_quantity, 0), 0) AS shortage_quantity,
          CASE
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.confirmed_required_quantity, 0) THEN '결품 경보'
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.required_quantity_2weeks, 0) THEN '발주 권고'
            ELSE '충분'
          END AS judgement,
          CASE
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.confirmed_required_quantity, 0)
              THEN '리드타임 ' || m.lead_time_days || '일, 금일 발주 필요'
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.required_quantity_2weeks, 0)
              THEN '다음 작업 전 발주 권고 (리드타임 ' || m.lead_time_days || '일)'
            ELSE '-'
          END AS suggestion,
          CASE
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.confirmed_required_quantity, 0) THEN 'error'
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.required_quantity_2weeks, 0) THEN 'warning'
            ELSE 'info'
          END AS severity,
          CASE
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.confirmed_required_quantity, 0)
              THEN '결품 경보 — 리드타임 ' || m.lead_time_days || '일, 금일 발주 필요'
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.required_quantity_2weeks, 0)
              THEN '발주 권고 — 다음 작업 전 ' ||
                   ROUND(GREATEST(COALESCE(r.required_quantity_2weeks, 0) - COALESCE(s.current_quantity, 0), 0), 1) ||
                   m.unit || ' 보충 권고'
            ELSE '충분'
          END AS message
        FROM materials m
        LEFT JOIN stock s ON s.material_id = m.id
        LEFT JOIN required r ON r.material_id = m.id
        ORDER BY
          CASE
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.confirmed_required_quantity, 0) THEN 1
            WHEN COALESCE(s.current_quantity, 0) < COALESCE(r.required_quantity_2weeks, 0) THEN 2
            ELSE 3
          END,
          shortage_quantity DESC,
          required_quantity_2weeks DESC,
          m.name
        """,
        {"base_date": base_date},
    )
    return rows


@router.get("/inventories", response_model=list[InventoryItem])
def get_inventories(db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT
          i.id,
          m.name AS material_name,
          m.unit,
          i.lot_no,
          i.purchased_quantity,
          i.current_quantity,
          i.received_at
        FROM inventories i
        JOIN materials m ON m.id = i.material_id
        ORDER BY m.name, i.received_at DESC
        """,
    )
