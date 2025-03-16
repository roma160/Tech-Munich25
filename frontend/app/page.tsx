'use client';

import { useState } from 'react';
import AudioRecorder from '../components/AudioRecorder';
import ResultsDisplay from '../components/ResultsDisplay';
import { uploadAudio, pollStatus, reprocessAudio, useSampleAudio, ProcessResponse, startProcessing } from '../lib/api';
import Link from 'next/link';

// Interface for recording entry
interface RecordingEntry {
  id: string;
  response: ProcessResponse;
  isProcessing: boolean;
  audioUrl?: string;
}

export default function Home() {
  const [recordings, setRecordings] = useState<RecordingEntry[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRecordingId, setSelectedRecordingId] = useState<string | null>(null);
  const [includePhonetics, setIncludePhonetics] = useState(false);

  const handleRecordingComplete = async (audioBlob: Blob) => {
    try {
      setIsUploading(true);
      setError(null);
      
      // Create WAV file from blob
      const file = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
      
      // Create URL for audio preview
      const audioURL = URL.createObjectURL(audioBlob);
      
      // Upload to backend - only upload, no processing yet
      const response = await uploadAudio(file);
      const newRecording: RecordingEntry = {
        id: response.id,
        response,
        isProcessing: false, // Not processing yet
        audioUrl: audioURL
      };
      
      // Add to recordings list
      setRecordings(prev => [newRecording, ...prev]);
      setSelectedRecordingId(response.id);
      
      setIsUploading(false);
    } catch (err) {
      setIsUploading(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      console.error('Error processing audio:', err);
    }
  };

  // Handle file uploads
  const handleFileUpload = async (file: File) => {
    try {
      setIsUploading(true);
      setError(null);
      
      // Create URL for audio preview
      const audioURL = URL.createObjectURL(file);
      
      // Upload to backend - only upload, no processing yet
      const response = await uploadAudio(file);
      const newRecording: RecordingEntry = {
        id: response.id,
        response,
        isProcessing: false, // Not processing yet
        audioUrl: audioURL
      };
      
      // Add to recordings list
      setRecordings(prev => [newRecording, ...prev]);
      setSelectedRecordingId(response.id);
      
      setIsUploading(false);
    } catch (err) {
      setIsUploading(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      console.error('Error processing audio file:', err);
    }
  };

  // Handle starting processing for a recording
  const handleStartProcessing = async () => {
    if (!selectedRecordingId) return;
    
    try {
      setIsUploading(true);
      setError(null);
      
      // Update the recording to processing state
      setRecordings(prev => 
        prev.map(rec => 
          rec.id === selectedRecordingId 
            ? { ...rec, isProcessing: true } 
            : rec
        )
      );
      
      // Start processing
      const response = await startProcessing(selectedRecordingId, includePhonetics);
      
      // Update recordings list with the new status
      setRecordings(prev => 
        prev.map(rec => 
          rec.id === selectedRecordingId 
            ? { ...rec, response: response } 
            : rec
        )
      );
      
      setIsUploading(false);
      
      // Poll for status updates
      pollStatus(selectedRecordingId, (updatedResponse) => {
        setRecordings(prev => 
          prev.map(rec => 
            rec.id === selectedRecordingId 
              ? { 
                  ...rec, 
                  response: updatedResponse, 
                  isProcessing: !(updatedResponse.status === 'complete' || updatedResponse.status === 'failed')
                } 
              : rec
          )
        );
      });
    } catch (err) {
      setIsUploading(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      console.error('Error starting processing:', err);
    }
  };

  // Handle using the sample audio
  const handleUseSample = async () => {
    try {
      setIsUploading(true);
      setError(null);
      
      // Create audio URL for sample.wav
      const sampleAudioURL = "/api/sample.wav"; // URL to sample file
      
      // Request processing of sample file - for simplicity, we'll use the existing endpoint which
      // processes it immediately
      const response = await useSampleAudio(includePhonetics);
      const newRecording: RecordingEntry = {
        id: response.id,
        response,
        isProcessing: true,
        audioUrl: sampleAudioURL // Use the direct URL to the sample file
      };
      
      // Add to recordings list
      setRecordings(prev => [newRecording, ...prev]);
      setSelectedRecordingId(response.id);
      
      setIsUploading(false);
      
      // Poll for status updates
      pollStatus(response.id, (updatedResponse) => {
        setRecordings(prev => 
          prev.map(rec => 
            rec.id === response.id 
              ? { 
                  ...rec, 
                  response: updatedResponse, 
                  isProcessing: !(updatedResponse.status === 'complete' || updatedResponse.status === 'failed')
                } 
              : rec
          )
        );
      });
    } catch (err) {
      setIsUploading(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      console.error('Error processing sample audio:', err);
    }
  };

  // Handle reprocessing an existing recording
  const handleReprocessRecording = async () => {
    if (!selectedRecordingId) return;
    
    try {
      setIsUploading(true);
      setError(null);
      
      // Get the original recording
      const originalRecording = recordings.find(r => r.id === selectedRecordingId);
      if (!originalRecording) {
        throw new Error("Selected recording not found");
      }
      
      // Send reprocess request
      const response = await reprocessAudio(selectedRecordingId, includePhonetics);
      const newRecording: RecordingEntry = {
        id: response.id,
        response,
        isProcessing: true,
        audioUrl: originalRecording.audioUrl
      };
      
      // Add to recordings list
      setRecordings(prev => [newRecording, ...prev]);
      setSelectedRecordingId(response.id);
      
      setIsUploading(false);
      
      // Poll for status updates
      pollStatus(response.id, (updatedResponse) => {
        setRecordings(prev => 
          prev.map(rec => 
            rec.id === response.id 
              ? { 
                  ...rec, 
                  response: updatedResponse, 
                  isProcessing: !(updatedResponse.status === 'complete' || updatedResponse.status === 'failed')
                } 
              : rec
          )
        );
      });
    } catch (err) {
      setIsUploading(false);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      console.error('Error reprocessing recording:', err);
    }
  };

  // Get the selected recording
  const selectedRecording = selectedRecordingId 
    ? recordings.find(r => r.id === selectedRecordingId) 
    : recordings[0];

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Speech Processing Application</h1>
      
      <div className="flex justify-end mb-4">
        <Link href="/test-page" className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm">
          Test Page
        </Link>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <AudioRecorder 
            onRecordingComplete={handleRecordingComplete} 
            onFileUpload={handleFileUpload}
            onUseSample={handleUseSample}
          />
          
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
          
          {recordings.length > 0 && (
            <div className="mt-6">
              <h3 className="text-xl font-semibold mb-2">Your Recordings</h3>
              <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-lg">
                {recordings.map((rec) => (
                  <div 
                    key={rec.id}
                    onClick={() => setSelectedRecordingId(rec.id)}
                    className={`p-3 border-b border-gray-200 cursor-pointer ${
                      selectedRecordingId === rec.id ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <div className="font-mono text-sm truncate">{rec.id}</div>
                      <div className={`text-xs px-2 py-1 rounded-full ${
                        rec.isProcessing 
                          ? 'bg-yellow-100 text-yellow-800' 
                          : rec.response.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-green-100 text-green-800'
                      }`}>
                        {rec.response.status}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div>
          <ResultsDisplay 
            results={selectedRecording?.response || null} 
            isLoading={selectedRecording?.isProcessing || false}
            audioUrl={selectedRecording?.audioUrl}
            onReprocess={selectedRecordingId ? handleReprocessRecording : undefined}
            includePhonetics={includePhonetics}
            onTogglePhonetics={() => setIncludePhonetics(!includePhonetics)}
            onStartProcessing={selectedRecordingId && selectedRecording?.response.status === 'uploaded' ? handleStartProcessing : undefined}
          />
        </div>
      </div>
    </div>
  );
} 