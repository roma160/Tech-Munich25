"""
Pronunciation assessment service using neural network phoneme-level scoring (GOP-based).
"""
import os
import asyncio
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import re
import base64
import logging
import tempfile
import sys
import subprocess
import json
import requests
import tarfile
import shutil
import urllib.request
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for dictionary sources
DICTIONARY_SOURCES = {
    "german": [
        # Primary source - direct download from MFA GitHub
        "https://github.com/MontrealCorpusTools/mfa-models/raw/main/dictionary/german/mfa/3.0.0/german_mfa.dict",
        # Backup direct URL to the raw file
        "https://raw.githubusercontent.com/MontrealCorpusTools/mfa-models/main/dictionary/german/mfa/3.0.0/german_mfa.dict",
        # Alternative mirror (replace with your actual mirror if you have one)
        "https://huggingface.co/datasets/batikano/pronunciation-assessment/resolve/main/german_mfa.dict",
        # CMU Sphinx German dictionary as a reliable fallback
        "https://sourceforge.net/projects/cmusphinx/files/Acoustic%20and%20Language%20Models/German/de_400k_cmu07a.dict.gz/download"
    ]
}

# Minimum dictionary size in bytes to be considered valid
MIN_DICT_SIZE = 30000  # 30KB is sufficient for a basic German dictionary

class PronunciationAssessmentService:
    """
    Service for assessing pronunciation quality using a neural network model
    with Goodness of Pronunciation (GOP) technique at the phoneme level.
    """
    
    def __init__(self):
        """
        Initialize the pronunciation assessment service.
        In a production environment, this would load models for:
        - Grapheme to phoneme conversion
        - Acoustic model for phoneme scoring
        - TTS model for audio feedback
        """
        self.mock_mode = True
        self.enhanced_dict = {}
        
        # Create directory for dictionary files if it doesn't exist
        self.dict_dir = os.path.abspath("mfa_models/dictionaries")
        os.makedirs(self.dict_dir, exist_ok=True)
        
        # Try to load the German dictionary if available
        self.german_dict_path = os.path.join(self.dict_dir, "german_mfa.dict")
        
        # Load built-in fallback dictionary first as a temporary measure
        self.initialize_fallback_dictionary()
        
        # Try to load or download the enhanced dictionary
        self.load_or_download_dictionary()
        
        # Phonemes that are commonly difficult for non-native German speakers
        self.difficult_phonemes = {
            "ç": "The 'ch' sound in 'ich' is made by raising the middle of the tongue to the hard palate.",
            "x": "The 'ch' sound in 'Bach' is made at the back of the throat.",
            "ʁ": "The German 'r' is more guttural than in English.",
            "y": "The 'ü' sound is made by saying 'ee' while rounding your lips.",
            "ø": "The 'ö' sound is made by saying 'eh' while rounding your lips.",
            "ɔ": "The short 'o' sound as in 'Gott' is more open than in English.",
            "ə": "The 'schwa' sound as in the final 'e' in 'bitte' should be unstressed.",
            "ɛ": "The 'ä' sound is more open than the English 'e' in 'bed'.",
            "ʊ": "The short 'u' sound as in 'und' is more relaxed than in English.",
            "ʏ": "The short 'ü' sound is made with relaxed, rounded lips.",
            "œ": "The short 'ö' sound is made with relaxed, rounded lips.",
            "aɪ": "The 'ei' or 'ai' sound should flow smoothly.",
            "aʊ": "The 'au' sound should flow smoothly.",
            "ɔɪ": "The 'eu' or 'äu' sound should flow smoothly.",
        }
    
    def initialize_fallback_dictionary(self):
        """
        Initialize the fallback dictionary with common German words and their phonemes.
        This will be used if the enhanced dictionary download fails.
        """
        # Dictionary mapping some common German words to phonemes (IPA)
        self.enhanced_dict = {
            "hallo": ["h", "a", "l", "o"],
            "ich": ["ɪ", "ç"],
            "spreche": ["ʃ", "p", "ʁ", "ɛ", "ç", "ə"],
            "deutsch": ["d", "ɔ", "y", "t", "ʃ"],
            "wie": ["v", "i:"],
            "geht": ["g", "e:", "t"],
            "es": ["ɛ", "s"],
            "ihnen": ["i:", "n", "ə", "n"],
            "gut": ["g", "u:", "t"],
            "danke": ["d", "a", "ŋ", "k", "ə"],
            "bitte": ["b", "ɪ", "t", "ə"],
            "ja": ["j", "a:"],
            "nein": ["n", "aɪ", "n"],
            "tag": ["t", "a:", "k"],
            "guten": ["g", "u:", "t", "ə", "n"],
            "morgen": ["m", "ɔ", "ʁ", "g", "ə", "n"],
            "abend": ["a:", "b", "ə", "n", "t"],
            "nacht": ["n", "a", "x", "t"],
            "schön": ["ʃ", "ø:", "n"],
            "tschüss": ["tʃ", "ʏ", "s"],
            "auf": ["aʊ", "f"],
            "wiedersehen": ["v", "i:", "d", "ɐ", "z", "e:", "ə", "n"],
            "bald": ["b", "a", "l", "t"],
            "später": ["ʃ", "p", "ɛ:", "t", "ɐ"],
            "heute": ["h", "ɔɪ", "t", "ə"],
            "woche": ["v", "ɔ", "x", "ə"],
            "monat": ["m", "o:", "n", "a", "t"],
            "jahr": ["j", "a:", "ʁ"],
            "zeit": ["ts", "aɪ", "t"],
            "uhr": ["u:", "ʁ"],
            "stunde": ["ʃ", "t", "ʊ", "n", "d", "ə"],
            "minute": ["m", "i", "n", "u:", "t", "ə"],
            "sekunde": ["z", "e", "k", "ʊ", "n", "d", "ə"],
            "wasser": ["v", "a", "s", "ɐ"],
            "brot": ["b", "ʁ", "o:", "t"],
            "käse": ["k", "ɛ:", "z", "ə"],
            "fleisch": ["f", "l", "aɪ", "ʃ"],
            "gemüse": ["g", "ə", "m", "y:", "z", "ə"],
            "obst": ["o:", "p", "s", "t"],
            "apfel": ["a", "p", "f", "ə", "l"],
            "banane": ["b", "a", "n", "a:", "n", "ə"],
            "orange": ["o", "ʁ", "a", "n", "ʒ", "ə"],
            "erdbeere": ["e:", "ʁ", "t", "b", "e:", "ʁ", "ə"],
            "himbeere": ["h", "ɪ", "m", "b", "e:", "ʁ", "ə"],
            "blaubeere": ["b", "l", "aʊ", "b", "e:", "ʁ", "ə"],
            "kaffee": ["k", "a", "f", "e:"],
            "tee": ["t", "e:"],
            "milch": ["m", "ɪ", "l", "ç"],
            "zucker": ["ts", "ʊ", "k", "ɐ"],
            "salz": ["z", "a", "l", "ts"],
            "pfeffer": ["p", "f", "ɛ", "f", "ɐ"],
            "heißen": ["h", "aɪ", "s", "ə", "n"],
            "sein": ["z", "aɪ", "n"],
            "haben": ["h", "a:", "b", "ə", "n"],
            "können": ["k", "œ", "n", "ə", "n"],
            "mögen": ["m", "ø:", "g", "ə", "n"],
            "pontecan": ["p", "o", "n", "t", "e", "c", "a", "n"],
            "einigermaßen": ["aɪ", "n", "i", "g", "ɐ", "m", "a:", "s", "ə", "n"],
            # Adding more common German words
            "und": ["ʊ", "n", "t"],
            "der": ["d", "e:", "ɐ"],
            "die": ["d", "i:"],
            "das": ["d", "a", "s"],
            "ein": ["aɪ", "n"],
            "eine": ["aɪ", "n", "ə"],
            "zu": ["ts", "u:"],
            "von": ["f", "ɔ", "n"],
            "mit": ["m", "ɪ", "t"],
            "für": ["f", "y:", "ɐ"],
            "ist": ["ɪ", "s", "t"],
            "sind": ["z", "ɪ", "n", "t"],
            "war": ["v", "a:", "ɐ"],
            "waren": ["v", "a:", "ʁ", "ə", "n"],
            "werden": ["v", "e:", "ɐ", "d", "ə", "n"],
            "wurde": ["v", "ʊ", "ʁ", "d", "ə"],
            "wurden": ["v", "ʊ", "ʁ", "d", "ə", "n"],
            "machen": ["m", "a", "x", "ə", "n"],
            "sagen": ["z", "a:", "g", "ə", "n"],
            "gehen": ["g", "e:", "ə", "n"],
            "sehen": ["z", "e:", "ə", "n"],
            "kommen": ["k", "ɔ", "m", "ə", "n"],
            "nehmen": ["n", "e:", "m", "ə", "n"],
            "wissen": ["v", "ɪ", "s", "ə", "n"],
            "kennen": ["k", "ɛ", "n", "ə", "n"],
            "denken": ["d", "ɛ", "ŋ", "k", "ə", "n"],
            "glauben": ["g", "l", "aʊ", "b", "ə", "n"],
            "finden": ["f", "ɪ", "n", "d", "ə", "n"],
            "fehlen": ["f", "e:", "l", "ə", "n"],
            "lieben": ["l", "i:", "b", "ə", "n"],
            "leben": ["l", "e:", "b", "ə", "n"],
            "bleiben": ["b", "l", "aɪ", "b", "ə", "n"],
            "geben": ["g", "e:", "b", "ə", "n"],
            "lassen": ["l", "a", "s", "ə", "n"],
            "tun": ["t", "u:", "n"],
            "machen": ["m", "a", "x", "ə", "n"],
            "heiße": ["h", "aɪ", "s", "ə"],
        }
        
        logger.info(f"Initialized fallback dictionary with {len(self.enhanced_dict)} entries")
    
    def load_or_download_dictionary(self):
        """
        Load the dictionary from file if it exists and is valid, or download it otherwise.
        """
        dict_loaded = False
        
        # Check if dictionary file exists and is valid
        if os.path.exists(self.german_dict_path):
            file_size = os.path.getsize(self.german_dict_path)
            logger.info(f"Found existing dictionary at {self.german_dict_path} (size: {file_size} bytes)")
            
            # First check if the file is a valid dictionary despite its size
            try:
                with open(self.german_dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_few_lines = [f.readline() for _ in range(10)]
                    # Check if the file has a proper dictionary format
                    valid_format = sum(1 for line in first_few_lines if '\t' in line and not line.startswith('#'))
                    
                if valid_format > 3:  # At least 3 valid lines in the first 10 lines
                    logger.info("Existing file appears to be a valid dictionary, attempting to load")
                    dict_loaded = self.load_enhanced_german_dictionary()
                    if dict_loaded:
                        logger.info("Dictionary loaded successfully from existing file")
                        return
                else:
                    logger.warning("Existing file does not appear to be a valid dictionary format")
            except Exception as e:
                logger.warning(f"Error checking dictionary format: {str(e)}")
            
            # Only check size if format check failed
            if not dict_loaded and file_size > MIN_DICT_SIZE:
                dict_loaded = self.load_enhanced_german_dictionary()
                
                # If dictionary loaded successfully, we're done
                if dict_loaded:
                    logger.info("Dictionary loaded successfully from existing file")
                    return
                else:
                    logger.warning("Existing dictionary file is invalid")
            elif not dict_loaded:
                logger.warning(f"Existing dictionary file is too small ({file_size} bytes < {MIN_DICT_SIZE} bytes minimum)")
        
        # If we reach here, we need to download the dictionary
        if not dict_loaded:
            # Try all download methods until one succeeds
            success = self.download_german_dictionary()
            
            if success:
                dict_loaded = self.load_enhanced_german_dictionary()
                if dict_loaded:
                    logger.info("Dictionary loaded successfully after download")
                else:
                    logger.warning("Downloaded dictionary could not be loaded")
            else:
                logger.warning("All download attempts failed, using fallback dictionary")
    
    def download_german_dictionary(self):
        """
        Download the German dictionary using multiple methods and sources.
        
        Returns:
            bool: True if download was successful, False otherwise
        """
        logger.info("Downloading German MFA dictionary...")
        
        # Try each source URL in sequence
        for i, url in enumerate(DICTIONARY_SOURCES["german"]):
            logger.info(f"Trying dictionary source {i+1}/{len(DICTIONARY_SOURCES['german'])}: {url}")
            
            # Method 1: Try using urllib
            try:
                logger.info(f"Downloading with urllib from {url}")
                
                # Create a temporary file to download to
                temp_path = f"{self.german_dict_path}.download"
                
                # Download with progress info
                def report_progress(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(int(block_num * block_size * 100 / total_size), 100)
                        if percent % 20 == 0:  # Report every 20%
                            logger.info(f"Download progress: {percent}%")
                
                # Perform the download
                urllib.request.urlretrieve(url, temp_path, reporthook=report_progress)
                
                # Verify the download
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > MIN_DICT_SIZE:
                    # Check content
                    with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        first_lines = [f.readline() for _ in range(5)]
                        # Check for typical dictionary format (word\tphonemes)
                        valid_format = any('\t' in line for line in first_lines if line.strip())
                        
                        if valid_format:
                            # Move to final location
                            shutil.move(temp_path, self.german_dict_path)
                            logger.info(f"Dictionary successfully downloaded with urllib: {os.path.getsize(self.german_dict_path)} bytes")
                            return True
                        else:
                            logger.warning(f"Downloaded file does not appear to be a valid dictionary (no tab-separated content)")
                else:
                    logger.warning(f"Downloaded file is too small or does not exist")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            except Exception as e:
                logger.warning(f"Download with urllib failed: {str(e)}")
                if os.path.exists(f"{self.german_dict_path}.download"):
                    os.remove(f"{self.german_dict_path}.download")
            
            # Method 2: Try using curl as a subprocess
            try:
                logger.info(f"Downloading with curl from {url}")
                temp_path = f"{self.german_dict_path}.curl"
                curl_cmd = f"curl -L -s -o {temp_path} {url}"
                
                # Execute curl
                result = subprocess.run(curl_cmd, shell=True, check=True, capture_output=True, text=True)
                
                # Verify the download
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > MIN_DICT_SIZE:
                    # Check content format
                    with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        first_lines = [f.readline() for _ in range(5)]
                        valid_format = any('\t' in line for line in first_lines if line.strip())
                        
                        if valid_format:
                            # Move to final location
                            shutil.move(temp_path, self.german_dict_path)
                            logger.info(f"Dictionary successfully downloaded with curl: {os.path.getsize(self.german_dict_path)} bytes")
                            return True
                        else:
                            logger.warning("Downloaded file does not appear to be a valid dictionary")
                else:
                    logger.warning(f"Curl download failed or file is too small")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            except Exception as e:
                logger.warning(f"Download with curl failed: {str(e)}")
                if os.path.exists(f"{self.german_dict_path}.curl"):
                    os.remove(f"{self.german_dict_path}.curl")
            
            # Method 3: Try using requests
            try:
                logger.info(f"Downloading with requests from {url}")
                
                # Set appropriate headers to avoid redirects or server-side rendering
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
                    'Accept': 'text/plain'
                }
                
                response = requests.get(url, headers=headers, allow_redirects=True, stream=True)
                logger.info(f"Response status code: {response.status_code}")
                
                if response.status_code == 200:
                    # Check content type
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type.lower():
                        logger.warning(f"Received HTML content instead of a dictionary file")
                        continue
                    
                    # Save the dictionary
                    temp_path = f"{self.german_dict_path}.requests"
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:  # Filter out keep-alive new chunks
                                f.write(chunk)
                    
                    # Verify the download
                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > MIN_DICT_SIZE:
                        # Check content format
                        with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                            first_lines = [f.readline() for _ in range(5)]
                            valid_format = any('\t' in line for line in first_lines if line.strip())
                            
                            if valid_format:
                                # Move to final location
                                shutil.move(temp_path, self.german_dict_path)
                                logger.info(f"Dictionary successfully downloaded with requests: {os.path.getsize(self.german_dict_path)} bytes")
                                return True
                            else:
                                logger.warning("Downloaded file does not appear to be a valid dictionary")
                    else:
                        logger.warning(f"Downloaded file is too small or does not exist")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    logger.warning(f"Request failed with status code {response.status_code}")
            
            except Exception as e:
                logger.warning(f"Download with requests failed: {str(e)}")
                if os.path.exists(f"{self.german_dict_path}.requests"):
                    os.remove(f"{self.german_dict_path}.requests")
        
        # All download methods and sources failed
        logger.error("All download methods failed")
        
        # Create a more comprehensive dictionary file from our built-in dictionary
        self.create_fallback_dictionary_file()
        
        return False
    
    def create_fallback_dictionary_file(self):
        """
        Create a dictionary file from our built-in fallback dictionary.
        This function is called as a last resort when all download attempts fail.
        """
        logger.info("Creating fallback dictionary file from built-in dictionary")
        
        try:
            with open(self.german_dict_path, 'w', encoding='utf-8') as f:
                f.write("# German pronunciation dictionary (built-in fallback)\n")
                f.write("# This is a limited fallback dictionary\n")
                
                for word, phonemes in sorted(self.enhanced_dict.items()):
                    # Format phonemes with spaces between them
                    phoneme_str = ' '.join(phonemes)
                    f.write(f"{word}\t{phoneme_str}\n")
            
            logger.info(f"Created fallback dictionary file at {self.german_dict_path} with {len(self.enhanced_dict)} entries")
        except Exception as e:
            logger.error(f"Error creating fallback dictionary file: {str(e)}")
    
    def load_enhanced_german_dictionary(self):
        """
        Load the enhanced German dictionary from the downloaded file.
        
        Returns:
            bool: True if dictionary loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.german_dict_path):
                logger.info(f"Loading German dictionary from {self.german_dict_path}")
                file_size = os.path.getsize(self.german_dict_path)
                logger.info(f"Dictionary file size: {file_size} bytes")
                
                # Check if file is too small
                if file_size < 1000:  # Reduced minimum size for validity check
                    logger.warning(f"Dictionary file is suspiciously small ({file_size} bytes), skipping load")
                    return False
                
                # Parse the dictionary file
                valid_entries = 0
                total_lines = 0
                
                # First, count total lines for progress reporting
                with open(self.german_dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                    total_lines = sum(1 for _ in f)
                
                with open(self.german_dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            # Check if line looks like HTML
                            if "<html" in line or "<!DOCTYPE" in line:
                                logger.error(f"Dictionary file contains HTML, not a valid dictionary")
                                return False
                            
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                word = parts[0].lower()
                                phonemes = parts[1].split()
                                
                                # Store in our dictionary
                                self.enhanced_dict[word] = phonemes
                                valid_entries += 1
                                
                                # Log progress occasionally
                                if valid_entries % 10000 == 0 or line_num % 50000 == 0:
                                    logger.info(f"Loaded {valid_entries} words, processed {line_num}/{total_lines} lines ({line_num/total_lines*100:.1f}%)")
                            else:
                                # Only log a limited number of warnings to avoid log flooding
                                if valid_entries < 5 or line_num % 10000 == 0:
                                    logger.warning(f"Invalid line format at line {line_num}: {line}")
                        except Exception as e:
                            if valid_entries < 5 or line_num % 10000 == 0:
                                logger.warning(f"Error processing line {line_num}: {str(e)}")
                            continue
                
                # Check if we loaded enough entries
                if valid_entries < 20:  # Reduced minimum threshold to accommodate smaller dictionaries
                    logger.error(f"Dictionary loaded only {valid_entries} valid entries, which is suspiciously low")
                    return False
                
                logger.info(f"Loaded {valid_entries} words into enhanced dictionary from {total_lines} total lines")
                
                # Log a sample of the dictionary
                sample_words = sorted(list(self.enhanced_dict.keys())[:10])
                logger.info(f"Sample words in dictionary: {sample_words}")
                
                # Dictionary loaded successfully
                return True
            else:
                logger.warning(f"German dictionary file not found at {self.german_dict_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading German dictionary: {str(e)}")
            logger.exception("Detailed error trace:")
            return False
    
    def g2p(self, text: str) -> List[str]:
        """
        Convert German text to phoneme sequence (Grapheme to Phoneme).
        
        Args:
            text: German text to convert
            
        Returns:
            List of phonemes (IPA symbols)
        """
        logger.info(f"Converting text to phonemes: {text}")
        
        # Lowercase and remove punctuation
        processed_text = re.sub(r'[^\w\s\'-]', '', text.lower())
        words = processed_text.split()
        logger.info(f"Processed text for G2P: {words}")
        
        # Check our dictionary size - if it's too small, we might have had an issue
        if len(self.enhanced_dict) < 10:
            logger.warning("Dictionary seems to be almost empty, reinitializing fallback dictionary")
            self.initialize_fallback_dictionary()
        
        # Look up each word in our dictionaries
        phonemes = []
        unknown_words = []
        
        for word in words:
            # Check our dictionary
            if word in self.enhanced_dict:
                word_phonemes = self.enhanced_dict[word]
                logger.info(f"Word '{word}' found in dictionary: {word_phonemes}")
                phonemes.extend(word_phonemes)
            else:
                # Check subwords (for compounds)
                found = False
                
                # Try to break down compound words
                if len(word) > 6:  # Only try for longer words
                    best_breakdown = []
                    for i in range(3, len(word)-2):
                        part1 = word[:i]
                        part2 = word[i:]
                        
                        if part1 in self.enhanced_dict and part2 in self.enhanced_dict:
                            logger.info(f"Compound word '{word}' broken down to '{part1}'+'{part2}'")
                            phonemes.extend(self.enhanced_dict[part1])
                            phonemes.extend(self.enhanced_dict[part2])
                            found = True
                            break
                
                if not found:
                    # Word not found in dictionary
                    logger.warning(f"Word '{word}' not found in dictionary, using letters as approximation")
                    unknown_words.append(word)
                    # Use letters as approximate phonemes
                    phonemes.extend(list(word))
        
        if unknown_words:
            logger.warning(f"Words not found in dictionary: {unknown_words}")
        
        logger.info(f"G2P generated {len(phonemes)} phonemes: {phonemes}")
        return phonemes
    
    async def score_phonemes(self, audio_data: bytes, expected_phonemes: List[str]) -> List[Tuple[str, float]]:
        """
        Score each phoneme in the audio against the expected phonemes.
        
        Args:
            audio_data: Raw audio bytes
            expected_phonemes: List of expected phonemes (IPA)
            
        Returns:
            List of tuples containing (phoneme, score)
        """
        if self.mock_mode:
            # Generate mock scores for demonstration
            # In a real implementation, this would use the acoustic model
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Generate scores with some random variation
            # Difficult phonemes are given lower scores on average
            scores = []
            for phoneme in expected_phonemes:
                if phoneme in self.difficult_phonemes:
                    # More likely to have lower score for difficult phonemes
                    base_score = np.random.uniform(0.5, 0.9)
                else:
                    # More likely to have higher score for common phonemes
                    base_score = np.random.uniform(0.7, 0.98)
                
                scores.append((phoneme, base_score))
            
            return scores
        else:
            # In a real implementation, this would:
            # 1. Convert audio to features (e.g., MFCC, filterbank)
            # 2. Run the acoustic model to get phoneme posteriors
            # 3. Compute GOP scores
            # 4. Return the scores
            raise NotImplementedError("Non-mock mode not implemented")
    
    def generate_feedback(self, phoneme_scores: List[Tuple[str, float]]) -> Dict[str, Any]:
        """
        Generate feedback based on phoneme scores.
        
        Args:
            phoneme_scores: List of (phoneme, score) tuples
            
        Returns:
            Dictionary with feedback information
        """
        total_score = 0.0
        feedback_points = []
        
        # Threshold for considering a phoneme "mispronounced"
        threshold = 0.7
        
        problematic_phonemes = []
        
        for phoneme, score in phoneme_scores:
            total_score += score
            if score < threshold:
                problematic_phonemes.append(phoneme)
                if phoneme in self.difficult_phonemes:
                    feedback_points.append(f"The '{phoneme}' sound needs improvement. {self.difficult_phonemes[phoneme]}")
                else:
                    feedback_points.append(f"The '{phoneme}' sound was not pronounced clearly.")
        
        avg_score = total_score / len(phoneme_scores) if phoneme_scores else 0
        
        # Scale to 0-100 for easier understanding
        scaled_score = avg_score * 100
        
        # Generate overall feedback
        if scaled_score > 90:
            overall_feedback = "Excellent pronunciation! Keep up the good work."
        elif scaled_score > 80:
            overall_feedback = "Very good pronunciation. Practice a few sounds to perfect it."
        elif scaled_score > 70:
            overall_feedback = "Good pronunciation. Focus on the highlighted areas for improvement."
        elif scaled_score > 60:
            overall_feedback = "Fair pronunciation. Continue practicing the difficult sounds."
        else:
            overall_feedback = "Keep practicing! Focus on pronouncing each sound clearly."
        
        # Combine feedback
        if feedback_points:
            detailed_feedback = "Areas for improvement:\n" + "\n".join(feedback_points)
        else:
            detailed_feedback = "No specific issues detected. Great pronunciation!"
        
        return {
            "score": float(f"{scaled_score:.1f}"),
            "overall_feedback": overall_feedback,
            "detailed_feedback": detailed_feedback,
            "problematic_phonemes": problematic_phonemes
        }
    
    async def synthesize_correct_speech(self, text: str) -> bytes:
        """
        Synthesize correct pronunciation of the text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio bytes of synthesized speech
        """
        if self.mock_mode:
            # For demonstration, return a placeholder audio (1 second of silence)
            # In a real implementation, this would use a TTS model
            await asyncio.sleep(0.5)  # Simulate processing time
            
            # Generate a short sine wave as placeholder audio
            sample_rate = 16000
            duration = 2.0  # seconds
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            sine_wave = np.sin(2 * np.pi * 440 * t) * 0.3
            
            # Convert to 16-bit PCM
            audio_16bit = (sine_wave * 32767).astype(np.int16)
            
            # Convert to bytes
            audio_bytes = audio_16bit.tobytes()
            
            # For demonstration, we'll return base64-encoded audio
            # In a real implementation, this might be stored and returned as a URL
            return base64.b64encode(audio_bytes)
        else:
            # In a real implementation, this would use a TTS service
            # For example, using ElevenLabs or another TTS service
            raise NotImplementedError("Non-mock mode not implemented")
    
    async def assess_pronunciation(self, audio_data: bytes, reference_text: str) -> Dict[str, Any]:
        """
        Assess pronunciation of the audio against the reference text.
        
        Args:
            audio_data: Raw audio bytes
            reference_text: Reference text that was supposed to be spoken
            
        Returns:
            Dictionary with assessment results
        """
        try:
            logger.info(f"Assessing pronunciation for text: {reference_text}")
            
            # Convert reference text to phonemes
            expected_phonemes = self.g2p(reference_text)
            logger.info(f"Expected phonemes: {expected_phonemes}")
            
            # Score phonemes
            phoneme_scores = await self.score_phonemes(audio_data, expected_phonemes)
            
            # Generate feedback
            feedback = self.generate_feedback(phoneme_scores)
            
            # Synthesize correct pronunciation
            correct_audio = await self.synthesize_correct_speech(reference_text)
            
            # Combine results
            result = {
                **feedback,
                "reference_text": reference_text,
                "expected_phonemes": expected_phonemes,
                "correct_audio": correct_audio.decode('utf-8') if isinstance(correct_audio, bytes) else correct_audio,
                "phoneme_scores": [{"phoneme": p, "score": float(f"{s:.2f}")} for p, s in phoneme_scores]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in pronunciation assessment: {str(e)}")
            raise Exception(f"Error in pronunciation assessment: {str(e)}")

# Singleton instance
pronunciation_service = PronunciationAssessmentService() 