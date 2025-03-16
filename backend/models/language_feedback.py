from pydantic import BaseModel
from typing import List

class ErrorItem(BaseModel):
    quote: str
    error_type: str
    correction: str

class VocabItem(BaseModel):
    quote: str
    synonyms: List[str]

class EvaluationResponse(BaseModel):
    mistakes: List[ErrorItem]
    inaccuracies: List[ErrorItem]
    vocabularies: List[VocabItem]