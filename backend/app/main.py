from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import FRONTEND_URL
from app.routes import auth

# Create FastAPI app
app = FastAPI(
    title="Auth Backend",
    description="Backend with Supabase authentication",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],   # frontend URL from config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register auth routes with prefix
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])

# Root endpoint (health check)
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}
