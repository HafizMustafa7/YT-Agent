import React, { useState, useEffect } from 'react';
import './ResultsScreen.css';

const ResultsScreen = ({ data, onBack, onGenerate, loading }) => {
  const [selectedVideoId, setSelectedVideoId] = useState(null);
  const [topic, setTopic] = useState('');
  const [error, setError] = useState('');

  // Auto-fill topic when a video is selected
  useEffect(() => {
    if (selectedVideoId) {
      const selectedVideo = data.trends.find(v => v.id === selectedVideoId);
      if (selectedVideo) {
        setTopic(selectedVideo.title);
      }
    }
  }, [selectedVideoId, data.trends]);

  if (!data || !data.trends || data.trends.length === 0) {
    return (
      <div className="results-container">
        <div className="results-header">
          <h2>No Trending Videos Found for "{data?.niche || 'your niche'}"</h2>
          <button className="back-button" onClick={onBack}>
            Back to Search
          </button>
        </div>
        <p>Try a different niche or check your connection.</p>
      </div>
    );
  }

  const handleSelectVideo = (videoId) => {
    setSelectedVideoId(videoId);
    setError('');
  };

  const handleGenerate = (e) => {
    e.preventDefault();
    setError('');
    
    if (!selectedVideoId) {
      setError('Please select a video topic first.');
      return;
    }
    
    if (!topic.trim()) {
      setError('Please enter a topic for story generation.');
      return;
    }
    
    const selectedVideo = data.trends.find(v => v.id === selectedVideoId);
    onGenerate({ video: selectedVideo, topic: topic.trim() });
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>Trending AI-Generated Videos in "{data.niche}"</h2>
        <button className="back-button" onClick={onBack}>
          ← Back to Search
        </button>
      </div>
      
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Generating your story...</p>
        </div>
      )}
      
      <div className="stats-summary">
        <div className="stat-card">
          <div className="stat-number">{data.trends.length}</div>
          <div className="stat-label">Videos Found</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{formatNumber(Math.round(data.averageViews))}</div>
          <div className="stat-label">Avg Views</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {selectedVideoId ? '1' : '0'}
          </div>
          <div className="stat-label">Selected</div>
        </div>
      </div>
      
      <div className="video-grid">
        {data.trends.map((video) => {
          const isSelected = selectedVideoId === video.id;
          
          return (
            <div 
              key={video.id} 
              className={`video-card ${isSelected ? 'selected' : ''}`}
            >
              <div className="video-thumbnail-wrapper">
                <img 
                  src={video.thumbnail} 
                  alt={video.title}
                  className="video-thumbnail"
                />
                <span className="video-duration">{video.duration}</span>
                {video.ai_confidence && (
                  <span className="ai-badge">AI: {video.ai_confidence}%</span>
                )}
              </div>
              
              <div className="video-details">
                <h3 className="video-title">{video.title}</h3>
                
                <p className="channel-name">
                  <span className="channel-icon">📺</span>
                  {video.channel}
                </p>
                
                <div className="video-stats-row">
                  <span className="stat-item">
                    <span className="stat-icon">👁️</span>
                    {formatNumber(video.views)}
                  </span>
                  <span className="stat-item">
                    <span className="stat-icon">👍</span>
                    {formatNumber(video.likes)}
                  </span>
                  <span className="stat-item">
                    <span className="stat-icon">💬</span>
                    {formatNumber(video.comments)}
                  </span>
                </div>
                
                {video.description && (
                  <p className="video-description">
                    {video.description.length > 150 
                      ? `${video.description.substring(0, 150)}...` 
                      : video.description}
                  </p>
                )}
                
                {video.tags && video.tags.length > 0 && (
                  <div className="tags-section">
                    <div className="tags-list">
                      {video.tags.slice(0, 5).map((tag, idx) => (
                        <span key={idx} className="tag">#{tag}</span>
                      ))}
                      {video.tags.length > 5 && (
                        <span className="tag more">+{video.tags.length - 5}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
              
              <button 
                className={`select-button ${isSelected ? 'selected' : ''}`}
                onClick={() => handleSelectVideo(video.id)}
                disabled={loading}
              >
                {isSelected ? (
                  <>
                    <span className="check-icon">✓</span>
                    Selected
                  </>
                ) : (
                  'Select Topic'
                )}
              </button>
            </div>
          );
        })}
      </div>

      <div className="topic-generation-section">
        <div className="section-header">
          <h3>Generate Your Story</h3>
          <p>Select a video above or enter your custom topic</p>
        </div>
        
        <div className="topic-form">
          <div className="form-group">
            <label htmlFor="topic-input">Story Topic</label>
            <input
              id="topic-input"
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter your topic or modify the selected one..."
              className="topic-input"
              disabled={loading}
            />
            {selectedVideoId && (
              <small className="input-hint">
                Topic auto-filled from selected video. You can edit it.
              </small>
            )}
          </div>
          
          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
          
          <button 
            onClick={handleGenerate}
            className="generate-button"
            disabled={!topic.trim() || loading}
          >
            {loading ? (
              <>
                <span className="spinner-small"></span>
                Generating...
              </>
            ) : (
              <>
                <span className="generate-icon">✨</span>
                Generate Story & Frames
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResultsScreen;