import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI application
app = FastAPI(title="Git Music Dashboard")

# Serve frontend HTML files directly from root & subfolders
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/login")
async def serve_login():
    return FileResponse("login.html")

@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse("Dashboard/dashboard.html")

# Optional: Run Discord bot concurrently on startup
@app.on_event("startup")
async def start_bot():
    # If bot startup function is in bot.py, trigger it here as a background task
    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)