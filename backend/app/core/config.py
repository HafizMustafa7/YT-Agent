import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI_CHANNELS = os.getenv("GOOGLE_REDIRECT_URI_CHANNELS", "http://localhost:8000/api/channels/oauth/callback")
GOOGLE_REDIRECT_URI_DRIVE = os.getenv("GOOGLE_REDIRECT_URI_DRIVE", "http://localhost:8000/api/drive/oauth/callback")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
