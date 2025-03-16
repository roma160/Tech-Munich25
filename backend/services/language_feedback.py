"""
Mistral API service implementation with OpenAI fallback.
"""
import asyncio
import json
import logging

from typing import Dict, Any, Tuple, Optional
from openai import AsyncOpenAI
from mistralai.client import MistralClient
from models.elevenlabs import ElevenLabsOutput
from models.language_feedback import (
    EvaluationResponse,
    EvaluationResponseRanged,
    ErrorItem,
    ErrorItemRanged,
    VocabItem,
    VocabItemRanged
)

PROMPT_PREFIX = """
Du bist ein sprachlicher Evaluierungsassistent, der dafür zuständig ist, transkribierte Audioaufnahmen (auf Deutsch) auf sprachliche Fehler und stilistische Verbesserungsmöglichkeiten zu untersuchen. Deine Aufgabe besteht darin, typische Fehler von Deutschlernenden zu erkennen und konstruktives Feedback zu geben.

WICHTIG: Unterscheide sehr genau zwischen Fehlern, die das Verständnis oder die Kommunikation massiv beeinträchtigen (Mistakes), und solchen, bei denen die Kernaussage trotz Fehlern klar erkennbar bleibt (Inaccuracies). Klassifiziere einen Fehler als "Mistake" NUR dann, wenn die Bedeutung oder der Zweck des Satzes unklar oder schwer nachvollziehbar wird. Ist die Grundinformation trotz sprachlicher Unstimmigkeiten erkennbar, so gilt der Fehler als "Inaccuracy".

Suche AKTIV nach allen folgenden Fehlertypen und markiere sie konsequent:

1. **Fehler (Mistakes):** Gravierende Sprachfehler, die das Verständnis oder die Kommunikation erheblich beeinträchtigen:
   - **Nicht existierendes Wort:** 
      * Wortschöpfungen oder falsche Übertragungen aus anderen Sprachen
      * Erfundene Komposita
      
      **Beispiele:**
      - "Gestern Abend habe ich drei Stunden lang gecomputert" (statt: "Gestern Abend habe ich drei Stunden lang am Computer gearbeitet")
      - "Ich muss noch mein Hausaufgabenbuch aus der Tasche holen" (statt: "Ich muss noch mein Hausaufgabenheft aus der Tasche holen")
      
   - **Grammatikalischer Fehler:**
      * Schwerwiegende grammatikalische Fehler, die das Verständnis erheblich beeinträchtigen
      * Falsche Verbkonjugation, die den Sinn verändert
      * Fehlerhafte Satzstellung, die den Sinn entstellt
      * Fehlende Subjekt-Verb-Kongruenz, die zu Missverständnissen führt
      
      **Beispiele:**
      - "Wenn ich habe Zeit am Wochenende, besuche ich meine Eltern" (statt: "Wenn ich Zeit am Wochenende habe, besuche ich meine Eltern")
      - "Die Kinder ist müde und nicht können schlafen" (statt: "Die Kinder sind müde und können nicht schlafen")
      - "Ich gestern gehen Schule" (statt: "Ich bin gestern zur Schule gegangen")
      
   - **Lexikalischer Fehler:**
      * Falsche Wortbedeutung im Kontext, die zu Missverständnissen führt
      * Verwechslung ähnlich klingender Wörter mit unterschiedlicher Bedeutung
      * Falsche Kollokationen, die den Sinn entstellen
      * Falsche Präfixe/Suffixe, die die Bedeutung verändern
      
      **Beispiele:**
      - "Ich möchte verschiedene Alternativen spenden" (statt: "nennen")
      - "Er hat die Prüfung geschrieben" (wenn gemeint ist: "bestanden")
      - "Ich nehme einen Spaziergang" (statt: "mache einen Spaziergang")

2. **Unstimmigkeiten (Inaccuracies):** Fehler, die zwar vorhanden sind, das Verständnis aber nicht oder nur geringfügig beeinträchtigen:
   - **Füllwörter:** 
      * Jedes Füllwort ("äh", "ähm", "also", "ja", "nun") wird als eigener Eintrag aufgeführt
      * Die "quote" enthält NUR das Füllwort selbst, ohne Kontext
      * Der error_type MUSS "filling_word" sein
      * Mehrfaches Vorkommen desselben Füllworts wird als EIN Eintrag gelistet
      
      **Beispiele:**
      - "ähm" → Ein Eintrag für "ähm"
      - "also" → Ein Eintrag für "also"
      
   - **Stilistischer Fehler:** 
      * Ungewöhnliche oder unnatürliche Wortwahl bzw. Ausdrucksweise, die zwar auffällt, aber die Verständlichkeit nicht signifikant stört
      * Leichte Artikelfehler oder fehlende Artikel, die das Verständnis nicht beeinträchtigen
      * Leichte Präpositionsfehler oder falsche Kasusendungen, bei denen der Sinn klar bleibt
      
      **Beispiele:**
      - "Ich tue jetzt essen" (statt: "Ich esse jetzt")
      - "Machen Sie einen schönen Tag noch" (statt: "Ich wünsche Ihnen noch einen schönen Tag")
      - "Ich gehe zu Supermarkt" (statt: "Ich gehe zum Supermarkt") – fehlender Artikel, aber verständlich
      - "Ich warte auf dem Bus" (statt: "Ich warte auf den Bus") – falscher Kasus, aber verständlich
      - "Ich fahre mit Auto zur Arbeit" (statt: "Ich fahre mit dem Auto zur Arbeit") – fehlender Artikel
      
   - **Aussprache und Sprachfluss:**
      * Stottern, Selbstkorrekturen oder abgebrochene Wörter/Sätze, die den Sprachfluss stören, aber die Kernaussage erhalten bleibt
      
      **Beispiele:**
      - "Ich w-w-wollte sagen..."
      - "Das ist sehr int- interessant"
      
   - **Idiomatische Ausdrücke:**
      * Wörtliche Übersetzungen aus der Muttersprache oder unpassende Redewendungen, die dennoch verständlich sind
      
      **Beispiele:**
      - "Es macht keinen Sinn" (als Anglizismus, statt: "Das ergibt keinen Sinn")
      - "Ich bin 20 Jahre alt geworden" (statt: "Ich bin 20 Jahre alt")

3. **Vokabular:** Vorschläge zur Verbesserung des aktiven Wortschatzes:
   - Alternative Ausdrucksmöglichkeiten für:
      * Häufig verwendete Verben ("machen", "sein", "haben")
      * Einfache Adjektive ("gut", "schlecht", "schön")
      * Basale Substantive
   - Situationsangemessene Synonyme
   - Idiomatische Alternativen
   - Fachspezifische Begriffe, wenn passend
      
   **Beispiele:**  
   - "Es war sehr hektisch im Büro"
     - Quote: "sehr hektisch im Büro"
     - Vorschläge: ["sehr stressig im Büro", "sehr geschäftig im Büro", "sehr unruhig im Büro"]
   - "Das Essen war gut"
     - Quote: "war gut"
     - Vorschläge: ["hat ausgezeichnet geschmeckt", "war vorzüglich", "war köstlich"]

Für jeden identifizierten Fehler sollst du ein JSON-Objekt mit folgendem Format erstellen:

{
  "mistakes": [
    {"quote": "exakter Transkriptionsausschnitt mit Kontext", "error_type": "Fehlertyp (z.B. 'grammatical_error', 'lexical_error')", "correction": "Vorgeschlagene Korrektur"}
  ],
  "inaccuracies": [
    {"quote": "exakter Transkriptionsausschnitt mit Kontext", "error_type": "filling_word oder stylistic_error", "correction": "Vorgeschlagene Korrektur"}
  ],
  "vocabularies": [
    {"quote": "das betroffene Wort oder die Phrase mit Kontext", "synonyms": ["Synonym1", "Synonym2", "..."]}
  ]
}

**Wichtige Anweisungen zur Ausgabe:**
1. Der Wert von "quote" MUSS:
   - Eine exakte Teilzeichenkette aus dem Originaltext sein.
   - Genügend Kontext enthalten, um die Stelle eindeutig zu identifizieren (verwende mehrere Wörter vor und nach dem Fehler). Insbesondere in der "mistakes"-Sektion, selbst wenn der Fehler nur ein einzelnes Wort betrifft, muss die "quote" so erweitert werden, dass sie einen eindeutigen Abgleich (1-1 String-Matching) mit dem Originaltext ermöglicht.
   - AUSNAHME bei Füllwörtern: NUR das Füllwort selbst ohne Kontext.
   - Bei Artikelfehlern: Den kompletten Teilsatz mit dem falschen Artikel.

2. Gib konstruktives, lernförderndes Feedback:
   - Unter "mistakes" NUR echte Verständnisfehler listen, die die Kommunikation erheblich beeinträchtigen.
   - Unter "inaccuracies":
     * Füllwörter mit error_type "filling_word".
     * Andere Unstimmigkeiten (z.B. leichte grammatikalische Fehler, die das Verständnis nicht wesentlich stören) mit error_type "stylistic_error".
     
3. Verwende ausschließlich diese Fehlertypen:
   - "nonexistent_word"
   - "grammatical_error"
   - "filling_word"
   - "stylistic_error"
   - "lexical_error"

4. Liefere NUR valides JSON ohne zusätzlichen Text oder Erklärungen.

5. Stelle sicher, dass jede "quote" ausreichend Kontext enthält, um die genaue Position im Text eindeutig zu identifizieren. Bei längeren Fehlern sollte der gesamte relevante Satz oder Teilsatz zitiert werden.
"""

logger = logging.getLogger(__name__)

class LanguageFeedbackService:
    def __init__(self, use_mistral: bool = True, api_key: Optional[str] = None):
        """Initialize the service with either Mistral or OpenAI client.
        
        Args:
            use_mistral: If True, use Mistral AI API, otherwise use OpenAI
            api_key: Optional API key. If not provided, will look for MISTRAL_API_KEY or OPENAI_API_KEY in environment
        """
        self.use_mistral = use_mistral
        if use_mistral:
            self.client = MistralClient(api_key=api_key)
        else:
            self.client = AsyncOpenAI(api_key=api_key)
    
    async def process_transcript(self, transcript: ElevenLabsOutput) -> EvaluationResponseRanged:
        transcript_text = transcript.extract_text()
        
        if self.use_mistral:
            # Mistral AI implementation
            messages = [
                {"role": "system", "content": PROMPT_PREFIX},
                {"role": "user", "content": transcript_text}
            ]
            
            completion = self.client.chat(
                model="mistral-large-latest",  # You can adjust the model as needed
                messages=messages,
                response_format={"type": "json_object"}  # Ensure JSON response
            )
            
            result = completion.choices[0].message.content
            eval_response = EvaluationResponse(**json.loads(result))
        else:
            # OpenAI implementation
            completion = await self.client.beta.chat.completions.parse(
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

    
