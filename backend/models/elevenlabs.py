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
        
        for word_data in words_data:
            # Convert to our Word model format
            words.append(
                Word(
                    text=word_data.get("text", ""),
                    start=word_data.get("start", 0.0),
                    end=word_data.get("end", 0.0),
                    type="word",  # Default to word type
                    speaker_id=word_data.get("speaker", "speaker_0")  # Default to speaker_0
                )
            )
            
        return cls(
            text=text,
            words=words,
            language_code=response_data.get("language", ""),
            language_probability=response_data.get("confidence_score", 1.0)
        )

    def extract_text(self) -> str:
        """
        Extract the full text of the transcription.
        """
        if self.text:
            return self.text
            
        # Fallback to reconstructing from words
        return " ".join(word.text for word in self.words if word.type == "word")
    
    def extract_speaker0_text(self) -> str:
        sequences =  self._extract_speaker_sequences()
        conversation_text = "\n".join(
            sequence['content']
            for sequence in sequences
            if sequence['speaker_id'] == 'speaker_0'
        )
        return conversation_text

    def extract_segments(self) -> List[str]:
        """
        Extract segments of text by speaker.
        """
        # If no words with speaker info, return the full text as a single segment
        if not self.words or all(word.speaker_id is None for word in self.words):
            return [self.extract_text()]
            
        return [
            sequence['content']
            for sequence in self._extract_speaker_sequences()
            if sequence['speaker_id'] in ['speaker_0', 'speaker_1']
        ]
    
    def _extract_speaker_sequences(self) -> List[Dict[str, str]]:
        """
        Extract sequences of text by speaker.
        """
        sequences = []
        current_sequence = []
        current_speaker = None

        for item in (w for w in self.words if w.type == 'word'):
            speaker_id = item.speaker_id or 'speaker_0'  # Default to speaker_0 if None
            
            if current_speaker is None or speaker_id != current_speaker:
                if current_sequence:
                    sequences.append({
                        "speaker_id": current_speaker,
                        "content": " ".join(current_sequence)
                    })
                current_sequence = [item.text]
                current_speaker = speaker_id
            else:
                current_sequence.append(item.text)
        
        # Add the last sequence
        if current_sequence:
            sequences.append({
                "speaker_id": current_speaker,
                "content": " ".join(current_sequence)
            })
            
        return sequences

