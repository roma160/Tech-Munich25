"""
Test the Allosaurus service integration.
"""
import os
import pytest
import asyncio
from services.allosaurus_service import AllosaurusService

@pytest.fixture
def sample_wav_path():
    """
    Provides a path to a sample WAV file for testing.
    """
    # Path to test audio file
    sample_path = os.path.join(os.path.dirname(__file__), "sample.wav")
    
    if not os.path.exists(sample_path):
        pytest.skip(f"Test WAV file doesn't exist at {sample_path}. Required for testing.")
    
    return sample_path

@pytest.mark.asyncio
async def test_allosaurus_service_initialization():
    """Test that the AllosaurusService initializes properly."""
    service = AllosaurusService()
    assert service is not None
    assert hasattr(service, 'model')

@pytest.mark.asyncio
async def test_phoneme_recognition(sample_wav_path):
    """Test phoneme recognition function."""
    service = AllosaurusService()
    
    result = await service.recognize_phonemes(sample_wav_path)
    
    assert result is not None
    assert "text" in result
    assert "phonemes" in result
    assert isinstance(result["phonemes"], list)
    
    # For real model results, verify structure but not exact content
    assert isinstance(result["text"], str)
    assert len(result["phonemes"]) > 0

if __name__ == "__main__":
    asyncio.run(test_allosaurus_service_initialization()) 