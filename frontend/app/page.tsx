'use client';

import { useState } from 'react';
import AudioRecorder from '../components/AudioRecorder';
import ResultsDisplay from '../components/ResultsDisplay';
import { uploadAudio, pollStatus, ProcessResponse } from '../lib/api';

export default function Home() {
  const [processId, setProcessId] = useState<string | null>(null);
  const [results, setResults] = useState<ProcessResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRecordingComplete = async (audioBlob: Blob) => {
    try {
      setIsUploading(true);
      setError(null);
      
      // Create WAV file from blob
      const file = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
      
      // Upload to backend
      const response = await uploadAudio(file);
      const newProcessId = response.id;
      setProcessId(newProcessId);
      
      // Set initial results from upload response
      setResults(response);
      
      setIsUploading(false);
      setIsProcessing(true);
      
      // Poll for status updates
      pollStatus(newProcessId, (response) => {
        setResults(response);
        
        if (response.status === 'completed' || response.status === 'failed') {
          setIsProcessing(false);
        }
      });
    } catch (err) {
      setIsUploading(false);
      setIsProcessing(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      console.error('Error processing audio:', err);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Speech Processing Application</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <AudioRecorder onRecordingComplete={handleRecordingComplete} />
          
          {error && (
            <div className="mt-4 p-4 bg-red-100 text-red-800 rounded-lg">
              {error}
            </div>
          )}
          
          {isUploading && (
            <div className="mt-4 p-4 bg-blue-100 text-blue-800 rounded-lg">
              Uploading audio file...
            </div>
          )}
          
          {processId && !isUploading && (
            <div className="mt-4 p-4 bg-gray-100 rounded-lg">
              <p className="font-semibold">Process ID:</p>
              <code className="block mt-1 p-2 bg-gray-200 rounded">{processId}</code>
            </div>
          )}
        </div>
        
        <div>
          <ResultsDisplay 
            results={results} 
            isLoading={isProcessing} 
          />
        </div>
      </div>
    </div>
  );
} 