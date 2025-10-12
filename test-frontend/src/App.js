// frontend/src/App.js
import React, { useState } from 'react';
import Header from './components/Header';
import NicheInput from './components/NicheInput';  // Updated from ChatBot (per earlier rename)
import ResultsScreen from './components/ResultsScreen';
import FrameResults from './components/FrameResults';  // New import
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [trendingData, setTrendingData] = useState(null);
  const [generatedData, setGeneratedData] = useState(null);  // New: For story/frames
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyzeTrends = async (niche) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/analyze-trends', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ niche }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch trends: ${response.statusText}`);
      }
      
      const data = await response.json();
      setTrendingData(data);
      setCurrentView('results');
    } catch (err) {
      setError(err.message);
      console.error('Error fetching trends:', err);
    } finally {
      setLoading(false);
    }
  };

  // New: Handle generation from ResultsScreen
  const handleGenerateStory = async (payload) => {  // payload: { video, topic } from ResultsScreen
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/generate-story-and-frames', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),  // { selected_video, user_topic }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to generate story: ${response.statusText}`);
      }
      
      const data = await response.json();
      setGeneratedData(data);
      setCurrentView('frames');
    } catch (err) {
      setError(err.message);
      console.error('Error generating story:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleBackToResults = () => {
    setCurrentView('results');
    // Optionally clear generatedData if regenerating: setGeneratedData(null);
  };

  const handleBackToHome = () => {
    setCurrentView('home');
    setTrendingData(null);
    setGeneratedData(null);  // Clear all data on full reset
    setError(null);
  };

  const clearError = () => setError(null);  // Utility to dismiss errors

  return (
    <div className="App">
      <Header />
      <div className="floating-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
        <div className="shape shape-4"></div>
      </div>
      
      {/* Global Error Banner (shows on any view if error) */}
      {error && (
        <div className="global-error">
          <p role="alert">{error}</p>
          <button onClick={clearError} aria-label="Dismiss error">×</button>
        </div>
      )}
      
      {currentView === 'home' ? (
        <div className="hero-section">
          <h1 className="title">AI-Powered YouTube Trend Generator</h1>
          <p className="subtitle">
            Our cutting-edge AI analyzes YouTube trends to help you create viral content. 
            Simply enter your niche and our system will generate trending video ideas, 
            optimal titles, descriptions, and even generate video scripts using advanced AI algorithms.
          </p>
          
          <NicheInput  // Updated component name
            onAnalyze={handleAnalyzeTrends}
            loading={loading}
          />
        </div>
      ) : currentView === 'results' ? (
        <ResultsScreen 
          data={trendingData} 
          onBack={handleBackToHome}
          onGenerate={handleGenerateStory}  // New prop
          loading={loading}
        />
      ) : currentView === 'frames' ? (
        <FrameResults 
          data={generatedData}
          onBack={handleBackToResults}  // New back handler
          loading={loading}
        />
      ) : null}
    </div>
  );
}

export default App;