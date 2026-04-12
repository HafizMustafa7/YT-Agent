# TODO: Fix FrameResults.jsx Data Fetching Issue

## Problem
FrameResults.jsx page shows "0 frames generated" even though the backend is successfully generating frames. The issue is in the data validation logic.

## Root Cause
1. FrameResults.jsx checks for `data.story` but backend returns `data.full_story`
2. Backend response missing `user_topic` field that frontend expects
3. This causes the "No Frames Generated" error message to display incorrectly

## Tasks
- [ ] Update backend `generatestory.py` to include `user_topic` in response
- [ ] Update FrameResults.jsx to check for `data.full_story` instead of `data.story`
- [ ] Test the fix by generating a story and verifying frames display correctly

## Files to Edit
- backend/app/routes/generatestory.py
- frontend/src/pages/FrameResults.jsx
