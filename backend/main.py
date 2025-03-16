from dotenv import load_dotenv
import os
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydub import AudioSegment

from models.process import ProcessStatus, ProcessInfo

from services.elevenlabs import ElevenLabsService
from services.language_feedback import LanguageFeedbackService
from services.allosaurus_service import AllosaurusService
from services.phonemizer_service import PhonemizerService

from utils import get_root_folder

load_dotenv(dotenv_path=get_root_folder() / ".env")


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
phenomizer_service = PhonemizerService()

def lcs(X, Y):
    m = len(X)
    n = len(Y)
    L = [[0] * (n + 1) for i in range(m + 1)]
    
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0 or j == 0:
                L[i][j] = 0
            elif X[i - 1] == Y[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])
    
    index = L[m][n]
    lcs_str = [""] * (index + 1)
    lcs_str[index] = ""
    
    i = m
    j = n
    while i > 0 and j > 0:
        if X[i - 1] == Y[j - 1]:
            lcs_str[index - 1] = X[i - 1]
            i -= 1
            j -= 1
            index -= 1
        elif L[i - 1][j] > L[i][j - 1]:
            i -= 1
        else:
            j -= 1
    
    return "".join(lcs_str)

# Process WAV file
async def process_wav_file(process_id: str, file_path: str):
    try:
        # Update status to ElevenLabs processing
        active_processes[process_id].status = ProcessStatus.ELEVENLABS_PROCESSING
        active_processes[process_id].updated_at = datetime.now().isoformat()
        
        # Step 1: Send to ElevenLabs for speech-to-text
        elevenlabs_result = await elevenlabs_service.speech_to_text(file_path)


        # Construct segmented audio of just speaker_0
        speaker_0_segments = [segment for segment in elevenlabs_result.words if segment.speaker_id == "speaker_0"]
        speaker_0_audio_path = f"temp_{process_id}_speaker_0.wav"
        
        # Load the original audio file
        original_audio = AudioSegment.from_file(file_path)
        
        # Create an empty audio segment for speaker_0
        speaker_0_audio = AudioSegment.empty()
        
        # Iterate over the segments and extract the parts belonging to speaker_0
        for segment in speaker_0_segments:
            start_time = segment.start * 1000  # Convert to milliseconds
            end_time = segment.end * 1000  # Convert to milliseconds
            speaker_0_audio += original_audio[start_time:end_time]
        
        # Export the constructed audio to a new file
        speaker_0_audio.export(speaker_0_audio_path, format="wav")


        
        # Step 1.5: Process with Allosaurus for phoneme recognition
        allosaurus_result: str = await allosaurus_service.recognize_phonemes(speaker_0_audio_path)

        phonemizer_result = [
            await phenomizer_service.phonemize_string(word.text)
            for word in elevenlabs_result.words
            if word.speaker_id == "speaker_0"
        ]

        # Use hard-coded longest common subsequence to compare the two phoneme strings
        lcs_result = lcs(allosaurus_result, "".join(phonemizer_result))

        lcs_pieces = [""] * len(phonemizer_result)
        lcs_index = 0
        allosaurus_pieces = [""] * len(phonemizer_result)
        allosaurus_index = 0
        for j, phoneme in enumerate(phonemizer_result):
            i = 0
            while i < len(phoneme) and lcs_index < len(lcs_result):
                if phoneme[i] == lcs_result[lcs_index]:
                    while allosaurus_result[allosaurus_index] != lcs_result[lcs_index]:
                        allosaurus_pieces[j] += allosaurus_result[allosaurus_index]
                        allosaurus_index += 1
                    
                    allosaurus_pieces[j] += allosaurus_result[allosaurus_index]
                    allosaurus_index += 1

                    lcs_pieces[lcs_index] += phoneme[i]
                    lcs_index += 1
                i += 1
        
        phonetic_correction = [*zip(allosaurus_pieces, lcs_pieces)]
        
        # Step 2: Send to Mistral
        active_processes[process_id].status = ProcessStatus.MISTRAL_PROCESSING
        active_processes[process_id].updated_at = datetime.now().isoformat()
        
        # Extract text from ElevenLabs result and send to Mistral
        elevenlabs_segments = elevenlabs_result.extract_segments()
        mistral_result = await mistral_service.process_transcript(elevenlabs_result, elevenlabs_segments)
        summary = await mistral_service.summarize_conversation(elevenlabs_result)
        
        # Update process with final result
        active_processes[process_id].status = ProcessStatus.COMPLETE
        active_processes[process_id].updated_at = datetime.now().isoformat()
        active_processes[process_id].result = {
            "elevenlabs": elevenlabs_segments,
            "mistral": mistral_result,
            "summary": summary,
            "phonetic_correction": phonetic_correction
        }
        
    except Exception as e:
        # Update process with error
        active_processes[process_id].status = ProcessStatus.FAILED
        active_processes[process_id].updated_at = datetime.now().isoformat()
        active_processes[process_id].error = str(e)
        
    finally:
        pass
        # Clean up the temporary file
        # if os.path.exists(file_path):
        #     os.remove(file_path)

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
    temp_file_path = str(get_root_folder() / f"backend/temp_{process_id}.wav")
    
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