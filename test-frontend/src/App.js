// frontend/src/App.js
import React, { useState } from 'react';
import Header from './components/Header';
import ChatBot from './components/NicheInput';
import ResultsScreen from './components/ResultsScreen';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [trendingData, setTrendingData] = useState(null);
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
        throw new Error('Failed to fetch trends');
      }
      
      const data = await response.json();
      setTrendingData(data);
      setCurrentView('results');
    } catch (err) {
      setError(err.message);
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleBackToHome = () => {
    setCurrentView('home');
    setTrendingData(null);
  };

  return (
    <div className="App">
      <Header />
      <div className="floating-shapes">
        <div className="shape shape-1"></div>
        <div className="shape shape-2"></div>
        <div className="shape shape-3"></div>
        <div className="shape shape-4"></div>
      </div>
      
      {currentView === 'home' ? (
        <div className="hero-section">
          <h1 className="title">AI-Powered YouTube Trend Generator</h1>
          <p className="subtitle">
            Our cutting-edge AI analyzes YouTube trends to help you create viral content. 
            Simply enter your niche and our system will generate trending video ideas, 
            optimal titles, descriptions, and even generate video scripts using advanced AI algorithms.
          </p>
          
          {error && <div className="error-message">{error}</div>}
          
          <ChatBot 
            onAnalyze={handleAnalyzeTrends}
            loading={loading}
          />
        </div>
      ) : (
        <ResultsScreen 
          data={trendingData} 
          onBack={handleBackToHome}
        />
      )}
    </div>
  );
}

export default App;