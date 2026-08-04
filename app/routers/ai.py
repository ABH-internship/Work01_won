from fastapi import APIRouter, HTTPException, status

from app.schemas.ai import QuoteProbabilityInput, QuoteProbabilityResponse
from app.services.quote_probability import MODEL_PATH, planning_probability, predict_quote_probability

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/quote-probability", response_model=QuoteProbabilityResponse)
def predict_probability(payload: QuoteProbabilityInput) -> QuoteProbabilityResponse:
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MODEL_NOT_READY", "message": "학습된 모델 파일이 없습니다."},
        )

    model_probability = predict_quote_probability(payload.model_dump())
    conservative_probability = planning_probability(model_probability)

    return QuoteProbabilityResponse(
        code="OK",
        message="수주 전환 확률이 예측되었습니다.",
        data={
            "model_probability": round(model_probability, 4),
            "planning_probability": round(conservative_probability, 4),
        },
    )
