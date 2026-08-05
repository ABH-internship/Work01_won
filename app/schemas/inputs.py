from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

OrderStatus = Literal["대기", "진행중", "완료", "지연주의", "자재발주중"]
ProcessStatus = Literal["대기", "진행중", "완료", "지연주의"]
QualityResult = Literal["PASS", "FAIL"]
EventSeverity = Literal["info", "warning", "error"]
CustomerGrade = Literal["A", "B", "C", "N"]
QuoteStage = Literal["초기", "협의중", "유력"]
QuoteStatus = Literal["진행중", "전환", "실패", "보류"]


class CustomerInput(BaseModel):
    name: str
    grade: CustomerGrade = "B"


class OrderInput(BaseModel):
    customer_id: int
    quote_id: int | None = None
    item_name: str
    quantity: int
    due_date: date
    status: OrderStatus


class QuoteInput(BaseModel):
    customer_id: int
    item_name: str
    quantity: int
    expected_due_date: date
    quote_stage: QuoteStage
    estimated_amount: Decimal
    status: QuoteStatus = "진행중"


class UnitInput(BaseModel):
    order_id: int
    unit_no: str
    item_detail: str | None = None
    status: OrderStatus


class ProcessMasterInput(BaseModel):
    name: str
    sequence: int
    standard_days: Decimal


class UnitProcessInput(BaseModel):
    unit_id: int
    process_master_id: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: ProcessStatus
    result_quantity: int | None = None
    is_rework: bool = False


class MaterialInput(BaseModel):
    name: str
    unit: str
    lead_time_days: int = 0


class InventoryInput(BaseModel):
    material_id: int
    lot_no: str
    purchased_quantity: Decimal
    current_quantity: Decimal
    received_at: date


class OrderMaterialInput(BaseModel):
    order_id: int
    material_id: int
    required_quantity: Decimal
    inventory_id: int | None = None


class QuoteMaterialInput(BaseModel):
    quote_id: int
    material_id: int
    required_quantity: Decimal


class AiInspectionInput(BaseModel):
    unit_id: int
    inspection_type: str
    result: QualityResult
    confidence: Decimal | None = None
    finding: str | None = None
    inspected_at: datetime | None = None


class TestInput(BaseModel):
    unit_id: int
    test_item: str
    measured_value: str
    criteria: str
    result: QualityResult
    tester: str
    tested_at: datetime | None = None


class EventInput(BaseModel):
    unit_id: int | None = None
    event_type: str
    message: str
    severity: EventSeverity
    occurred_at: datetime | None = None
