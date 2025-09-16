# Drive Integration Implementation TODO

## Database Layer
- [x] Create drive_accounts table in Supabase
- [x] Create backend/app/models/drive.py with Pydantic models

## Backend Implementation
- [x] Create backend/app/routes/drive.py with 4 endpoints:
  - [x] POST /api/drive/oauth/start
  - [x] GET /api/drive/oauth/callback
  - [x] GET /api/drive/status
  - [x] POST /api/drive/disconnect
- [x] Update backend/app/routes/auth.py /me endpoint to include drive_connected and drive_email

## Frontend Implementation
- [x] Create frontend/src/pages/ConnectDrivePage.jsx
- [x] Update frontend/src/pages/AuthPage.jsx login flow to check drive_connected
- [x] Add /connect-drive route in frontend/src/App.jsx
- [x] Extend frontend/src/api/auth.js with startDriveOAuth and updated getCurrentUser

## Testing & Followup
- [x] Test OAuth flow end-to-end (requires Google OAuth app configuration)
- [ ] Handle token refresh logic if needed
- [x] Add error handling for Drive API failures
