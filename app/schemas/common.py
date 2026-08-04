from pydantic import BaseModel


class IdData(BaseModel):
    id: int


class ApiResponse(BaseModel):
    code: str
    message: str
    data: IdData


class MessageResponse(BaseModel):
    code: str
    message: str
