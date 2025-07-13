# fastapi_app/main.py
from fastapi import FastAPI

app = FastAPI(title="Telegram Data Product API")

@app.get("/")
async def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {"message": "Telegram Data Product API is running!"}