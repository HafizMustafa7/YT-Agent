from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="Video Generation API", version="1.0.0")

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class Prompt(BaseModel):
    id: Optional[int] = None
    text: str
    created_at: Optional[datetime] = None
    video_url: Optional[str] = None
    status: Optional[str] = "pending"  # pending, processing, completed, failed

class PromptCreate(BaseModel):
    text: str

class VideoRequest(BaseModel):
    prompt_id: int

# In-memory storage (will replace with Supabase later)
prompts_db = []
next_id = 1

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
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { margin: 20px 0; }
            input, textarea { width: 100%; padding: 10px; margin: 10px 0; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>Video Generation System - Step 1</h1>
        
        <div class="container">
            <h2>Add New Prompt</h2>
            <form id="promptForm">
                <textarea id="promptText" placeholder="Enter your video prompt here..." rows="3" required></textarea>
                <button type="submit">Add Prompt</button>
            </form>
            <div id="message"></div>
        </div>

        <div class="container">
            <h2>All Prompts</h2>
            <button onclick="loadPrompts()">Refresh Prompts</button>
            <table id="promptsTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Prompt Text</th>
                        <th>Status</th>
                        <th>Created At</th>
                        <th>Video URL</th>
                    </tr>
                </thead>
                <tbody id="promptsBody">
                </tbody>
            </table>
        </div>

        <script>
            // Add prompt functionality
            document.getElementById('promptForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const text = document.getElementById('promptText').value;
                const messageDiv = document.getElementById('message');
                
                try {
                    const response = await fetch('/api/prompts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: text })
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        messageDiv.innerHTML = '<div class="status success">Prompt added successfully!</div>';
                        document.getElementById('promptText').value = '';
                        loadPrompts();
                    } else {
                        throw new Error('Failed to add prompt');
                    }
                } catch (error) {
                    messageDiv.innerHTML = '<div class="status error">Error: ' + error.message + '</div>';
                }
            });

            // Load prompts functionality
            async function loadPrompts() {
                try {
                    const response = await fetch('/api/prompts');
                    const prompts = await response.json();
                    
                    const tbody = document.getElementById('promptsBody');
                    tbody.innerHTML = '';
                    
                    prompts.forEach(prompt => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${prompt.id}</td>
                            <td>${prompt.text}</td>
                            <td>${prompt.status}</td>
                            <td>${new Date(prompt.created_at).toLocaleString()}</td>
                            <td>${prompt.video_url || 'Not generated'}</td>
                        `;
                    });
                } catch (error) {
                    console.error('Error loading prompts:', error);
                }
            }

            // Load prompts on page load
            window.onload = () => loadPrompts();
        </script>
    </body>
    </html>
    """

@app.get("/api/prompts", response_model=List[Prompt])
async def get_prompts():
    """Get all prompts"""
    return prompts_db

@app.post("/api/prompts", response_model=Prompt)
async def create_prompt(prompt: PromptCreate):
    """Create a new prompt"""
    global next_id
    
    new_prompt = Prompt(
        id=next_id,
        text=prompt.text,
        created_at=datetime.now(),
        status="pending"
    )
    
    prompts_db.append(new_prompt)
    next_id += 1
    
    return new_prompt

@app.get("/api/prompts/{prompt_id}", response_model=Prompt)
async def get_prompt(prompt_id: int):
    """Get a specific prompt by ID"""
    for prompt in prompts_db:
        if prompt.id == prompt_id:
            return prompt
    
    raise HTTPException(status_code=404, detail="Prompt not found")

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: int):
    """Delete a specific prompt"""
    global prompts_db
    
    for i, prompt in enumerate(prompts_db):
        if prompt.id == prompt_id:
            prompts_db.pop(i)
            return {"message": "Prompt deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Prompt not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "step": "1 - Basic FastAPI Setup"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)