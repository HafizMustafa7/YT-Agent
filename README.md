# YT-Agent - AI-Powered YouTube Shorts Generator

An automated platform that analyzes YouTube trends, validates topics, and generates complete storyboards with AI video generation prompts.

## Project Structure

```
YT-Agent/
├── backend/              # FastAPI backend application
│   ├── main.py          # API entry point
│   ├── requirements.txt # Python dependencies
│   ├── fetchtrend.py    # YouTube API service
│   ├── generatestory.py # Story generation service
│   └── app/
│       └── core/        # Core business logic modules
│           ├── trend_fetcher.py
│           ├── topic_validator.py
│           └── creative_builder.py
│
├── frontend/            # React frontend application
│   ├── src/
│   │   ├── App.js      # Main app component
│   │   └── components/ # React components
│   │       ├── HomeScreen
│   │       ├── TrendsScreen
│   │       ├── TopicValidationScreen
│   │       ├── CreativeFormScreen
│   │       └── StoryResultsScreen
│   └── package.json
│
└── README.md           # This file
```

## Features

### Input Layer Pipeline
1. **Entry Screen**: Choose between "Search Trends" or "Analyze by Niche"
2. **Trend Engine**: Fetches and displays trending YouTube Shorts
3. **Topic Selection**: Select, edit, or enter custom topic
4. **Topic Validation**: Validates topic (policy compliance + quality check)
5. **Creative Direction**: Configure video style via dropdowns
6. **Story Generation**: Generates complete story with dynamic frames
7. **JSON Output**: Frame prompts in JSON format with creative modules

## Getting Started

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

5. Run the server:
```bash
python main.py
```

Backend runs on http://localhost:8000

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm start
```

Frontend runs on http://localhost:3000

## API Endpoints

- `POST /api/fetch-trends` - Fetch trending videos
- `POST /api/validate-topic` - Validate a topic
- `POST /api/generate-story` - Generate story and frames

## Technologies

### Backend
- FastAPI
- Google YouTube Data API
- Google Gemini AI
- Python 3.8+

### Frontend
- React 19
- CSS3
- Modern JavaScript (ES6+)

## License

This project is for educational purposes.

