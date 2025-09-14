from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS so frontend (possibly on different port) can call backend APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount React build static files (JS, CSS, images)
app.mount("/static", StaticFiles(directory="../frontend/build/static"), name="static")

# Setup Jinja2 templates to serve index.html
templates = Jinja2Templates(directory="../frontend/build")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"

@app.get("/api/youtube/trending")
async def get_trending_videos(region_code: str = "US", max_results: int = 10):
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")

    params = {
        "part": "snippet,contentDetails,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{YOUTUBE_API_URL}/videos", params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch YouTube data")

    return response.json()

# Catch-all route to serve React app for any frontend route (SPA support)
@app.get("/{full_path:path}")
async def serve_react_app(request: Request, full_path: str):
    return templates.TemplateResponse("index.html", {"request": request})