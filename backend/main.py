from dotenv import load_dotenv
import os
import uuid
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks, File, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
async def process_wav_file(process_id: str, file_path: str, includePhonetics: bool = False):
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
            
            # Debug logs
            logger.info(f"ElevenLabs segments type: {type(elevenlabs_segments)}")
            logger.info(f"ElevenLabs segments count: {len(elevenlabs_segments)}")
            logger.info(f"ElevenLabs segments sample: {elevenlabs_segments[:2]}")
            
            # Convert Pydantic models to dictionaries if needed
            if elevenlabs_segments and isinstance(elevenlabs_segments, list):
                elevenlabs_segments = [
                    item.dict() if hasattr(item, "dict") else item 
                    for item in elevenlabs_segments
                ]
                logger.info(f"Converted segments sample: {elevenlabs_segments[:2]}")
            
            partial_results["elevenlabs"] = elevenlabs_segments
            
            # Update status for intermediate completion
            active_processes[process_id].status = ProcessStatus.ELEVENLABS_COMPLETE
            active_processes[process_id].updated_at = datetime.now().isoformat()
            active_processes[process_id].result = partial_results
            
            # Debug log for what we're storing
            logger.info(f"Stored elevenlabs result type: {type(partial_results['elevenlabs'])}")
            if isinstance(partial_results["elevenlabs"], list) and len(partial_results["elevenlabs"]) > 0:
                logger.info(f"First elevenlabs result item type: {type(partial_results['elevenlabs'][0])}")
                logger.info(f"First elevenlabs result item: {partial_results['elevenlabs'][0]}")
            
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
            mistral_result = await mistral_service.process_transcript(
                elevenlabs_result, 
                elevenlabs_segments, 
                include_phonetics=includePhonetics,
                phonetics_data=partial_results.get("allosaurus", None) if includePhonetics else None
            )
            
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
async def upload_file(
    file: UploadFile = File(...)
):
    """
    Upload a WAV file without starting processing.
    
    This endpoint only uploads and saves the file, creating a process record.
    To start processing, call the /start-processing/{process_id} endpoint.
    
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
    
    # Initialize process info but set status as UPLOADED (not PENDING)
    process_info = ProcessInfo(
        id=process_id,
        status="uploaded",  # Custom status for files not yet processed
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    active_processes[process_id] = process_info
    
    return process_info

@app.post("/start-processing/{process_id}", response_model=ProcessInfo, summary="Start processing an uploaded file")
async def start_processing(
    process_id: str,
    background_tasks: BackgroundTasks,
    includePhonetics: bool = Form(False, description="Whether to include phonetics data in analysis")
):
    """
    Start processing a previously uploaded file identified by process_id.
    
    Returns the updated process ID info with status set to PENDING.
    
    - **includePhonetics**: If True, phonetics data will be included in the analysis for improved pronunciation feedback
    """
    if process_id not in active_processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    # Find the temp file
    temp_file_path = f"temp_{process_id}.wav"
    
    # Check if the file exists
    if not os.path.exists(temp_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Update process status to PENDING
    active_processes[process_id].status = ProcessStatus.PENDING
    active_processes[process_id].updated_at = datetime.now().isoformat()
    
    # Start processing in background
    background_tasks.add_task(process_wav_file, process_id, temp_file_path, includePhonetics)
    
    return active_processes[process_id]

@app.get("/status/{process_id}", response_model=None, summary="Check the status of a process")
async def check_status(process_id: str):
    """
    Check the status of a process.
    
    Returns the current status, creation time, last update time, and result (if available).
    """
    if process_id not in active_processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    # Log the data we're returning
    process_info = active_processes[process_id]
    if process_info.result and "elevenlabs" in process_info.result:
        logger.info(f"Status endpoint - elevenlabs result type: {type(process_info.result['elevenlabs'])}")
        if isinstance(process_info.result["elevenlabs"], list) and len(process_info.result["elevenlabs"]) > 0:
            logger.info(f"Status endpoint - first item type: {type(process_info.result['elevenlabs'][0])}")
            # Check if it's a Pydantic model that needs to be converted
            if hasattr(process_info.result["elevenlabs"][0], "dict"):
                logger.info("Converting Pydantic models to dictionaries...")
                # It's possible the data is still in Pydantic model form
                process_info.result["elevenlabs"] = [
                    item.dict() if hasattr(item, "dict") else item 
                    for item in process_info.result["elevenlabs"]
                ]
    
    # Convert to dict and ensure all objects are JSON serializable
    try:
        process_dict = process_info.dict()
        # Test serialization
        json.dumps(process_dict)
        return process_dict
    except TypeError as e:
        logger.error(f"Serialization error: {str(e)}")
        # Fall back to a simpler representation
        safe_result = {
            "id": process_info.id,
            "status": process_info.status,
            "created_at": process_info.created_at,
            "updated_at": process_info.updated_at,
            "error": process_info.error
        }
        
        # Handle the result manually
        if process_info.result:
            safe_result["result"] = {}
            if "elevenlabs" in process_info.result:
                if isinstance(process_info.result["elevenlabs"], list):
                    safe_result["result"]["elevenlabs"] = []
                    for item in process_info.result["elevenlabs"]:
                        if isinstance(item, dict):
                            # Keep only primitive types
                            safe_item = {
                                "speaker_id": str(item.get("speaker_id", "speaker_0")),
                                "content": str(item.get("content", ""))
                            }
                            safe_result["result"]["elevenlabs"].append(safe_item)
                        elif hasattr(item, "dict"):
                            # It's a Pydantic model
                            item_dict = item.dict()
                            safe_item = {
                                "speaker_id": str(item_dict.get("speaker_id", "speaker_0")),
                                "content": str(item_dict.get("content", ""))
                            }
                            safe_result["result"]["elevenlabs"].append(safe_item)
                        else:
                            # It's a primitive type like string
                            safe_result["result"]["elevenlabs"].append(str(item))
            
            # Copy other result fields
            for key in process_info.result:
                if key != "elevenlabs":
                    safe_result["result"][key] = process_info.result[key]
        
        return safe_result

@app.post("/reprocess/{process_id}", response_model=ProcessInfo, summary="Reprocess an existing audio file")
async def reprocess_audio(
    process_id: str, 
    background_tasks: BackgroundTasks, 
    includePhonetics: bool = Form(False, description="Whether to include phonetics data in analysis")
):
    """
    Reprocess an existing audio file by its process ID.
    
    This will create a new process with a new ID that reprocesses the same audio file.
    Returns a new process ID that can be used to check the status of the processing.
    
    - **includePhonetics**: If True, phonetics data will be included in the analysis for improved pronunciation feedback
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
    background_tasks.add_task(process_wav_file, new_process_id, new_temp_file_path, includePhonetics)
    
    return new_process_info

@app.post("/use-sample", response_model=ProcessInfo, summary="Use the sample.wav file for processing")
async def use_sample(
    background_tasks: BackgroundTasks,
    includePhonetics: bool = Form(False, description="Whether to include phonetics data in analysis")
):
    """
    Process the sample.wav file that's included with the backend.
    
    This creates a new processing job for the sample audio file.
    Returns a process ID that can be used to check the status of the processing.
    
    - **includePhonetics**: If True, phonetics data will be included in the analysis for improved pronunciation feedback
    """
    # Check if sample file exists - use absolute path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_file_path = os.path.join(current_dir, "sample.wav")
    
    if not os.path.exists(sample_file_path):
        raise HTTPException(status_code=404, detail="Sample audio file not found")
    
    # Generate a unique ID for this process
    process_id = str(uuid.uuid4())
    
    # Initialize process info
    process_info = ProcessInfo(
        id=process_id,
        status=ProcessStatus.PENDING,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    active_processes[process_id] = process_info
    
    # Start processing in background
    background_tasks.add_task(process_wav_file, process_id, sample_file_path, includePhonetics)
    
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