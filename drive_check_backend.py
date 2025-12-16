from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import requests
from supabase import create_client, Client

# ==========================================================
# 🚀 FASTAPI APP
# ==========================================================
app = FastAPI(
    title="Google Drive Connection Checker",
    version="1.0.0",
    description="Check Google Drive access token connections"
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

# Google OAuth Credentials
GOOGLE_CLIENT_ID = "417933740796-865s0u7bhpv6pms84ne762aes5oj5fpq.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_REDIRECT_URI = "http://localhost:8000/api/channels/oauth/callback"

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
print("✓ Drive Check Backend: Supabase Connected")

# ==========================================================
# 🧠 MODELS
# ==========================================================
class DriveAccount(BaseModel):
    id: str
    user_id: str
    google_user_id: Optional[str] = None
    google_email: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    creation_time: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    drive_connected: bool = False

class DriveCheckResult(BaseModel):
    account: DriveAccount
    status: str  # "connected", "expired", "error"
    message: str
    user_info: Optional[dict] = None

# ==========================================================
# 🔄 TOKEN REFRESH FUNCTIONS
# ==========================================================
async def refresh_google_token(refresh_token: str) -> dict:
    """Refresh Google OAuth access token using refresh token"""
    try:
        token_url = "https://oauth2.googleapis.com/token"

        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        response = requests.post(token_url, data=data, timeout=30)

        if response.status_code == 200:
            token_data = response.json()
            new_access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour

            # Calculate new expiry time
            from datetime import datetime, timedelta
            new_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

            return {
                "success": True,
                "access_token": new_access_token,
                "expiry": new_expiry,
                "message": "Token refreshed successfully"
            }
        else:
            error_data = response.json()
            return {
                "success": False,
                "error": error_data.get("error", "Unknown error"),
                "message": f"Failed to refresh token: {error_data.get('error_description', 'Unknown error')}"
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": "network_error",
            "message": f"Network error during token refresh: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": "unexpected_error",
            "message": f"Unexpected error during token refresh: {str(e)}"
        }

async def update_account_tokens(account_id: str, access_token: str, token_expiry: datetime) -> bool:
    """Update account with new tokens in database"""
    try:
        update_data = {
            "access_token": access_token,
            "token_expiry": token_expiry.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        result = supabase.table('drive_accounts').update(update_data).eq('id', account_id).execute()

        if result.data:
            print(f"✓ Updated tokens for account {account_id}")
            return True
        else:
            print(f"✗ Failed to update tokens for account {account_id}")
            return False

    except Exception as e:
        print(f"✗ Error updating tokens for account {account_id}: {str(e)}")
        return False

# ==========================================================
# 🔍 DRIVE CHECK FUNCTIONS
# ==========================================================
async def check_drive_connection(access_token: str, refresh_token: str = None, account_id: str = None) -> dict:
    """Check if Google Drive access token is valid by getting user info, and refresh if expired"""
    try:
        # Test token by getting user profile
        user_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        response = requests.get(user_url, headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            return {
                "status": "connected",
                "message": "Access token is valid",
                "user_info": user_data
            }
        elif response.status_code == 401:
            # Token is expired, try to refresh if we have refresh_token and account_id
            if refresh_token and account_id:
                print(f"[REFRESH] Token expired for account {account_id}, attempting refresh...")
                refresh_result = await refresh_google_token(refresh_token)

                if refresh_result["success"]:
                    new_access_token = refresh_result["access_token"]
                    new_expiry = refresh_result["expiry"]

                    # Update database with new tokens
                    update_success = await update_account_tokens(account_id, new_access_token, new_expiry)

                    if update_success:
                        # Test the new token
                        headers["Authorization"] = f"Bearer {new_access_token}"
                        response = requests.get(user_url, headers=headers, timeout=10)

                        if response.status_code == 200:
                            user_data = response.json()
                            return {
                                "status": "refreshed",
                                "message": "Token was refreshed and is now valid",
                                "user_info": user_data
                            }
                        else:
                            return {
                                "status": "refresh_failed",
                                "message": "Token refreshed but still invalid",
                                "user_info": None
                            }
                    else:
                        return {
                            "status": "refresh_failed",
                            "message": "Token refreshed but failed to update database",
                            "user_info": None
                        }
                else:
                    return {
                        "status": "refresh_failed",
                        "message": f"Token refresh failed: {refresh_result['message']}",
                        "user_info": None
                    }
            else:
                return {
                    "status": "expired",
                    "message": "Access token expired and no refresh token available",
                    "user_info": None
                }
        else:
            return {
                "status": "error",
                "message": f"Unexpected response: {response.status_code}",
                "user_info": None
            }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "user_info": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "user_info": None
        }

# ==========================================================
# 📡 API ROUTES
# ==========================================================
@app.get("/api/drive-accounts", response_model=List[DriveCheckResult])
async def get_drive_accounts():
    """Get all drive accounts and check their connection status"""
    try:
        # Fetch all drive accounts
        result = supabase.table('drive_accounts').select('*').execute()

        if not result.data:
            return []

        check_results = []

        for account_data in result.data:
            account = DriveAccount(**account_data)

            # Check connection if access_token exists
            if account.access_token:
                check_result = await check_drive_connection(
                    account.access_token,
                    account.refresh_token,
                    account.id
                )
                result_item = DriveCheckResult(
                    account=account,
                    status=check_result["status"],
                    message=check_result["message"],
                    user_info=check_result["user_info"]
                )
            else:
                result_item = DriveCheckResult(
                    account=account,
                    status="no_token",
                    message="No access token available",
                    user_info=None
                )

            check_results.append(result_item)

        return check_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching drive accounts: {str(e)}")

@app.get("/api/drive-accounts/{account_id}", response_model=DriveCheckResult)
async def get_drive_account(account_id: str):
    """Get specific drive account and check its connection"""
    try:
        # Fetch specific account
        result = supabase.table('drive_accounts').select('*').eq('id', account_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Drive account not found")

        account_data = result.data[0]
        account = DriveAccount(**account_data)

        # Check connection if access_token exists
        if account.access_token:
            check_result = await check_drive_connection(account.access_token)
            result_item = DriveCheckResult(
                account=account,
                status=check_result["status"],
                message=check_result["message"],
                user_info=check_result["user_info"]
            )
        else:
            result_item = DriveCheckResult(
                account=account,
                status="no_token",
                message="No access token available",
                user_info=None
            )

        return result_item

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking drive account: {str(e)}")

# ==========================================================
# 🌐 MAIN ROUTES
# ==========================================================
@app.get("/")
async def root():
    """Serve the drive check HTML"""
    return FileResponse("drive_check.html")

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        result = supabase.table('drive_accounts').select('count', count='exact').execute()
        return {
            "status": "healthy",
            "database": "connected",
            "total_accounts": result.count
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ==========================================================
# 🔥 RUN SERVER
# ==========================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔍 GOOGLE DRIVE CONNECTION CHECKER")
    print("="*60)
    print("🚀 Server: http://0.0.0.0:8001")
    print("📚 API Docs: http://0.0.0.0:8001/docs")
    print("🔍 Checker: http://0.0.0.0:8001")
    print("="*60 + "\n")

    uvicorn.run("drive_check_backend:app", host="0.0.0.0", port=8001, reload=True)
