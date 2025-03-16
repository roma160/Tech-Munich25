import axios from 'axios';

const API_BASE_URL = '/api';  // This will use Next.js API rewrite to proxy to backend

// Response interface from backend
export interface ProcessResponse {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  result?: {
    transcription?: string;
    phonemes?: string;
    allosaurus?: any;
    elevenlabs?: any;
    mistral?: any;
  };
  error?: string;
}

// Upload response from backend - matches ProcessInfo format from backend
interface UploadResponse extends ProcessResponse {}

/**
 * Upload audio file to backend for processing
 */
export const uploadAudio = async (file: File): Promise<UploadResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post<UploadResponse>(`${API_BASE_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  } catch (error) {
    console.error('Error uploading audio:', error);
    throw error;
  }
};

/**
 * Check status of a processing job
 */
export const checkStatus = async (processId: string): Promise<ProcessResponse> => {
  try {
    const response = await axios.get<ProcessResponse>(`${API_BASE_URL}/status/${processId}`);
    return response.data;
  } catch (error) {
    console.error('Error checking status:', error);
    throw error;
  }
};

/**
 * Poll status of a processing job until complete or failed
 */
export const pollStatus = (
  processId: string, 
  onUpdate: (response: ProcessResponse) => void,
  intervalMs = 2000,
  maxAttempts = 30
): void => {
  let attempts = 0;
  
  const poll = async () => {
    try {
      const response = await checkStatus(processId);
      onUpdate(response);
      
      if (response.status !== 'completed' && response.status !== 'failed' && attempts < maxAttempts) {
        attempts++;
        setTimeout(poll, intervalMs);
      }
    } catch (error) {
      console.error('Error polling status:', error);
      onUpdate({
        id: processId,
        status: 'failed',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        error: 'Failed to retrieve status',
      });
    }
  };
  
  poll();
}; 