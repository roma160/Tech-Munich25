from pydantic import BaseModel
from typing import List, Tuple, Optional

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
    ranges: Optional[List[Tuple[int, int, int]]] = None
    error_type: str
    correction: str
    quote: str
    found_range: bool = True

class VocabItemRanged(BaseModel):
    range: Optional[Tuple[int, int, int]] = None
    synonyms: List[str]
    quote: str
    found_range: bool = True

class EvaluationResponseRanged(BaseModel):
    mistakes: List[ErrorItemRanged]
    inaccuracies: List[ErrorItemRanged]
    vocabularies: List[VocabItemRanged]