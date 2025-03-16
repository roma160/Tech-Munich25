"""
ElevenLabs Speech-to-Text API service.
"""
import os
import aiohttp
import asyncio
from typing import Optional
from models.elevenlabs import ElevenLabsOutput
import logging

logger = logging.getLogger(__name__)

class ElevenLabsService:
    """
    Service for interacting with the ElevenLabs Speech-to-Text API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ElevenLabs service with API key.
        
        Args:
            api_key: ElevenLabs API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("ELEVEN_LABS_API_KEY")
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required but was not provided or found in environment variables")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.speech_to_text_url = f"{self.base_url}/speech-to-text"
    
    async def speech_to_text(self, file_path: str) -> ElevenLabsOutput:
        """
        Convert speech in a WAV file to text using ElevenLabs API.
        
        Args:
            file_path: Path to the WAV file
            
        Returns:
            Dictionary containing the transcription results
        """
        # Read file binary data
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        # Prepare headers and data for the request
        headers = {
            "xi-api-key": self.api_key,
        }
        
        data = aiohttp.FormData()
        data.add_field(
            "audio", 
            file_data, 
            filename=os.path.basename(file_path),
            content_type="audio/wav"
        )
        
        # Add parameters for speech-to-text
        data.add_field("model_id", "eleven_turbo_v2")
        data.add_field("language", "de")  # German language
        
        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.speech_to_text_url, 
                headers=headers,
                data=data
            ) as response:
                response_json = await response.json()
                logger.warning(response_json)
                return ElevenLabsOutput.from_response(response_json)