# Integration Plan for Analytics Page

## Backend Changes
- [ ] Modify `backend/app/routes/analysis.py` to use APIRouter instead of FastAPI app
- [ ] Update `backend/app/main.py` to include the analysis router

## Frontend Changes
- [ ] Add protected route for `/analytics` in `frontend/src/App.jsx`
- [ ] Update `frontend/src/pages/Analytics.jsx` to match app theme and session handling like `NicheInputPage.jsx`

## Testing
- [ ] Test session handling and navigation
- [ ] Verify API endpoints work
- [ ] Check theme consistency
