from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn
from datetime import datetime
import json
import time
import asyncio
import requests
import base64
from supabase import create_client, Client

# ==========================================================
# 🚀 FASTAPI INITIALIZATION
# ==========================================================
app = FastAPI(
    title="Gemini Veo 3 Video Generation API",
    version="2.0.0",
    description="AI-Powered Video Generation using Google's Gemini Veo 3"
)

# CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# ⚙️ CONFIGURATION
# ==========================================================
SUPABASE_URL = "https://enwzcoocguqxxkkzxdtj.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVud3pjb29jZ3VxeHhra3p4ZHRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM3NTI0NiwiZXhwIjoyMDcxOTUxMjQ2fQ.AMZMo7jEe7iuhaTYAwM1FahlFI7pDOy4axWp-kGQMI4"
GEMINI_API_KEY = "AIzaSyBOX3Nrr6goc1qXHaElN82-igqBl7KZUGw"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "veo-3.0-generate-001"

VEO3_CONFIG = {
    "duration": 8,
    "aspectRatio": "16:9",
    "resolution": "720p",
    "generateAudio": True
}

# ==========================================================
# 🗄️ SUPABASE INITIALIZATION
# ==========================================================
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✓ Supabase initialized")
except Exception as e:
    print(f"✗ Supabase error: {e}")
    supabase = None

# ==========================================================
# 🧠 DATA MODELS
# ==========================================================
class VideoGenerationResponse(BaseModel):
    message: str
    total_prompts: int
    total_users: int

# ==========================================================
# 🎥 GEMINI VIDEO GENERATION FUNCTIONS
# ==========================================================
video_generation_progress: Dict[str, Dict] = {}

async def submit_to_gemini_veo3(prompt: str) -> str:
    """Submit prompt to Gemini Veo 3 API"""
    url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:predictLongRunning"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": VEO3_CONFIG
    }
    
    print(f"[GEMINI] Submitting: {prompt[:50]}...")
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    operation_name = result.get("name")
    if not operation_name:
        raise Exception("No operation name in response")
    
    print(f"[GEMINI] Operation: {operation_name}")
    return operation_name

async def poll_gemini_operation(operation_name: str) -> str:
    """Poll Gemini operation until video is ready"""
    status_url = f"{GEMINI_BASE_URL}/{operation_name}"
    headers = {"x-goog-api-key": GEMINI_API_KEY}
    
    print(f"[GEMINI] Polling operation...")
    for attempt in range(120):  # 10 minutes max
        response = requests.get(status_url, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("done"):
            if "error" in result:
                raise Exception(f"Generation failed: {result['error'].get('message')}")
            
            # Extract video data
            video_data = (result.get("response", {})
                         .get("generateVideoResponse", {})
                         .get("generatedSamples", [{}])[0]
                         .get("video", {}))
            
            if uri := video_data.get("uri"):
                print(f"[GEMINI] Video URI: {uri}")
                return uri
            
            if bytes_b64 := video_data.get("bytesBase64Encoded"):
                print(f"[GEMINI] Video as base64 ({len(bytes_b64)} chars)")
                return f"base64:{bytes_b64}"
            
            raise Exception("No video in response")
        
        await asyncio.sleep(5)
    
    raise Exception("Timeout after 10 minutes")

async def download_video_from_gemini(video_uri_or_bytes: str) -> bytes:
    """Download or decode video from Gemini"""
    if video_uri_or_bytes.startswith("base64:"):
        print(f"[GEMINI] Decoding base64 video...")
        return base64.b64decode(video_uri_or_bytes.replace("base64:", ""))
    
    print(f"[GEMINI] Downloading from URI...")
    response = requests.get(video_uri_or_bytes, stream=True, timeout=60)
    response.raise_for_status()
    
    video_content = response.content
    print(f"[GEMINI] Downloaded {len(video_content)} bytes")
    return video_content

async def get_or_create_folder(access_token: str, folder_name: str = "gen_videos") -> str:
    """
    Check if 'gen_videos' folder exists in Google Drive, create if not
    Returns the folder ID
    """
    print(f"[DRIVE] Checking for '{folder_name}' folder...")
    
    # Search for the folder
    search_url = f"https://www.googleapis.com/drive/v3/files"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Query to find folder with exact name
    params = {
        "q": f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        "fields": "files(id, name)",
        "spaces": "drive"
    }
    
    response = requests.get(search_url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    files = result.get("files", [])
    
    if files:
        folder_id = files[0]["id"]
        print(f"[DRIVE] ✓ Folder '{folder_name}' found (ID: {folder_id})")
        return folder_id
    
    # Folder doesn't exist, create it
    print(f"[DRIVE] Folder '{folder_name}' not found, creating...")
    
    create_url = "https://www.googleapis.com/drive/v3/files"
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    
    response = requests.post(
        create_url,
        headers=headers,
        json=folder_metadata,
        timeout=30
    )
    response.raise_for_status()
    
    folder_data = response.json()
    folder_id = folder_data.get("id")
    
    print(f"[DRIVE] ✓ Folder '{folder_name}' created (ID: {folder_id})")
    return folder_id

async def upload_to_google_drive(video_content: bytes, prompt_id: int, access_token: str) -> str:
    """
    Upload video to user's Google Drive inside 'gen_videos' folder
    
    THIS IS THE GOOGLE DRIVE UPLOAD LOGIC - FULLY IMPLEMENTED!
    1. Check if 'gen_videos' folder exists, create if not
    2. Upload video to that folder
    3. Make it publicly shareable
    4. Return Google Drive link
    """
    print(f"[DRIVE] Uploading video for prompt {prompt_id} ({len(video_content)} bytes)")
    
    # Step 1: Get or create 'gen_videos' folder
    folder_id = await get_or_create_folder(access_token, "gen_videos")
    
    # Step 2: Upload video to the folder
    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    
    # File metadata with parent folder
    file_metadata = {
        "name": f"veo3_video_{prompt_id}_{int(time.time())}.mp4",
        "mimeType": "video/mp4",
        "parents": [folder_id]  # Upload to 'gen_videos' folder
    }
    
    # Create multipart body
    boundary = "===============7330845974216740156=="
    body_parts = [
        f"--{boundary}",
        "Content-Type: application/json; charset=UTF-8",
        "",
        json.dumps(file_metadata),
        "",
        f"--{boundary}",
        "Content-Type: video/mp4",
        "",
    ]
    
    body = "\r\n".join(body_parts).encode('utf-8') + video_content + f"\r\n--{boundary}--".encode('utf-8')
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": f'multipart/related; boundary="{boundary}"'
    }
    
    # Upload to Google Drive
    response = requests.post(upload_url, headers=headers, data=body, timeout=120)
    response.raise_for_status()
    
    file_data = response.json()
    file_id = file_data.get("id")
    
    if not file_id:
        raise Exception(f"No file ID in response: {file_data}")
    
    print(f"[DRIVE] ✓ Uploaded to 'gen_videos' folder! File ID: {file_id}")
    
    # Step 3: Make file publicly shareable (anyone with link can view)
    permission_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
    permission_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    permission_body = {
        "role": "reader",
        "type": "anyone"
    }
    
    requests.post(
        permission_url,
        headers=permission_headers,
        json=permission_body,
        timeout=30
    )
    print(f"[DRIVE] ✓ File made public")
    
    # Step 4: Return shareable Google Drive link
    drive_link = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"[DRIVE] ✓ Shareable link: {drive_link}")
    
    return drive_link

# ==========================================================
# 🧩 BACKGROUND TASK
# ==========================================================
async def generate_videos_for_all_users(user_prompts: Dict[int, Dict]):
    """
    Background task that processes all pending prompts:
    1. Submit to Gemini Veo 3
    2. Wait for video generation
    3. Download video
    4. Upload to user's Google Drive (using their access_token)
    5. Update database with Drive link
    """
    try:
        completed = 0
        total = sum(len(d['prompts']) for d in user_prompts.values())
        
        print(f"\n{'='*60}")
        print(f"Starting generation: {len(user_prompts)} users, {total} prompts")
        print(f"{'='*60}\n")
        
        for user_id, user_data in user_prompts.items():
            access_token = user_data['user_data']['access_token']
            user_email = user_data['user_data'].get('google_email', f'User {user_id}')
            
            video_generation_progress["all_users"]["current_user"] = f"{user_email}"
            
            for prompt_data in user_data['prompts']:
                prompt_text = prompt_data['promt']
                prompt_id = prompt_data['id']
                
                print(f"\n--- Prompt {completed + 1}/{total} ---")
                print(f"User: {user_email}")
                print(f"Prompt: {prompt_text[:100]}...")
                
                # Update progress
                video_generation_progress["all_users"].update({
                    "current_prompt": prompt_text[:50],
                    "current_step": "Step 1/4: Submitting to Gemini Veo 3",
                    "completed_count": completed,
                    "progress_percentage": (completed / total) * 100
                })
                
                # Step 1: Submit to Gemini
                operation = await submit_to_gemini_veo3(prompt_text)
                
                # Step 2: Wait for video generation
                video_generation_progress["all_users"]["current_step"] = "Step 2/4: Generating video (1-2 min)"
                video_uri = await poll_gemini_operation(operation)
                
                # Step 3: Download video
                video_generation_progress["all_users"]["current_step"] = "Step 3/4: Downloading video"
                video_content = await download_video_from_gemini(video_uri)
                
                # Step 4: Upload to user's Google Drive
                video_generation_progress["all_users"]["current_step"] = "Step 4/4: Uploading to Google Drive"
                drive_url = await upload_to_google_drive(video_content, prompt_id, access_token)
                
                # Update database with Drive link
                supabase.table('video').update({'video_url': drive_url}).eq('id', prompt_id).execute()
                
                print(f"✓ Completed! Drive URL: {drive_url}")
                
                completed += 1
                video_generation_progress["all_users"].update({
                    "completed_count": completed,
                    "progress_percentage": (completed / total) * 100
                })
        
        # Mark as completed
        print(f"\n{'='*60}")
        print(f"✓ ALL VIDEOS GENERATED SUCCESSFULLY!")
        print(f"{'='*60}\n")
        
        video_generation_progress["all_users"].update({
            "status": "completed",
            "current_step": "All videos generated and uploaded to Drive!",
            "progress_percentage": 100.0
        })
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        video_generation_progress["all_users"].update({
            "status": "error",
            "error_message": str(e),
            "current_step": f"Error: {str(e)}"
        })

# ==========================================================
# 🌐 API ROUTES
# ==========================================================
@app.get("/api/video-records")
async def get_video_records():
    """Get all video records from database"""
    if not supabase:
        raise HTTPException(500, "Database not connected")
    
    result = supabase.table('video').select('*').order('id').execute()
    return result.data

@app.post("/api/generate-videos", response_model=VideoGenerationResponse)
async def start_video_generation(background_tasks: BackgroundTasks):
    """Start video generation for all pending prompts"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY":
        raise HTTPException(500, "Gemini API key not configured")
    
    # Get all pending prompts (no video URL)
    prompts_null = supabase.table('video').select('*').is_('video_url', 'null').execute()
    prompts_empty = supabase.table('video').select('*').in_('video_url', ['', 'Nullable']).execute()
    all_pending = prompts_null.data + prompts_empty.data
    
    if not all_pending:
        raise HTTPException(400, "No pending prompts")
    
    # Get user data (with Google Drive access tokens)
    user_ids = list(set(p.get('userid') for p in all_pending if p.get('userid')))
    users = supabase.table('drive_accounts').select('*').in_('user_id', user_ids).execute()
    users_dict = {u['user_id']: u for u in users.data}
    
    # Group prompts by user
    user_prompts = {}
    for prompt in all_pending:
        user_id = prompt.get('userid')
        if user_id and user_id in users_dict and users_dict[user_id].get('access_token'):
            if user_id not in user_prompts:
                user_prompts[user_id] = {'prompts': [], 'user_data': users_dict[user_id]}
            user_prompts[user_id]['prompts'].append(prompt)
    
    if not user_prompts:
        raise HTTPException(400, "No users with valid Google Drive access tokens")
    
    total = sum(len(d['prompts']) for d in user_prompts.values())
    
    # Initialize progress tracking
    video_generation_progress["all_users"] = {
        "status": "processing",
        "completed_count": 0,
        "total_count": total,
        "progress_percentage": 0.0,
        "current_step": "Starting...",
        "current_prompt": None,
        "current_user": None,
        "error_message": None
    }
    
    # Start background task
    background_tasks.add_task(generate_videos_for_all_users, user_prompts)
    
    return VideoGenerationResponse(
        message="Video generation started",
        total_prompts=total,
        total_users=len(user_prompts)
    )

@app.get("/api/progress-stream")
async def get_progress_stream():
    """Server-Sent Events stream for real-time progress updates"""
    async def generate():
        while True:
            progress = video_generation_progress.get("all_users", {
                "status": "idle",
                "completed_count": 0,
                "total_count": 0,
                "progress_percentage": 0.0,
                "current_step": "No generation in progress",
                "current_prompt": None,
                "current_user": None,
                "error_message": None
            })
            
            yield f"data: {json.dumps(progress)}\n\n"
            
            if progress.get("status") in ["completed", "error"]:
                break
                
            await asyncio.sleep(1)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/api/stats")
async def get_stats():
    """Get statistics about video generation"""
    if not supabase:
        raise HTTPException(500, "Database not connected")
    
    all_records = supabase.table('video').select('*').execute()
    total = len(all_records.data)
    completed = sum(1 for r in all_records.data 
                   if r.get('video_url') and r['video_url'] not in ['', 'Nullable'])
    
    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "completion_rate": round((completed / total * 100) if total > 0 else 0, 1)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not supabase:
        return {"status": "unhealthy", "error": "Database not connected"}
    
    try:
        result = supabase.table('video').select('count', count='exact').execute()
        return {
            "status": "healthy",
            "service": "Gemini Veo 3 API",
            "database": "connected",
            "total_records": result.count,
            "api_configured": bool(GEMINI_API_KEY),
            "google_drive_upload": "enabled"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ==========================================================
# 🧭 STATIC FRONTEND (index.html)
# ==========================================================
# Serve index.html and other static files from current directory
app.mount("/", StaticFiles(directory=".", html=True), name="frontend")

# ==========================================================
# 🏁 MAIN ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎬 GEMINI VEO 3 API SERVER")
    print("="*60)
    print(f"Model: {GEMINI_MODEL}")
    print(f"Config: {VEO3_CONFIG['duration']}s | {VEO3_CONFIG['aspectRatio']} | {VEO3_CONFIG['resolution']}")
    print(f"API Key: {'✓ Configured' if GEMINI_API_KEY else '✗ Missing'}")
    print(f"Google Drive: ✓ Upload enabled")
    print("="*60 + "\n")
    print("🚀 Starting server on http://0.0.0.0:8080")
    print("📚 API Docs: http://0.0.0.0:8080/docs\n")
    uvicorn.run("backend:app", host="0.0.0.0", port=8080, reload=True)