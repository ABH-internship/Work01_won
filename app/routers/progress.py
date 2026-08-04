from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.screens import DueRisk, ProgressUnitItem
from app.services.read import fetch_all, fetch_one

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/units", response_model=list[ProgressUnitItem])
def get_progress_units(
    base_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> list[dict]:
    return fetch_all(
        db,
        """
        WITH progress AS (
          SELECT
            u.id AS unit_id,
            ROUND(
              100.0 * COUNT(up.id) FILTER (WHERE up.status = '완료') / NULLIF(COUNT(up.id), 0),
              1
            ) AS progress_rate
          FROM units u
          LEFT JOIN unit_processes up ON up.unit_id = u.id
          GROUP BY u.id
        ),
        next_process AS (
          SELECT DISTINCT ON (u.id)
            u.id AS unit_id,
            CASE
              WHEN u.status = '자재발주중' THEN '설계 확정'
              ELSE pm.name
            END AS process_name
          FROM units u
          JOIN unit_processes up ON up.unit_id = u.id
          JOIN process_masters pm ON pm.id = up.process_master_id
          WHERE u.status <> '완료'
            AND up.status <> '완료'
          ORDER BY u.id, pm.sequence
        ),
        last_process AS (
          SELECT DISTINCT ON (u.id)
            u.id AS unit_id,
            pm.name AS process_name
          FROM units u
          JOIN unit_processes up ON up.unit_id = u.id
          JOIN process_masters pm ON pm.id = up.process_master_id
          WHERE u.status = '완료'
            AND up.status = '완료'
          ORDER BY u.id, pm.sequence DESC
        )
        SELECT
          u.unit_no,
          o.item_name,
          c.name AS customer_name,
          o.due_date,
          CAST(o.due_date - CAST(:base_date AS date) AS integer) AS days_until_due,
          COALESCE(p.progress_rate, 0) AS progress_rate,
          COALESCE(np.process_name, lp.process_name) AS current_process,
          u.status
        FROM units u
        JOIN orders o ON o.id = u.order_id
        JOIN customers c ON c.id = o.customer_id
        LEFT JOIN progress p ON p.unit_id = u.id
        LEFT JOIN next_process np ON np.unit_id = u.id
        LEFT JOIN last_process lp ON lp.unit_id = u.id
        ORDER BY o.due_date, u.unit_no
        """,
        {"base_date": base_date},
    )


@router.get("/due-risk/{unit_no}", response_model=DueRisk)
def get_due_risk(
    unit_no: str,
    base_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> dict:
    row = fetch_one(
        db,
        """
        SELECT
          u.unit_no,
          o.due_date,
          COALESCE(SUM(pm.standard_days) FILTER (WHERE up.status <> '완료'), 0) AS remaining_standard_days,
          (o.due_date - CAST(:base_date AS date)) AS days_until_due
        FROM units u
        JOIN orders o ON o.id = u.order_id
        LEFT JOIN unit_processes up ON up.unit_id = u.id
        LEFT JOIN process_masters pm ON pm.id = up.process_master_id
        WHERE u.unit_no = :unit_no
        GROUP BY u.id, u.unit_no, o.due_date
        """,
        {"unit_no": unit_no, "base_date": base_date},
    )

    safety_buffer_days = 1
    required_days = row["remaining_standard_days"] + safety_buffer_days
    buffer_days = row["days_until_due"] - required_days
    row["safety_buffer_days"] = safety_buffer_days
    row["buffer_days"] = buffer_days
    row["status"] = "지연위험" if buffer_days < 1 else "정상"
    row["message"] = (
        f"잔여 표준 {row['remaining_standard_days']}일 + 여유 {safety_buffer_days}일, "
        f"납기까지 {row['days_until_due']}일 남았습니다."
    )
    return row
