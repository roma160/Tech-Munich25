import axios from 'axios';

// Create a custom axios instance with specific configuration
const apiClient = axios.create({
  baseURL: '/api',
});

// Response interface from backend
export interface ProcessResponse {
  id: string;
  status: 'pending' | 'elevenlabs_processing' | 'elevenlabs_complete' | 
          'allosaurus_processing' | 'allosaurus_complete' | 
          'mistral_processing' | 'complete' | 'failed' | 'uploaded';
  created_at: string;
  updated_at: string;
  result?: {
    elevenlabs?: any;
    mistral?: any;
    summary?: string;
    allosaurus?: any;
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
    
    const response = await apiClient.post<UploadResponse>('/upload', formData, {
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
    const response = await apiClient.get<ProcessResponse>(`/status/${processId}`);
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
      
      if (response.status !== 'complete' && response.status !== 'failed' && attempts < maxAttempts) {
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

/**
 * Request reprocessing of an existing audio file
 */
export const reprocessAudio = async (processId: string, includePhonetics: boolean = false): Promise<UploadResponse> => {
  try {
    // Create URLSearchParams for form data
    const formData = new URLSearchParams();
    formData.append('includePhonetics', includePhonetics.toString());
    
    const response = await apiClient.post<UploadResponse>(`/reprocess/${processId}`, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error reprocessing audio:', error);
    throw error;
  }
};

/**
 * Request processing of the sample.wav file
 */
export const useSampleAudio = async (includePhonetics: boolean = false): Promise<UploadResponse> => {
  try {
    // Create URLSearchParams for form data
    const formData = new URLSearchParams();
    formData.append('includePhonetics', includePhonetics.toString());
    
    const response = await apiClient.post<UploadResponse>('/use-sample', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error processing sample audio:', error);
    throw error;
  }
};

/**
 * Start processing a previously uploaded file
 */
export const startProcessing = async (processId: string, includePhonetics: boolean = false): Promise<UploadResponse> => {
  try {
    // Create URLSearchParams for form data
    const formData = new URLSearchParams();
    formData.append('includePhonetics', includePhonetics.toString());
    
    const response = await apiClient.post<UploadResponse>(`/start-processing/${processId}`, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error starting processing:', error);
    throw error;
  }
}; 