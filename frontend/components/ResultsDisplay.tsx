import React, { useState } from 'react';
import { ProcessResponse } from '../lib/api';

interface ResultsDisplayProps {
  results: ProcessResponse | null;
  isLoading: boolean;
  audioUrl?: string | null;
  onReprocess?: () => void;
  includePhonetics?: boolean;
  onTogglePhonetics?: () => void;
  onStartProcessing?: () => void;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ 
  results, 
  isLoading, 
  audioUrl,
  onReprocess,
  includePhonetics = false,
  onTogglePhonetics,
  onStartProcessing
}) => {
  // State for toggleable sections
  const [showFullPhonetics, setShowFullPhonetics] = useState(false);
  const [showDetailedAnalysis, setShowDetailedAnalysis] = useState(false);

  if (!results) {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">No Recording Selected</h2>
        <p className="text-gray-500">Record audio or select a recording to see results</p>
      </div>
    );
  }

  const { status, result, error } = results;

  if (status === 'failed') {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4 text-red-500">Processing Failed</h2>
        <p className="text-red-500">{error || 'An unknown error occurred'}</p>
        {onReprocess && (
          <button 
            onClick={onReprocess}
            className="btn mt-4 bg-blue-500 hover:bg-blue-600 text-white"
          >
            Try Reprocessing
          </button>
        )}
      </div>
    );
  }

  // Handle uploaded but not processed status
  if (status === 'uploaded') {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Ready for Processing</h2>
        
        {/* Audio playback if available */}
        {audioUrl && (
          <div className="mb-6">
            <h3 className="font-semibold text-lg mb-2">Audio Recording</h3>
            <audio controls src={audioUrl} className="w-full" />
          </div>
        )}
        
        <div className="mb-6 flex justify-between items-center">
          <button 
            onClick={onStartProcessing}
            className="btn bg-green-500 hover:bg-green-600 text-white"
          >
            Start Processing
          </button>
          
          {onTogglePhonetics && (
            <div className="flex items-center">
              <input
                type="checkbox"
                id="includePhonetics"
                className="mr-2"
                checked={includePhonetics}
                onChange={onTogglePhonetics}
              />
              <label htmlFor="includePhonetics" className="text-sm text-gray-700">
                Include phonetics in analysis
              </label>
            </div>
          )}
        </div>
        
        <p className="text-gray-500">Click "Start Processing" to analyze this audio recording.</p>
      </div>
    );
  }

  // Calculate progress based on status
  const getProgress = () => {
    switch(status) {
      case 'pending': return 10;
      case 'elevenlabs_processing': return 25;
      case 'elevenlabs_complete': return 40;
      case 'allosaurus_processing': return 60;
      case 'allosaurus_complete': return 75;
      case 'mistral_processing': return 90;
      case 'complete': return 100;
      default: return 0;
    }
  };

  // Organize transcription by speaker
  const organizeTranscriptionBySpeaker = () => {
    if (!result?.elevenlabs) {
      console.log("No elevenlabs results found");
      return [];
    }

    // Clean print for objects to filter out unnecessary details
    const cleanPrint = (obj: any): any => {
      if (Array.isArray(obj)) {
        return obj.slice(0, 3).map(cleanPrint); // Show only first 3 items
      } else if (typeof obj === 'object' && obj !== null) {
        const clean: any = {};
        Object.keys(obj).forEach(key => {
          // Skip keys that look like IDs or timestamps
          if (!key.includes('_id') && !key.includes('_at')) {
            clean[key] = cleanPrint(obj[key]);
          } else {
            clean[key] = '[filtered]';
          }
        });
        return clean;
      }
      return obj;
    };

    console.log("ElevenLabs result type:", typeof result.elevenlabs);
    console.log("ElevenLabs data sample:", 
      Array.isArray(result.elevenlabs) 
        ? cleanPrint(result.elevenlabs.slice(0, 3)) 
        : cleanPrint(result.elevenlabs));

    // Check if the segments already have speaker information
    if (Array.isArray(result.elevenlabs) && result.elevenlabs.length > 0) {
      console.log("ElevenLabs is array with length:", result.elevenlabs.length);
      console.log("First item type:", typeof result.elevenlabs[0]);
      console.log("First item:", result.elevenlabs[0]);
      
      // Check if each item has speaker_id and content
      if (typeof result.elevenlabs[0] === 'object' && 
          'speaker_id' in result.elevenlabs[0] && 
          'content' in result.elevenlabs[0]) {
        console.log("Found proper speaker format");
        // Return as is - already properly formatted
        return result.elevenlabs;
      }
      
      // If they're just strings, create alternating speaker segments
      if (typeof result.elevenlabs[0] === 'string') {
        console.log("Found string array format");
        return result.elevenlabs.map((text, index) => {
          const speakerId = `speaker_${index % 2}`; // Alternate between speaker_0 and speaker_1
          return { speaker_id: speakerId, content: text };
        });
      }
    }
    
    // Fallback for unexpected format
    if (typeof result.elevenlabs === 'string') {
      console.log("Found single string format");
      return [{ speaker_id: 'speaker_0', content: result.elevenlabs }];
    }
    
    console.log("Unknown format, returning empty array");
    return [];
  };

  // Extract just the phonetic text from allosaurus
  const getPhoneticText = () => {
    if (!result?.allosaurus) return '';
    
    if (typeof result.allosaurus === 'object' && result.allosaurus.text) {
      return result.allosaurus.text;
    }
    
    if (typeof result.allosaurus === 'string') {
      return result.allosaurus;
    }
    
    return JSON.stringify(result.allosaurus);
  };

  // Get speaker name for display
  const getSpeakerName = (speakerId: string): string => {
    // Extract numeric part from speaker ID (e.g., "speaker_0" -> "0")
    const speakerNumber = speakerId.split('_')[1] || '0';
    return `Speaker ${parseInt(speakerNumber) + 1}`; // Make it 1-indexed for display
  };

  const progress = getProgress();
  const transcriptionSegments = organizeTranscriptionBySpeaker();

  // Helper function to highlight errors in text
  const highlightErrorsInText = (text: string, speakerSegmentIndex: number) => {
    if (!results?.result?.mistral) return text; // No errors to highlight

    // Combine all error types that have ranges
    const allErrors = [
      ...(results.result.mistral.mistakes || []).filter((err: any) => err.found_range && err.ranges),
      ...(results.result.mistral.inaccuracies || []).filter((err: any) => err.found_range && err.ranges),
      ...(results.result.mistral.phonetics || []).filter((err: any) => err.found_range && err.range)
    ];

    // No errors with ranges
    if (!allErrors.length) return text;

    // Find errors that apply to this segment
    const segmentErrors = allErrors.filter((err: any) => {
      if (err.ranges) {
        return err.ranges.some((range: any) => range[0] === speakerSegmentIndex);
      } else if (err.range) {
        return err.range[0] === speakerSegmentIndex;
      }
      return false;
    });

    if (!segmentErrors.length) return text;
    
    // Sort errors by their position in text (start index)
    const sortedErrors = segmentErrors.flatMap((err: any) => {
      if (err.ranges) {
        return err.ranges
          .filter((range: any) => range[0] === speakerSegmentIndex)
          .map((range: any) => ({
            start: range[1],
            end: range[2],
            type: err.error_type || 'phonetic',
            correction: err.correction || err.suggested_pronunciation,
            tooltip: err.phonetic_issue ? `${err.phonetic_issue}: ${err.suggested_pronunciation}` : 
                     `${err.error_type}: ${err.correction}`
          }));
      } else if (err.range && err.range[0] === speakerSegmentIndex) {
        return [{
          start: err.range[1],
          end: err.range[2],
          type: 'phonetic',
          correction: err.suggested_pronunciation,
          tooltip: `${err.phonetic_issue}: ${err.suggested_pronunciation}`
        }];
      }
      return [];
    }).sort((a, b) => a.start - b.start);

    // Replace text parts with highlighted versions
    let resultHtml = '';
    let lastIndex = 0;

    for (const error of sortedErrors) {
      // Add text before the error
      resultHtml += text.substring(lastIndex, error.start);
      
      // Add the highlighted error
      const errorText = text.substring(error.start, error.end);
      const errorClass = error.type === 'phonetic' ? 'text-purple-600 font-bold underline' :
                       error.type.includes('grammatical') ? 'text-red-600 font-bold underline' :
                       error.type.includes('stylistic') ? 'text-yellow-600 font-bold underline' :
                       'text-orange-600 font-bold underline';
      
      // Create a tooltip with error details                 
      const tooltip = error.tooltip || `${error.type}: "${errorText}" → "${error.correction}"`;
      
      resultHtml += `<span class="${errorClass}" title="${tooltip}">${errorText}</span>`;
      
      lastIndex = error.end;
    }
    
    // Add remaining text
    resultHtml += text.substring(lastIndex);
    
    return resultHtml;
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Results {status !== 'complete' && `(${status})`}</h2>
      
      {/* Audio playback if available */}
      {audioUrl && (
        <div className="mb-6">
          <h3 className="font-semibold text-lg mb-2">Audio Recording</h3>
          <audio controls src={audioUrl} className="w-full" />
        </div>
      )}
      
      {status !== 'complete' && (
        <div className="mb-6">
          <div className="flex justify-between mb-1">
            <span>Processing Status: {status}</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div 
              className="bg-blue-600 h-2.5 rounded-full" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      )}
      
      {/* Show reprocess button for completed items */}
      {status === 'complete' && onReprocess && (
        <div className="mb-6 flex justify-between items-center">
          <button 
            onClick={onReprocess}
            className="btn bg-blue-500 hover:bg-blue-600 text-white"
          >
            Reprocess Audio
          </button>
          
          {onTogglePhonetics && (
            <div className="flex items-center">
              <input
                type="checkbox"
                id="includePhonetics"
                className="mr-2"
                checked={includePhonetics}
                onChange={onTogglePhonetics}
              />
              <label htmlFor="includePhonetics" className="text-sm text-gray-700">
                Include phonetics in analysis
              </label>
            </div>
          )}
        </div>
      )}
      
      {/* Show ElevenLabs results if available - with speaker labels */}
      {result?.elevenlabs && (
        <div className="mb-6">
          <h3 className="font-semibold text-lg mb-2">Transcription</h3>
          <div className="rounded-lg">
            {transcriptionSegments.length > 0 ? (
              <div>
                {transcriptionSegments.map((segment, idx) => (
                  <div 
                    key={idx} 
                    className={`p-3 mb-2 rounded-lg ${
                      segment.speaker_id.includes('0') 
                        ? 'bg-blue-50 text-blue-800' 
                        : 'bg-green-50 text-green-800'
                    }`}
                  >
                    <div className="font-medium mb-1">{getSpeakerName(segment.speaker_id)}</div>
                    <p dangerouslySetInnerHTML={{
                      __html: highlightErrorsInText(segment.content, idx)
                    }}></p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 bg-gray-100 rounded-lg text-gray-800">
                {typeof result.elevenlabs === 'string' 
                  ? result.elevenlabs 
                  : JSON.stringify(result.elevenlabs, null, 2)}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Show Allosaurus results if available - with toggle */}
      {result?.allosaurus && (
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-lg">Phonetic Analysis</h3>
            <button 
              onClick={() => setShowFullPhonetics(!showFullPhonetics)}
              className="text-sm px-2 py-1 rounded bg-gray-200 hover:bg-gray-300"
            >
              {showFullPhonetics ? 'Show Simple View' : 'Show Full Details'}
            </button>
          </div>
          
          <div className="p-4 bg-gray-100 rounded-lg text-gray-800">
            {!showFullPhonetics ? (
              // Simple view - just the phonetic text
              <div className="whitespace-pre-wrap text-sm">
                {getPhoneticText()}
              </div>
            ) : (
              // Full view - all phonetic details
              <pre className="whitespace-pre-wrap overflow-x-auto text-sm">
                {typeof result.allosaurus === 'string' 
                  ? result.allosaurus 
                  : JSON.stringify(result.allosaurus, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
      
      {/* Show Mistral analysis if available - with toggle */}
      {result?.mistral && (
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-lg">Detailed Analysis</h3>
            <button 
              onClick={() => setShowDetailedAnalysis(!showDetailedAnalysis)}
              className="text-sm px-2 py-1 rounded bg-gray-200 hover:bg-gray-300"
            >
              {showDetailedAnalysis ? 'Show Simple View' : 'Show Full Details'}
            </button>
          </div>
          
          {!showDetailedAnalysis ? (
            // Simple view - formatted summary
            <div className="space-y-4">
              {typeof result.mistral === 'object' && (
                <>
                  {/* Mistakes section */}
                  <div className="p-4 bg-red-50 rounded-lg">
                    <h4 className="font-medium text-red-800 mb-2">Mistakes</h4>
                    {Array.isArray(result.mistral.mistakes) && result.mistral.mistakes.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-1">
                        {result.mistral.mistakes.map((mistake: any, idx: number) => (
                          <li key={idx} className="text-red-700">
                            {mistake.found_range ? (
                              // Highlight the error and show correction
                              <div>
                                <span className="font-bold text-red-800">{mistake.quote}</span>
                                <span className="text-gray-700"> → </span>
                                <span className="text-green-700">{mistake.correction}</span>
                                <span className="text-xs text-red-600 ml-2">({mistake.error_type})</span>
                              </div>
                            ) : (
                              // Display without highlight but still show the error
                              <div>
                                <span className="font-medium">{mistake.quote}</span>
                                <span className="text-gray-700"> → </span>
                                <span className="text-green-700">{mistake.correction}</span>
                                <span className="text-xs text-red-600 ml-2">({mistake.error_type})</span>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-600">No mistakes detected</p>
                    )}
                  </div>
                  
                  {/* Inaccuracies section */}
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <h4 className="font-medium text-yellow-800 mb-2">Inaccuracies</h4>
                    {Array.isArray(result.mistral.inaccuracies) && result.mistral.inaccuracies.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-1">
                        {result.mistral.inaccuracies.slice(0, 5).map((item: any, idx: number) => (
                          <li key={idx} className="text-yellow-700">
                            {item.found_range ? (
                              <div>
                                <span className="font-bold text-yellow-800">{item.quote}</span>
                                <span className="text-gray-700"> → </span>
                                <span className="text-green-700">{item.correction}</span>
                                <span className="text-xs text-yellow-600 ml-2">({item.error_type})</span>
                              </div>
                            ) : (
                              <div>
                                <span className="font-medium">{item.quote}</span>
                                <span className="text-gray-700"> → </span>
                                <span className="text-green-700">{item.correction}</span>
                                <span className="text-xs text-yellow-600 ml-2">({item.error_type})</span>
                              </div>
                            )}
                          </li>
                        ))}
                        {result.mistral.inaccuracies.length > 5 && (
                          <li className="text-yellow-700 italic">
                            And {result.mistral.inaccuracies.length - 5} more...
                          </li>
                        )}
                      </ul>
                    ) : (
                      <p className="text-gray-600">No inaccuracies detected</p>
                    )}
                  </div>
                  
                  {/* Vocabularies section */}
                  <div className="p-4 bg-green-50 rounded-lg">
                    <h4 className="font-medium text-green-800 mb-2">Vocabulary Suggestions</h4>
                    {Array.isArray(result.mistral.vocabularies) && result.mistral.vocabularies.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-1">
                        {result.mistral.vocabularies.map((item: any, idx: number) => (
                          <li key={idx} className="text-green-700">
                            {item.found_range ? (
                              <div>
                                <span className="font-bold text-green-800">{item.quote}</span>
                                <span className="text-gray-700"> → </span>
                                <span className="text-blue-700">{item.synonyms.join(', ')}</span>
                              </div>
                            ) : (
                              <div>
                                <span className="font-medium">{item.quote}</span>
                                <span className="text-gray-700"> → </span>
                                <span className="text-blue-700">{item.synonyms.join(', ')}</span>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-600">No vocabulary suggestions available</p>
                    )}
                  </div>
                  
                  {/* Phonetics section */}
                  {Array.isArray(result.mistral.phonetics) && result.mistral.phonetics.length > 0 && (
                    <div className="p-4 bg-purple-50 rounded-lg">
                      <h4 className="font-medium text-purple-800 mb-2">Pronunciation Feedback</h4>
                      <ul className="list-disc pl-5 space-y-2">
                        {result.mistral.phonetics.map((item: any, idx: number) => (
                          <li key={idx} className="text-purple-700">
                            {item.found_range ? (
                              <div>
                                <div>
                                  <span className="font-bold text-purple-800">{item.quote}</span>
                                </div>
                                <div className="text-sm text-purple-600 mt-1">
                                  <span className="font-medium">Issue: </span>
                                  {item.phonetic_issue}
                                </div>
                                <div className="text-sm text-blue-600 mt-1">
                                  <span className="font-medium">Suggestion: </span>
                                  {item.suggested_pronunciation}
                                </div>
                              </div>
                            ) : (
                              <div>
                                <div>
                                  <span className="font-medium">{item.quote}</span>
                                </div>
                                <div className="text-sm text-purple-600 mt-1">
                                  <span className="font-medium">Issue: </span>
                                  {item.phonetic_issue}
                                </div>
                                <div className="text-sm text-blue-600 mt-1">
                                  <span className="font-medium">Suggestion: </span>
                                  {item.suggested_pronunciation}
                                </div>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            // Full view - all details
            <div className="p-4 bg-gray-100 rounded-lg text-gray-800">
              <pre className="whitespace-pre-wrap overflow-x-auto">
                {typeof result.mistral === 'string' 
                  ? result.mistral 
                  : JSON.stringify(result.mistral, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
      
      {/* Show summary if available */}
      {result?.summary && (
        <div>
          <h3 className="font-semibold text-lg mb-2">Summary</h3>
          <div className="p-4 bg-blue-50 rounded-lg text-gray-800 border border-blue-100">
            <p>{result.summary}</p>
          </div>
        </div>
      )}
      
      {/* If no results available yet */}
      {!result && isLoading && (
        <div className="flex justify-center items-center h-40">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay; 