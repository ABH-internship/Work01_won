from pydantic import BaseModel, Field

from app.schemas.inputs import CustomerGrade, QuoteStage


class QuoteProbabilityInput(BaseModel):
    customer_grade: CustomerGrade
    quote_stage: QuoteStage
    quantity: int = Field(gt=0)
    estimated_amount: float = Field(ge=0)
    days_until_due: int = Field(ge=0)


class QuoteProbabilityData(BaseModel):
    model_probability: float = Field(ge=0, le=1)
    planning_probability: float = Field(ge=0, le=1)


class QuoteProbabilityResponse(BaseModel):
    code: str
    message: str
    data: QuoteProbabilityData
