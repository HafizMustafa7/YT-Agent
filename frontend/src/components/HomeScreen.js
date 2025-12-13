import React, { useState } from 'react';
import './HomeScreen.css';

const HomeScreen = ({ onAnalyzeTrends, onSearchNiche, loading }) => {
  const [nicheInput, setNicheInput] = useState('');

  const handleNicheSearch = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (nicheInput.trim()) {
      onSearchNiche(nicheInput.trim());
    }
  };

  return (
    <div className="home-screen">
      <div className="home-content">
        <h1 className="home-title">AI-Powered YouTube Shorts Generator</h1>
        <p className="home-intro">
          Transform your ideas into viral YouTube Shorts with our advanced automation platform. 
          Our AI analyzes trending content, validates your concepts, and generates complete 
          storyboards with frame-by-frame prompts ready for video creation.
        </p>
        <p className="home-description">
          Whether you're looking for inspiration or have a specific niche in mind, 
          we'll help you create engaging short-form content that captivates your audience.
        </p>

        <div className="home-actions">
          <button
            className="action-btn primary-btn"
            onClick={onAnalyzeTrends}
            disabled={loading}
          >
            <span className="btn-icon">🔍</span>
            Analyze Trends
          </button>

          <div className="or-divider">
            <span>OR</span>
          </div>

          <div className="niche-search-container">
            <div className="niche-input-wrapper">
              <input
                type="text"
                placeholder="Enter your niche (e.g., fitness, cooking, tech)"
                value={nicheInput}
                onChange={(e) => setNicheInput(e.target.value)}
                className="niche-input"
                disabled={loading}
                onKeyPress={(e) => e.key === 'Enter' && handleNicheSearch(e)}
              />
            </div>
            <button
              className="action-btn secondary-btn"
              onClick={handleNicheSearch}
              disabled={loading || !nicheInput.trim()}
            >
              <span className="btn-icon">🎯</span>
              Search Niche
            </button>
          </div>
        </div>

        {loading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <p>Fetching trending content...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default HomeScreen;

