from pydantic import BaseModel
from typing import List, Tuple

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


class ErrorItemRanged(BaseModel):
    ranges: List[Tuple[int, int]]
    error_type: str
    correction: str

class VocabItemRanged(BaseModel):
    range: Tuple[int, int]
    synonyms: List[str]

class EvaluationResponseRanged(BaseModel):
    transcript: str
    mistakes: List[ErrorItemRanged]
    inaccuracies: List[ErrorItemRanged]
    vocabularies: List[VocabItemRanged]