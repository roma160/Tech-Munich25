from dotenv import load_dotenv
import os
import asyncio
import uuid
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks, File, Query, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import models
from models.process import ProcessStatus, ProcessInfo
from models.pronunciation import PronunciationAssessmentResponse

# Import services
from services.elevenlabs import elevenlabs_service
from services.mistral import mistral_service
from services.pronunciation import pronunciation_service

from utils import get_root_folder

# Load environment variables from .env outside of the current directory
load_dotenv(dotenv_path=get_root_folder() / ".env")
# print(get_root_folder() / ".env")

# import sys
# sys.exit()

# Create FastAPI app
app = FastAPI(
    title="Speech Processing API",
    description="API for processing speech data using ElevenLabs and Mistral",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active processes
active_processes = {}

# Process WAV file
async def process_wav_file(process_id: str, file_path: str):
    try:
        # Update status to ElevenLabs processing
        active_processes[process_id].status = ProcessStatus.ELEVENLABS_PROCESSING
        active_processes[process_id].updated_at = datetime.now().isoformat()
        
        # Step 1: Send to ElevenLabs for speech-to-text
        elevenlabs_result = await elevenlabs_service.speech_to_text(file_path)
        
        # Update status after ElevenLabs
        active_processes[process_id].status = ProcessStatus.ELEVENLABS_COMPLETE
        active_processes[process_id].updated_at = datetime.now().isoformat()
        
        # Step 2: Send to Mistral
        active_processes[process_id].status = ProcessStatus.MISTRAL_PROCESSING
        active_processes[process_id].updated_at = datetime.now().isoformat()
        
        # Extract text from ElevenLabs result and send to Mistral
        text_content = elevenlabs_result.get("text", "")
        mistral_result = await mistral_service.process_text(text_content)
        
        # Update process with final result
        active_processes[process_id].status = ProcessStatus.COMPLETE
        active_processes[process_id].updated_at = datetime.now().isoformat()
        active_processes[process_id].result = {
            "elevenlabs": elevenlabs_result,
            "mistral": mistral_result
        }
        
    except Exception as e:
        # Update process with error
        active_processes[process_id].status = ProcessStatus.FAILED
        active_processes[process_id].updated_at = datetime.now().isoformat()
        active_processes[process_id].error = str(e)
        
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/upload", response_model=ProcessInfo, summary="Upload a WAV file for processing")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a WAV file for processing.
    
    The file will be processed in two steps:
    1. Speech-to-text conversion with ElevenLabs
    2. Text processing with Mistral
    
    Returns a process ID that can be used to check the status of the processing.
    """
    if not file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="File must be a WAV file")
    
    # Generate a unique ID for this process
    process_id = str(uuid.uuid4())
    
    # Create temporary file path
    temp_file_path = f"temp_{process_id}.wav"
    
    # Save uploaded file
    with open(temp_file_path, "wb") as f:
        f.write(await file.read())
    
    # Initialize process info
    process_info = ProcessInfo(
        id=process_id,
        status=ProcessStatus.PENDING,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    active_processes[process_id] = process_info
    
    # Start processing in background
    background_tasks.add_task(process_wav_file, process_id, temp_file_path)
    
    return process_info

@app.post("/assess_pronunciation", response_model=PronunciationAssessmentResponse, summary="Assess pronunciation of spoken text")
async def assess_pronunciation(file: UploadFile = File(...), reference_text: str = Form(...)):
    """
    Assess pronunciation of a spoken audio file against a reference text.
    
    This endpoint uses a neural network phoneme-level scoring approach (GOP-based) to:
    1. Convert reference text to phonemes
    2. Score each phoneme in the audio
    3. Generate feedback on pronunciation quality
    4. Provide synthesized audio of correct pronunciation
    
    Args:
        file: WAV audio file of spoken text to assess
        reference_text: The text that was supposed to be spoken
        
    Returns:
        Detailed pronunciation assessment with scores, feedback, and audio
    """
    if not file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="File must be a WAV file")
    
    # Read the file
    audio_data = await file.read()
    
    # Process with pronunciation assessment service
    try:
        result = await pronunciation_service.assess_pronunciation(audio_data, reference_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assessing pronunciation: {str(e)}")

@app.get("/status/{process_id}", response_model=ProcessInfo, summary="Check the status of a process")
async def check_status(process_id: str):
    """
    Check the status of a process.
    
    Returns the current status, creation time, last update time, and result (if available).
    """
    if process_id not in active_processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    return active_processes[process_id]

@app.get("/", summary="API root endpoint")
async def root():
    """
    Root endpoint providing basic information about the API.
    """
    return {
        "name": "Speech Processing API",
        "version": "1.0.0",
        "description": "API for processing speech data using ElevenLabs and Mistral",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)