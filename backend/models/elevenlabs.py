from pydantic import BaseModel
from typing import Literal, List, Dict, Optional, Any


class Word(BaseModel):
    text: str
    start: float
    end: float
    type: Literal["word", "spacing", "audio_event"]
    speaker_id: Optional[str] = None


class ElevenLabsOutput(BaseModel):
    text: str
    words: List[Word] = []
    language_code: Optional[str] = None
    language_probability: Optional[float] = None

    @classmethod
    def from_response(cls, response_data: Dict[str, Any]) -> "ElevenLabsOutput":
        """
        Create an instance from the ElevenLabs API response.
        """
        # Extract the full text
        text = response_data.get("text", "")
        
        # Process words if available
        words_data = response_data.get("words", [])
        words = []
        
        # Log speaker information
        speaker_counts = {}
        print(f"DEBUG - Total words from ElevenLabs: {len(words_data)}")
        
        for i, word_data in enumerate(words_data):
            # Get speaker info - use the correct field name from ElevenLabs response
            speaker_id = None
            if "speaker" in word_data:  # ElevenLabs uses "speaker", not "speaker_id"
                speaker_id = word_data["speaker"]
            elif "speaker_id" in word_data:
                speaker_id = word_data["speaker_id"]
            
            # Default to speaker_0 if no speaker information
            if not speaker_id:
                speaker_id = "speaker_0"
            
            # Count speakers for debugging
            speaker_counts[speaker_id] = speaker_counts.get(speaker_id, 0) + 1
            
            # Debug the first few words to ensure we're capturing speaker info
            if i < 10 or i > len(words_data) - 10:
                print(f"DEBUG - Word {i}: '{word_data.get('text', '')}' - speaker: {speaker_id}")
            
            # Convert to our Word model format
            words.append(
                Word(
                    text=word_data.get("text", ""),
                    start=word_data.get("start", 0.0),
                    end=word_data.get("end", 0.0),
                    type=word_data.get("type", "word"),  # Get actual type if available
                    speaker_id=speaker_id  # Set the speaker ID we found
                )
            )
        
        # Log speaker information
        print(f"SPEAKER DISTRIBUTION IN WORDS: {speaker_counts}")
        
        instance = cls(
            text=text,
            words=words,
            language_code=response_data.get("language", ""),
            language_probability=response_data.get("confidence_score", 1.0)
        )
        
        # Debug: Print the first segments that will be extracted
        segments = instance._extract_speaker_sequences()
        print(f"SEGMENTS BY SPEAKER (all):")
        for i, seg in enumerate(segments):
            print(f"  Segment {i}: speaker={seg['speaker_id']}, content={seg['content'][:30]}...")
        
        return instance

    def extract_text(self) -> str:
        """
        Extract the full text of the transcription.
        """
        if self.text:
            return self.text
            
        # Fallback to reconstructing from words
        return " ".join(word.text for word in self.words if word.type == "word")
    
    def extract_segments(self) -> List[Dict[str, str]]:
        """
        Extract segments of text by speaker.
        """
        # If no words with speaker info, return the full text as a single segment
        if not self.words:
            print("DEBUG: No words found, returning full text as single segment")
            return [{"speaker_id": "speaker_0", "content": self.extract_text()}]
        
        # Check if we have any speaker information
        if all(word.speaker_id is None for word in self.words):
            print("DEBUG: No speaker info found in words, returning full text as single segment")
            return [{"speaker_id": "speaker_0", "content": self.extract_text()}]
        
        # Get the segments from extract_speaker_sequences  
        segments = self._extract_speaker_sequences()
        
        # Check if we found any segments
        if not segments:
            print("DEBUG: No segments created, falling back to full text")
            return [{"speaker_id": "speaker_0", "content": self.extract_text()}]
        
        # Debug: print what we're returning
        print(f"DEBUG: Returning {len(segments)} speaker segments")
        for i, seg in enumerate(segments):  # Print all segments
            print(f"DEBUG: Segment {i}: speaker_id={seg['speaker_id']}, content_prefix={seg['content'][:30]}...")
        
        return segments
    
    def _extract_speaker_sequences(self) -> List[Dict[str, str]]:
        """
        Extract sequences of text by speaker.
        """
        sequences = []
        current_sequence = []
        current_speaker = None
        
        # Debug - print raw words with speaker IDs
        print("DEBUG - Raw words with speaker IDs:")
        for i, word in enumerate(self.words[:10]):  # Print first 10 words only
            print(f"Word {i}: '{word.text}' - speaker_id: {word.speaker_id}")
        
        # Count unique speakers to verify we have multiple
        unique_speakers = set(word.speaker_id for word in self.words if word.speaker_id is not None)
        print(f"DEBUG - Found {len(unique_speakers)} unique speakers: {unique_speakers}")
        
        # We'll process in order, building up segments by speaker
        for item in (w for w in self.words if w.type == 'word'):
            # Make sure we have a speaker_id (default to speaker_0 if None)
            speaker_id = item.speaker_id or 'speaker_0'
            
            # Print debug info for speaker transitions
            if current_speaker is not None and speaker_id != current_speaker:
                print(f"DEBUG - Speaker transition: '{current_speaker}' -> '{speaker_id}' at word '{item.text}'")
            
            # If we're starting a new speaker segment
            if current_speaker is None or speaker_id != current_speaker:
                # Save the previous segment if it exists
                if current_sequence:
                    sequence_text = " ".join(current_sequence)
                    print(f"DEBUG - Completing segment for '{current_speaker}': '{sequence_text[:20]}...'")
                    sequences.append({
                        "speaker_id": current_speaker,
                        "content": sequence_text
                    })
                # Start a new segment
                current_sequence = [item.text]
                current_speaker = speaker_id
            else:
                # Continue current segment
                current_sequence.append(item.text)
        
        # Add the last sequence
        if current_sequence:
            sequence_text = " ".join(current_sequence)
            print(f"DEBUG - Final segment for '{current_speaker}': '{sequence_text[:20]}...'")
            sequences.append({
                "speaker_id": current_speaker,
                "content": sequence_text
            })
        
        # Final check
        print(f"DEBUG - Created {len(sequences)} segments from {len(unique_speakers)} speakers")
        return sequences

