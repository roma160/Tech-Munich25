import React, { useState, useEffect, useRef } from 'react';
import Recorder from 'recorder-js';

interface AudioRecorderProps {
  onRecordingComplete: (audioBlob: Blob) => void;
  onFileUpload: (file: File) => void;
  onUseSample: () => void;
}

const AudioRecorder: React.FC<AudioRecorderProps> = ({ 
  onRecordingComplete, 
  onFileUpload,
  onUseSample
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPermissionGranted, setIsPermissionGranted] = useState(false);
  
  const recorderRef = useRef<any>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Initialize audio context and recorder
    const initRecorder = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;
        
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        recorderRef.current = new Recorder(audioContext, {
          onAnalysed: (data) => {
            // You can use this for visualizations
          },
        });
        
        await recorderRef.current.init(stream);
        setIsPermissionGranted(true);
      } catch (err) {
        console.error('Error initializing recorder:', err);
        setIsPermissionGranted(false);
      }
    };
    
    if (typeof window !== 'undefined' && navigator.mediaDevices) {
      initRecorder();
    }
    
    return () => {
      // Cleanup
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);
  
  const startRecording = () => {
    if (!recorderRef.current || !isPermissionGranted) return;
    
    recorderRef.current.start().then(() => {
      setIsRecording(true);
      setRecordingTime(0);
      setAudioUrl(null);
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    });
  };
  
  const stopRecording = () => {
    if (!recorderRef.current || !isRecording) return;
    
    recorderRef.current.stop().then(({ blob }: { blob: Blob }) => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      setIsRecording(false);
      
      // Create URL for audio preview
      const audioURL = URL.createObjectURL(blob);
      setAudioUrl(audioURL);
      
      // Pass blob to parent component
      onRecordingComplete(blob);
    });
  };
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === 'audio/wav' || file.name.endsWith('.wav')) {
        onFileUpload(file);
        
        // Create URL for audio preview
        const audioURL = URL.createObjectURL(file);
        setAudioUrl(audioURL);
      } else {
        alert('Please upload a WAV file');
      }
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleUseSample = () => {
    onUseSample();
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Audio Recorder</h2>
      
      {!isPermissionGranted ? (
        <div className="text-red-500 mb-4">
          Microphone access is required for recording. Please allow access in your browser settings.
        </div>
      ) : null}
      
      <div className="flex flex-col items-center">
        <div className="text-4xl font-mono mb-6">
          {formatTime(recordingTime)}
        </div>
        
        <div className="flex space-x-4">
          <button
            onClick={startRecording}
            disabled={isRecording || !isPermissionGranted}
            className={`btn ${isRecording ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            Start Recording
          </button>
          
          <button
            onClick={stopRecording}
            disabled={!isRecording}
            className={`btn-secondary ${!isRecording ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            Stop Recording
          </button>
        </div>
        
        {/* File upload section */}
        <div className="mt-6 w-full">
          <h3 className="font-semibold mb-2">Upload Audio</h3>
          <div className="flex flex-col space-y-3">
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/wav"
              onChange={handleFileChange}
              className="w-full border p-2 rounded"
            />
            
            <button 
              onClick={handleUseSample}
              className="btn bg-green-500 hover:bg-green-600 text-white"
            >
              Use Sample Audio
            </button>
          </div>
        </div>
        
        {audioUrl && (
          <div className="mt-6 w-full">
            <h3 className="font-semibold mb-2">Preview:</h3>
            <audio controls src={audioUrl} className="w-full" />
          </div>
        )}
      </div>
    </div>
  );
};

export default AudioRecorder; 