from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dates import default_base_date
from app.db.session import get_db
from app.schemas.common import ApiResponse, QuoteApiResponse, QuoteIdData
from app.schemas.inputs import (
    AiInspectionInput,
    CustomerInput,
    EventInput,
    InventoryInput,
    MaterialInput,
    OrderInput,
    OrderMaterialInput,
    ProcessMasterInput,
    QuoteInput,
    QuoteMaterialInput,
    TestInput,
    UnitInput,
    UnitProcessInput,
)
from app.services.insert import insert_id, integrity_error_response, validate_order_material_inventory
from app.services.quote_probability import MODEL_PATH, planning_probability, predict_quote_probability

router = APIRouter(tags=["input"])


@router.post("/customers", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_customer(payload: CustomerInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO customers (name, grade)
        VALUES (:name, :grade)
        RETURNING id
        """,
        payload.model_dump(),
        "수요처가 입력되었습니다.",
    )


@router.post("/orders", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_order(payload: OrderInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO orders (customer_id, quote_id, item_name, quantity, due_date, status)
        VALUES (:customer_id, :quote_id, :item_name, :quantity, :due_date, :status)
        RETURNING id
        """,
        payload.model_dump(),
        "수주가 입력되었습니다.",
    )


@router.post("/quotes", status_code=status.HTTP_201_CREATED, response_model=QuoteApiResponse)
def create_quote(
    payload: QuoteInput,
    base_date: date = Query(default_factory=default_base_date),
    db: Session = Depends(get_db),
) -> QuoteApiResponse:
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_NOT_READY", "message": "학습된 견적 확률 모델 파일이 없습니다."},
        )

    customer = db.execute(
        text("SELECT grade FROM customers WHERE id = :customer_id"),
        {"customer_id": payload.customer_id},
    ).mappings().one_or_none()
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "존재하지 않는 수요처입니다."},
        )

    days_until_due = max((payload.expected_due_date - base_date).days, 0)
    model_probability = predict_quote_probability(
        {
            "customer_grade": customer["grade"],
            "quote_stage": payload.quote_stage,
            "quantity": payload.quantity,
            "estimated_amount": payload.estimated_amount,
            "days_until_due": days_until_due,
        }
    )
    conservative_probability = planning_probability(model_probability)
    values = payload.model_dump()
    values["probability"] = round(conservative_probability, 4)

    try:
        quote = db.execute(
            text(
                """
                INSERT INTO quotes (
                  customer_id, item_name, quantity, expected_due_date, quote_stage,
                  estimated_amount, probability, status
                )
                VALUES (
                  :customer_id, :item_name, :quantity, :expected_due_date, :quote_stage,
                  :estimated_amount, :probability, :status
                )
                RETURNING id
                """
            ),
            values,
        ).mappings().one()
        db.execute(
            text(
                """
                INSERT INTO events (unit_id, event_type, message, severity)
                VALUES (NULL, 'AI', :message, :severity)
                """
            ),
            {
                "message": f"{payload.item_name} 견적 전환 확률 {conservative_probability * 100:.1f}% 산정",
                "severity": "info" if conservative_probability >= 0.5 else "warning",
            },
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise integrity_error_response(error) from error

    return QuoteApiResponse(
        code="CREATED",
        message="견적이 입력되었고 AI 전환 확률이 자동 반영되었습니다.",
        data=QuoteIdData(
            id=quote["id"],
            model_probability=round(model_probability, 4),
            planning_probability=round(conservative_probability, 4),
        ),
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
        INSERT INTO order_materials (order_id, material_id, required_quantity, inventory_id)
        VALUES (:order_id, :material_id, :required_quantity, :inventory_id)
        RETURNING id
        """,
        values,
        "수주자재가 입력되었습니다.",
    )


@router.post("/quote-materials", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_quote_material(payload: QuoteMaterialInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO quote_materials (quote_id, material_id, required_quantity)
        VALUES (:quote_id, :material_id, :required_quantity)
        RETURNING id
        """,
        payload.model_dump(),
        "견적자재가 입력되었습니다.",
    )


@router.post("/ai-inspections", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_ai_inspection(payload: AiInspectionInput, db: Session = Depends(get_db)) -> ApiResponse:
    return insert_id(
        db,
        """
        INSERT INTO ai_inspections (
          unit_id, inspection_type, result, confidence, finding, read_seconds, inspected_at
        )
        VALUES (
          :unit_id, :inspection_type, :result, :confidence, :finding, :read_seconds, COALESCE(:inspected_at, now())
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
