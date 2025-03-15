from pydantic import BaseModel
from typing import List

class ErrorCorrection(BaseModel):
    quote: str
    error_type: str
    correction: str

class LanguageFeedback(BaseModel):
    high: List[ErrorCorrection] = []
    mid: List[ErrorCorrection] = []
    low: List[ErrorCorrection] = []