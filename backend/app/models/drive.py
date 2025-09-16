from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DriveAccountBase(BaseModel):
    user_id: str
    google_user_id: str
    google_email: str
    refresh_token: str
    access_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    drive_connected: bool = True

class DriveAccountCreate(DriveAccountBase):
    pass

class DriveAccountUpdate(BaseModel):
    access_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    drive_connected: Optional[bool] = None

class DriveAccount(DriveAccountBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
