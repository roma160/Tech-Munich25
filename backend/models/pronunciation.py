"""
Pronunciation assessment models.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PhonemeScore(BaseModel):
    """Model representing a score for an individual phoneme."""
    phoneme: str = Field(..., description="The phoneme (IPA symbol)")
    score: float = Field(..., description="Score for this phoneme (0-1)")


class PronunciationAssessmentResponse(BaseModel):
    """Response model for pronunciation assessment endpoint."""
    score: float = Field(..., description="Overall pronunciation score (0-100)")
    overall_feedback: str = Field(..., description="Overall feedback on pronunciation")
    detailed_feedback: str = Field(..., description="Detailed feedback with specific issues")
    reference_text: str = Field(..., description="The reference text that was assessed")
    expected_phonemes: List[str] = Field(..., description="The expected phonemes (IPA)")
    correct_audio: str = Field(..., description="Base64-encoded audio of correct pronunciation")
    problematic_phonemes: List[str] = Field([], description="List of phonemes that were problematic")
    phoneme_scores: List[PhonemeScore] = Field(..., description="Individual scores for each phoneme") 