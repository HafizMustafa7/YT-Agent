from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict
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
# 🚀 FASTAPI INITIALIZATION
# ==========================================================
app = FastAPI(
    title="Gemini Image Generation API",
    version="2.0.0",
    description="AI-Powered Image Generation using Google's Gemini"
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

# 🎨 IMAGE GENERATION MODELS (Choose one)
# Option 1: Gemini 2.0 Flash Preview (NEW - Try this first!)
MODEL = "gemini-2.0-flash-preview-image-generation"

# Option 2: Nano Banana (Stable alternative)
# MODEL = "gemini-2.5-flash-image"

# Option 3: Imagen models (Requires billing)
# MODEL = "imagen-3.0-generate-002"  # Imagen 3
# MODEL = "imagen-4.0-fast-generate-001"  # Imagen 4 Fast

# ⚠️ RATE LIMITING (Very important for free tier!)
DELAY_BETWEEN_PROMPTS = 30  # 30 seconds between each image (FREE TIER SAFE)
# For paid tier, you can reduce to 10 or 5 seconds

print(f"\n{'='*60}")
print(f"🎨 MODEL: {MODEL}")
print(f"⏱️  RATE LIMIT: {DELAY_BETWEEN_PROMPTS} seconds between prompts")
print(f"{'='*60}\n")

# Initialize Gemini Client
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    print("✓ Gemini client initialized")
except Exception as e:
    print(f"✗ Gemini client error: {e}")
    gemini_client = None

# Initialize Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✓ Supabase initialized")
except Exception as e:
    print(f"✗ Supabase error: {e}")
    supabase = None

# ==========================================================
# 🧠 DATA MODELS
# ==========================================================
class ImageGenerationResponse(BaseModel):
    message: str
    total_prompts: int
    total_users: int
    delay_info: str

# Global progress tracking
image_generation_progress: Dict[str, Dict] = {}

# ==========================================================
# 🎨 IMAGE GENERATION FUNCTIONS
# ==========================================================
async def generate_image_with_gemini(prompt: str, retry_count: int = 3) -> bytes:
    """
    Generate image using Gemini with retry logic
    """
    print(f"[IMAGE] Generating: {prompt[:80]}...")
    
    for attempt in range(retry_count):
        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            ]
            
            # ✅ FIXED: Model requires BOTH IMAGE and TEXT
            generate_content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],  # Changed from ["IMAGE"]
                temperature=1.0,
            )
            
            image_data = None
            
            # Stream response
            for chunk in gemini_client.models.generate_content_stream(
                model=MODEL,
                contents=contents,
                config=generate_content_config,
            ):
                if (chunk.candidates and 
                    chunk.candidates[0].content and 
                    chunk.candidates[0].content.parts):
                    
                    # Loop through all parts to find the image
                    for part in chunk.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.data:
                            image_data = part.inline_data.data
                            mime_type = part.inline_data.mime_type
                            print(f"[IMAGE] ✓ Generated ({mime_type}, {len(image_data)} bytes)")
                            return image_data
            
            if not image_data:
                raise Exception("No image data in response")
            
            return image_data
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for quota/rate limit errors
            if "quota" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                wait_time = 60 * (attempt + 1)  # Exponential backoff
                print(f"[IMAGE] ⚠️  Rate limit hit! Waiting {wait_time}s before retry {attempt + 1}/{retry_count}")
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded after {retry_count} retries. Please wait before trying again.")
            
            # Other errors
            print(f"[IMAGE ERROR] Attempt {attempt + 1}/{retry_count}: {e}")
            if attempt < retry_count - 1:
                await asyncio.sleep(10)
                continue
            else:
                raise Exception(f"Failed to generate image after {retry_count} attempts: {str(e)}")
    
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
    
    response = requests.get(search_url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    
    files = response.json().get("files", [])
    
    if files:
        folder_id = files[0]["id"]
        print(f"[DRIVE] ✓ Found folder (ID: {folder_id})")
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
    print(f"[DRIVE] ✓ Created folder (ID: {folder_id})")
    return folder_id

async def upload_to_google_drive(image_content: bytes, prompt_id: int, access_token: str) -> str:
    """Upload image to Google Drive"""
    print(f"[DRIVE] Uploading image for prompt {prompt_id}")
    
    folder_id = await get_or_create_folder(access_token)
    
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
    
    response = requests.post(upload_url, headers=headers, data=body, timeout=120)
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
    print(f"[DRIVE] ✓ Uploaded: {drive_link}")
    
    return drive_link

# ==========================================================
# 🔄 BACKGROUND TASK
# ==========================================================
async def generate_images_for_all_users(user_prompts: Dict[int, Dict]):
    """Process all prompts with delay to avoid rate limits"""
    try:
        completed = 0
        total = sum(len(d['prompts']) for d in user_prompts.values())
        
        print(f"\n{'='*60}")
        print(f"🎨 Starting: {len(user_prompts)} users, {total} prompts")
        print(f"⏱️  {DELAY_BETWEEN_PROMPTS}s delay between prompts")
        print(f"⏰ Estimated time: {(total * DELAY_BETWEEN_PROMPTS) // 60} minutes")
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
                    # Generate image
                    image_content = await generate_image_with_gemini(prompt_text)
                    
                    # Upload to Drive
                    image_generation_progress["all_users"]["current_step"] = "Uploading to Drive..."
                    drive_url = await upload_to_google_drive(image_content, prompt_id, access_token)
                    
                    # Update database
                    supabase.table('video').update({'video_url': drive_url}).eq('id', prompt_id).execute()
                    
                    print(f"✓ Success! {drive_url}")
                    
                except Exception as e:
                    error_msg = f"ERROR: {str(e)[:200]}"
                    print(f"✗ Failed: {error_msg}")
                    supabase.table('video').update({'video_url': error_msg}).eq('id', prompt_id).execute()
                
                completed += 1
                image_generation_progress["all_users"].update({
                    "completed_count": completed,
                    "progress_percentage": (completed / total) * 100
                })
                
                # Delay before next prompt
                if completed < total:
                    print(f"\n⏱️  Waiting {DELAY_BETWEEN_PROMPTS}s...")
                    image_generation_progress["all_users"]["current_step"] = f"Waiting {DELAY_BETWEEN_PROMPTS}s (rate limit protection)"
                    await asyncio.sleep(DELAY_BETWEEN_PROMPTS)
        
        print(f"\n{'='*60}")
        print(f"✓ ALL DONE! {completed}/{total} images processed")
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
# 🌐 API ENDPOINTS
# ==========================================================
@app.get("/api/video-records")
async def get_video_records():
    """Get all records"""
    if not supabase:
        raise HTTPException(500, "Database not connected")
    
    result = supabase.table('video').select('*').order('id').execute()
    return result.data

@app.post("/api/generate-videos", response_model=ImageGenerationResponse)
async def start_image_generation(background_tasks: BackgroundTasks):
    """Start image generation"""
    if not gemini_client:
        raise HTTPException(500, "Gemini client not initialized")
    
    # Get pending prompts
    prompts_null = supabase.table('video').select('*').is_('video_url', 'null').execute()
    prompts_empty = supabase.table('video').select('*').in_('video_url', ['', 'Nullable']).execute()
    all_pending = prompts_null.data + prompts_empty.data
    
    if not all_pending:
        raise HTTPException(400, "No pending prompts")
    
    # Get users
    user_ids = list(set(p.get('userid') for p in all_pending if p.get('userid')))
    users = supabase.table('drive_accounts').select('*').in_('user_id', user_ids).execute()
    users_dict = {u['user_id']: u for u in users.data}
    
    # Group by user
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
    estimated_time = (total * DELAY_BETWEEN_PROMPTS) // 60
    
    # Initialize progress
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
    
    # Start background task
    background_tasks.add_task(generate_images_for_all_users, user_prompts)
    
    return ImageGenerationResponse(
        message="Image generation started",
        total_prompts=total,
        total_users=len(user_prompts),
        delay_info=f"{DELAY_BETWEEN_PROMPTS}s between prompts (~{estimated_time} min total)"
    )

@app.get("/api/progress-stream")
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
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/api/stats")
async def get_stats():
    """Get statistics"""
    if not supabase:
        raise HTTPException(500, "Database not connected")
    
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

@app.get("/health")
async def health_check():
    """Health check"""
    if not supabase or not gemini_client:
        return {"status": "unhealthy", "error": "Services not initialized"}
    
    try:
        result = supabase.table('video').select('count', count='exact').execute()
        return {
            "status": "healthy",
            "service": "Gemini Image Generation API",
            "model": MODEL,
            "database": "connected",
            "total_records": result.count,
            "rate_limit": f"{DELAY_BETWEEN_PROMPTS}s between prompts"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/test-image")
async def test_image_generation(prompt: str = "A beautiful sunset over mountains"):
    """Test image generation with custom prompt"""
    try:
        print(f"\n[TEST] Generating image for: {prompt}")
        image_data = await generate_image_with_gemini(prompt)
        
        # Return the image directly so you can see it!
        from fastapi.responses import Response
        return Response(
            content=image_data,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=test_image_{int(time.time())}.png"
            }
        )
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/test-image-json")
async def test_image_generation_json(prompt: str = "A beautiful sunset over mountains"):
    """Test image generation and return JSON info (not the actual image)"""
    try:
        print(f"\n[TEST] Generating image for: {prompt}")
        image_data = await generate_image_with_gemini(prompt)
        return {
            "status": "success",
            "message": "Image generated!",
            "prompt": prompt,
            "size_bytes": len(image_data),
            "note": "Use /api/test-image?prompt=YOUR_PROMPT to see the actual image"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/list-models")
async def list_models():
    """List available models"""
    try:
        models = gemini_client.models.list()
        
        image_models = []
        for model in models:
            name = model.name
            if any(keyword in name.lower() for keyword in ['image', 'imagen', 'banana']):
                image_models.append({
                    "name": name,
                    "display_name": model.display_name,
                    "description": model.description if hasattr(model, 'description') else None
                })
        
        return {
            "status": "success",
            "total": len(image_models),
            "models": image_models
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================================
# 🔥 MAIN
# ==========================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎨 GEMINI IMAGE GENERATION API")
    print("="*60)
    print(f"Model: {MODEL}")
    print(f"Rate Limit: {DELAY_BETWEEN_PROMPTS}s between prompts")
    print(f"API Key: {'✓ Configured' if GEMINI_API_KEY else '✗ Missing'}")
    print("="*60 + "\n")
    print("🚀 Server: http://0.0.0.0:8080")
    print("📚 API Docs: http://0.0.0.0:8080/docs")
    print("🧪 Test: http://0.0.0.0:8080/api/test-image\n")
    
    # ⚠️ IMPORTANT: Change this to match your filename!
    # If your file is named backend2.py, use "backend2:app"
    # If your file is named backend_image.py, use "backend_image:app"
    uvicorn.run("backend2:app", host="0.0.0.0", port=8080, reload=True)