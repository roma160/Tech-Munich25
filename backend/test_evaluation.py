import requests
import time 
import json 

with open("./sample_roman.wav", "rb") as file:
    r = requests.post("http://localhost:8000/upload", files={"file": file})

response_json = r.json()
status_code = response_json["status"]
status_response = None
task_id = response_json["id"]

while not status_code == "completed":
    print("waiting for task to complete")
    status_response = requests.get(f"http://localhost:8000/status/{task_id}")
    print(status_response.json())
    status_code = status_response.json()["status"]
    time.sleep(1)

print(status_response.json())