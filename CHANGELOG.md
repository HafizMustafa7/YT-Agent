# Changelog - Bug Fixes and Improvements

## [v2.0.0] - 2025-12-16 - Architecture Refactoring

### Major Restructuring

#### Backend Architecture (Breaking Changes)
- **✅ API Versioning**: All endpoints now use `/api/v1/` prefix
  - `/api/fetch-trends` → `/api/v1/trends/fetch`
  - `/api/validate-topic` → `/api/v1/topics/validate`
  - `/api/generate-story` → `/api/v1/stories/generate`
  
- **✅ Layered Architecture**: Implemented proper separation of concerns
  - **API Layer** (`app/api/`): Route handlers with versioning
  - **Services Layer** (`app/services/`): Business logic
    - `youtube_service.py` (moved from `fetchtrend.py`)
    - `story_service.py` (moved from `generatestory.py`)
  - **Schemas Layer** (`app/schemas/`): Pydantic models
  - **Config Layer** (`app/config/`): Centralized settings
  - **Core Layer** (`app/core/`): Utilities (topic_validator, creative_builder)

- **✅ Centralized Configuration**: 
  - Created `app/config/settings.py` for environment variables
  - CORS settings now configurable
  - API keys managed centrally

- **✅ Simplified main.py**: 
  - Reduced from 115 lines to 50 lines
  - Now only handles app initialization
  - Routes imported from API layer

- **✅ Removed Redundancy**:
  - Deleted `app/core/trend_fetcher.py` (redundant wrapper)
  - Deprecated `fetchtrend.py` and `generatestory.py` (kept for reference)

#### Frontend Architecture
- **✅ Organized Styles**: All CSS files moved to `src/styles/`
  - Global styles: `styles/index.css`, `styles/App.css`
  - Component styles: `styles/components/*.css`
  - Components now only contain JS logic

- **✅ Services Layer**: Created centralized API communication
  - `services/apiService.js`: All API calls with error handling
  - Timeout management for long-running requests
  - Consistent error handling across the app

- **✅ Configuration Layer**:
  - `config/constants.js`: API endpoints and app constants
  - Environment-based configuration support
  - Easy to switch between dev/prod environments

- **✅ Updated Imports**: All components updated to use new paths
  - CSS imports: `'../styles/components/ComponentName.css'`
  - API calls: Use `apiService.fetchTrends()` instead of inline fetch

### Benefits
- 📈 **Scalability**: Modular structure allows easy feature additions
- 🔧 **Maintainability**: Clear separation of concerns
- ✅ **Testability**: Services can be tested independently
- 🚀 **Future-proof**: API versioning supports backward compatibility
- 📦 **Organization**: Logical file structure and grouping

### Migration Guide
**For Frontend:**
- Update API base URL to use new versioned endpoints
- Import `apiService` instead of inline API calls
- Update CSS import paths if customizing components

**For Backend:**
- Environment variables now managed in `app/config/settings.py`
- Import services from `app.services` instead of root level
- Use new API routes from `app.api.routes`

---

## [v1.0.0] - Previous Version

## Fixed Issues

### Frontend
1. **ESLint Warning Fixed**: Removed unused `creativePrefs` variable from App.js
   - Variable was being set but never used
   - Removed from state management

### Backend
2. **Pydantic Deprecation Fixed**: Updated `.dict()` to `.model_dump()`
   - Changed in `backend/main.py` line 92
   - Compatible with Pydantic V2.0+

## Improvements Implemented

### 1. Trend Search Window
- **Changed**: Trend search now looks for viral shorts from last **15 days** (was 30 days)
- **File**: `backend/fetchtrend.py`
- **Reason**: More recent trends are more relevant for viral content

### 2. Custom Topic Input Field
- **Added**: Custom input field at top of TrendsScreen
- **Feature**: Users can skip video selection and enter custom topic directly
- **Files**: 
  - `frontend/src/components/TrendsScreen.js`
  - `frontend/src/components/TrendsScreen.css`
- **Flow**: Custom topic → Direct to validation screen

### 3. Stricter Topic Validation
- **Improved**: Topic validation now enforces quality standards for trending-worthy content
- **Checks Added**:
  - Minimum 10 characters (was 2)
  - Maximum 100 characters (was 200)
  - At least 2 meaningful words
  - Quality score threshold (60/100 minimum)
  - Trending indicator detection
  - Word diversity checks
- **File**: `backend/app/core/topic_validator.py`
- **Result**: Only topics with good viral potential pass validation

### 4. Enhanced JSON Prompts
- **Improved**: Frame prompts now ensure:
  - **Consistency**: Visual continuity between frames
  - **Perfect Scenes**: Detailed technical specifications
  - **Creativity**: Eye-catching, dynamic compositions
- **Enhancements**:
  - 200-300 word prompts (was 150-250)
  - Production-ready specifications (resolution, frame rate, aspect ratio)
  - Detailed camera, lighting, movement descriptions
  - Creative visual elements included
- **File**: `backend/generatestory.py`

### 5. Duration Options
- **Changed**: Duration increments from 5 seconds to **10 seconds**
- **Range**: **20 seconds to 2 minutes (120 seconds)**
- **Options**: 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120 seconds
- **Default**: 60 seconds
- **Display**: Shows both seconds and MM:SS format
- **Files**:
  - `frontend/src/components/CreativeFormScreen.js`
  - `backend/generatestory.py` (frame duration logic updated)

### 6. Custom Topic Support
- **Added**: Full support for custom topics without video selection
- **File**: `frontend/src/App.js`
- **Feature**: Creates dummy video object when using custom topic for story generation

## Summary

All requested changes have been implemented:
- ✅ Frontend warning fixed
- ✅ Backend deprecation fixed
- ✅ 15-day trend search window
- ✅ Custom topic input field
- ✅ Stricter topic validation
- ✅ Enhanced JSON prompts
- ✅ 10-second duration increments (20-120s range)

