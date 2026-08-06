from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dates import default_base_date
from app.db.session import get_db
from app.schemas.screens import (
    DashboardSummary,
    EquipmentUtilization,
    EventItem,
    ProcessLineItem,
    WeeklyOutputItem,
)
from app.services.read import fetch_all, fetch_one

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
events_router = APIRouter(prefix="/events", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    base_date: date = Query(default_factory=default_base_date),
    db: Session = Depends(get_db),
) -> dict:
    return fetch_one(
        db,
        """
        WITH process_stats AS (
          SELECT
            CAST(COALESCE(SUM(result_quantity) FILTER (WHERE CAST(completed_at AS date) = :base_date), 0) AS integer)
              AS today_process_results,
            CAST(COALESCE(SUM(result_quantity) FILTER (WHERE CAST(completed_at AS date) = CAST(:base_date AS date) - INTERVAL '1 day'), 0) AS integer)
              AS yesterday_process_results,
            CAST(COUNT(id) FILTER (
              WHERE is_rework = true
                AND CAST(completed_at AS date) BETWEEN CAST(:base_date AS date) - INTERVAL '6 days' AND CAST(:base_date AS date)
            ) AS integer) AS weekly_reworks
          FROM unit_processes
        ),
        rework_summary AS (
          SELECT STRING_AGG(name || ' ' || count, ' · ' ORDER BY count DESC, name) AS summary
          FROM (
            SELECT pm.name, COUNT(*) AS count
            FROM unit_processes up
            JOIN process_masters pm ON pm.id = up.process_master_id
            WHERE up.is_rework = true
              AND CAST(up.completed_at AS date) BETWEEN CAST(:base_date AS date) - INTERVAL '6 days' AND CAST(:base_date AS date)
            GROUP BY pm.name
            ORDER BY COUNT(*) DESC, pm.name
            LIMIT 2
          ) ranked
        ),
        unit_completion AS (
          SELECT u.id, u.status, o.due_date, MAX(up.completed_at) AS completed_at
          FROM units u
          JOIN orders o ON o.id = u.order_id
          LEFT JOIN unit_processes up ON up.unit_id = u.id
          GROUP BY u.id, u.status, o.due_date
        ),
        rates AS (
          SELECT
            COALESCE(
              ROUND(
                100.0 * COUNT(id) FILTER (
                  WHERE status = '완료'
                    AND completed_at IS NOT NULL
                    AND CAST(completed_at AS date) <= due_date
                    AND due_date >= date_trunc('month', CAST(:base_date AS date))::date
                    AND due_date < (date_trunc('month', CAST(:base_date AS date)) + INTERVAL '1 month')::date
                )
                / NULLIF(COUNT(id) FILTER (
                  WHERE status = '완료'
                    AND due_date >= date_trunc('month', CAST(:base_date AS date))::date
                    AND due_date < (date_trunc('month', CAST(:base_date AS date)) + INTERVAL '1 month')::date
                ), 0),
                1
              ),
              0
            ) AS current_month_on_time_rate,
            COALESCE(
              ROUND(
                100.0 * COUNT(id) FILTER (
                  WHERE status = '완료'
                    AND completed_at IS NOT NULL
                    AND CAST(completed_at AS date) <= due_date
                    AND due_date >= (date_trunc('month', CAST(:base_date AS date)) - INTERVAL '1 month')::date
                    AND due_date < date_trunc('month', CAST(:base_date AS date))::date
                )
                / NULLIF(COUNT(id) FILTER (
                  WHERE status = '완료'
                    AND due_date >= (date_trunc('month', CAST(:base_date AS date)) - INTERVAL '1 month')::date
                    AND due_date < date_trunc('month', CAST(:base_date AS date))::date
                ), 0),
                1
              ),
              0
            ) AS previous_month_on_time_rate
          FROM unit_completion
        )
        SELECT
          ps.today_process_results,
          CASE
            WHEN ps.today_process_results > ps.yesterday_process_results
              THEN '전일 대비 +' || (ps.today_process_results - ps.yesterday_process_results)
            WHEN ps.today_process_results < ps.yesterday_process_results
              THEN '전일 대비 -' || (ps.yesterday_process_results - ps.today_process_results)
            ELSE '전일과 동일'
          END AS today_process_message,
          CAST(COUNT(uc.id) FILTER (WHERE uc.status <> '완료') AS integer) AS active_units,
          CAST(COUNT(uc.id) FILTER (
            WHERE uc.status <> '완료'
              AND uc.due_date BETWEEN CAST(:base_date AS date) AND CAST(:base_date AS date) + INTERVAL '7 days'
          ) AS integer) AS due_soon_units,
          rates.current_month_on_time_rate AS on_time_rate,
          rates.previous_month_on_time_rate,
          rates.current_month_on_time_rate - rates.previous_month_on_time_rate AS on_time_rate_delta,
          ps.weekly_reworks,
          COALESCE(rs.summary, '-') AS weekly_rework_summary
        FROM process_stats ps
        CROSS JOIN rates
        LEFT JOIN rework_summary rs ON true
        LEFT JOIN unit_completion uc ON true
        GROUP BY
          ps.today_process_results,
          ps.yesterday_process_results,
          ps.weekly_reworks,
          rs.summary,
          rates.current_month_on_time_rate,
          rates.previous_month_on_time_rate
        """,
        {"base_date": base_date},
    )


@router.get("/equipment-utilization", response_model=EquipmentUtilization)
def get_equipment_utilization(
    base_date: date = Query(default_factory=default_base_date),
    db: Session = Depends(get_db),
) -> dict:
    row = fetch_one(
        db,
        """
        WITH bending AS (
          SELECT up.*
          FROM unit_processes up
          JOIN process_masters pm ON pm.id = up.process_master_id
          WHERE pm.name = '판금·절곡'
        ),
        today_targets AS (
          SELECT b.*
          FROM bending b
          WHERE b.status IN ('진행중', '지연주의')
             OR CAST(b.completed_at AS date) = CAST(:base_date AS date)
             OR (
               b.status = '대기'
               AND NOT EXISTS (
                 SELECT 1
                 FROM unit_processes prev
                 JOIN process_masters prev_pm ON prev_pm.id = prev.process_master_id
                 JOIN process_masters cur_pm ON cur_pm.id = b.process_master_id
                 WHERE prev.unit_id = b.unit_id
                   AND prev_pm.sequence < cur_pm.sequence
                   AND prev.status <> '완료'
               )
             )
        )
        SELECT
          CAST(COUNT(*) FILTER (
            WHERE status IN ('진행중', '지연주의')
               OR CAST(completed_at AS date) = CAST(:base_date AS date)
          ) AS integer) AS active_count,
          CAST(COUNT(*) AS integer) AS total_count
        FROM today_targets
        """,
        {"base_date": base_date},
    )
    active_count = row["active_count"]
    total_count = row["total_count"]
    utilization_rate = round(active_count / total_count * 100, 1) if total_count else 0

    return {
        "utilization_rate": utilization_rate,
        "equipments": [
            {
                "name": "판금·절곡",
                "active_count": active_count,
                "total_count": total_count,
                "utilization_rate": utilization_rate,
            }
        ],
    }


@router.get("/process-line", response_model=list[ProcessLineItem])
def get_process_line(db: Session = Depends(get_db)) -> list[dict]:
    return fetch_all(
        db,
        """
        WITH display_groups AS (
          SELECT *
          FROM (VALUES
            (1, '판금·절곡'),
            (2, '도장'),
            (3, '부스바·조립'),
            (4, '배선'),
            (5, '검사·시험')
          ) AS groups(sequence, name)
        ),
        current_process AS (
          SELECT DISTINCT ON (u.id)
            u.id AS unit_id,
            u.unit_no,
            u.status AS unit_status,
            CASE
              WHEN u.status = '자재발주중' THEN '설계 확정'
              WHEN pm.name = '판금/조립' THEN '판금·절곡'
              WHEN pm.name IN ('검사', '시험') THEN '검사·시험'
              ELSE pm.name
            END AS process_name,
            CASE
              WHEN u.status = '지연주의' THEN '지연주의'
              WHEN u.status = '자재발주중' THEN '진행중'
              ELSE up.status
            END AS process_status
          FROM units u
          JOIN unit_processes up ON up.unit_id = u.id
          JOIN process_masters pm ON pm.id = up.process_master_id
          WHERE u.status <> '완료'
            AND up.status <> '완료'
          ORDER BY u.id, pm.sequence
        ),
        completed_stats AS (
          SELECT
            CASE
              WHEN pm.name = '판금/조립' THEN '판금·절곡'
              WHEN pm.name IN ('검사', '시험') THEN '검사·시험'
              ELSE pm.name
            END AS process_name,
            CAST(COUNT(*) FILTER (WHERE status = '완료') AS integer) AS completed_count
          FROM unit_processes up
          JOIN process_masters pm ON pm.id = up.process_master_id
          GROUP BY
            CASE
              WHEN pm.name = '판금/조립' THEN '판금·절곡'
              WHEN pm.name IN ('검사', '시험') THEN '검사·시험'
              ELSE pm.name
            END
        ),
        current_stats AS (
          SELECT
            process_name,
            CAST(COUNT(*) FILTER (WHERE process_status = '진행중') AS integer) AS running_count,
            CAST(COUNT(*) FILTER (WHERE process_status = '지연주의') AS integer) AS warning_count,
            MIN(unit_no) FILTER (WHERE process_status = '지연주의') AS warning_unit_no
          FROM current_process
          GROUP BY process_name
        ),
        process_stats AS (
          SELECT
            dg.name,
            dg.sequence,
            COALESCE(cs.completed_count, 0) AS completed_count,
            COALESCE(cur.running_count, 0) AS running_count,
            COALESCE(cur.warning_count, 0) AS warning_count,
            cur.warning_unit_no
          FROM display_groups dg
          LEFT JOIN completed_stats cs ON cs.process_name = dg.name
          LEFT JOIN current_stats cur ON cur.process_name = dg.name
        )
        SELECT
          name AS process_name,
          completed_count,
          running_count,
          warning_count,
          CASE
            WHEN warning_count > 0 THEN 'warn'
            WHEN running_count > 0 THEN 'run'
            ELSE 'wait'
          END AS line_state,
          CASE
            WHEN warning_count > 0 THEN '지연주의 · ' || warning_unit_no
            WHEN running_count > 0 AND name = '판금·절곡' THEN 'RUN · CNC #2 가동'
            WHEN running_count > 0 AND name = '도장' THEN 'RUN · 건조로 78℃'
            WHEN running_count > 0 AND name = '부스바·조립' THEN 'RUN'
            WHEN running_count > 0 AND name = '배선' THEN 'RUN · 배선 작업중'
            WHEN running_count > 0 AND name = '검사·시험' THEN 'RUN · AI검사 연동'
            WHEN running_count > 0 THEN 'RUN'
            ELSE '대기'
          END AS status_text
        FROM process_stats
        ORDER BY sequence
        """,
    )


@router.get("/weekly-output", response_model=list[WeeklyOutputItem])
def get_weekly_output(
    base_date: date = Query(default_factory=default_base_date),
    db: Session = Depends(get_db),
) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT
          CAST(d AS date) AS work_date,
          CAST(COALESCE(SUM(up.result_quantity), 0) AS integer) AS completed_count
        FROM generate_series(
          date_trunc('week', CAST(:base_date AS date))::date,
          date_trunc('week', CAST(:base_date AS date))::date + INTERVAL '6 days',
          INTERVAL '1 day'
        ) d
        LEFT JOIN unit_processes up ON CAST(up.completed_at AS date) = CAST(d AS date)
        GROUP BY d
        ORDER BY d
        """,
        {"base_date": base_date},
    )


@events_router.get("/recent", response_model=list[EventItem])
def get_recent_events(
    limit: int = Query(10, ge=1, le=50),
    base_date: date = Query(default_factory=default_base_date),
    db: Session = Depends(get_db),
) -> list[dict]:
    return fetch_all(
        db,
        """
        SELECT e.id, u.unit_no, e.event_type, e.message, e.severity, e.occurred_at
        FROM events e
        LEFT JOIN units u ON u.id = e.unit_id
        WHERE e.occurred_at < CAST(:base_date AS date) + INTERVAL '1 day'
        ORDER BY e.occurred_at DESC
        LIMIT :limit
        """,
        {"limit": limit, "base_date": base_date},
    )
