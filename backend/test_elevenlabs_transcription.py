import asyncio
import json
import logging
import os
import sys
import wave
from datetime import datetime
from dotenv import load_dotenv
import requests  # Add for direct API testing

from services.elevenlabs import ElevenLabsService
from utils import get_root_folder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"elevenlabs_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("elevenlabs_test")

# Load environment variables
load_dotenv(dotenv_path=get_root_folder() / ".env")

def check_wav_file(file_path):
    """Check WAV file properties and log details."""
    try:
        with wave.open(file_path, 'rb') as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            duration = n_frames / frame_rate
            
            logger.info(f"WAV file details:")
            logger.info(f"  Channels: {channels}")
            logger.info(f"  Sample width: {sample_width} bytes")
            logger.info(f"  Frame rate: {frame_rate} Hz")
            logger.info(f"  Number of frames: {n_frames}")
            logger.info(f"  Duration: {duration:.2f} seconds")
            logger.info(f"  File size: {os.path.getsize(file_path)} bytes")
            
            return True
    except Exception as e:
        logger.error(f"Error checking WAV file: {str(e)}")
        return False

async def test_elevenlabs_transcription():
    # Find all WAV files in current directory
    wav_files = [f for f in os.listdir() if f.endswith(".wav")]
    logger.info(f"Found WAV files: {wav_files}")
    
    # Check if test file exists
    test_file = "sample.wav"
    if not os.path.exists(test_file):
        test_file = "test.wav"
    if not os.path.exists(test_file):
        # Use the first .wav file we can find
        for file in wav_files:
            test_file = file
            break
    
    if not os.path.exists(test_file):
        logger.error(f"Test file {test_file} not found. Please provide a WAV file.")
        return
    
    logger.info(f"Testing ElevenLabs transcription with file: {test_file}")
    
    # Check WAV file properties
    if not check_wav_file(test_file):
        logger.error("Invalid WAV file. Please check the file format.")
        return
    
    try:
        # Initialize the ElevenLabs service
        api_key = os.getenv("ELEVEN_LABS_API_KEY")
        logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:] if api_key else 'None'}")
        
        elevenlabs_service = ElevenLabsService()
        
        # Make a direct API call with correct format
        logger.info("Making direct API call to ElevenLabs...")
        try:
            with open(test_file, "rb") as f:
                file_data = f.read()
            
            # Use proper multipart/form-data format
            files = {
                "audio": (os.path.basename(test_file), file_data, "audio/wav")
            }
            data = {
                "model_id": "eleven_turbo_v2",
                "language": "de"
            }
            headers = {
                "xi-api-key": api_key,
                # No Content-Type header - let requests set it for multipart/form-data
            }
            
            # Log request details
            logger.info(f"API URL: https://api.elevenlabs.io/v1/speech-to-text")
            logger.info(f"Headers: {headers}")
            logger.info(f"Data: {data}")
            logger.info(f"File name: {os.path.basename(test_file)}")
            logger.info(f"File size: {len(file_data)} bytes")
            
            response = requests.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers=headers,
                files=files,
                data=data
            )
            
            logger.info(f"Direct API response status: {response.status_code}")
            logger.info(f"Direct API response headers: {response.headers}")
            logger.info(f"Direct API response content: {response.text}")
            
            if response.status_code == 200:
                logger.info("Direct API call successful!")
                
        except Exception as e:
            logger.error(f"Error in direct API call: {str(e)}")
        
        # Try with a smaller sample to rule out file size issues
        logger.info("Testing with a smaller sample (first 10 seconds)...")
        try:
            # Create a temporary file with just the first 10 seconds
            temp_file = "temp_sample.wav"
            with wave.open(test_file, 'rb') as infile:
                n_frames = infile.getframerate() * 10  # 10 seconds of audio
                params = infile.getparams()
                with wave.open(temp_file, 'wb') as outfile:
                    outfile.setparams(params)
                    outfile.writeframes(infile.readframes(n_frames))
            
            # Check the temporary file
            check_wav_file(temp_file)
            
            # Test the service with the smaller file
            logger.info("Sending smaller file to ElevenLabs API via service...")
            result = await elevenlabs_service.speech_to_text(temp_file)
            
            # Log the raw API response
            logger.info("ElevenLabs API Response via service (smaller file):")
            logger.info(json.dumps(result.model_dump(), indent=2))
            
            # Extract and log the transcription text
            transcription = result.extract_text()
            logger.info(f"Transcription text (smaller file): {transcription}")
            
            # If that worked, return this result
            if transcription:
                logger.info("Test completed successfully with smaller file")
                return result
            
            # Otherwise, continue with the original file
            os.remove(temp_file)
            
        except Exception as e:
            logger.error(f"Error testing with smaller file: {str(e)}")
        
        # Test the speech-to-text API through our service with original file
        logger.info("Sending original file to ElevenLabs API via service...")
        result = await elevenlabs_service.speech_to_text(test_file)
        
        # Log the raw API response
        logger.info("ElevenLabs API Response via service:")
        logger.info(json.dumps(result.model_dump(), indent=2))
        
        # Extract and log the transcription text
        transcription = result.extract_text()
        logger.info(f"Transcription text: {transcription}")
        
        # Extract and log segments
        segments = result.extract_segments()
        logger.info("Extracted segments:")
        for i, segment in enumerate(segments):
            logger.info(f"Segment {i+1}: {segment}")
        
        logger.info("Test completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error testing ElevenLabs transcription: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_elevenlabs_transcription())
    
    # Print summary
    if result:
        print("\nSUMMARY:")
        print(f"Transcription: {result.extract_text()}")
        print("\nSegments:")
        for i, segment in enumerate(result.extract_segments()):
            print(f"Segment {i+1}: {segment}")
    else:
        print("\nTest failed. See log for details.") 