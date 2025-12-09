# Backend Structure

## Directory Hierarchy

```
backend/
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── fetchtrend.py             # YouTube API service module
├── generatestory.py          # Story generation service module
└── app/                      # Application package
    ├── __init__.py
    └── core/                 # Core business logic modules
        ├── __init__.py
        ├── trend_fetcher.py  # Trend fetching logic
        ├── topic_validator.py # Topic validation logic
        └── creative_builder.py # Creative brief builder
```

## Module Organization

### Root Level
- **main.py**: FastAPI app with API endpoints
- **fetchtrend.py**: YouTube API integration service
- **generatestory.py**: AI story generation service (Gemini)

### app/core/
- **trend_fetcher.py**: Orchestrates trend fetching
- **topic_validator.py**: Validates topics (policy + quality)
- **creative_builder.py**: Builds structured creative briefs

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/fetch-trends` - Fetch trending videos
- `POST /api/validate-topic` - Validate a topic
- `POST /api/generate-story` - Generate story and frames

## Environment Variables

Create a `.env` file in the backend directory:
```
YOUTUBE_API_KEY=your_youtube_api_key
GEMINI_API_KEY=your_gemini_api_key
```

