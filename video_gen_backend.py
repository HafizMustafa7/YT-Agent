from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import openai
import os
import time
from datetime import datetime
import json
import asyncio
import httpx
import ffmpeg
import requests
from supabase import create_client, Client

# ==========================================================
# 🚀 FASTAPI APP
# ==========================================================
app = FastAPI(
    title="Video Generation API",
    version="2.1.0",
    description="Generate videos using OpenAI Sora model with Project Workflow (Sequential + Local Cache)"
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
OPENAI_API_KEY = "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"

# Supabase Configuration
SUPABASE_URL = "https://enwzcoocguqxxkkzxdtj.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVud3pjb29jZ3VxeHhra3p4ZHRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM3NTI0NiwiZXhwIjoyMDcxOTUxMjQ2fQ.AMZMo7jEe7iuhaTYAwM1FahlFI7pDOy4axWp-kGQMI4"

# Cloudflare Worker Configuration
WORKER_URL = "https://soft-frog-2d4c.bsdsf22m019.workers.dev"
R2_UPLOAD_API_KEY = "sora_r2upload_9f3a7d8c21e44f8b"

# Hardware User ID
USER_ID = "489f2092-1a7d-40f9-87be-53e5578165f1"

# Local Cache Directory
TEMP_DIR = "temp_video_cache"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Initialize clients
client = openai.OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ==========================================================
# 🧠 MODELS
# ==========================================================
class VideoGenerationRequest(BaseModel):
    prompt: str
    model: str = "sora-2"
    size: str = "1280x720"
    seconds: int = 4

class CombineRequest(BaseModel):
    project_id: str

# In-memory job tracking (optional, mainly relying on DB now)
active_jobs: Dict[str, Any] = {}

# ==========================================================
# 📝 PROMPTS
# ==========================================================
# Reduced to 2 hardcoded prompts as requested
PROMPTS = [
    {
        "id": "cyberpunk",
        "title": "Futuristic Cyberpunk",
        "prompt": "Wide aerial establishing shot of a futuristic neon city at night. The camera slowly dollies forward between tall skyscrapers covered in glowing holographic signs. Flying vehicles move smoothly along layered traffic lanes."
    },
    {
        "id": "nature",
        "title": "Peaceful Forest",
        "prompt": "Medium tracking shot following a calm adult deer walking slowly through a dense green forest clearing at sunrise. Cool morning mist drifting slowly, warm golden sunlight filtering through trees."
    }
]

# ==========================================================
# 🔧 HELPER FUNCTIONS
# ==========================================================
async def create_project_in_supabase(user_id: str) -> str:
    """Create a new project in Supabase"""
    try:
        project_result = supabase.table('projects').insert({
            "user_id": user_id,
            "input_type": "trend",
            "input_value": "Hardcoded Prompts Batch",
            "status": "queued"
        }).execute()
        return project_result.data[0]['id']
    except Exception as e:
        print(f"Error creating project: {e}")
        raise

async def update_project_status(project_id: str, status: str):
    """Update project status in Supabase"""
    try:
        supabase.table('projects').update({"status": status}).eq('id', project_id).execute()
    except Exception as e:
        print(f"Error updating project status: {e}")

async def create_asset_record(project_id: str, asset_type: str, file_path: str, file_size: int):
    """Create asset record in Supabase"""
    try:
        supabase.table('assets').insert({
            "project_id": project_id,
            "asset_type": asset_type,
            "file_path": file_path,
            "file_size": file_size
        }).execute()
    except Exception as e:
        print(f"Error creating asset: {e}")

async def upload_to_r2(file_data: bytes, bucket: str, path: str) -> bool:
    """Upload file to Cloudflare R2 via Worker"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WORKER_URL}?bucket={bucket}&path={path}",
                headers={
                    "x-api-key": R2_UPLOAD_API_KEY,
                    "Content-Type": "video/mp4" if path.endswith('.mp4') else "application/octet-stream"
                },
                content=file_data,
                timeout=120.0
            )
            if response.status_code == 200:
                print(f"✅ R2 Upload Success: {bucket}/{path}")
                return True
            else:
                print(f"❌ R2 Upload Failed ({response.status_code}): {response.text}")
                return False
    except Exception as e:
        print(f"❌ R2 Upload Error: {str(e)}")
        return False

# ==========================================================
# 🎥 CORE LOGIC
# ==========================================================

async def generate_single_video_task(prompt: str, project_id: str, video_index: int):
    """
    Background task to generate ONE video.
    """
    job_id = f"gen_{project_id}_{video_index}"
    try:
        print(f"🚀 [{job_id}] Starting generation...", flush=True)

        # 1. Call OpenAI Sora API
        url = "https://api.openai.com/v1/videos"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "sora-2",
            "prompt": prompt,
            "size": "1280x720",
            "seconds": "4" 
        }

        print(f"📡 [{job_id}] Sending request to OpenAI...", flush=True)
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ [{job_id}] OpenAI API Failed: {response.text}", flush=True)
            raise Exception(f"OpenAI API Error ({response.status_code}): {response.text}")
        
        video_id = response.json().get("id")
        print(f"⏳ [{job_id}] OpenAI Task ID: {video_id}", flush=True)

        # 2. Poll for completion (Max 5 minutes)
        attempts = 0
        max_attempts = 120 # 120 * 5s = 10 mins (Sora can be slow)
        
        video_data = None
        while attempts < max_attempts:
            attempts += 1
            if attempts % 6 == 0:
                print(f"🔹 [{job_id}] Polling Attempt {attempts}/{max_attempts}...", flush=True)

            status_res = requests.get(f"{url}/{video_id}", headers=headers, timeout=10)
            if status_res.status_code != 200:
                print(f"⚠️ [{job_id}] Status check failed: {status_res.text}", flush=True)
                time.sleep(5)
                continue
            
            status_data = status_res.json()
            status = status_data.get("status")
            
            if status == "completed":
                print(f"📥 [{job_id}] Generation Completed! Downloading...", flush=True)
                dl_res = requests.get(f"{url}/{video_id}/content", headers=headers, timeout=60)
                if dl_res.status_code == 200:
                    video_data = dl_res.content
                    break
                else:
                    raise Exception(f"Failed to download video content: {dl_res.text}")
            elif status == "failed":
                err_details = status_data.get("error", {})
                raise Exception(f"OpenAI Job Failed: {err_details}")
            
            time.sleep(5)
        
        if not video_data:
            raise Exception("Timeout: Video generation took too long")

        # 3. Save to LOCAL CACHE (Critical for FFmpeg later)
        local_filename = f"clip_{project_id}_{video_index}.mp4"
        local_path = os.path.join(TEMP_DIR, local_filename) 
        
        with open(local_path, "wb") as f:
            f.write(video_data)
        
        print(f"💾 [{job_id}] Saved locally to {local_path}", flush=True)

        # 4. Upload to R2 (TRASH bucket) - as BACKUP
        file_size = len(video_data)
        r2_path = f"trash/videos/{project_id}/clip_{video_index}.mp4"
        
        print(f"☁️ [{job_id}] Uploading to R2 backup...", flush=True)
        await upload_to_r2(video_data, "trash", r2_path)

        # 5. Create Asset Record
        await create_asset_record(project_id, "video", r2_path, file_size)
        
        print(f"✅ [{job_id}] Completed & Asset Created", flush=True)

    except Exception as e:
        print(f"❌ [{job_id}] EXCEPTION: {e}", flush=True)
        raise e

async def batch_process_project_sequential(project_id: str):
    """
    Orchestrator for SEQUENTIAL generation
    """
    try:
        await update_project_status(project_id, "generating")
        
        # Loop sequentially instead of parallel gather
        for i, p_data in enumerate(PROMPTS):
            print(f"\n--- Starting Prompt {i+1}/{len(PROMPTS)} ---")
            
            # Optional: Update status to granular level if we had that field
            # But we only agreed on 'generating' enum. 
            # We can rely on assets count in frontend to know progress.
            
            await generate_single_video_task(p_data['prompt'], project_id, i+1)
            
            print(f"--- Finished Prompt {i+1} ---\n")
        
        await update_project_status(project_id, "completed")
        print(f"🏁 Project {project_id} generation batch ALL finished")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ Batch Validation Error: {error_msg}")
        # Store error in input_value for visibility in UI
        try:
            supabase.table('projects').update({
                "status": "failed", 
                "input_value": error_msg
            }).eq('id', project_id).execute()
        except:
            print("Failed to save error log to DB")


async def combine_process_task_local(project_id: str):
    """
    Concatenates videos using LOCAL CACHE files.
    """
    try:
        print(f"🔄 Combining project {project_id} using local cache...")
        
        # 1. Identify local files based on convention
        # We know we generated prompts 1..N
        # Filename format: clip_{project_id}_{index}.mp4
        
        local_inputs = []
        for i in range(len(PROMPTS)):
            idx = i + 1
            path = os.path.join(TEMP_DIR, f"clip_{project_id}_{idx}.mp4")
            if os.path.exists(path):
                local_inputs.append(path)
            else:
                print(f"⚠️ Warning: Missing local clip {path}")
        
        if not local_inputs:
            raise Exception("No local video clips found to combine!")

        print(f"🎞️ Found {len(local_inputs)} clips to combine: {local_inputs}")

        # 2. FFmpeg Concat
        output_filename = f"final_{project_id}.mp4"
        output_path = os.path.join(TEMP_DIR, output_filename)

        # Create list file for FFmpeg
        list_file_path = os.path.join(TEMP_DIR, f"list_{project_id}.txt")
        with open(list_file_path, "w") as f:
            for p in local_inputs:
                # ffmpeg requires absolute paths or relative. Let's use absolute.
                abs_p = os.path.abspath(p).replace("\\", "/") # Windows fix
                f.write(f"file '{abs_p}'\n")

        # Run FFmpeg
        print("⚙️ Running FFmpeg...")
        (
            ffmpeg
            .input(list_file_path, format='concat', safe=0)
            .output(output_path, c='copy')
            .overwrite_output()
            .run(quiet=True)
        )
        print("⚙️ FFmpeg Done.")

        # 3. Read Final Video
        if not os.path.exists(output_path):
            raise Exception("FFmpeg failed to create output file")

        with open(output_path, "rb") as f:
            final_data = f.read()

        # 4. Upload Final to R2
        r2_final_path = f"final/videos/{project_id}/final.mp4"
        print(f"⬆️ Uploading final video to {r2_final_path}...")
        
        success = await upload_to_r2(final_data, "final", r2_final_path)
        if not success:
            raise Exception("Failed to upload final video")

        # 5. Asset Record
        await create_asset_record(project_id, "video", r2_final_path, len(final_data))
        
        print("✅ Combination Complete!")

        # Cleanup (Optional - keep for debugging or future combines)
        # os.remove(list_file_path)
        # for p in local_inputs: os.remove(p)

    except Exception as e:
        print(f"❌ Combine Error: {e}")
        # Could update supabase status logic if needed

# ==========================================================
# 📡 API ROUTES
# ==========================================================

@app.post("/generate-project")
async def start_project(background_tasks: BackgroundTasks):
    """
    1. Creates Project
    2. Starts SEQUENTIAL generation
    """
    try:
        # 1. Create Project
        pid = await create_project_in_supabase(USER_ID)
        print(f"🆕 Project Created: {pid}")

        # 2. Background Task (Sequential)
        background_tasks.add_task(batch_process_project_sequential, pid)

        return {
            "project_id": pid,
            "status": "queued",
            "message": "Project started. Generating videos sequentially."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/combine-project")
async def combine_project(request: CombineRequest, background_tasks: BackgroundTasks):
    """
    1. Triggers combination task using LOCAL CACHE
    """
    # Simple validation
    proj = supabase.table('projects').select('*').eq('id', request.project_id).execute()
    if not proj.data:
        raise HTTPException(404, "Project not found")

    background_tasks.add_task(combine_process_task_local, request.project_id)
    
    return {"status": "processing", "message": "Combination processing started"}


@app.get("/projects")
async def list_projects():
    """List all projects for dashboard"""
    try:
        res = supabase.table('projects').select('*').order('created_at', desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/project/{project_id}/assets")
async def get_project_assets(project_id: str):
    """Get all assets (clips + final) for a project"""
    try:
        res = supabase.table('assets').select('*').eq('project_id', project_id).execute()
        return res.data
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/")
async def root():
    """Serve the video generation HTML"""
    return FileResponse("video_gen.html")

# ==========================================================
# 🔥 MAIN
# ==========================================================
if __name__ == "__main__":
    uvicorn.run("video_gen_backend:app", host="0.0.0.0", port=8002, reload=True)
