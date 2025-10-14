// frontend/src/components/FrameResults.js
import React, { useState } from 'react';
import './FrameResults.css';  // Assume this CSS file for styling

const FrameResults = ({ data, onBack, loading }) => {
  const [expandedFrames, setExpandedFrames] = useState({});  // Track expanded prompts per frame
  const [copiedFrame, setCopiedFrame] = useState(null);  // For copy feedback

  const toggleExpand = (frameNum) => {
    setExpandedFrames(prev => ({
      ...prev,
      [frameNum]: !prev[frameNum]
    }));
  };

  const copyToClipboard = async (prompt, frameNum) => {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(prompt);
        setCopiedFrame(frameNum);
        setTimeout(() => setCopiedFrame(null), 2000);  // Hide feedback after 2s
      } catch (err) {
        console.error('Failed to copy: ', err);
        // Fallback: Select and copy manually
        const textArea = document.createElement('textarea');
        textArea.value = prompt;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        setCopiedFrame(frameNum);
        setTimeout(() => setCopiedFrame(null), 2000);
      }
    } else {
      alert('Copy not supported; please select and copy the prompt manually.');
    }
  };

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
          <p><strong>Based on:</strong> {data.selected_video_title}</p>
          <p><strong>Your Topic:</strong> {data.user_topic}</p>
        </div>
        <button className="back-button" onClick={onBack} aria-label="Go back to video selection">
          Back to Trends
        </button>
      </div>

      {/* Full Story Section */}
      <section className="story-section" aria-labelledby="story-heading">
        <h2 id="story-heading">Full Story Script</h2>
        <div className="story-content">
          <p>{data.story}</p>  {/* Render as paragraphs; could use dangerouslySetInnerHTML if HTML-formatted */}
        </div>
        <p className="story-note">
          This story features consistent characters throughout. Use it as a base for your YouTube Short!
        </p>
      </section>

      {/* Frames Grid */}
      <section className="frames-section" aria-labelledby="frames-heading">
        <h2 id="frames-heading">Storyboard Frames ({data.frames.length} Frames)</h2>
        <p className="frames-note">
          Each frame is 3-7 seconds. Copy the prompts for AI video generation tools (e.g., RunwayML, Sora).
        </p>
        <div className="frames-grid">
          {data.frames.map((frame) => (
            <div key={frame.frame_num} className="frame-card" role="article">
              <div className="frame-header">
                <h3 className="frame-title">Frame {frame.frame_num}</h3>
                <button
                  className="expand-button"
                  onClick={() => toggleExpand(frame.frame_num)}
                  aria-expanded={expandedFrames[frame.frame_num] || false}
                  aria-label={`Toggle ${expandedFrames[frame.frame_num] ? 'collapse' : 'expand'} prompt for frame ${frame.frame_num}`}
                >
                  {expandedFrames[frame.frame_num] ? '−' : '+'}
                </button>
              </div>
              <div className="frame-description">
                <p>{frame.description}</p>
              </div>
              <div className={`frame-prompt ${expandedFrames[frame.frame_num] ? 'expanded' : 'collapsed'}`}>
                <pre>{frame.prompt}</pre>  {/* <pre> preserves formatting for prompts */}
              </div>
              <div className="frame-actions">
                <button
                  className="copy-button"
                  onClick={() => copyToClipboard(frame.prompt, frame.frame_num)}
                  aria-label={`Copy prompt for frame ${frame.frame_num}`}
                >
                  {copiedFrame === frame.frame_num ? 'Copied!' : 'Copy Prompt'}
                </button>
                {/* Optional: Placeholder for video preview */}
                <div className="frame-preview-placeholder">
                  <span>AI Video Preview Here</span>  {/* Future: Embed generated video */}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="next-steps">
        <h3>Next Steps</h3>
        <ul>
          <li>Copy prompts and generate videos using an AI tool.</li>
          <li>Edit the story if needed and regenerate frames.</li>
          <li>Upload to YouTube as a Short!</li>
        </ul>
      </div>
    </div>
  );
};

export default FrameResults;