from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 60
KST = ZoneInfo("Asia/Seoul")
MAX_BASE_TIME = time(9, 0)


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", path, payload or {})

    def get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path, {})

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = None if method == "GET" else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed: {error.code} {detail} payload={payload}") from error
        except TimeoutError as error:
            raise RuntimeError(
                f"{method} {path} timed out after {DEFAULT_TIMEOUT_SECONDS}s. "
                "Check the API server log for the request that is still running or failed."
            ) from error
        except URLError as error:
            raise RuntimeError(f"API server is not reachable: {self.base_url}") from error

        return json.loads(body) if body else {}


def created_id(response: dict[str, Any]) -> int:
    return int(response["data"]["id"])


def as_date(value: date) -> str:
    return value.isoformat()


def as_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=KST)
    return value.isoformat()


def cap_base_datetime(value: datetime, base_date: date) -> datetime:
    max_value = datetime.combine(base_date, MAX_BASE_TIME)
    if value.date() == base_date and value > max_value:
        return max_value
    return value


def seed(base_url: str, base_date: date | None, reset: bool) -> None:
    client = ApiClient(base_url)
    health = client.get("/api/health")
    app_env = str(health.get("app_env", "")).lower()
    if app_env != "development":
        raise RuntimeError(f"Seed data can run only when APP_ENV=development. Current APP_ENV={app_env or 'unknown'}")
    effective_base_date = base_date or date.fromisoformat(str(health["base_date"]))

    if reset:
        client.post("/api/dev/reset")

    customers = seed_customers(client)
    quotes = seed_quotes(client, customers, effective_base_date)
    orders = seed_orders(client, customers, quotes, effective_base_date)
    units = seed_units(client, orders)
    processes = seed_process_masters(client)
    seed_unit_processes(client, units, processes, effective_base_date)
    materials = seed_materials(client)
    inventories = seed_inventories(client, materials, effective_base_date)
    seed_order_materials(client, orders, materials, inventories)
    seed_quote_materials(client, quotes, materials)
    seed_ai_inspections(client, units, effective_base_date)
    seed_tests(client, units, effective_base_date)
    seed_events(client, units, effective_base_date)

    print("Seed data created.")
    print("customers=7 quotes=10 orders=16 units=30 process_masters=8 unit_processes=240")
    print("materials=12 inventories=24 order_materials=71 quote_materials=40")
    print("ai_inspections=16 tests=36 events=12")


def seed_customers(client: ApiClient) -> list[int]:
    rows = [
        {"name": "대한전력", "grade": "A"},
        {"name": "세광산업", "grade": "A"},
        {"name": "한빛전자", "grade": "B"},
        {"name": "우진플랜트", "grade": "B"},
        {"name": "동원설비", "grade": "C"},
        {"name": "미래에너지", "grade": "N"},
        {"name": "청명테크", "grade": "N"},
    ]
    return [created_id(client.post("/api/customers", row)) for row in rows]


def seed_quotes(client: ApiClient, customers: list[int], base_date: date) -> list[int]:
    rows = [
        (0, "저압 배전반", 2, 9, "유력", 84000000, "전환"),
        (1, "MCC 제어반", 1, 12, "유력", 47000000, "전환"),
        (2, "분전반", 3, 16, "협의중", 66000000, "전환"),
        (3, "고압 배전반", 1, 21, "초기", 92000000, "진행중"),
        (4, "자동제어반", 2, 10, "협의중", 51000000, "전환"),
        (5, "PLC 판넬", 2, 13, "협의중", 38000000, "진행중"),
        (6, "인버터 판넬", 1, 7, "유력", 29000000, "진행중"),
        (0, "계장 제어반", 2, 18, "초기", 44000000, "진행중"),
        (2, "모터 제어반", 1, 25, "협의중", 36000000, "보류"),
        (4, "현장 조작반", 2, 11, "초기", 24000000, "실패"),
    ]
    return [
        created_id(
            client.post(
                f"/api/quotes?base_date={as_date(base_date)}",
                {
                    "customer_id": customers[customer_index],
                    "item_name": item_name,
                    "quantity": quantity,
                    "expected_due_date": as_date(base_date + timedelta(days=days)),
                    "quote_stage": stage,
                    "estimated_amount": amount,
                    "status": status,
                },
            )
        )
        for customer_index, item_name, quantity, days, stage, amount, status in rows
    ]


def seed_orders(client: ApiClient, customers: list[int], quotes: list[int], base_date: date) -> list[int]:
    rows = [
        (0, quotes[0], "저압 배전반", 2, 6, "진행중"),
        (1, quotes[1], "MCC 제어반", 1, 8, "지연주의"),
        (2, quotes[2], "분전반", 3, 14, "진행중"),
        (3, None, "고압 배전반", 2, 18, "대기"),
        (4, quotes[4], "자동제어반", 2, 9, "자재발주중"),
        (5, None, "PLC 판넬", 1, 4, "완료"),
        (6, None, "인버터 판넬", 2, 11, "진행중"),
        (0, None, "계장 제어반", 1, 20, "대기"),
        (1, None, "모터 제어반", 2, 13, "지연주의"),
        (2, None, "현장 조작반", 1, -2, "완료"),
        (3, None, "분전반", 1, 2, "완료"),
        (4, None, "저압 배전반", 2, 24, "대기"),
        (0, None, "고압 배전반", 2, -25, "완료"),
        (1, None, "MCC 제어반", 1, -20, "완료"),
        (2, None, "분전반", 2, -15, "완료"),
        (3, None, "자동제어반", 1, 1, "완료"),
    ]
    return [
        created_id(
            client.post(
                "/api/orders",
                {
                    "customer_id": customers[customer_index],
                    "quote_id": quote_id,
                    "item_name": item_name,
                    "quantity": quantity,
                    "due_date": as_date(base_date + timedelta(days=days)),
                    "status": status,
                },
            )
        )
        for customer_index, quote_id, item_name, quantity, days, status in rows
    ]


def seed_units(client: ApiClient, orders: list[int]) -> list[int]:
    unit_counts = [2, 1, 3, 2, 2, 1, 2, 1, 2, 1, 1, 4, 2, 1, 2, 3]
    statuses = [
        "진행중",
        "진행중",
        "진행중",
        "진행중",
        "진행중",
        "대기",
        "대기",
        "자재발주중",
        "자재발주중",
        "완료",
        "진행중",
        "진행중",
        "대기",
        "지연주의",
        "진행중",
        "진행중",
        "완료",
        "대기",
        "대기",
        "대기",
        "진행중",
        "자재발주중",
        "완료",
        "완료",
        "완료",
        "완료",
        "완료",
        "완료",
        "완료",
        "완료",
    ]
    units: list[int] = []
    unit_index = 0

    for order_index, count in enumerate(unit_counts):
        for _ in range(count):
            unit_index += 1
            units.append(
                created_id(
                    client.post(
                        "/api/units",
                        {
                            "order_id": orders[order_index],
                            "unit_no": (
                                f"DN-2607-{unit_index + 10:03d}"
                                if unit_index <= 10
                                else f"DN-2608-{unit_index - 10:03d}"
                            ),
                            "item_detail": f"{unit_index}호기",
                            "status": statuses[unit_index - 1],
                        },
                    )
                )
            )

    return units


def seed_process_masters(client: ApiClient) -> list[int]:
    rows = [
        ("설계", 1, "1.0"),
        ("설계 확정", 2, "0.5"),
        ("판금·절곡", 3, "1.0"),
        ("도장", 4, "1.0"),
        ("부스바·조립", 5, "1.0"),
        ("배선", 6, "2.5"),
        ("검사·시험", 7, "2.0"),
        ("출하 대기", 8, "0.5"),
    ]
    return [
        created_id(
            client.post(
                "/api/process-masters",
                {"name": name, "sequence": sequence, "standard_days": standard_days},
            )
        )
        for name, sequence, standard_days in rows
    ]


def seed_unit_processes(client: ApiClient, units: list[int], processes: list[int], base_date: date) -> None:
    completion_by_unit = [2, 2, 1, 4, 3, 0, 0, 2, 1, 8, 5, 4, 0, 2, 3, 5, 8, 0, 0, 1, 2, 0, 8, 8, 8, 8, 8, 8, 8, 8]
    active_current_units = {1, 4, 5, 11, 14, 16}
    warning_units = {14}
    bending_wait_units = {2}
    rework_pairs = {(2, 3), (11, 6), (16, 6), (17, 7)}
    week_start = base_date - timedelta(days=base_date.weekday())
    historical_completed_dates = {
        23: date(2026, 7, 10),
        24: date(2026, 7, 10),
        25: date(2026, 7, 18),
        26: date(2026, 7, 23),
        27: date(2026, 7, 20),
        28: date(2026, 8, 4),
        29: date(2026, 8, 4),
        30: date(2026, 8, 4),
    }

    for unit_index, unit_id in enumerate(units, start=1):
        completed_count = completion_by_unit[unit_index - 1]
        last_completed_at = None

        for process_index, process_id in enumerate(processes, start=1):
            started_at = None
            completed_at = None
            result_quantity = None

            if process_index <= completed_count:
                status = "완료"
                if unit_index in historical_completed_dates:
                    work_date = historical_completed_dates[unit_index] - timedelta(days=completed_count - process_index)
                else:
                    work_date = week_start + timedelta(days=(unit_index + process_index) % 3)
                started_at = cap_base_datetime(datetime.combine(work_date, time(8 + (process_index % 3), 30)), base_date)
                completed_at = cap_base_datetime(started_at + timedelta(hours=4), base_date)
                last_completed_at = completed_at
                result_quantity = 2 + ((unit_index + process_index) % 4)
            elif process_index == completed_count + 1:
                if unit_index in bending_wait_units and process_index == 3:
                    status = "대기"
                elif unit_index not in active_current_units:
                    status = "대기"
                else:
                    status = "지연주의" if unit_index in warning_units else "진행중"
                    started_at = (
                        last_completed_at + timedelta(hours=1)
                        if last_completed_at
                        else datetime.combine(base_date, time(9, 0))
                    )
                    started_at = cap_base_datetime(started_at, base_date)
            else:
                status = "대기"

            client.post(
                "/api/unit-processes",
                {
                    "unit_id": unit_id,
                    "process_master_id": process_id,
                    "started_at": as_datetime(started_at) if started_at else None,
                    "completed_at": as_datetime(completed_at) if completed_at else None,
                    "status": status,
                    "result_quantity": result_quantity,
                    "is_rework": (unit_index, process_index) in rework_pairs,
                },
            )


def seed_materials(client: ApiClient) -> list[int]:
    rows = [
        ("차단기", "EA", 7),
        ("전자접촉기", "EA", 5),
        ("릴레이", "EA", 3),
        ("단자대", "EA", 4),
        ("동부스바", "M", 10),
        ("제어케이블", "M", 6),
        ("전선", "M", 5),
        ("계기용 변류기", "EA", 9),
        ("표시등", "EA", 3),
        ("스위치", "EA", 3),
        ("판넬 외함", "EA", 14),
        ("퓨즈", "EA", 4),
    ]
    return [
        created_id(client.post("/api/materials", {"name": name, "unit": unit, "lead_time_days": lead_time}))
        for name, unit, lead_time in rows
    ]


def seed_inventories(client: ApiClient, materials: list[int], base_date: date) -> dict[int, list[int]]:
    stocks = [
        (120, 80, 18, 10),
        (160, 90, 27, 13),
        (360, 240, 62, 36),
        (500, 300, 78, 46),
        (300, 180, 52, 30),
        (1200, 700, 169, 78),
        (1800, 1000, 221, 117),
        (140, 80, 21, 12),
        (240, 160, 57, 31),
        (260, 140, 49, 25),
        (50, 30, 7, 4),
        (420, 260, 85, 46),
    ]
    inventories: dict[int, list[int]] = {}

    for index, material_id in enumerate(materials, start=1):
        first_purchase, second_purchase, first_current, second_current = stocks[index - 1]
        inventories[material_id] = [
            created_id(
                client.post(
                    "/api/inventories",
                    {
                        "material_id": material_id,
                        "lot_no": f"LOT-2607-{index:02d}A",
                        "purchased_quantity": first_purchase,
                        "current_quantity": first_current,
                        "received_at": as_date(base_date - timedelta(days=24 + index)),
                    },
                )
            ),
            created_id(
                client.post(
                    "/api/inventories",
                    {
                        "material_id": material_id,
                        "lot_no": f"LOT-2608-{index:02d}B",
                        "purchased_quantity": second_purchase,
                        "current_quantity": second_current,
                        "received_at": as_date(base_date - timedelta(days=index)),
                    },
                )
            ),
        ]

    return inventories


def seed_order_materials(
    client: ApiClient,
    orders: list[int],
    materials: list[int],
    inventories: dict[int, list[int]],
) -> None:
    order_base_quantities = [8, 12, 24, 36, 18, 80, 120, 10, 18, 20, 3, 30]

    for order_index, order_id in enumerate(orders):
        material_count = 5 if order_index < 7 else 4
        start = order_index % len(materials)

        for offset in range(material_count):
            material_index = (start + offset) % len(materials)
            material_id = materials[material_index]
            quantity = order_base_quantities[material_index] + ((order_index + offset) % 4) * 2

            client.post(
                "/api/order-materials",
                {
                    "order_id": order_id,
                    "material_id": material_id,
                    "required_quantity": quantity,
                    "inventory_id": inventories[material_id][offset % 2],
                },
            )


def seed_quote_materials(client: ApiClient, quotes: list[int], materials: list[int]) -> None:
    quote_base_quantities = [6, 10, 20, 30, 14, 60, 90, 8, 14, 16, 2, 24]

    for quote_index, quote_id in enumerate(quotes):
        start = (quote_index * 2) % len(materials)

        for offset in range(4):
            material_index = (start + offset) % len(materials)
            material_id = materials[material_index]
            quantity = quote_base_quantities[material_index] + ((quote_index + offset) % 5) * 2

            client.post(
                "/api/quote-materials",
                {
                    "quote_id": quote_id,
                    "material_id": material_id,
                    "required_quantity": quantity,
                },
            )


def seed_ai_inspections(client: ApiClient, units: list[int], base_date: date) -> None:
    findings = [
        None,
        "단자 배선 경로 상이",
        None,
        "라벨 누락",
        None,
        None,
        "케이블 타이 간격 초과",
        None,
        "접지선 체결 확인 필요",
        None,
        None,
        "단자 체결 토크 재확인",
        None,
        None,
        "배선 색상 기준 불일치",
        None,
    ]
    inspection_times = [
        datetime.combine(base_date, time(8, 10)),
        datetime.combine(base_date, time(8, 25)),
        datetime.combine(base_date, time(8, 40)),
        datetime.combine(base_date, time(8, 50)),
        datetime.combine(base_date, time(9, 0)),
    ] + [
        datetime.combine(base_date - timedelta(days=1), time(9, 30)) + timedelta(minutes=index * 45)
        for index in range(5)
    ] + [
        datetime.combine(base_date - timedelta(days=2), time(10, 10)) + timedelta(minutes=index * 50)
        for index in range(4)
    ] + [
        datetime.combine(base_date - timedelta(days=3), time(11, 0)) + timedelta(minutes=index * 60)
        for index in range(2)
    ]
    read_seconds = [
        "1.6", "1.9", "1.7", "2.0", "1.8", "1.5", "1.7", "1.9",
        "1.6", "1.8", "1.7", "1.9", "1.5", "1.8", "2.0", "1.6",
    ]

    for index, unit_id in enumerate(units[:16]):
        result = "FAIL" if findings[index] else "PASS"
        client.post(
            "/api/ai-inspections",
            {
                "unit_id": unit_id,
                "inspection_type": "배선검사",
                "result": result,
                "confidence": "96.20" if result == "PASS" else "98.10",
                "finding": findings[index],
                "read_seconds": read_seconds[index],
                "inspected_at": as_datetime(cap_base_datetime(inspection_times[index], base_date)),
            },
        )


def seed_tests(client: ApiClient, units: list[int], base_date: date) -> None:
    tests = [
        ("절연저항", "100MΩ 이상"),
        ("내전압", "AC 1500V 1분"),
        ("동작시험", "정상 동작"),
    ]

    for unit_index, unit_id in enumerate(units[:12]):
        for test_index, (test_item, criteria) in enumerate(tests):
            fail = unit_index in {1, 8} and test_index == 1
            measured = "불안정" if fail else ("정상" if test_item == "동작시험" else "적합")
            client.post(
                "/api/tests",
                {
                    "unit_id": unit_id,
                    "test_item": test_item,
                    "measured_value": measured,
                    "criteria": criteria,
                    "result": "FAIL" if fail else "PASS",
                    "tester": ["김민수", "이서연", "박지훈"][test_index],
                    "tested_at": as_datetime(
                        cap_base_datetime(
                            datetime.combine(base_date - timedelta(days=unit_index % 5), time(14, 0))
                            + timedelta(minutes=test_index * 20),
                            base_date,
                        )
                    ),
                },
            )


def seed_events(client: ApiClient, units: list[int], base_date: date) -> None:
    rows = [
        (0, "납기", "잔여 공정 대비 납기 여유 부족", "warning"),
        (2, "자재", "차단기 입고 지연 가능성", "warning"),
        (4, "자재", "외함 재고 부족으로 발주 필요", "warning"),
        (7, "자재", "동부스바 LOT 배정 완료", "info"),
        (8, "납기", "지연 위험 호기 발생", "error"),
        (11, "검사", "단자 체결 토크 재확인 필요", "warning"),
        (12, "수주", "신규 호기 등록", "info"),
        (13, "공정", "재작업 실적 확인", "warning"),
        (14, "자재", "전선 현재고 부족 예상", "warning"),
        (17, "수주", "납기 변경 검토 필요", "warning"),
        (18, "자재", "자재 발주 요청 대기", "info"),
        (19, "시스템", "일일 집계 갱신", "info"),
    ]

    for index, (unit_index, event_type, message, severity) in enumerate(rows):
        client.post(
            "/api/events",
            {
                "unit_id": units[unit_index],
                "event_type": event_type,
                "message": message,
                "severity": severity,
                "occurred_at": as_datetime(
                    datetime.combine(base_date, time(9, 0)) - timedelta(minutes=index * 8)
                ),
            },
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create deterministic demo data through the FastAPI input API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--base-date", default=None)
    parser.add_argument("--no-reset", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_date = date.fromisoformat(args.base_date) if args.base_date else None
    seed(args.base_url, base_date, reset=not args.no_reset)


if __name__ == "__main__":
    main()
