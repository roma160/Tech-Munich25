# Speech Processing API

A FastAPI-based backend for processing speech data through ElevenLabs Speech-to-Text API and Mistral for further text analysis.

## Features

- Speech-to-text conversion using ElevenLabs API
- Text processing using Mistral (currently mocked)
- Professional Swagger UI documentation
- Asynchronous processing with status tracking
- Polling endpoint for frontend status checks

## Setup

### Prerequisites

- Python 3.8 or higher
- ElevenLabs API key

### Installation

1. Clone the repository

2. Navigate to the backend directory
   ```
   cd Tech-Munich25/backend
   ```

3. Create a virtual environment
   ```
   python -m venv venv
   ```

4. Activate the virtual environment
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

5. Install dependencies
   ```
   pip install -r requirements.txt
   ```

6. Create a `.env` file in the project root directory (one level up from backend)
   ```
   ELEVEN_LABS_API_KEY=your_api_key_here
   ```

## Running the server

Start the development server:

```
python main.py
```

This will start the server at `http://localhost:8000`.

## API Documentation

Once the server is running, you can access:

- Swagger UI documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## API Endpoints

- `GET /`: Root endpoint with API information
- `POST /upload`: Upload a WAV file for processing
- `GET /status/{process_id}`: Check the status of a processing job

## Project Structure

```
backend/
├── main.py              # Main application file
├── requirements.txt     # Project dependencies
├── README.md            # This file
├── models/              # Data models
│   ├── __init__.py
│   └── process.py       # Process tracking models
└── services/            # External API services
    ├── __init__.py
    ├── elevenlabs.py    # ElevenLabs API integration
    └── mistral.py       # Mistral API integration (mock)
``` 