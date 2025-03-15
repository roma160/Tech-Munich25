"""
Test script for ElevenLabs speech-to-text conversion.

This script tests the ElevenLabs service by transcribing a sample.wav file
and saves the output to sample_output.json.
"""
import asyncio
import json
import os
from dotenv import load_dotenv
from services.elevenlabs import elevenlabs_service

# Load environment variables
load_dotenv()

async def test_elevenlabs():
    """Test the ElevenLabs speech-to-text service and save the output"""
    try:
        # Path to the sample WAV file
        sample_path = os.path.join(os.path.dirname(__file__), "sample.wav")
        
        # Check if file exists
        if not os.path.exists(sample_path):
            print(f"Error: Sample file not found at {sample_path}")
            return
        
        print(f"Processing sample file: {sample_path}")
        
        # Call the ElevenLabs service
        result = await elevenlabs_service.speech_to_text(sample_path)
        
        # Save the result to a JSON file
        output_path = os.path.join(os.path.dirname(__file__), "sample_output.json")
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"Transcription complete. Output saved to {output_path}")
        print("\nTranscription result:")
        print(result.get("text", "No text found in response"))
        
    except Exception as e:
        print(f"Error testing ElevenLabs service: {str(e)}")

if __name__ == "__main__":
    # Run the async test function
    asyncio.run(test_elevenlabs()) 