"""
Mistral API service (mock implementation).
"""
import asyncio
import json

import logging

from typing import Dict, Any, Tuple, Optional
from openai import OpenAI
from models.elevenlabs import ElevenLabsOutput
from models.language_feedback import EvaluationResponse, EvaluationResponseRanged
from models.language_feedback import ErrorItem, ErrorItemRanged, VocabItem, VocabItemRanged


PROMPT_PREFIX = """
Du bist ein sprachlicher Evaluierungsassistent, der dafür zuständig ist, transkribierte Audioaufnahmen (auf Deutsch) auf sprachliche Fehler und stilistische Verbesserungsmöglichkeiten zu untersuchen. Deine Aufgabe besteht darin, typische Fehler von Deutschlernenden zu erkennen und konstruktives Feedback zu geben.

WICHTIG: Suche AKTIV nach allen folgenden Fehlertypen und markiere sie konsequent:

1. **Fehler (Mistakes):** Gravierende Sprachfehler, die das Verständnis beeinträchtigen oder die Kommunikation erschweren:
   - **Nicht existierendes Wort:** 
      * Wortschöpfungen oder falsche Übertragungen aus anderen Sprachen
      * Erfundene Komposita
   - **Grammatikalischer Fehler:**
      * Falsche Artikel (der/die/das) - IMMER markieren!
      * Falsche Kasusendungen (Dativ/Akkusativ) - IMMER markieren!
      * Falsche Verbkonjugation
      * Fehlerhafte Satzstellung (besonders bei Nebensätzen)
      * Falsche Präpositionen
      * Fehlende Subjekt-Verb-Kongruenz
   - **Lexikalischer Fehler:**
      * Falsche Wortbedeutung im Kontext
      * Verwechslung ähnlich klingender Wörter
      * Falsche Kollokationen
      * Falsche Präfixe/Suffixe
   
   **Beispiel:**  
   - Transkription: „Ich möchte, äh, zuerst, äh, sagen und welche, äh, verschiedene Alternativen gibt es."  
     - Fehler: Falsche Satzstellung und Grammatik
     - Korrektur: „Ich möchte zuerst sagen, welche verschiedenen Alternativen es gibt."
     - error_type: "grammatikalischer Fehler"

2. **Unstimmigkeiten (Inaccuracies):** Fehler, die zwar verständlich sind, aber die Natürlichkeit der Sprache beeinträchtigen:
   - **Stilistischer Fehler:** 
      * JEDES Füllwort ("äh", "ähm", "also", "ja", "nun") MUSS markiert werden!
      * JEDE Wortwiederholung MUSS markiert werden!
      * Zu formelle/informelle Ausdrucksweise
      * Unnatürliche Wortkombinationen
      * Überflüssige Konjunktionen am Satzanfang ("Und", "Also")
   - **Aussprache und Sprachfluss:**
      * JEDES Stottern oder Selbstkorrektur MUSS markiert werden!
      * Abgebrochene Wörter oder Sätze
      * Unsicherheiten in der Aussprache
   - **Idiomatische Ausdrücke:**
      * Wörtliche Übersetzungen aus der Muttersprache
      * Unpassende Redewendungen
      * Unidiomatische Ausdrucksweisen
   
   **Beispiel:**  
   - Transkription: „a-a-auch in der, in den Familien"  
     - Fehler: Stottern und Wortwiederholung stören den Sprachfluss
     - Korrektur: „auch in den Familien"  
     - error_type: "stilistischer Fehler"

3. **Vokabular:** Vorschläge zur Verbesserung des aktiven Wortschatzes:
   - Alternative Ausdrucksmöglichkeiten für:
      * Häufig verwendete Verben ("machen", "sein", "haben")
      * Einfache Adjektive ("gut", "schlecht", "schön")
      * Basale Substantive
   - Situationsangemessene Synonyme
   - Idiomatische Alternativen
   - Fachspezifische Begriffe wenn passend
   
   **Beispiel:**  
   - Transkription enthält das Wort „hektisch"  
     - Vorschläge: Ersetze „hektisch" durch "stressig", "geschäftig" oder "unruhig"

Für jeden identifizierten Fehler sollst du ein JSON-Objekt mit folgendem Format erstellen:

{
  "mistakes": [
    {"quote": "exakter Transkriptionsausschnitt", "error_type": "Fehlertyp (z.B. 'grammatikalischer Fehler')", "correction": "Vorgeschlagene Korrektur"}
  ],
  "inaccuracies": [
    {"quote": "exakter Transkriptionsausschnitt", "error_type": "Fehlertyp (z.B. 'stilistischer Fehler')", "correction": "Vorgeschlagene Korrektur"}
  ],
  "vocabularies": [
    {"quote": "das betroffene Wort oder die Phrase", "synonyms": ["Synonym1", "Synonym2", "..."]}
  ]
}

**Wichtige Anweisungen zur Ausgabe:**
1. Der Wert von `"quote"` MUSS eine exakte Teilzeichenkette aus dem Originaltext sein - Wort für Wort, Buchstabe für Buchstabe identisch. Dies ist essentiell für die automatische Fehlermarkierung.

2. Gib konstruktives, lernförderndes Feedback:
   - Identifiziere JEDEN systematischen Fehler
   - Markiere ALLE Füllwörter und Wiederholungen
   - Biete konkrete Verbesserungsvorschläge an
   - Achte besonders auf:
     * Häufige Interferenzfehler aus anderen Sprachen
     * Typische Anfängerfehler
     * Stilistische Unsicherheiten
   - Ziel ist die kontinuierliche Verbesserung der Sprachkompetenz

3. Verwende ausschließlich diese Fehlertypen:
   - "nicht existierendes Wort"
   - "grammatikalischer Fehler"
   - "stilistischer Fehler"
   - "Lexikalischer Fehler"

4. Liefere NUR valides JSON ohne zusätzlichen Text oder Erklärungen.

Beispiel für erwarteten Umfang der Ausgabe:
- Für einen 5-Satz-Text MUSST du mindestens identifizieren:
  - ALLE vorhandenen grammatikalischen Fehler
  - ALLE Füllwörter und Wiederholungen
  - 2-3 weitere Einträge unter "mistakes" (wenn vorhanden)
  - 3-4 weitere Einträge unter "inaccuracies"
  - 4-5 Einträge unter "vocabularies"
"""

logger = logging.getLogger(__name__)

class LanguageFeedbackService:
    def __init__(self):
        self.client = OpenAI()
    
    async def process_transcript(self, transcript: ElevenLabsOutput) -> EvaluationResponseRanged:
        transcript_text = transcript.extract_text()
        completion = self.client.beta.chat.completions.parse(
            model="o1-2024-12-17",
            messages=[
                {"role": "system", "content": PROMPT_PREFIX},
                {"role": "user", "content": transcript_text}
            ],
            response_format=EvaluationResponse,
        )

        result = completion.choices[0].message.content
        assert result is not None
        eval_response = EvaluationResponse(**json.loads(result))

        return LanguageFeedbackService.__convert_to_ranges(eval_response, transcript_text)
    
    @staticmethod
    def __find_substring_range(full_string: str, substring: str, start_from: int = 0) -> Optional[Tuple[int, int]]:
        try:
            start = full_string.index(substring, start_from)
            end = start + len(substring)
            return start, end
        except:
            return None
    
    @staticmethod
    def __convert_error_item_to_ranged(error_item: ErrorItem, transcript: str) -> Optional[ErrorItemRanged]:
        ranges = []
        last_idx = 0
        while True:
            idx = LanguageFeedbackService.__find_substring_range(transcript, error_item.quote, last_idx)
            if idx is None:
                break
            ranges.append(idx)
            last_idx = idx[1]
        
        if not ranges:
            logger.warning(f"Could not find substring range for error item: {error_item}")
            return None
        
        return ErrorItemRanged(
            ranges=ranges,
            error_type=error_item.error_type,
            correction=error_item.correction
        )
    
    @staticmethod
    def __convert_vocab_item_to_ranged(vocab_item: VocabItem, transcript: str) -> Optional[VocabItemRanged]:
        range = LanguageFeedbackService.__find_substring_range(transcript, vocab_item.quote)
        if range is None:
            logger.warning(f"Could not find substring range for error item: {vocab_item}")
            return None
        
        return VocabItemRanged(
            range=range,
            synonyms=vocab_item.synonyms
        )

    @staticmethod
    def __convert_to_ranges(response: EvaluationResponse, transcript: str) -> EvaluationResponseRanged:
        mistakes = []
        for error_item in response.mistakes:
            ranged_error = LanguageFeedbackService.__convert_error_item_to_ranged(error_item, transcript)
            if ranged_error:
                mistakes.append(ranged_error)
        
        inaccuracies = []
        for error_item in response.inaccuracies:
            ranged_error = LanguageFeedbackService.__convert_error_item_to_ranged(error_item, transcript)
            if ranged_error:
                inaccuracies.append(ranged_error)

        vocabularies = []
        for vocab_item in response.vocabularies:
            ranged_vocab = LanguageFeedbackService.__convert_vocab_item_to_ranged(vocab_item, transcript)
            if ranged_vocab:
                vocabularies.append(ranged_vocab)
        
        return EvaluationResponseRanged(
            transcript=transcript,
            mistakes=mistakes,
            inaccuracies=inaccuracies,
            vocabularies=vocabularies
        )

