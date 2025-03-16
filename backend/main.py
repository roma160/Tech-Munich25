from dotenv import load_dotenv
import os
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import logging

from models.process import ProcessStatus, ProcessInfo

from services.elevenlabs import ElevenLabsService
from services.language_feedback import LanguageFeedbackService
from services.allosaurus_service import AllosaurusService

from utils import get_root_folder

load_dotenv(dotenv_path=get_root_folder() / ".env")

logger = logging.getLogger(__name__)

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

# Singleton instances
mistral_service = LanguageFeedbackService() 
elevenlabs_service = ElevenLabsService() 
allosaurus_service = AllosaurusService()


# Process WAV file
async def process_wav_file(process_id: str, file_path: str):
    try:
        # Update status to ElevenLabs processing
        active_processes[process_id].status = ProcessStatus.ELEVENLABS_PROCESSING
        active_processes[process_id].updated_at = datetime.now().isoformat()
        
        # Initialize result dictionary to store partial results
        partial_results = {}
        
        try:
            # Step 1: Send to ElevenLabs for speech-to-text
            elevenlabs_result = await elevenlabs_service.speech_to_text(file_path)
            elevenlabs_segments = elevenlabs_result.extract_segments()
            partial_results["elevenlabs"] = elevenlabs_segments
            
            # Update status for intermediate completion
            active_processes[process_id].status = ProcessStatus.ELEVENLABS_COMPLETE
            active_processes[process_id].updated_at = datetime.now().isoformat()
            active_processes[process_id].result = partial_results
        except Exception as e:
            logger.error(f"Error in ElevenLabs processing: {str(e)}")
            raise Exception(f"Speech-to-text processing failed: {str(e)}")
        
        try:
            # Step 1.5: Process with Allosaurus for phoneme recognition
            allosaurus_result = await allosaurus_service.recognize_phonemes(file_path)
            partial_results["allosaurus"] = allosaurus_result
            
            # Update status and partial results
            active_processes[process_id].status = ProcessStatus.ALLOSAURUS_PROCESSING
            active_processes[process_id].updated_at = datetime.now().isoformat()
            active_processes[process_id].result = partial_results
        except Exception as e:
            logger.error(f"Error in Allosaurus processing: {str(e)}")
            # Continue even if Allosaurus fails
            partial_results["allosaurus"] = {"error": str(e)}
        
        # Update status to Mistral processing
        active_processes[process_id].status = ProcessStatus.MISTRAL_PROCESSING
        active_processes[process_id].updated_at = datetime.now().isoformat()
        
        try:
            # Step 2: Send to Mistral for language feedback and summary
            mistral_result = await mistral_service.process_transcript(elevenlabs_result, elevenlabs_segments)
            summary = await mistral_service.summarize_conversation(elevenlabs_result)
            
            partial_results["mistral"] = mistral_result
            partial_results["summary"] = summary
        except Exception as e:
            logger.error(f"Error in Mistral processing: {str(e)}")
            # Continue with empty results if Mistral fails
            partial_results["mistral"] = {
                "mistakes": [],
                "inaccuracies": [],
                "vocabularies": []
            }
            partial_results["summary"] = "Could not generate summary due to an error."
        
        # Update process with final result - keep any partial results we got
        active_processes[process_id].status = ProcessStatus.COMPLETE
        active_processes[process_id].updated_at = datetime.now().isoformat()
        active_processes[process_id].result = partial_results
        
    except Exception as e:
        # Update process with error
        active_processes[process_id].status = ProcessStatus.FAILED
        active_processes[process_id].updated_at = datetime.now().isoformat()
        active_processes[process_id].error = str(e)
        
    finally:
        # Keep temporary file for potential reprocessing
        # Uncomment the following lines if you want to clean up files immediately
        # if os.path.exists(file_path):
        #     try:
        #         os.remove(file_path)
        #     except Exception as cleanup_error:
        #         logger.error(f"Error removing temporary file {file_path}: {str(cleanup_error)}")
        pass

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

@app.get("/status/{process_id}", response_model=ProcessInfo, summary="Check the status of a process")
async def check_status(process_id: str):
    """
    Check the status of a process.
    
    Returns the current status, creation time, last update time, and result (if available).
    """
    if process_id not in active_processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    return active_processes[process_id]

@app.post("/reprocess/{process_id}", response_model=ProcessInfo, summary="Reprocess an existing audio file")
async def reprocess_audio(process_id: str, background_tasks: BackgroundTasks):
    """
    Reprocess an existing audio file by its process ID.
    
    This will create a new process with a new ID that reprocesses the same audio file.
    Returns a new process ID that can be used to check the status of the processing.
    """
    if process_id not in active_processes:
        raise HTTPException(status_code=404, detail="Original process not found")
    
    # Find the original temp file
    original_temp_file = f"temp_{process_id}.wav"
    
    # Check if the file still exists, it might have been deleted
    if not os.path.exists(original_temp_file):
        raise HTTPException(status_code=404, detail="Original audio file no longer available")
    
    # Generate a new process ID
    new_process_id = str(uuid.uuid4())
    
    # Create a copy of the original file with the new process ID
    new_temp_file_path = f"temp_{new_process_id}.wav"
    try:
        with open(original_temp_file, "rb") as src_file:
            with open(new_temp_file_path, "wb") as dst_file:
                dst_file.write(src_file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error copying audio file: {str(e)}")
    
    # Initialize new process info
    new_process_info = ProcessInfo(
        id=new_process_id,
        status=ProcessStatus.PENDING,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    active_processes[new_process_id] = new_process_info
    
    # Start processing in background
    background_tasks.add_task(process_wav_file, new_process_id, new_temp_file_path)
    
    return new_process_info

@app.post("/use-sample", response_model=ProcessInfo, summary="Use the sample.wav file for processing")
async def use_sample(background_tasks: BackgroundTasks):
    """
    Process the sample.wav file that's included with the backend.
    
    This creates a new processing job for the sample audio file.
    Returns a process ID that can be used to check the status of the processing.
    """
    # Check if sample file exists - use absolute path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_file_path = os.path.join(current_dir, "sample.wav")
    
    if not os.path.exists(sample_file_path):
        # Try alternative locations
        alt_paths = [
            "sample.wav",  # Current working directory
            os.path.join(current_dir, "..", "sample.wav"),  # Parent directory
        ]
        
        for path in alt_paths:
            if os.path.exists(path):
                sample_file_path = path
                break
        else:
            raise HTTPException(status_code=404, detail=f"Sample audio file not found. Tried: {sample_file_path} and alternatives")
    
    # Generate a unique ID for this process
    process_id = str(uuid.uuid4())
    
    # Create a copy of the sample file with the process ID
    temp_file_path = f"temp_{process_id}.wav"
    try:
        with open(sample_file_path, "rb") as src_file:
            with open(temp_file_path, "wb") as dst_file:
                dst_file.write(src_file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error copying sample file: {str(e)}")
    
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

@app.get("/sample.wav", summary="Get the sample WAV file")
async def get_sample_file():
    """
    Serve the sample.wav file.
    
    This endpoint allows direct access to the sample audio file.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_file_path = os.path.join(current_dir, "sample.wav")
    
    if not os.path.exists(sample_file_path):
        # Try alternative locations
        alt_paths = [
            "sample.wav",  # Current working directory
            os.path.join(current_dir, "..", "sample.wav"),  # Parent directory
        ]
        
        for path in alt_paths:
            if os.path.exists(path):
                sample_file_path = path
                break
        else:
            raise HTTPException(status_code=404, detail="Sample audio file not found")
    
    return FileResponse(sample_file_path, media_type="audio/wav", filename="sample.wav")

@app.get("/", summary="API root endpoint")
async def root():
    """
    Root endpoint providing basic information about the API.
    """
    return {"message": "Welcome to the Speech Processing API. Visit /docs for documentation."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)