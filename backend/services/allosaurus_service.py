"""
Allosaurus phoneme recognition service.
"""
import os
from typing import Optional, Dict, Any, List
import asyncio

class AllosaurusService:
    """
    Service for phoneme recognition using Allosaurus.
    """
    
    def __init__(self):
        """
        Initialize the Allosaurus service.
        """
        # Import here to avoid dependency issues if allosaurus is not installed
        from allosaurus.app import read_recognizer
        self.model = read_recognizer()
    
    async def recognize_phonemes(self, file_path: str) -> Dict[str, Any]:
        """
        Recognize phonemes in an audio file using Allosaurus.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing the recognized phonemes
        """
        # Ensure running in an async context doesn't block
        return await asyncio.to_thread(self._recognize_sync, file_path)
    
    def _recognize_sync(self, file_path: str) -> Dict[str, Any]:
        """
        Synchronous method to recognize phonemes.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing the recognized phonemes
        """
        # Run inference
        phoneme_string = self.model.recognize(file_path)
        
        # Process the phoneme string
        phonemes = [p for p in phoneme_string.split() if p.strip()]
        
        return {
            "text": phoneme_string,
            "phonemes": phonemes,
            "confidence": 1.0  # Allosaurus doesn't provide confidence scores by default
        } 