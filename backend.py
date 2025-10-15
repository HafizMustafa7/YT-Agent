"""
🎬 UNIFIED VIDEO GENERATION SYSTEM
Combines Dashboard + Image Generation in one application
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
from datetime import datetime
import json
import time
import asyncio
import requests
from supabase import create_client, Client
from google import genai
from google.genai import types

# ==========================================================
# 🚀 FASTAPI APP - UNIFIED
# ==========================================================
app = FastAPI(
    title="Unified Video Generation System",
    version="3.0.0",
    description="Complete Dashboard + AI Image Generation"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# ⚙️ CONFIGURATION
# ==========================================================
SUPABASE_URL = "https://enwzcoocguqxxkkzxdtj.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVud3pjb29jZ3VxeHhra3p4ZHRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM3NTI0NiwiZXhwIjoyMDcxOTUxMjQ2fQ.AMZMo7jEe7iuhaTYAwM1FahlFI7pDOy4axWp-kGQMI4"
GEMINI_API_KEY = "AIzaSyCZKNrCrRG04BjcQ9HQ5DXCvd5q6Lee02k"
MODEL = "gemini-2.0-flash-preview-image-generation"
DELAY_BETWEEN_PROMPTS = 30

print(f"\n{'='*70}")
print(f"🎨 UNIFIED VIDEO GENERATION SYSTEM")
print(f"{'='*70}")
print(f"📦 Model: {MODEL}")
print(f"⏱️  Rate Limit: {DELAY_BETWEEN_PROMPTS} seconds")
print(f"{'='*70}\n")

# Initialize clients
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
print("✅ Gemini & Supabase Connected\n")

# ==========================================================
# 🧠 MODELS
# ==========================================================
class VideoRecord(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    userid: Optional[str] = None
    video_url: Optional[str] = None
    promt: Optional[str] = None

class PromptUpdate(BaseModel):
    promt: str

class ImageGenerationResponse(BaseModel):
    message: str
    total_prompts: int
    total_users: int
    delay_info: str

# Global progress tracker
image_generation_progress: Dict[str, Dict] = {}

# ==========================================================
# 🎨 IMAGE GENERATION FUNCTIONS
# ==========================================================
async def generate_image_with_gemini(prompt: str, retry_count: int = 3) -> bytes:
    """Generate image using Gemini"""
    print(f"[IMAGE] Generating: {prompt[:80]}...")
    
    for attempt in range(retry_count):
        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                temperature=1.0,
            )
            
            image_data = None
            
            for chunk in gemini_client.models.generate_content_stream(
                model=MODEL,
                contents=contents,
                config=generate_content_config,
            ):
                if (chunk.candidates and 
                    chunk.candidates[0].content and 
                    chunk.candidates[0].content.parts):
                    
                    for part in chunk.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            image_data = part.inline_data.data
                            print(f"[IMAGE] ✅ Generated ({len(image_data)} bytes)")
                            return image_data
            
            if not image_data:
                raise Exception("No image data in response")
            
            return image_data
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "quota" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                wait_time = 60 * (attempt + 1)
                print(f"[IMAGE] ⚠️ Rate limit! Waiting {wait_time}s...")
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {retry_count} retries")
            
            print(f"[IMAGE ERROR] Attempt {attempt + 1}/{retry_count}: {e}")
            if attempt < retry_count - 1:
                await asyncio.sleep(10)
                continue
            else:
                raise Exception(f"Failed after {retry_count} attempts: {str(e)}")
    
    raise Exception("Image generation failed")

async def get_or_create_folder(access_token: str, folder_name: str = "ai_generated_images") -> str:
    """Get or create Google Drive folder"""
    print(f"[DRIVE] Checking for '{folder_name}' folder...")
    
    search_url = "https://www.googleapis.com/drive/v3/files"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "q": f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        "fields": "files(id, name)",
        "spaces": "drive"
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 401:
            raise Exception("Access token expired. Please reconnect Google Drive.")
        
        response.raise_for_status()
        files = response.json().get("files", [])
        
        if files:
            folder_id = files[0]["id"]
            print(f"[DRIVE] ✅ Found folder (ID: {folder_id})")
            return folder_id
        
        print(f"[DRIVE] Creating new folder...")
        create_url = "https://www.googleapis.com/drive/v3/files"
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        
        response = requests.post(create_url, headers=headers, json=folder_metadata, timeout=30)
        response.raise_for_status()
        
        folder_id = response.json().get("id")
        print(f"[DRIVE] ✅ Created folder (ID: {folder_id})")
        return folder_id
        
    except Exception as e:
        raise Exception(f"Failed to access Drive folder: {str(e)}")

async def upload_to_google_drive(image_content: bytes, prompt_id: int, access_token: str) -> str:
    """Upload image to Google Drive"""
    print(f"[DRIVE] Uploading image for prompt {prompt_id}")
    
    try:
        folder_id = await get_or_create_folder(access_token)
    except Exception as e:
        raise
    
    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    
    file_metadata = {
        "name": f"gemini_image_{prompt_id}_{int(time.time())}.png",
        "mimeType": "image/png",
        "parents": [folder_id]
    }
    
    boundary = "===============7330845974216740156=="
    body_parts = [
        f"--{boundary}",
        "Content-Type: application/json; charset=UTF-8",
        "",
        json.dumps(file_metadata),
        "",
        f"--{boundary}",
        "Content-Type: image/png",
        "",
    ]
    
    body = "\r\n".join(body_parts).encode('utf-8') + image_content + f"\r\n--{boundary}--".encode('utf-8')
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": f'multipart/related; boundary="{boundary}"'
    }
    
    try:
        response = requests.post(upload_url, headers=headers, data=body, timeout=120)
        
        if response.status_code == 401:
            raise Exception("🔒 Google Drive token expired. User needs to reconnect.")
        
        response.raise_for_status()
        file_id = response.json().get("id")
        
        # Make public
        perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
        requests.post(
            perm_url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"role": "reader", "type": "anyone"},
            timeout=30
        )
        
        drive_link = f"https://drive.google.com/file/d/{file_id}/view"
        print(f"[DRIVE] ✅ Uploaded: {drive_link}")
        
        return drive_link
        
    except Exception as e:
        raise Exception(f"Failed to upload to Drive: {str(e)}")

# ==========================================================
# 📄 BACKGROUND TASK
# ==========================================================
async def generate_images_for_all_users(user_prompts: Dict[int, Dict]):
    """Process all prompts with delay"""
    try:
        completed = 0
        total = sum(len(d['prompts']) for d in user_prompts.values())
        
        print(f"\n{'='*60}")
        print(f"🎨 Starting: {len(user_prompts)} users, {total} prompts")
        print(f"⏱️ {DELAY_BETWEEN_PROMPTS}s delay between prompts")
        print(f"{'='*60}\n")
        
        for user_id, user_data in user_prompts.items():
            access_token = user_data['user_data']['access_token']
            user_email = user_data['user_data'].get('google_email', f'User {user_id}')
            
            image_generation_progress["all_users"]["current_user"] = user_email
            
            for prompt_data in user_data['prompts']:
                prompt_text = prompt_data['promt']
                prompt_id = prompt_data['id']
                
                print(f"\n--- Prompt {completed + 1}/{total} ---")
                print(f"User: {user_email}")
                print(f"Prompt: {prompt_text[:100]}")
                
                image_generation_progress["all_users"].update({
                    "current_prompt": prompt_text[:50],
                    "current_step": "Generating image...",
                    "completed_count": completed,
                    "progress_percentage": (completed / total) * 100
                })
                
                try:
                    # Generate
                    image_content = await generate_image_with_gemini(prompt_text)
                    
                    # Upload
                    image_generation_progress["all_users"]["current_step"] = "Uploading..."
                    drive_url = await upload_to_google_drive(image_content, prompt_id, access_token)
                    
                    # Update DB
                    supabase.table('video').update({'video_url': drive_url}).eq('id', prompt_id).execute()
                    print(f"✅ Success! {drive_url}")
                    
                except Exception as e:
                    error_msg = f"ERROR: {str(e)[:200]}"
                    print(f"✗ Failed: {error_msg}")
                    supabase.table('video').update({'video_url': error_msg}).eq('id', prompt_id).execute()
                
                completed += 1
                image_generation_progress["all_users"].update({
                    "completed_count": completed,
                    "progress_percentage": (completed / total) * 100
                })
                
                if completed < total:
                    print(f"\n⏱️ Waiting {DELAY_BETWEEN_PROMPTS}s...")
                    image_generation_progress["all_users"]["current_step"] = f"Waiting {DELAY_BETWEEN_PROMPTS}s"
                    await asyncio.sleep(DELAY_BETWEEN_PROMPTS)
        
        print(f"\n{'='*60}")
        print(f"✅ ALL DONE! {completed}/{total} images processed")
        print(f"{'='*60}\n")
        
        image_generation_progress["all_users"].update({
            "status": "completed",
            "current_step": f"Completed! {completed} images generated",
            "progress_percentage": 100.0
        })
        
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}\n")
        image_generation_progress["all_users"].update({
            "status": "error",
            "error_message": str(e)
        })

# ==========================================================
# 📡 API ROUTES - DASHBOARD
# ==========================================================
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@dashboard_router.get("/video-records", response_model=List[VideoRecord])
async def get_dashboard_records():
    """Get all video records for dashboard"""
    try:
        result = supabase.table('video').select('*').order('id').execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@dashboard_router.get("/video-records/{record_id}", response_model=VideoRecord)
async def get_dashboard_record(record_id: int):
    """Get specific record"""
    try:
        result = supabase.table('video').select('*').eq('id', record_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Record not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@dashboard_router.put("/video-records/{record_id}")
async def update_dashboard_record(record_id: int, update_data: PromptUpdate):
    """Update prompt"""
    try:
        result = supabase.table('video').update({
            'promt': update_data.promt
        }).eq('id', record_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Record not found")

        return {"message": "Updated successfully", "data": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ==========================================================
# 📡 API ROUTES - IMAGE GENERATION
# ==========================================================
image_router = APIRouter(prefix="/api/generate", tags=["Image Generation"])

@image_router.get("/video-records")
async def get_generation_records():
    """Get all records for generation interface"""
    result = supabase.table('video').select('*').order('id').execute()
    return result.data

@image_router.post("/generate-videos", response_model=ImageGenerationResponse)
async def start_image_generation(background_tasks: BackgroundTasks):
    """Start generation"""
    prompts_null = supabase.table('video').select('*').is_('video_url', 'null').execute()
    prompts_empty = supabase.table('video').select('*').in_('video_url', ['', 'Nullable']).execute()
    all_pending = prompts_null.data + prompts_empty.data
    
    if not all_pending:
        raise HTTPException(400, "No pending prompts")
    
    user_ids = list(set(p.get('userid') for p in all_pending if p.get('userid')))
    users = supabase.table('drive_accounts').select('*').in_('user_id', user_ids).execute()
    users_dict = {u['user_id']: u for u in users.data}
    
    user_prompts = {}
    for prompt in all_pending:
        user_id = prompt.get('userid')
        if user_id and user_id in users_dict and users_dict[user_id].get('access_token'):
            if user_id not in user_prompts:
                user_prompts[user_id] = {'prompts': [], 'user_data': users_dict[user_id]}
            user_prompts[user_id]['prompts'].append(prompt)
    
    if not user_prompts:
        raise HTTPException(400, "No users with valid tokens")
    
    total = sum(len(d['prompts']) for d in user_prompts.values())
    
    image_generation_progress["all_users"] = {
        "status": "processing",
        "completed_count": 0,
        "total_count": total,
        "progress_percentage": 0.0,
        "current_step": "Starting...",
        "current_prompt": None,
        "current_user": None,
        "error_message": None
    }
    
    background_tasks.add_task(generate_images_for_all_users, user_prompts)
    
    return ImageGenerationResponse(
        message="Image generation started",
        total_prompts=total,
        total_users=len(user_prompts),
        delay_info=f"{DELAY_BETWEEN_PROMPTS}s between prompts"
    )

@image_router.get("/progress-stream")
async def get_progress_stream():
    """Real-time progress"""
    async def generate():
        while True:
            progress = image_generation_progress.get("all_users", {
                "status": "idle",
                "completed_count": 0,
                "total_count": 0,
                "progress_percentage": 0.0
            })
            
            yield f"data: {json.dumps(progress)}\n\n"
            
            if progress.get("status") in ["completed", "error"]:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@image_router.get("/stats")
async def get_stats():
    """Get statistics"""
    all_records = supabase.table('video').select('*').execute()
    total = len(all_records.data)
    completed = sum(1 for r in all_records.data 
                   if r.get('video_url') and r['video_url'] not in ['', 'Nullable'] 
                   and not r['video_url'].startswith('ERROR:'))
    
    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "completion_rate": round((completed / total * 100) if total > 0 else 0, 1)
    }

@image_router.get("/test-image")
async def test_image(prompt: str = "A beautiful sunset"):
    """Test image generation"""
    try:
        image_data = await generate_image_with_gemini(prompt)
        return Response(content=image_data, media_type="image/png")
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Include routers
app.include_router(dashboard_router)
app.include_router(image_router)

# ==========================================================
# 📡 API ROUTES - ROOT LEVEL (for frontend compatibility)
# ==========================================================
@app.get("/api/video-records")
async def get_video_records():
    """Get all video records (root level for frontend)"""
    try:
        result = supabase.table('video').select('*').order('id').execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/stats")
async def get_stats_root():
    """Get statistics (root level for frontend)"""
    try:
        all_records = supabase.table('video').select('*').execute()
        total = len(all_records.data)
        completed = sum(1 for r in all_records.data
                       if r.get('video_url') and r['video_url'] not in ['', 'Nullable']
                       and not r['video_url'].startswith('ERROR:'))

        return {
            "total": total,
            "completed": completed,
            "pending": total - completed,
            "completion_rate": round((completed / total * 100) if total > 0 else 0, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/generate-videos")
async def start_generation_root(background_tasks: BackgroundTasks):
    """Start generation (root level for frontend)"""
    try:
        prompts_null = supabase.table('video').select('*').is_('video_url', 'null').execute()
        prompts_empty = supabase.table('video').select('*').in_('video_url', ['', 'Nullable']).execute()
        all_pending = prompts_null.data + prompts_empty.data

        if not all_pending:
            raise HTTPException(400, "No pending prompts")

        user_ids = list(set(p.get('userid') for p in all_pending if p.get('userid')))
        users = supabase.table('drive_accounts').select('*').in_('user_id', user_ids).execute()
        users_dict = {u['user_id']: u for u in users.data}

        user_prompts = {}
        for prompt in all_pending:
            user_id = prompt.get('userid')
            if user_id and user_id in users_dict and users_dict[user_id].get('access_token'):
                if user_id not in user_prompts:
                    user_prompts[user_id] = {'prompts': [], 'user_data': users_dict[user_id]}
                user_prompts[user_id]['prompts'].append(prompt)

        if not user_prompts:
            raise HTTPException(400, "No users with valid tokens")

        total = sum(len(d['prompts']) for d in user_prompts.values())

        image_generation_progress["all_users"] = {
            "status": "processing",
            "completed_count": 0,
            "total_count": total,
            "progress_percentage": 0.0,
            "current_step": "Starting...",
            "current_prompt": None,
            "current_user": None,
            "error_message": None
        }

        background_tasks.add_task(generate_images_for_all_users, user_prompts)

        return {
            "message": "Image generation started",
            "total_prompts": total,
            "total_users": len(user_prompts),
            "delay_info": f"{DELAY_BETWEEN_PROMPTS}s between prompts"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/progress-stream")
async def get_progress_stream_root():
    """Real-time progress (root level for frontend)"""
    async def generate():
        while True:
            progress = image_generation_progress.get("all_users", {
                "status": "idle",
                "completed_count": 0,
                "total_count": 0,
                "progress_percentage": 0.0
            })

            yield f"data: {json.dumps(progress)}\n\n"

            if progress.get("status") in ["completed", "error"]:
                break

            await asyncio.sleep(1)

    return StreamingResponse(generate(), media_type="text/event-stream")

# ==========================================================
# 🌐 MAIN ROUTES
# ==========================================================
@app.get("/")
async def root():
    """Landing page - redirect to dashboard"""
    return FileResponse("dashboard.html")

@app.get("/dashboard")
async def serve_dashboard():
    """Serve dashboard HTML"""
    return FileResponse("dashboard.html")

@app.get("/index")
async def serve_index():
    """Serve index HTML (generation interface)"""
    return FileResponse("index.html")

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        result = supabase.table('video').select('count', count='exact').execute()
        return {
            "status": "healthy",
            "model": MODEL,
            "database": "connected",
            "total_records": result.count,
            "services": {
                "dashboard": "active",
                "image_generation": "active",
                "database": "connected",
                "gemini_api": "connected"
            }
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ==========================================================
# 🔥 RUN SERVER
# ==========================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎬 UNIFIED VIDEO GENERATION SYSTEM")
    print("="*70)
    print(f"📦 Model: {MODEL}")
    print(f"⏱️  Rate Limit: {DELAY_BETWEEN_PROMPTS}s")
    print("🚀 Server: http://0.0.0.0:8000")
    print("📊 Dashboard: http://0.0.0.0:8000/dashboard")
    print("🎨 Generator: http://0.0.0.0:8000/index")
    print("📚 API Docs: http://0.0.0.0:8000/docs")
    print("="*70 + "\n")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
