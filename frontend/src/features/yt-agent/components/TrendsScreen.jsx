import React, { useState } from 'react';
import '../styles/components/TrendsScreen.css';

const TrendsScreen = ({ trendsData, onSelectVideo, onBack, loading, onCustomTopic }) => {
  const [customTopic, setCustomTopic] = useState('');
  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="trends-screen">
      <div className="trends-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <h2>Trending Videos</h2>
        <p className="trends-subtitle">
          {trendsData?.mode === 'analyze_niche'
            ? `Results for: ${trendsData.query_used}`
            : 'Top trending YouTube Shorts'}
        </p>
      </div>

      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Loading trends...</p>
        </div>
      )}

      <div className="custom-topic-section">
        <div className="custom-topic-input-wrapper">
          <label htmlFor="custom-topic-input">Or Enter Your Custom Topic:</label>
          <div className="custom-topic-controls">
            <input
              id="custom-topic-input"
              type="text"
              value={customTopic}
              onChange={(e) => setCustomTopic(e.target.value)}
              placeholder="Enter your custom topic idea..."
              className="custom-topic-input"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && customTopic.trim() && onCustomTopic) {
                  onCustomTopic(customTopic.trim());
                }
              }}
            />
            <button
              className="custom-topic-btn"
              onClick={() => {
                if (customTopic.trim() && onCustomTopic) {
                  onCustomTopic(customTopic.trim());
                }
              }}
              disabled={!customTopic.trim()}
            >
              Use Custom Topic
            </button>
          </div>
          <p className="custom-topic-hint">
            Skip video selection and go directly to topic validation
          </p>
        </div>
      </div>

      <div className="trends-grid">
        {trendsData?.trends?.map((video) => (
          <div
            key={video.id}
            className="video-card"
            onClick={() => onSelectVideo(video)}
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

            <div className="video-content">
              <h3 className="video-title">{video.title}</h3>

              <div className="video-meta">
                <span className="channel-name">
                  <span className="icon">📺</span>
                  {video.channel}
                </span>
              </div>

              <div className="video-stats">
                <span className="stat">
                  <span className="icon">👁️</span>
                  {formatNumber(video.views)}
                </span>
                <span className="stat">
                  <span className="icon">👍</span>
                  {formatNumber(video.likes)}
                </span>
                <span className="stat">
                  <span className="icon">💬</span>
                  {formatNumber(video.comments)}
                </span>
              </div>

              {video.description && (
                <p className="video-description">
                  {video.description.length > 100
                    ? `${video.description.substring(0, 100)}...`
                    : video.description}
                </p>
              )}

              <button className="select-btn">Select This Topic</button>
            </div>
          </div>
        ))}
      </div>

      {trendsData?.trends?.length === 0 && !loading && (
        <div className="empty-state">
          <p>No trends found. Try a different search.</p>
        </div>
      )}
    </div>
  );
};

export default TrendsScreen;

