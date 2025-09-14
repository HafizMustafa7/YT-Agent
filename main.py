from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import os
from supabase import create_client, Client

# Initialize FastAPI app
app = FastAPI(title="Video Generation API", version="1.0.0")

# Supabase configuration
SUPABASE_URL = "https://enwzcoocguqxxkkzxdtj.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVud3pjb29jZ3VxeHhra3p4ZHRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM3NTI0NiwiZXhwIjoyMDcxOTUxMjQ2fQ.AMZMo7jEe7iuhaTYAwM1FahlFI7pDOy4axWp-kGQMI4"

# Initialize Supabase client with service role key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class VideoRecord(BaseModel):
    id: Optional[int] = None
    Promt: str  # Match your database column name
    created_at: Optional[datetime] = None
    video_url: Optional[str] = None

class PromptUpdate(BaseModel):
    Promt: str  # Match your database column name

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
        </style>
    </head>
    <body>
        <h1>Video Generation System - Step 1 (Supabase Connected)</h1>
        
        <div class="container">
            <h2>Video Prompts from Supabase</h2>
            <button class="refresh-btn" onclick="loadPrompts()">🔄 Refresh Data</button>
            <div id="message"></div>
            
            <div id="loading" class="loading" style="display: none;">Loading data from Supabase...</div>
            
            <table id="promptsTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Prompt</th>
                        <th>Created At</th>
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

            // Load prompts from Supabase
            async function loadPrompts() {
                const loadingDiv = document.getElementById('loading');
                const messageDiv = document.getElementById('message');
                
                loadingDiv.style.display = 'block';
                messageDiv.innerHTML = '';
                
                try {
                    const response = await fetch('/api/video-records');
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const records = await response.json();
                    
                    const tbody = document.getElementById('promptsBody');
                    tbody.innerHTML = '';
                    
                    if (records.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No records found in Supabase</td></tr>';
                        return;
                    }
                    
                    records.forEach(record => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${record.id}</td>
                            <td id="prompt-${record.id}">${record.Promt}</td>
                            <td>${new Date(record.created_at).toLocaleString()}</td>
                            <td>${record.video_url || 'Not generated'}</td>
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
                const actionsCell = row.cells[4];
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
                        body: JSON.stringify({ Promt: newPrompt })
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
            window.onload = () => loadPrompts();
        </script>
    </body>
    </html>
    """

@app.get("/api/video-records", response_model=List[VideoRecord])
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
        print(f"Attempting to update record {record_id} with: {update_data.Promt}")  # Debug log
        result = supabase.table('video').update({
            'Promt': update_data.Promt  # Match your database column name
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
