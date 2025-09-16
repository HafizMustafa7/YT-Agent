from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
from datetime import datetime
import os
import json
import time
import asyncio
import requests
from supabase import create_client, Client

# Initialize FastAPI app
app = FastAPI(title="Video Generation API", version="1.0.0")

# Supabase configuration
SUPABASE_URL = "https://enwzcoocguqxxkkzxdtj.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVud3pjb29jZ3VxeHhra3p4ZHRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM3NTI0NiwiZXhwIjoyMDcxOTUxMjQ2fQ.AMZMo7jEe7iuhaTYAwM1FahlFI7pDOy4axWp-kGQMI4"

# Initialize Supabase client with service role key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Pollo AI Configuration
POLLO_API_KEY = "pollo_1pO1IP9qJvpF6FhOJptl0bPDPEO9lS7qMGE0VMsOomw2"
POLLO_BASE_URL = "https://pollo.ai/api/platform/generation"
POLLO_MODEL = "pollo/pollo-v1-6"

# Global progress tracking
video_generation_progress: Dict[str, Dict] = {}  # "all_users" -> progress data

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class VideoRecord(BaseModel):
    id: Optional[int] = None
    promt: str  # Match your database column name (lowercase)
    created_at: Optional[datetime] = None
    video_url: Optional[str] = None
    userid: Optional[int] = None

class PromptUpdate(BaseModel):
    promt: str  # Match your database column name (lowercase)

class VideoGenerationRequest(BaseModel):
    pass  # No user_id needed anymore

class VideoGenerationStatus(BaseModel):
    status: str  # "idle", "processing", "completed", "error"
    current_prompt: Optional[str] = None
    current_step: Optional[str] = None
    completed_count: int = 0
    total_count: int = 0
    progress_percentage: float = 0.0
    error_message: Optional[str] = None
    current_user: Optional[str] = None

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Generation System</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .container { margin: 20px 0; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f2f2f2; }
            .edit-btn, .save-btn, .cancel-btn { 
                padding: 5px 10px; margin: 2px; border: none; cursor: pointer; border-radius: 3px;
            }
            .edit-btn { background: #007bff; color: white; }
            .save-btn { background: #28a745; color: white; }
            .cancel-btn { background: #6c757d; color: white; }
            .edit-btn:hover { background: #0056b3; }
            .save-btn:hover { background: #218838; }
            .cancel-btn:hover { background: #545b62; }
            .refresh-btn { 
                padding: 10px 20px; background: #17a2b8; color: white; 
                border: none; cursor: pointer; border-radius: 5px; margin: 10px 0;
            }
            .refresh-btn:hover { background: #138496; }
            .edit-input { width: 100%; padding: 5px; border: 1px solid #ddd; }
            .loading { color: #007bff; font-style: italic; }
            .stats-box { 
                background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;
            }
            .stat-item { text-align: center; }
            .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
            .stat-label { color: #6c757d; }
            .prompt-text { max-width: 400px; word-wrap: break-word; }
        </style>
    </head>
    <body>
        <h1>Video Generation System - Automatic Processing</h1>
        
        <div class="container">
            <h2>Video Prompts Overview</h2>
            
            <!-- Statistics -->
            <div id="statsBox" class="stats-box">
                <div class="stat-item">
                    <div class="stat-number" id="totalPrompts">0</div>
                    <div class="stat-label">Total Prompts</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="completedVideos">0</div>
                    <div class="stat-label">Videos Generated</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="pendingVideos">0</div>
                    <div class="stat-label">Pending Generation</div>
                </div>
            </div>
            
            <!-- Video Generation Controls -->
            <div style="margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px;">
                <h3>Video Generation</h3>
                <p>Generate videos for all users who have prompts without video URLs</p>
                <button id="generateBtn" class="refresh-btn" onclick="startVideoGeneration()" style="background: #28a745;">
                    🎬 Generate All Pending Videos
                </button>
                <div id="generationProgress" style="display: none; margin-top: 15px;">
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">
                        <h4>Generation Progress</h4>
                        <div id="progressStatus">Initializing...</div>
                        <div style="background: #e9ecef; height: 20px; border-radius: 10px; margin: 10px 0;">
                            <div id="progressBar" style="background: #007bff; height: 100%; border-radius: 10px; width: 0%; transition: width 0.3s;"></div>
                        </div>
                        <div id="currentStep">Preparing...</div>
                        <div id="currentUser" style="font-size: 12px; color: #6c757d; margin-top: 5px;"></div>
                    </div>
                </div>
            </div>
            
            <div id="message"></div>
            
            <div id="loading" class="loading" style="display: none;">Loading data from Supabase...</div>
            
            <table id="promptsTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Prompt</th>
                        <th>Video URL</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="promptsBody">
                </tbody>
            </table>
        </div>

        <script>
            let editingId = null;
            let progressEventSource = null;

            // Start video generation process
            async function startVideoGeneration() {
                const generateBtn = document.getElementById('generateBtn');
                const progressDiv = document.getElementById('generationProgress');
                const messageDiv = document.getElementById('message');
                
                try {
                    // Disable button and show progress
                    generateBtn.disabled = true;
                    generateBtn.textContent = '🎬 Generating...';
                    progressDiv.style.display = 'block';
                    
                    // Start the background task
                    const response = await fetch('/api/generate-videos', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        messageDiv.innerHTML = '<div class="status success">Video generation started! Processing ' + result.total_prompts + ' prompts for ' + result.total_users + ' users.</div>';
                        
                        // Start listening for progress updates
                        startProgressUpdates();
                    } else {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to start video generation');
                    }
                } catch (error) {
                    messageDiv.innerHTML = '<div class="status error">Error starting video generation: ' + error.message + '</div>';
                    generateBtn.disabled = false;
                    generateBtn.textContent = '🎬 Generate All Pending Videos';
                    progressDiv.style.display = 'none';
                }
            }
            
            // Start listening for real-time progress updates
            function startProgressUpdates() {
                if (progressEventSource) {
                    progressEventSource.close();
                }
                
                progressEventSource = new EventSource('/api/progress-stream');
                
                progressEventSource.onmessage = function(event) {
                    const progress = JSON.parse(event.data);
                    updateProgressUI(progress);
                };
                
                progressEventSource.onerror = function(event) {
                    console.error('Progress stream error:', event);
                    progressEventSource.close();
                    progressEventSource = null;
                };
            }
            
            // Update progress UI
            function updateProgressUI(progress) {
                const statusDiv = document.getElementById('progressStatus');
                const progressBar = document.getElementById('progressBar');
                const stepDiv = document.getElementById('currentStep');
                const userDiv = document.getElementById('currentUser');
                const generateBtn = document.getElementById('generateBtn');
                const progressDiv = document.getElementById('generationProgress');
                
                statusDiv.textContent = `Status: ${progress.status} (${progress.completed_count}/${progress.total_count})`;
                progressBar.style.width = progress.progress_percentage + '%';
                stepDiv.textContent = progress.current_step || 'Processing...';
                
                if (progress.current_user) {
                    userDiv.textContent = `Current: ${progress.current_user}`;
                }
                
                if (progress.current_prompt) {
                    stepDiv.textContent += ` - "${progress.current_prompt}"`;
                }
                
                if (progress.status === 'completed') {
                    generateBtn.disabled = false;
                    generateBtn.textContent = '🎬 Generate All Pending Videos';
                    stepDiv.textContent = 'All videos generated successfully!';
                    
                    if (progressEventSource) {
                        progressEventSource.close();
                        progressEventSource = null;
                    }
                    
                    // Reload prompts to show updated video URLs
                    setTimeout(() => {
                        loadPrompts();
                        progressDiv.style.display = 'none';
                    }, 3000);
                }
                
                if (progress.status === 'error') {
                    generateBtn.disabled = false;
                    generateBtn.textContent = '🎬 Generate All Pending Videos';
                    stepDiv.textContent = 'Error: ' + (progress.error_message || 'Unknown error');
                    
                    if (progressEventSource) {
                        progressEventSource.close();
                        progressEventSource = null;
                    }
                }
            }

            // Load prompts from Supabase
            async function loadPrompts() {
                const loadingDiv = document.getElementById('loading');
                const messageDiv = document.getElementById('message');
                
                loadingDiv.style.display = 'block';
                messageDiv.innerHTML = '';
                
                try {
                    console.log('Fetching data from /api/video-records...');
                    
                    const response = await fetch('/api/video-records');
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const records = await response.json();
                    console.log('Received records:', records);
                    
                    // Update statistics
                    updateStatistics(records);
                    
                    const tbody = document.getElementById('promptsBody');
                    tbody.innerHTML = '';
                    
                    if (records.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No records found in Supabase</td></tr>';
                        return;
                    }
                    
                    records.forEach(record => {
                        console.log('Processing record:', record);
                        console.log('Promt value:', record.promt);
                        
                        const row = tbody.insertRow();
                        const videoStatus = record.video_url && record.video_url !== 'Nullable' ? 
                            `<a href="${record.video_url}" target="_blank">View Video</a>` : 
                            '<span style="color: #dc3545;">Not generated</span>';
                        
                        // Direct access to the promt field
                        const promptText = record.promt || '[Empty prompt]';
                        
                        row.innerHTML = `
                            <td>${record.id}</td>
                            <td id="prompt-${record.id}" class="prompt-text">${promptText}</td>
                            <td>${videoStatus}</td>
                            <td>
                                <button class="edit-btn" onclick="editPrompt(${record.id})">Edit</button>
                            </td>
                        `;
                    });
                    
                    messageDiv.innerHTML = '<div class="status success">Data loaded successfully from Supabase!</div>';
                } catch (error) {
                    console.error('Error loading prompts:', error);
                    messageDiv.innerHTML = '<div class="status error">Error loading data: ' + error.message + '</div>';
                } finally {
                    loadingDiv.style.display = 'none';
                }
            }

            // Update statistics
            function updateStatistics(records) {
                const totalPrompts = records.length;
                const completedVideos = records.filter(r => r.video_url && r.video_url !== 'Nullable').length;
                const pendingVideos = totalPrompts - completedVideos;
                
                document.getElementById('totalPrompts').textContent = totalPrompts;
                document.getElementById('completedVideos').textContent = completedVideos;
                document.getElementById('pendingVideos').textContent = pendingVideos;
            }

            // Edit prompt functionality
            function editPrompt(id) {
                if (editingId && editingId !== id) {
                    cancelEdit();
                }
                
                editingId = id;
                const promptCell = document.getElementById(`prompt-${id}`);
                const originalText = promptCell.textContent;
                
                promptCell.innerHTML = `
                    <input type="text" class="edit-input" value="${originalText}" id="edit-input-${id}">
                `;
                
                // Update the actions cell
                const row = promptCell.parentElement;
                const actionsCell = row.cells[3];
                actionsCell.innerHTML = `
                    <button class="save-btn" onclick="savePrompt(${id})">Save</button>
                    <button class="cancel-btn" onclick="cancelEdit()">Cancel</button>
                `;
                
                // Focus on input
                document.getElementById(`edit-input-${id}`).focus();
            }

            // Save edited prompt
            async function savePrompt(id) {
                const input = document.getElementById(`edit-input-${id}`);
                const newPrompt = input.value.trim();
                
                if (!newPrompt) {
                    alert('Prompt cannot be empty');
                    return;
                }
                
                const messageDiv = document.getElementById('message');
                
                try {
                    const response = await fetch(`/api/video-records/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ promt: newPrompt })
                    });
                    
                    if (response.ok) {
                        messageDiv.innerHTML = '<div class="status success">Prompt updated successfully in Supabase!</div>';
                        editingId = null;
                        loadPrompts(); // Reload the data
                    } else {
                        throw new Error('Failed to update prompt');
                    }
                } catch (error) {
                    messageDiv.innerHTML = '<div class="status error">Error updating prompt: ' + error.message + '</div>';
                }
            }

            // Cancel edit
            function cancelEdit() {
                if (editingId) {
                    loadPrompts(); // Reload to restore original state
                    editingId = null;
                }
            }

            // Load prompts on page load
            window.onload = () => {
                console.log('Page loaded, loading prompts...');
                loadPrompts();
            };
        </script>
    </body>
    </html>
    """

@app.post("/api/generate-videos")
async def start_video_generation(background_tasks: BackgroundTasks):
    """Start video generation process for all users with pending prompts"""
    try:
        # Get all prompts that don't have video URLs (without JOIN to avoid relationship error)
        prompts_result = supabase.table('video').select('*').is_('video_url', 'null').execute()
        
        # Also get prompts where video_url is empty string or 'Nullable'
        empty_prompts = supabase.table('video').select('*').in_('video_url', ['', 'Nullable']).execute()
        
        # Combine results
        all_pending_prompts = prompts_result.data + empty_prompts.data
        
        if not all_pending_prompts:
            raise HTTPException(status_code=400, detail="No prompts available for video generation")
        
        # Get all unique user IDs from prompts
        user_ids = list(set(prompt.get('userid') for prompt in all_pending_prompts if prompt.get('userid')))
        
        # Get user data for all these users
        users_result = supabase.table('drive_accounts').select('*').in_('user_id', user_ids).execute()
        users_data = {user['user_id']: user for user in users_result.data}
        
        # Group by user and filter users who have access tokens
        user_prompts = {}
        for prompt in all_pending_prompts:
            user_id = prompt.get('userid')
            if not user_id or user_id not in users_data:
                continue  # Skip prompts without valid user_id
            
            user_data = users_data[user_id]
            if not user_data.get('access_token'):
                continue  # Skip users without access tokens
            
            if user_id not in user_prompts:
                user_prompts[user_id] = {
                    'prompts': [],
                    'user_data': user_data
                }
            user_prompts[user_id]['prompts'].append(prompt)
        
        if not user_prompts:
            raise HTTPException(status_code=400, detail="No users with valid access tokens found")
        
        # Count total prompts and users
        total_prompts = sum(len(data['prompts']) for data in user_prompts.values())
        total_users = len(user_prompts)
        
        # Initialize progress tracking
        video_generation_progress["all_users"] = {
            "status": "processing",
            "current_prompt": None,
            "current_step": "Initializing...",
            "completed_count": 0,
            "total_count": total_prompts,
            "progress_percentage": 0.0,
            "error_message": None,
            "current_user": None
        }
        
        # Start background task
        background_tasks.add_task(generate_videos_for_all_users, user_prompts)
        
        return {
            "message": "Video generation started", 
            "total_prompts": total_prompts,
            "total_users": total_users
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting video generation: {str(e)}")

@app.get("/api/progress-stream")
async def get_progress_stream():
    """Server-Sent Events stream for real-time progress updates"""
    
    async def generate_progress_stream():
        while True:
            try:
                progress_data = video_generation_progress.get("all_users", {
                    "status": "idle",
                    "current_prompt": None,
                    "current_step": "No generation in progress",
                    "completed_count": 0,
                    "total_count": 0,
                    "progress_percentage": 0.0,
                    "error_message": None,
                    "current_user": None
                })
                
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # Stop streaming when completed or error
                if progress_data.get("status") in ["completed", "error"]:
                    break
                    
                await asyncio.sleep(1)  # Send updates every second
                
            except Exception as e:
                error_data = {
                    "status": "error",
                    "error_message": str(e),
                    "current_step": "Stream error",
                    "completed_count": 0,
                    "total_count": 0,
                    "progress_percentage": 0.0,
                    "current_user": None
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break
    
    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

async def generate_videos_for_all_users(user_prompts: Dict[int, Dict]):
    """Background task to generate videos for all users"""
    try:
        completed_total = 0
        total_prompts = sum(len(data['prompts']) for data in user_prompts.values())
        
        for user_id, user_data in user_prompts.items():
            prompts = user_data['prompts']
            access_token = user_data['user_data']['access_token']
            user_email = user_data['user_data']['google_email']
            
            # Update current user
            video_generation_progress["all_users"]["current_user"] = f"User {user_id} ({user_email})"
            
            for i, prompt_data in enumerate(prompts):
                # Update progress
                video_generation_progress["all_users"].update({
                    "current_prompt": prompt_data['promt'][:50] + "..." if len(prompt_data['promt']) > 50 else prompt_data['promt'],
                    "current_step": f"Step 1/4: Submitting to Pollo AI",
                    "completed_count": completed_total,
                    "progress_percentage": (completed_total / total_prompts) * 100
                })
                
                # Step 1: Submit to Pollo AI
                task_id = await submit_to_pollo_ai(prompt_data['promt'])
                
                # Update progress
                video_generation_progress["all_users"]["current_step"] = "Step 2/4: Waiting for video generation"
                
                # Step 2: Poll for completion
                video_url = await poll_pollo_completion(task_id)
                
                # Update progress
                video_generation_progress["all_users"]["current_step"] = "Step 3/4: Downloading video"
                
                # Step 3: Download video from Pollo
                video_content = await download_video_from_pollo(video_url)
                
                # Update progress
                video_generation_progress["all_users"]["current_step"] = "Step 4/4: Uploading to Google Drive"
                
                # Step 4: Upload to Google Drive
                drive_url = await upload_to_google_drive(video_content, prompt_data['id'], access_token)
                
                # Update database
                supabase.table('video').update({
                    'video_url': drive_url
                }).eq('id', prompt_data['id']).execute()
                
                # Update progress
                completed_total += 1
                video_generation_progress["all_users"].update({
                    "completed_count": completed_total,
                    "progress_percentage": (completed_total / total_prompts) * 100,
                    "current_step": f"Completed {completed_total} of {total_prompts} videos"
                })
        
        # Mark as completed
        video_generation_progress["all_users"].update({
            "status": "completed",
            "current_step": "All videos generated successfully!",
            "progress_percentage": 100.0,
            "current_user": "All users processed"
        })
        
    except Exception as e:
        video_generation_progress["all_users"].update({
            "status": "error",
            "error_message": str(e),
            "current_step": f"Error occurred: {str(e)}"
        })

async def submit_to_pollo_ai(prompt: str) -> str:
    """Submit prompt to Pollo AI and return task_id"""
    try:
        url = f"{POLLO_BASE_URL}/{POLLO_MODEL}"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": POLLO_API_KEY
        }
        payload = {
            "input": {
                "prompt": prompt,
                "resolution": "720p",
                "length": 5,
                "mode": "basic"
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        return result["taskId"]
        
    except Exception as e:
        raise Exception(f"Failed to submit to Pollo AI: {str(e)}")

async def poll_pollo_completion(task_id: str) -> str:
    """Poll Pollo AI until completion and return video URL"""
    try:
        status_url = f"{POLLO_BASE_URL}/{task_id}/status"
        headers = {"x-api-key": POLLO_API_KEY}
        
        max_attempts = 120  # 10 minutes max (5 second intervals)
        for attempt in range(max_attempts):
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            generations = result.get("generations", [])
            
            if not generations:
                await asyncio.sleep(5)
                continue
            
            generation = generations[0]
            status = generation.get("status")
            
            if status == "succeed":
                return generation["url"]
            elif status == "failed":
                raise Exception(f"Pollo AI generation failed: {generation.get('failMsg', 'Unknown error')}")
            
            await asyncio.sleep(5)  # Wait 5 seconds before next poll
        
        raise Exception("Pollo AI generation timeout")
        
    except Exception as e:
        raise Exception(f"Failed to poll Pollo AI: {str(e)}")

async def download_video_from_pollo(video_url: str) -> bytes:
    """Download video content from Pollo AI"""
    try:
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        return response.content
    except Exception as e:
        raise Exception(f"Failed to download video: {str(e)}")

async def upload_to_google_drive(video_content: bytes, prompt_id: int, access_token: str) -> str:
    """Upload video to Google Drive and return shareable link"""
    try:
        # For now, return a placeholder - we'll implement Google Drive upload in next step
        return f"https://drive.google.com/placeholder/video_{prompt_id}_{int(time.time())}.mp4"
    except Exception as e:
        raise Exception(f"Failed to upload to Google Drive: {str(e)}")

@app.get("/api/video-records")
async def get_video_records():
    """Get all video records from Supabase"""
    try:
        print("Attempting to fetch from Supabase...")  # Debug log
        result = supabase.table('video').select('*').order('id').execute()
        print(f"Supabase response: {result}")  # Debug log
        return result.data
    except Exception as e:
        print(f"Supabase error: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")

@app.put("/api/video-records/{record_id}")
async def update_video_record(record_id: int, update_data: PromptUpdate):
    """Update a video record's prompt in Supabase"""
    try:
        print(f"Attempting to update record {record_id} with: {update_data.promt}")  # Debug log
        result = supabase.table('video').update({
            'promt': update_data.promt  # Match your database column name (lowercase)
        }).eq('id', record_id).execute()
        
        print(f"Update result: {result}")  # Debug log
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return {"message": "Record updated successfully", "data": result.data[0]}
    except Exception as e:
        print(f"Update error: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=f"Error updating record: {str(e)}")

@app.get("/api/video-records/{record_id}", response_model=VideoRecord)
async def get_video_record(record_id: int):
    """Get a specific video record by ID"""
    try:
        result = supabase.table('video').select('*').eq('id', record_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return result.data[0]
    except Exception as e:
        print(f"Fetch single record error: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=f"Error fetching record: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Supabase connection
        print("Testing Supabase connection...")  # Debug log
        result = supabase.table('video').select('count', count='exact').execute()
        print(f"Health check result: {result}")  # Debug log
        return {
            "status": "healthy", 
            "step": "1 - FastAPI + Supabase Connected",
            "supabase_connection": "OK",
            "total_records": result.count
        }
    except Exception as e:
        print(f"Health check error: {str(e)}")  # Debug log
        return {
            "status": "unhealthy", 
            "step": "1 - FastAPI + Supabase Connection Error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)