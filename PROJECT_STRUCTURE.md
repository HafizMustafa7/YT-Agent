# Project Structure - Refactored Architecture

## Root Level
```
YT-Agent/
├── README.md                 # Main project documentation
├── PROJECT_STRUCTURE.md      # This file
├── CHANGELOG.md             # Version history
└── .gitignore               # Git ignore rules
```

## Backend Structure (Refactored)
```
backend/
├── main.py                          # FastAPI entry point (simplified)
├── requirements.txt                 # Python dependencies
├── README.md                       # Backend documentation
├── .env                            # Environment variables
├── fetchtrend.py                   # DEPRECATED - kept for reference
├── generatestory.py                # DEPRECATED - kept for reference
└── app/                            # Application package
    ├── __init__.py
    ├── api/                        # API layer (NEW)
    │   ├── __init__.py
    │   └── routes.py               # All API endpoints with /api/v1 prefix
    ├── services/                   # Business logic (NEW)
    │   ├── __init__.py
    │   ├── youtube_service.py      # YouTube API integration (moved from fetchtrend.py)
    │   └── story_service.py        # Gemini AI integration (moved from generatestory.py)
    ├── schemas/                    # Data models (NEW)
    │   ├── __init__.py
    │   └── models.py               # Pydantic request/response models
    ├── core/                       # Core utilities
    │   ├── __init__.py
    │   ├── topic_validator.py      # Topic validation logic
    │   └── creative_builder.py     # Creative brief builder
    └── config/                     # Configuration (NEW)
        ├── __init__.py
        └── settings.py             # Centralized settings & env vars
```

### Backend Architecture Improvements

**New Layered Structure:**
- **API Layer** (`app/api/`): Route handlers with versioning (`/api/v1/`)
- **Services Layer** (`app/services/`): Business logic and external API integrations
- **Schemas Layer** (`app/schemas/`): Pydantic models for validation
- **Config Layer** (`app/config/`): Centralized configuration management
- **Core Layer** (`app/core/`): Reusable utilities and helpers

**Key Changes:**
- ✅ API versioning: All endpoints now use `/api/v1/` prefix
- ✅ Centralized settings: Environment variables managed in `settings.py`
- ✅ Service separation: YouTube and Story services properly isolated
- ✅ Simplified main.py: Now only handles app initialization
- ✅ Better error handling: Consistent error responses across endpoints

### API Endpoints (Versioned)

```
GET  /                          → API information
GET  /api/v1/health             → Health check
POST /api/v1/trends/fetch       → Fetch trending videos
POST /api/v1/topics/validate    → Validate topic quality
POST /api/v1/stories/generate   → Generate AI story + frames
```

## Frontend Structure (Refactored)
```
frontend/
├── package.json                    # Node.js dependencies
├── README.md                      # Frontend documentation
├── public/                        # Static assets
│   ├── index.html
│   ├── favicon.ico
│   ├── logo192.png
│   ├── logo512.png
│   ├── manifest.json
│   └── robots.txt
└── src/
    ├── index.js                   # React entry point (updated imports)
    ├── App.js                     # Main app component (uses apiService)
    ├── components/                # React components (JS only)
    │   ├── Header.js
    │   ├── HomeScreen.js
    │   ├── TrendsScreen.js
    │   ├── TopicValidationScreen.js
    │   ├── CreativeFormScreen.js
    │   └── StoryResultsScreen.js
    ├── styles/                    # All CSS files (NEW)
    │   ├── index.css              # Global styles
    │   ├── App.css                # Main app styles
    │   └── components/            # Component-specific styles
    │       ├── Header.css
    │       ├── HomeScreen.css
    │       ├── TrendsScreen.css
    │       ├── TopicValidationScreen.css
    │       ├── CreativeFormScreen.css
    │       └── StoryResultsScreen.css
    ├── services/                  # API communication (NEW)
    │   └── apiService.js          # Centralized API calls
    └── config/                    # Configuration (NEW)
        └── constants.js           # API endpoints & app constants
```

### Frontend Architecture Improvements

**New Organization:**
- **Separation of Concerns**: JS components separate from CSS styles
- **Services Layer**: Centralized API communication with error handling
- **Configuration**: API endpoints and constants in dedicated config file
- **Cleaner Components**: Components now import from organized structure

**Key Changes:**
- ✅ Styles organized: All CSS files in `src/styles/` directory
- ✅ API service: Centralized API calls in `apiService.js`
- ✅ Configuration: API URLs and constants in `constants.js`
- ✅ Updated imports: All components use new import paths
- ✅ Better maintainability: Clear separation between logic and styling

### Frontend Components Flow

1. **Header**: Navigation header (used across all screens)
2. **HomeScreen**: Entry point - 2 buttons (Analyze Trends / Search Niche)
3. **TrendsScreen**: Displays trending YouTube Shorts videos
4. **TopicValidationScreen**: Topic selection, editing, and validation
5. **CreativeFormScreen**: Creative direction form (all dropdowns/selects)
6. **StoryResultsScreen**: Displays generated story + JSON frame prompts

## Architecture Benefits

### Backend
✅ **Scalability**: Modular structure allows easy addition of new features
✅ **Maintainability**: Clear separation of concerns
✅ **Testability**: Services can be tested independently
✅ **API Versioning**: Future-proof with `/api/v1/` prefix
✅ **Configuration**: Centralized settings management

### Frontend
✅ **Organization**: Clear file structure with logical grouping
✅ **Reusability**: Centralized API service reduces code duplication
✅ **Maintainability**: Styles separated from logic
✅ **Scalability**: Easy to add new components and services
✅ **Type Safety**: Consistent API communication layer

## File Count Summary

**Backend:**
- API Layer: 2 files
- Services: 3 files (including __init__)
- Schemas: 2 files
- Config: 2 files
- Core: 3 files
- **Total: 12 Python files** (excluding deprecated files)

**Frontend:**
- Components: 6 JS files
- Styles: 8 CSS files (2 global + 6 component)
- Services: 1 JS file
- Config: 1 JS file
- **Total: 16 source files**

**Overall: 28 source code files** (excluding config/docs/node_modules)

## Migration Notes

### Deprecated Files (Kept for Reference)
- `backend/fetchtrend.py` → Moved to `app/services/youtube_service.py`
- `backend/generatestory.py` → Moved to `app/services/story_service.py`
- `backend/app/core/trend_fetcher.py` → Deleted (redundant wrapper)

### Breaking Changes
- API endpoints now use `/api/v1/` prefix instead of `/api/`
- Frontend must update API base URL to use new endpoints
- Import paths changed throughout the codebase

## Next Steps

### Recommended Improvements
1. **Database Layer**: Add persistence for stories and user data
2. **Caching**: Implement caching for YouTube API responses
3. **Authentication**: Add user authentication if needed
4. **Rate Limiting**: Add rate limiting to API endpoints
5. **Logging**: Implement structured logging
6. **Testing**: Add unit and integration tests
7. **Docker**: Add Docker configuration for deployment
