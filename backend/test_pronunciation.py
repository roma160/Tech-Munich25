"""
Test script for pronunciation assessment.

This script tests the pronunciation assessment endpoint by sending a sample.wav file
and a reference text, then displays the pronunciation assessment results.
"""
import os
import json
import requests
import base64
import argparse

def test_pronunciation_assessment(sample_path, reference_text, api_url="http://localhost:8000"):
    """
    Test the pronunciation assessment endpoint.
    
    Args:
        sample_path: Path to the sample WAV file
        reference_text: Reference text for pronunciation assessment
        api_url: URL of the API server
    """
    try:
        # Check if file exists
        if not os.path.exists(sample_path):
            print(f"Error: Sample file not found at {sample_path}")
            return
        
        print(f"Testing pronunciation assessment with:")
        print(f"- Sample file: {sample_path}")
        print(f"- Reference text: '{reference_text}'")
        print(f"- API URL: {api_url}")
        
        # Prepare the request
        url = f"{api_url}/assess_pronunciation"
        
        # Open the WAV file
        with open(sample_path, "rb") as f:
            files = {"file": (os.path.basename(sample_path), f, "audio/wav")}
            data = {"reference_text": reference_text}
            
            # Send the request
            print("\nSending request...")
            response = requests.post(url, files=files, data=data)
            
            # Check for successful response
            if response.status_code == 200:
                result = response.json()
                
                # Display the results
                print("\n=== Pronunciation Assessment Results ===")
                print(f"Overall score: {result['score']}/100")
                print(f"\nOverall feedback: {result['overall_feedback']}")
                print(f"\nDetailed feedback: {result['detailed_feedback']}")
                
                print("\nPhoneme scores:")
                for phoneme_score in result['phoneme_scores']:
                    print(f"- {phoneme_score['phoneme']}: {phoneme_score['score']}")
                
                # Save correct pronunciation audio to file (for demonstration purposes)
                if 'correct_audio' in result:
                    correct_audio_path = "correct_pronunciation.wav"
                    audio_bytes = base64.b64decode(result['correct_audio'])
                    with open(correct_audio_path, "wb") as audio_file:
                        audio_file.write(audio_bytes)
                    print(f"\nCorrect pronunciation audio saved to: {correct_audio_path}")
                
                # Save full result to JSON file
                with open("pronunciation_result.json", "w") as json_file:
                    json.dump(result, json_file, indent=2)
                print("Full result saved to pronunciation_result.json")
                
            else:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Error testing pronunciation assessment: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test pronunciation assessment endpoint")
    parser.add_argument("--sample", default="sample.wav", help="Path to the sample WAV file")
    parser.add_argument("--text", default="Hallo, ich heiße Pontecan. Ich spreche einigermaßen Deutsch.", 
                        help="Reference text for pronunciation assessment")
    parser.add_argument("--api", default="http://localhost:8000", help="API URL")
    
    args = parser.parse_args()
    
    test_pronunciation_assessment(args.sample, args.text, args.api) 