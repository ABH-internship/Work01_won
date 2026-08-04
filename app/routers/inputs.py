from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.inputs import (
    AiInspectionInput,
    CustomerInput,
    EventInput,
    InventoryInput,
    MaterialInput,
    OrderInput,
    OrderMaterialInput,
    ProcessMasterInput,
    TestInput,
    UnitInput,
    UnitProcessInput,
)
from app.services.insert import insert_id, validate_order_material_inventory

router = APIRouter(tags=["input"])


@router.post("/customers", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_customer(payload: CustomerInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        "INSERT INTO customers (name) VALUES (:name) RETURNING id",
        payload.model_dump(),
        "수요처가 입력되었습니다.",
    )


@router.post("/orders", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_order(payload: OrderInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO orders (customer_id, item_name, quantity, due_date, status)
        VALUES (:customer_id, :item_name, :quantity, :due_date, :status)
        RETURNING id
        """,
        payload.model_dump(),
        "수주가 입력되었습니다.",
    )


@router.post("/units", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_unit(payload: UnitInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO units (order_id, unit_no, item_detail, status)
        VALUES (:order_id, :unit_no, :item_detail, :status)
        RETURNING id
        """,
        payload.model_dump(),
        "호기가 입력되었습니다.",
    )


@router.post("/process-masters", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_process_master(payload: ProcessMasterInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO process_masters (name, sequence, standard_days)
        VALUES (:name, :sequence, :standard_days)
        RETURNING id
        """,
        payload.model_dump(),
        "공정마스터가 입력되었습니다.",
    )


@router.post("/unit-processes", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_unit_process(payload: UnitProcessInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO unit_processes (
          unit_id, process_master_id, started_at, completed_at, status, result_quantity, is_rework
        )
        VALUES (
          :unit_id, :process_master_id, :started_at, :completed_at, :status, :result_quantity, :is_rework
        )
        RETURNING id
        """,
        payload.model_dump(),
        "호기공정이 입력되었습니다.",
    )


@router.post("/materials", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_material(payload: MaterialInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO materials (name, unit, lead_time_days)
        VALUES (:name, :unit, :lead_time_days)
        RETURNING id
        """,
        payload.model_dump(),
        "자재가 입력되었습니다.",
    )


@router.post("/inventories", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_inventory(payload: InventoryInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO inventories (
          material_id, lot_no, purchased_quantity, current_quantity, received_at
        )
        VALUES (
          :material_id, :lot_no, :purchased_quantity, :current_quantity, :received_at
        )
        RETURNING id
        """,
        payload.model_dump(),
        "재고가 입력되었습니다.",
    )


@router.post("/order-materials", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_order_material(payload: OrderMaterialInput, db: Session = Depends(get_db)) -> ApiResponse:
    values = payload.model_dump()
    validate_order_material_inventory(db, values)

    return insert_id(
        db,
        """
        INSERT INTO order_materials (
          order_id, material_id, required_quantity, lot_no, inventory_id
        )
        VALUES (
          :order_id, :material_id, :required_quantity, :lot_no, :inventory_id
        )
        RETURNING id
        """,
        values,
        "수주자재가 입력되었습니다.",
    )


@router.post("/ai-inspections", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_ai_inspection(payload: AiInspectionInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO ai_inspections (
          unit_id, inspection_type, result, confidence, finding, inspected_at
        )
        VALUES (
          :unit_id, :inspection_type, :result, :confidence, :finding, COALESCE(:inspected_at, now())
        )
        RETURNING id
        """,
        payload.model_dump(),
        "AI검사 결과가 입력되었습니다.",
    )


@router.post("/tests", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_test(payload: TestInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO tests (
          unit_id, test_item, measured_value, criteria, result, tester, tested_at
        )
        VALUES (
          :unit_id, :test_item, :measured_value, :criteria, :result, :tester, COALESCE(:tested_at, now())
        )
        RETURNING id
        """,
        payload.model_dump(),
        "시험성적이 입력되었습니다.",
    )


@router.post("/events", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_event(payload: EventInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO events (
          unit_id, event_type, message, severity, occurred_at
        )
        VALUES (
          :unit_id, :event_type, :message, :severity, COALESCE(:occurred_at, now())
        )
        RETURNING id
        """,
        payload.model_dump(),
        "이벤트가 입력되었습니다.",
    )
