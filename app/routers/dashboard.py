from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.screens import DashboardSummary, EventItem, ProcessLineItem, WeeklyOutputItem
from app.services.read import fetch_all, fetch_one

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
events_router = APIRouter(prefix="/events", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    base_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> dict:
    return fetch_one(
        db,
        """
        WITH process_stats AS (
          SELECT
            CAST(COALESCE(SUM(result_quantity) FILTER (WHERE CAST(completed_at AS date) = :base_date), 0) AS integer)
              AS today_process_results,
            CAST(COUNT(id) FILTER (
              WHERE is_rework = true
                AND CAST(completed_at AS date) BETWEEN CAST(:base_date AS date) - INTERVAL '6 days' AND CAST(:base_date AS date)
            ) AS integer) AS weekly_reworks
          FROM unit_processes
        ),
        unit_completion AS (
          SELECT u.id, u.status, o.due_date, MAX(up.completed_at) AS completed_at
          FROM units u
          JOIN orders o ON o.id = u.order_id
          LEFT JOIN unit_processes up ON up.unit_id = u.id
          GROUP BY u.id, u.status, o.due_date
        )
        SELECT
          ps.today_process_results,
          CAST(COUNT(uc.id) FILTER (WHERE uc.status <> '완료') AS integer) AS active_units,
          COALESCE(
            ROUND(
              100.0 * COUNT(uc.id) FILTER (WHERE uc.status = '완료' AND CAST(uc.completed_at AS date) <= uc.due_date)
              / NULLIF(COUNT(uc.id) FILTER (WHERE uc.status = '완료'), 0),
              1
            ),
            0
          ) AS on_time_rate,
          ps.weekly_reworks
        FROM process_stats ps
        LEFT JOIN unit_completion uc ON true
        GROUP BY ps.today_process_results, ps.weekly_reworks
        """,
        {"base_date": base_date},
    )


@router.get("/process-line", response_model=list[ProcessLineItem])
def get_process_line(db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT
          pm.name AS process_name,
          CAST(COUNT(up.id) FILTER (WHERE up.status = '완료') AS integer) AS completed_count,
          CAST(COUNT(up.id) FILTER (WHERE up.status = '진행중') AS integer) AS running_count,
          CAST(COUNT(up.id) FILTER (WHERE up.status = '지연주의') AS integer) AS warning_count
        FROM process_masters pm
        LEFT JOIN unit_processes up ON up.process_master_id = pm.id
        GROUP BY pm.id, pm.name, pm.sequence
        ORDER BY pm.sequence
        """,
    )


@router.get("/weekly-output", response_model=list[WeeklyOutputItem])
def get_weekly_output(
    base_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT
          CAST(d AS date) AS work_date,
          CAST(COALESCE(SUM(up.result_quantity), 0) AS integer) AS completed_count
        FROM generate_series(CAST(:base_date AS date) - INTERVAL '6 days', CAST(:base_date AS date), INTERVAL '1 day') d
        LEFT JOIN unit_processes up ON CAST(up.completed_at AS date) = CAST(d AS date)
        GROUP BY d
        ORDER BY d
        """,
        {"base_date": base_date},
    )


@events_router.get("/recent", response_model=list[EventItem])
def get_recent_events(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT e.id, u.unit_no, e.event_type, e.message, e.severity, e.occurred_at
        FROM events e
        LEFT JOIN units u ON u.id = e.unit_id
        ORDER BY e.occurred_at DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )
