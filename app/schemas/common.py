from pydantic import BaseModel


class IdData(BaseModel):
    id: int


class QuoteIdData(IdData):
    model_probability: float
    planning_probability: float


class ApiResponse(BaseModel):
    code: str
    message: str
    data: IdData


class QuoteApiResponse(BaseModel):
    code: str
    message: str
    data: QuoteIdData


class MessageResponse(BaseModel):
    code: str
    message: str
