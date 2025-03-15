from pydantic import BaseModel
from typing import Literal, List, Dict, Optional


class Word(BaseModel):
    text: str
    start: float
    end: float
    type: Literal["word", "spacing"]
    speaker_id: str


class ElevenLabsOutput(BaseModel):
    language_code: str
    language_probability: float
    text: Optional[str] = None
    words: list[Word]

    def extract_text(self) -> str:
        sequences =  self._extract_speaker_sequences()
        conversation_text = "\n".join(
            f"{sequence['speaker_id']}: {sequence['content']}"
            for sequence in sequences
        )
        return conversation_text

    
    def _extract_speaker_sequences(self) -> List[Dict[str, str]]:
        sequences = []
        current_sequence = []
        current_speaker = None

        for item in (w for w in self.words if w.type == 'word'):
            speaker_id = item.speaker_id
            
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

        if current_sequence:
            sequences.append({
                "speaker_id": current_speaker,
                "content": " ".join(current_sequence)
            })
            
        return sequences

