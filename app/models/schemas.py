from pydantic import BaseModel


class GenerateRequest(BaseModel):
    model_id: int
    temperature: float = 0.7
    prompt: str
    max_tokens: int = 100


class GenerateResponse(BaseModel):
    response: str
    model_id: int
