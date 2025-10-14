// frontend/src/App.js
import React, { useState } from 'react';
import Header from './components/Header';
import NicheInput from './components/NicheInput';
import ResultsScreen from './components/ResultsScreen';
import FrameResults from './components/FrameResults';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [trendingData, setTrendingData] = useState(null);
  const [generatedData, setGeneratedData] = useState(null);
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

  // Handle story generation from ResultsScreen
  const handleGenerateStory = async ({ video, topic }) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/generate-story-and-frames', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          selected_video: video,
          user_topic: topic 
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to generate story: ${response.statusText}`);
      }
      
      const data = await response.json();
      setGeneratedData(data);
      setCurrentView('frames');
    } catch (err) {
      setError(err.message || 'Failed to generate story. Please try again.');
      console.error('Error generating story:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleBackToResults = () => {
    setCurrentView('results');
    setGeneratedData(null);  // Clear generated data when going back
  };

  const handleBackToHome = () => {
    setCurrentView('home');
    setTrendingData(null);
    setGeneratedData(null);
    setError(null);
  };

  const clearError = () => setError(null);

  return (
    <div className="App">
      <Header />
      <div className="floating-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
        <div className="shape shape-4"></div>
      </div>
      
      {/* Global Error Banner */}
      {error && (
        <div className="global-error" role="alert">
          <div className="error-content">
            <span className="error-icon">⚠️</span>
            <p>{error}</p>
          </div>
          <button 
            onClick={clearError} 
            className="error-dismiss"
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      )}
      
      {/* Loading Overlay (Global) */}
      {loading && currentView !== 'results' && (
        <div className="global-loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner-large"></div>
            <p>
              {currentView === 'home' ? 'Analyzing trends...' : 'Generating story...'}
            </p>
          </div>
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
          
          <NicheInput
            onAnalyze={handleAnalyzeTrends}
            loading={loading}
          />
        </div>
      ) : currentView === 'results' ? (
        <ResultsScreen 
          data={trendingData} 
          onBack={handleBackToHome}
          onGenerate={handleGenerateStory}
          loading={loading}
        />
      ) : currentView === 'frames' ? (
        <FrameResults 
          data={generatedData}
          onBack={handleBackToResults}
          onBackToHome={handleBackToHome}
          loading={loading}
        />
      ) : null}
    </div>
  );
}

export default App;