from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    today_process_results: int
    active_units: int
    on_time_rate: Decimal
    weekly_reworks: int


class ProcessLineItem(BaseModel):
    process_name: str
    completed_count: int
    running_count: int
    warning_count: int


class WeeklyOutputItem(BaseModel):
    work_date: date
    completed_count: int


class EventItem(BaseModel):
    id: int
    unit_no: str | None
    event_type: str
    message: str
    severity: str
    occurred_at: datetime


class ProgressUnitItem(BaseModel):
    unit_no: str
    item_name: str
    customer_name: str
    due_date: date
    progress_rate: Decimal
    current_process: str | None
    status: str


class DueRisk(BaseModel):
    unit_no: str
    due_date: date
    remaining_standard_days: Decimal
    days_until_due: int
    buffer_days: Decimal
    status: str
    message: str


class AiInspectionSummary(BaseModel):
    today_count: int
    detection_count: int
    average_confidence: Decimal | None


class MockAiInspectionInput(BaseModel):
    unit_no: str
    inspection_type: str = "배선검사"
    result: Literal["PASS", "FAIL"] = "FAIL"
    confidence: Decimal = Decimal("97.20")
    finding: str | None = "단자 배선 경로 상이"


class AiInspectionItem(BaseModel):
    id: int
    unit_no: str
    inspection_type: str
    result: str
    confidence: Decimal | None
    finding: str | None
    inspected_at: datetime


class MaterialRequirementItem(BaseModel):
    material_id: int
    material_name: str
    unit: str
    current_quantity: Decimal
    required_quantity_2weeks: Decimal
    shortage_quantity: Decimal
    judgement: str
    suggestion: str


class InventoryItem(BaseModel):
    id: int
    material_name: str
    unit: str
    lot_no: str
    purchased_quantity: Decimal
    current_quantity: Decimal
    received_at: date


class TestRecordItem(BaseModel):
    id: int
    unit_no: str
    test_item: str
    measured_value: str
    criteria: str
    result: str
    tester: str
    tested_at: datetime


class TraceProcessItem(BaseModel):
    process_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None


class TraceMaterialItem(BaseModel):
    material_name: str
    required_quantity: Decimal
    unit: str
    lot_no: str | None


class TraceResponse(BaseModel):
    unit_no: str
    item_name: str
    customer_name: str
    due_date: date
    processes: list[TraceProcessItem]
    materials: list[TraceMaterialItem]
    inspections: list[AiInspectionItem]
    tests: list[TestRecordItem]
