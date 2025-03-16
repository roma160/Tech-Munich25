"""
Models related to process tracking.
"""
from enum import Enum
from typing import Dict, Optional, List, Any
from pydantic import BaseModel

class ProcessStatus(str, Enum):
    """
    Enum representing the possible states of a process.
    """
    PENDING = "pending"
    ELEVENLABS_PROCESSING = "elevenlabs_processing"
    ELEVENLABS_COMPLETE = "elevenlabs_complete"
    ALLOSAURUS_PROCESSING = "allosaurus_processing"
    ALLOSAURUS_COMPLETE = "allosaurus_complete"
    MISTRAL_PROCESSING = "mistral_processing"
    COMPLETE = "complete"
    FAILED = "failed"

class ProcessInfo(BaseModel):
    """
    Model representing information about a processing job.
    """
    id: str
    status: ProcessStatus
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None 