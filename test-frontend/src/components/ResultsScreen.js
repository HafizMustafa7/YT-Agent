// frontend/src/components/ResultsScreen.js
import React, { useState } from 'react';
import './ResultsScreen.css';

const ResultsScreen = ({ data, onBack }) => {
  const [selectedVideo, setSelectedVideo] = useState(null);

  if (!data || !data.trends) {
    return (
      <div className="results-container">
        <div className="results-header">
          <h2>No Data Available</h2>
          <button className="back-button" onClick={onBack}>
            Back to Search
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>Trending Videos in "{data.niche}"</h2>
        <button className="back-button" onClick={onBack}>
          Back to Search
        </button>
      </div>
      
      <div className="stats-summary">
        <div className="stat-item">
          <h3>{data.trends.length}</h3>
          <p>Trending Videos Found</p>
        </div>
        <div className="stat-item">
          <h3>{Math.round(data.averageViews / 1000)}K</h3>
          <p>Average Views</p>
        </div>
        <div className="stat-item">
          <h3>{Math.round(data.averageLikes / 1000)}K</h3>
          <p>Average Likes</p>
        </div>
      </div>
      
      <div className="video-grid">
        {data.trends.map((video, index) => (
          <div 
            key={index} 
            className="video-card"
            onClick={() => setSelectedVideo(video)}
          >
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
              <p className="channel-name">{video.channel}</p>
              <div className="video-stats">
                <span className="stat">{video.views} views</span>
                <span className="stat">{video.likes} likes</span>
                <span className="stat">{video.comments} comments</span>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {selectedVideo && (
        <div className="modal-overlay" onClick={() => setSelectedVideo(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button 
              className="modal-close"
              onClick={() => setSelectedVideo(null)}
            >
              ×
            </button>
            <h2>{selectedVideo.title}</h2>
            <p className="channel-name">{selectedVideo.channel}</p>
            <div className="modal-stats">
              <span>{selectedVideo.views} views</span>
              <span>{selectedVideo.likes} likes</span>
              <span>{selectedVideo.comments} comments</span>
              <span>{selectedVideo.duration}</span>
            </div>
            <div className="modal-description">
              <h4>Description</h4>
              <p>{selectedVideo.description}</p>
            </div>
            <div className="modal-tags">
              <h4>Tags</h4>
              <div className="tags-container">
                {selectedVideo.tags.map((tag, index) => (
                  <span key={index} className="tag">{tag}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsScreen;