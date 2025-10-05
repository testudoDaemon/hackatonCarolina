# pip install fastapi uvicorn requests
from fastapi import FastAPI
import os, requests

API_KEY = os.getenv("5E3D86BE-A17B-11F0-BDE5-4201AC1DC121")  # export PURPLEAIR_API_KEY="tu_key"
SENSOR  = os.getenv("PURPLEAIR_SENSOR=12345")   # export PURPLEAIR_SENSOR="12345"

app = FastAPI()

@app.get("/api/humedad")
def humedad():
    url = f"https://api.purpleair.com/v1/sensors/{SENSOR}"
    headers = {"X-API-Key": API_KEY}
    params = {"fields": "humidity"}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# uvicorn main:app --host 127.0.0.1 --port 8000
