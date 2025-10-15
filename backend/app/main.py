from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import FRONTEND_URL
from app.routes import auth, channels, drive, analysis, trends, generatestory   # ✅ include channels, drive, analysis, trends, and generatestory routers

app = FastAPI(
    title="Auth + Channels Backend",
    description="Backend with Supabase authentication + YouTube channel linking + Analytics",
    version="1.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(drive.router, prefix="/api/drive", tags=["Drive"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(trends.router, prefix="/api/trends", tags=["Trends"])
app.include_router(generatestory.router, prefix="/api/generatestory", tags=["GenerateStory"])

@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}
