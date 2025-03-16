from phonemizer import phonemize
from dotenv import load_dotenv
import pathlib

load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent.parent.absolute() / ".env")

class PhonemizerService:
    """
    Service for phonemizing text using the phonemizer module.

    Installation guide for the dependencies:
    https://bootphon.github.io/phonemizer/install.html
    """
    
    def __init__(self, language='de'):
        """
        Initialize the Phonemizer service with the specified language.
        
        Args:
            language (str): The language code for phonemization (default is 'en-us').
        """
        self.language = language
    
    async def phonemize_string(self, input_string: str) -> str:
        """
        Phonemizes the given input string using the specified language.
        
        Args:
            input_string (str): The string to phonemize.
        
        Returns:
            str: The phonemized string.
        """
        return phonemize(input_string, language=self.language, backend='espeak', strip=True)

if __name__ == "__main__":
    # Example usage
    service = PhonemizerService()
    input_string = "Hallo, wie heißt du?"
    phonemized_string = service.phonemize_string(input_string)
    print(f"Original: {input_string}")
    print(f"Phonemized: {phonemized_string}")
