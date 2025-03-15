"""
ElevenLabs Speech-to-Text API service.
"""
import os
import aiohttp
import asyncio
from typing import Optional
from models.elevenlabs import ElevenLabsOutput
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
        
        # For testing purposes, use a mock API key if none is found
        if not self.api_key:
            print("Warning: Using mock ElevenLabs API key for testing purposes")
            self.api_key = "mock-api-key-for-testing"
            self.mock_mode = True
        else:
            self.mock_mode = False
        
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
        # If in mock mode, return a sample response
        if self.mock_mode:
            print("Using mock ElevenLabs response for testing")
            # Simulate API call delay
            await asyncio.sleep(2)
            
            # Return sample response
            return ElevenLabsOutput(**{
                "text": "This is a sample transcription of spoken content. The ElevenLabs API converts speech to text with high accuracy.",
                "transcription": [
                    {
                        "text": "This is a sample transcription",
                        "start": 0.0,
                        "end": 2.5
                    },
                    {
                        "text": "of spoken content.",
                        "start": 2.5,
                        "end": 4.0
                    },
                    {
                        "text": "The ElevenLabs API converts speech to text",
                        "start": 4.0,
                        "end": 7.5
                    },
                    {
                        "text": "with high accuracy.",
                        "start": 7.5,
                        "end": 9.0
                    }
                ],
                "language": "en",
                "detected_language": "en",
                "confidence_score": 0.98
            })
        
        # Real API call implementation
        headers = {
            "xi-api-key": self.api_key,
            "accept": "application/json"
        }
        
        try:
            # Read audio file
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            async with aiohttp.ClientSession() as session:
                # Prepare the multipart form data
                form_data = aiohttp.FormData()
                form_data.add_field(
                    'file',
                    file_data,
                    filename=os.path.basename(file_path),
                    content_type='audio/wav'
                )
                form_data.add_field('model_id', 'scribe_v1')
                form_data.add_field('diarize', 'true')  # Enable speaker diarization
                # No language_code provided to allow auto-detection
                
                # Make the POST request
                async with session.post(
                    self.speech_to_text_url,
                    headers=headers,
                    data=form_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"ElevenLabs API error: {response.status}, {error_text}")
                    
                    result = await response.json()
                    return ElevenLabsOutput(**result)
        
        except Exception as e:
            raise Exception(f"Error calling ElevenLabs API: {str(e)}")