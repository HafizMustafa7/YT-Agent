// frontend/src/components/ResultsScreen.js
import React, { useState } from 'react';
import './ResultsScreen.css';

const ResultsScreen = ({ data, onBack, onGenerate, loading }) => {  // Added onGenerate and loading props
  const [selectedVideoId, setSelectedVideoId] = useState(null);  // Track by ID for single selection
  const [topic, setTopic] = useState('');  // User topic input
  const [error, setError] = useState('');  // For validation

  if (!data || !data.trends || data.trends.length === 0) {
    return (
      <div className="results-container">
        <div className="results-header">
          <h2>No Trending Videos Found for "{data?.niche || 'your niche'}"</h2>
          <button className="back-button" onClick={onBack}>
            Back to Search
          </button>
        </div>
        <p>Try a different niche or check your connection.</p>  // Improved message
      </div>
    );
  }

  const handleGenerate = (e) => {
    e.preventDefault();
    setError('');
    if (!selectedVideoId) {
      setError('Please select one video topic.');
      return;
    }
    if (!topic.trim()) {
      setError('Please enter a topic for story generation.');
      return;
    }
    const selectedVideo = data.trends.find(v => v.id === selectedVideoId);
    onGenerate({ video: selectedVideo, topic: topic.trim() });  // Pass to parent/backend
  };

  const selectedVideo = data.trends.find(v => v.id === selectedVideoId);

  return (
    <div className="results-container" role="main">
      <div className="results-header">
        <h2>Trending Videos in "{data.niche}"</h2>
        <button className="back-button" onClick={onBack} aria-label="Go back to niche input">
          Back to Search
        </button>
      </div>
      
      {loading && (
        <div className="loading" role="status" aria-live="polite">
          <div className="loading-spinner" aria-label="Generating story..."></div>
        </div>
      )}
      
      <div className="stats-summary">
        <div className="stat-item">
          <h3>{data.trends.length}</h3>
          <p>Trending Videos Found</p>
        </div>
        <div className="stat-item">
          <h3>{Math.round(data.averageViews / 1000)}K</h3>
          <p>Average Views</p>
        </div>
      </div>  {/* Simplified stats */}
      
      <div className="video-grid">
        {data.trends.map((video) => (
          <div key={video.id} className={`video-card ${selectedVideoId === video.id ? 'selected' : ''}`}>
            <label className="video-selection-label">  {/* Radio label for accessibility */}
              <input
                type="radio"
                name="video-selection"  // Groups for single selection
                value={video.id}
                checked={selectedVideoId === video.id}
                onChange={() => setSelectedVideoId(video.id)}
                className="selection-radio"
                aria-label={`Select ${video.title} as topic`}
              />
              <div className="video-content">  {/* Wrap content to avoid radio interference */}
                <div className="video-thumbnail">
                  <img 
                    src={video.thumbnail} 
                    alt={`Thumbnail for ${video.title}`}
                    className="thumbnail-image"
                  />
                  <div className="video-duration">{video.duration}</div>
                </div>
                <div className="video-info">
                  <h3 className="video-title">{video.title}</h3>
                  <p className="video-description truncate">  {/* Truncated for list view */}
                    {video.description?.substring(0, 100)}...  {/* Show partial description */}
                  </p>
                  <p className="channel-name">{video.channel}</p>
                  <div className="video-stats">
                    <span className="stat">{video.views} views</span>
                    {/* Add likes/comments if needed */}
                  </div>
                  <div className="video-tags">
                    <h4>Hashtags:</h4>
                    <div className="tags-container">
                      {video.tags?.slice(0, 3).map((tag, index) => (  // Show first 3 in list
                        <span key={index} className="tag">{tag}</span>
                      )) || <span>No tags</span>}
                    </div>
                  </div>
                </div>
                <button 
                  className="view-more-button"
                  onClick={() => {/* Open modal logic here if needed */}}  // Optional: Trigger modal
                  aria-label={`View full details for ${video.title}`}
                >
                  View More
                </button>
              </div>
            </label>
          </div>
        ))}
      </div>

      {/* Bottom Topic Input Form */}
      <form onSubmit={handleGenerate} className="topic-form">
        <div className="input-container">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter your topic for story generation (e.g., 'A fitness journey for beginners')"
            className="topic-input"
            disabled={loading}
            aria-label="Custom topic input for LLM story"
          />
          <button 
            type="submit" 
            className="generate-button"
            disabled={!selectedVideoId || !topic.trim() || loading}
          >
            {loading ? 'Generating...' : 'Generate Story & Frames'}
          </button>
        </div>
        {error && <p className="error-message" role="alert">{error}</p>}
        {selectedVideoId && (
          <p className="selection-info">
            Selected: <strong>{selectedVideo.title}</strong> as base topic.
          </p>
        )}
      </form>

      {/* Optional Modal for Full Details - Triggered by View More if needed */}
      {false && selectedVideo && (  // Placeholder; implement if keeping modal
        <div className="modal-overlay" onClick={() => setSelectedVideoId(null)}>  // Reuse selection state
          {/* Modal content similar to original, with ARIA */}
        </div>
      )}
    </div>
  );
};

export default ResultsScreen;