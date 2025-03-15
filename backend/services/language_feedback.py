"""
Mistral API service (mock implementation).
"""
import asyncio
import json

from typing import Dict, Any
from openai import OpenAI
from models.elevenlabs import ElevenLabsOutput
from models.language_feedback import LanguageFeedback

PROMPT_PREFIX = f"""
Below is an excerpt of a discussion (infer the tone and formality from it).
Your goal as a coach is to check if speaker_1 did any mistakes. If so, classify all the mistakes of the same urgency (high, mid, low) together, and for each _quoted_ mistake, provide a _concise correction_. You should be pragmatic and actionable.
Result should be in JSON format which has the following structure:
```
{{
  "high": [
    {{
      "quote": "in der Arbeit Platz",
      "error_type": "Präpositionsfehler",
      "correction": "am Arbeitsplatz"
    }},
    {{
      "quote": "die deutsche Menschen",
      "error_type": "Kongruenzfehler",
      "correction": "die Deutschen"
    }}
  ],
  "mid": [
    {{
      "quote": "Zeit spenden",
      "error_type": "Wortwahlfehler",
      "correction": "Zeit sparen"
    }},
    {{
      "quote": "man braucht, äh, äh, viel Geld als ich habe schon gesagt",
      "error_type": "Syntaxfehler",
      "correction": "Man braucht viel Geld, wie ich bereits sagte"
    }}
  ],
  "low": [
    {{
      "quote": "äh",
      "error_type": "Füllwort",
      "correction": ""
    }},
    {{
      "quote": "äh",
      "error_type": "Also",
      "correction": ""
    }}
  ]
}}
```
"""


class LanguageFeedbackService:
    def __init__(self):
        self.client = OpenAI()
    
    async def process_transcript(self, transcript: ElevenLabsOutput) -> LanguageFeedback:
        transcript_text = transcript.extract_text()

        completion = self.client.chat.completions.create(
            model="o1",
            messages=[
                {"role": "user", "content": PROMPT_PREFIX + transcript_text}
            ],
            response_format={ "type": "json_object" }
        )

        result = completion.choices[0].message.content
        return LanguageFeedback(**json.loads(result))

