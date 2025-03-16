"""
ElevenLabs Speech-to-Text API service.
"""
import os
import aiohttp
import asyncio
from typing import Optional
from models.elevenlabs import ElevenLabsOutput
import json

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
            "accept": "application/json"
        }
        
        data = aiohttp.FormData()
        data.add_field(
            "file",  # Use 'file' instead of 'audio' as the field name
            file_data, 
            filename=os.path.basename(file_path),
            content_type="audio/wav"
        )
        
        # Add parameters for speech-to-text
        data.add_field("model_id", "scribe_v1")  # Use scribe_v1 instead of eleven_turbo_v2
        data.add_field("diarize", "true")  # Enable speaker diarization
        data.add_field("language", "de")  # German language
        
        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.speech_to_text_url, 
                headers=headers,
                data=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error: {response.status}, {error_text}")
                
                response_json = await response.json()
                
                # Log the full response
                print("FULL ELEVENLABS RESPONSE:")
                print(json.dumps(response_json, indent=2))
                
                # Specifically check for speaker information
                words = response_json.get("words", [])
                speaker_ids = set()
                for word in words[:20]:  # Check first 20 words
                    if "speaker" in word:
                        speaker_ids.add(word["speaker"])
                
                print(f"Found {len(speaker_ids)} unique speaker IDs in first 20 words: {speaker_ids}")
                
                return ElevenLabsOutput.from_response(response_json)