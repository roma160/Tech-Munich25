import React from 'react';
import { ProcessResponse } from '../lib/api';

interface ResultsDisplayProps {
  results: ProcessResponse | null;
  isLoading: boolean;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ results, isLoading }) => {
  if (isLoading) {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Processing</h2>
        <div className="flex justify-center items-center h-40">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  if (!results) {
    return null;
  }

  const { status, result, error } = results;

  if (status === 'failed') {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4 text-red-500">Processing Failed</h2>
        <p className="text-red-500">{error || 'An unknown error occurred'}</p>
      </div>
    );
  }

  if (status === 'pending' || status === 'processing') {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Processing in Progress</h2>
        <p>Status: {status}</p>
        <div className="mt-4 w-full bg-gray-200 rounded-full h-2.5">
          <div className="bg-blue-600 h-2.5 rounded-full w-1/3"></div>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">No Results Available</h2>
        <p>The processing completed, but no results were returned.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Results</h2>
      
      {result.transcription && (
        <div className="mb-6">
          <h3 className="font-semibold text-lg mb-2">Transcription</h3>
          <div className="p-4 bg-gray-100 rounded-lg text-gray-800">
            {result.transcription}
          </div>
        </div>
      )}
      
      {result.phonemes && (
        <div className="mb-6">
          <h3 className="font-semibold text-lg mb-2">Phonemes</h3>
          <div className="p-4 bg-gray-100 rounded-lg text-gray-800 overflow-x-auto">
            <pre className="whitespace-pre-wrap">{result.phonemes}</pre>
          </div>
        </div>
      )}
      
      {result.allosaurus && (
        <div className="mb-6">
          <h3 className="font-semibold text-lg mb-2">Allosaurus Results</h3>
          <div className="p-4 bg-gray-100 rounded-lg text-gray-800">
            <pre className="whitespace-pre-wrap">{JSON.stringify(result.allosaurus, null, 2)}</pre>
          </div>
        </div>
      )}
      
      {result.elevenlabs && (
        <div className="mb-6">
          <h3 className="font-semibold text-lg mb-2">ElevenLabs Results</h3>
          <div className="p-4 bg-gray-100 rounded-lg text-gray-800">
            <pre className="whitespace-pre-wrap">{JSON.stringify(result.elevenlabs, null, 2)}</pre>
          </div>
        </div>
      )}
      
      {result.mistral && (
        <div>
          <h3 className="font-semibold text-lg mb-2">Mistral Results</h3>
          <div className="p-4 bg-gray-100 rounded-lg text-gray-800">
            <pre className="whitespace-pre-wrap">{JSON.stringify(result.mistral, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay; 