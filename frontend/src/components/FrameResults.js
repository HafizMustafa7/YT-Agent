import React from 'react';
import './FrameResults.css';  // Assume this CSS file for styling

const FrameResults = ({ data, onBack, loading }) => {

  if (loading) {
    return (
      <div className="frame-results-container">
        <div className="loading" role="status" aria-live="polite">
          <div className="loading-spinner" aria-label="Generating frames..."></div>
          <span className="sr-only">Generating story and frames...</span>
        </div>
      </div>
    );
  }

  if (!data || !data.story || !data.frames || data.frames.length === 0) {
    return (
      <div className="frame-results-container">
        <div className="error-section">
          <h2>No Frames Generated</h2>
          <p>Something went wrong. Please try generating again.</p>
          <button className="back-button" onClick={onBack} aria-label="Go back to trends">
            Back to Trends
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="frame-results-container" role="main">
      <div className="results-header">
        <h1>Generated Story & Frames</h1>
        <div className="context-info">
          <p><strong>Based on:</strong> {data.selected_video_title || 'N/A'}</p>
          <p><strong>Your Topic:</strong> {data.user_topic || 'N/A'}</p>
          <p><strong>Enhanced Topic:</strong> {data.enhanced_topic || 'N/A'}</p>
        </div>
        <button className="back-button" onClick={onBack} aria-label="Go back to video selection">
          Back to Trends
        </button>
      </div>

      {/* Full Story Section */}
      <section className="story-section" aria-labelledby="story-heading">
        <h2 id="story-heading">Full Story Script</h2>
        <div className="story-content">
          <p>{data.story}</p>
        </div>
        <p className="story-note">
          Themes: {data.themes && Array.isArray(data.themes) ? data.themes.join(', ') : 'N/A'} | Visual Style: {data.visual_style || 'N/A'} | Emotional Tone: {data.emotional_tone || 'N/A'}
        </p>
      </section>

      {/* Frames Grid */}
      <section className="frames-section" aria-labelledby="frames-heading">
        <h2 id="frames-heading">Storyboard Frames ({data.frames.length} Frames)</h2>
        <p className="frames-note">
          Each frame is designed for 3-7 seconds. Copy the prompts for AI video generation tools.
        </p>
        <div className="frames-grid">
          {data.frames.map((frame) => (
            <div key={frame.frame_num} className="frame-card" role="article">
              <div className="frame-header">
                <h3 className="frame-title">Frame {frame.frame_num}: {frame.scene_description.substring(0, 50)}...</h3>
              </div>
              <div className="frame-description">
                <p><strong>Description:</strong> {frame.scene_description}</p>
                <p><strong>Duration:</strong> {frame.duration_seconds} seconds</p>
              </div>
              <div className="frame-prompt expanded">
                <pre><strong>AI Video Prompt:</strong> {frame.ai_video_prompt}</pre>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="next-steps">
        <h3>Next Steps</h3>
        <ul>
          <li>Use the JSON prompts to generate videos with AI tools.</li>
          <li>Upload to YouTube as a Short!</li>
        </ul>
      </div>
    </div>
  );
};

export default FrameResults;
