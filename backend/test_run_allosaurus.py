"""
Simple script to test the Allosaurus service.
"""
import os
import asyncio
from services.allosaurus_service import AllosaurusService

async def main():
    print("Initializing Allosaurus service...")
    service = AllosaurusService()
    print("Running with Allosaurus model")
    
    sample_path = os.path.join(os.path.dirname(__file__), "sample.wav")
    
    if not os.path.exists(sample_path):
        print(f"Error: sample.wav not found at {sample_path}")
        return
    
    print(f"Processing {sample_path}...")
    result = await service.recognize_phonemes(sample_path)
    
    print("\nAllosaurus Result:")
    print(f"Phoneme text: {result['text']}")
    print(f"Phonemes: {result['phonemes']}")
    print(f"Confidence: {result['confidence']}")

if __name__ == "__main__":
    asyncio.run(main()) 