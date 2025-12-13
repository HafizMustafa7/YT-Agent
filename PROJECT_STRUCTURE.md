# Project Structure - Complete Hierarchy

## Root Level
```
YT-Agent/
├── README.md                 # Main project documentation
├── PROJECT_STRUCTURE.md      # This file
└── .gitignore               # Git ignore rules
```

## Backend Structure
```
backend/
├── main.py                   # FastAPI application entry point
├── requirements.txt          # Python dependencies
├── README.md                # Backend documentation
├── fetchtrend.py            # YouTube API service module
├── generatestory.py         # Story generation service (Gemini AI)
└── app/                     # Application package
    ├── __init__.py
    └── core/                # Core business logic
        ├── __init__.py
        ├── trend_fetcher.py     # Orchestrates trend fetching
        ├── topic_validator.py   # Topic validation logic
        └── creative_builder.py  # Creative brief builder
```

### Backend Files Description

**Root Level:**
- `main.py`: FastAPI app with all API endpoints
- `fetchtrend.py`: YouTube API integration (get_trending_shorts)
- `generatestory.py`: AI story generation with Gemini
- `requirements.txt`: All Python dependencies

**app/core/:**
- `trend_fetcher.py`: Wraps fetchtrend.py, provides fetch_trends()
- `topic_validator.py`: Validates topics (normalize, policy check)
- `creative_builder.py`: Builds structured creative briefs

## Frontend Structure
```
frontend/
├── package.json             # Node.js dependencies
├── README.md               # Frontend documentation
├── public/                 # Static assets
│   ├── index.html
│   └── ...
└── src/
    ├── index.js            # React entry point
    ├── index.css           # Global styles
    ├── App.js              # Main application component
    ├── App.css             # Main app styles
    └── components/         # React components (one per screen)
        ├── Header.js/css
        ├── HomeScreen.js/css          # Entry screen
        ├── TrendsScreen.js/css        # Trends display
        ├── TopicValidationScreen.js/css # Topic validation
        ├── CreativeFormScreen.js/css   # Creative direction
        └── StoryResultsScreen.js/css   # Final results
```

### Frontend Components Flow

1. **Header**: Navigation header (used across all screens)
2. **HomeScreen**: Entry point - 2 buttons (Analyze Trends / Search Niche)
3. **TrendsScreen**: Displays trending YouTube Shorts videos
4. **TopicValidationScreen**: Topic selection, editing, and validation
5. **CreativeFormScreen**: Creative direction form (all dropdowns/selects)
6. **StoryResultsScreen**: Displays generated story + JSON frame prompts

## Clean Structure Rules

✅ **Backend:**
- All services in root (fetchtrend.py, generatestory.py)
- Core logic modules in `app/core/`
- Main entry point: `main.py`

✅ **Frontend:**
- One component per screen
- Each component has its own CSS file
- Clear separation of concerns

✅ **Deleted Files:**
- ❌ `main2.py` (duplicate)
- ❌ `NicheInput.js/css` (replaced by HomeScreen)
- ❌ `ResultsScreen.js/css` (replaced by TrendsScreen)
- ❌ `FrameResults.js/css` (replaced by StoryResultsScreen)

## File Count Summary

**Backend:** 9 Python files
**Frontend:** 13 component files (6 JS + 6 CSS + 1 shared CSS)
**Total:** 22 source code files (excluding config/docs)

