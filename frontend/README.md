# Frontend Structure

## Directory Hierarchy

```
frontend/
├── public/                   # Static assets
├── src/
│   ├── App.js               # Main application component
│   ├── App.css              # Main application styles
│   ├── index.js             # React entry point
│   ├── index.css            # Global styles
│   └── components/          # React components
│       ├── Header.js/css
│       ├── HomeScreen.js/css
│       ├── TrendsScreen.js/css
│       ├── TopicValidationScreen.js/css
│       ├── CreativeFormScreen.js/css
│       └── StoryResultsScreen.js/css
├── package.json
└── README.md
```

## Component Flow

1. **HomeScreen**: Entry point with two options (Analyze Trends / Search Niche)
2. **TrendsScreen**: Displays trending videos from YouTube
3. **TopicValidationScreen**: Topic selection and validation
4. **CreativeFormScreen**: Creative direction form (dropdowns only)
5. **StoryResultsScreen**: Displays generated story with JSON frame prompts

## Getting Started

```bash
npm install
npm start
```

Frontend runs on http://localhost:3000
