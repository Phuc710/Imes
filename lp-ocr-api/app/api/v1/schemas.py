from pydantic import BaseModel
from typing import List, Optional


class Detection(BaseModel):
    char: str
    conf: float
    box: list[float]  # [x1,y1,x2,y2]
    row_id: int


class OCRResponse(BaseModel):
    text: str
    timestamp: str | None = None
