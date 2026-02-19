import React, { useState } from 'react';
import { useSelectedChannel } from '../../../contexts/SelectedChannelContext';
import '../styles/components/StoryResultsScreen.css';
const StoryResultsScreen = ({ storyResult, topic, onGenerateVideo }) => {
  const { channels, selectedChannelId: selectedChannel, loading: loadingChannels } = useSelectedChannel();
  const [expandedFrame, setExpandedFrame] = useState(null);
  const [copiedFrame, setCopiedFrame] = useState(null);
  const [videoCreating, setVideoCreating] = useState(false);

  const story = storyResult?.story || {};
  const frames = story?.frames || [];

  const handleGenerateVideo = async () => {
    if (!onGenerateVideo || frames.length === 0) return;
    if (!selectedChannel) {
      alert("Please select a YouTube channel first.");
      return;
    }
    setVideoCreating(true);
    try {
      await onGenerateVideo(storyResult, selectedChannel);
    } finally {
      setVideoCreating(false);
    }
  };

  const copyToClipboard = (text, frameNum) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedFrame(frameNum);
      setTimeout(() => setCopiedFrame(null), 2000);
    }).catch(err => {
      console.error('Failed to copy text: ', err);
      alert('Could not copy text. Please try selecting and copying manually.');
    });
  };

  const formatJSON = (obj) => {
    return JSON.stringify(obj, null, 2);
  };

  return (
    <div className="story-results-screen">
      <div className="story-header">
        <h2>Generated Story & Frames</h2>
        <p className="screen-subtitle">Your complete storyboard with AI video generation prompts</p>
      </div>

      {story.title && (
        <div className="story-info-card">
          <h3 className="story-title">{story.title}</h3>
          {topic && (
            <p className="story-topic"><strong>Topic:</strong> {topic}</p>
          )}
          {story.metadata && (
            <div className="story-metadata">
              <span>Frames: {story.metadata.total_frames}</span>
              <span>Duration: {story.metadata.estimated_duration}s</span>
              {story.metadata.target_duration && (
                <span>Target: {story.metadata.target_duration}</span>
              )}
            </div>
          )}
        </div>
      )}

      {story.full_story && (
        <div className="story-section">
          <h3>Full Story</h3>
          <div className="story-content">
            {story.full_story.split('\n').map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </div>
        </div>
      )}

      <div className="frames-section">
        <h3>Frame-by-Frame Prompts</h3>
        <p className="section-description">
          Each frame includes a JSON object with the AI video generation prompt and creative modules.
          Click "Copy JSON" to use these prompts with AI video tools.
        </p>

        {frames.length === 0 && (
          <div className="empty-state">
            <p>No frames generated. Please try again.</p>
          </div>
        )}

        {frames.map((frame, idx) => {
          const frameJson = {
            frame_num: frame.frame_num || idx + 1,
            duration_seconds: frame.duration_seconds,
            scene_description: frame.scene_description,
            ai_video_prompt: frame.ai_video_prompt,
            narration_text: frame.narration_text || '',
            transition: frame.transition || '',
            creative_modules: frame.creative_modules || {},
          };

          const isExpanded = expandedFrame === frame.frame_num;
          const isCopied = copiedFrame === frame.frame_num;

          return (
            <div key={idx} className="frame-card">
              <div className="frame-header" onClick={() => setExpandedFrame(isExpanded ? null : frame.frame_num)}>
                <div className="frame-number">Frame {frame.frame_num || idx + 1}</div>
                <div className="frame-duration">{frame.duration_seconds}s</div>
                <button className="expand-btn">
                  {isExpanded ? '▼' : '▶'}
                </button>
              </div>

              <div className="frame-description">
                <strong>Scene:</strong> {frame.scene_description}
              </div>

              {isExpanded && (
                <div className="frame-details">
                  {frame.narration_text && (
                    <div className="frame-narration">
                      <strong>Narration:</strong> {frame.narration_text}
                    </div>
                  )}

                  <div className="frame-prompt-section">
                    <div className="prompt-header">
                      <strong>AI Video Prompt:</strong>
                      <button
                        className="copy-btn"
                        onClick={() => copyToClipboard(formatJSON(frameJson), frame.frame_num)}
                      >
                        {isCopied ? '✓ Copied!' : 'Copy JSON'}
                      </button>
                    </div>
                    <div className="prompt-text">
                      {frame.ai_video_prompt}
                    </div>
                  </div>

                  {frame.creative_modules && Object.keys(frame.creative_modules).length > 0 && (
                    <div className="creative-modules-section">
                      <strong>Creative Modules:</strong>
                      <div className="creative-modules-grid">
                        {Object.entries(frame.creative_modules).map(([key, value]) => (
                          <div key={key} className="creative-module-item">
                            <span className="module-key">{key.replace(/_/g, ' ')}:</span>
                            <span className="module-value">{value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="frame-json-section">
                    <div className="json-header">
                      <strong>Complete JSON Format:</strong>
                      <button
                        className="copy-btn"
                        onClick={() => copyToClipboard(formatJSON(frameJson), `json-${frame.frame_num}`)}
                      >
                        {copiedFrame === `json-${frame.frame_num}` ? '✓ Copied!' : 'Copy JSON'}
                      </button>
                    </div>
                    <pre className="json-display">{formatJSON(frameJson)}</pre>
                  </div>

                  {frame.transition && (
                    <div className="frame-transition">
                      <strong>Transition:</strong> {frame.transition}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {frames.length > 0 && onGenerateVideo && (
        <div className="generate-video-actions">
          {/* Selected Channel Display (read-only — selected on Dashboard) */}
          <div className="channel-selector-container">
            <label>Uploading to YouTube Channel:</label>
            {loadingChannels ? (
              <span className="loading-text">Loading channel info...</span>
            ) : selectedChannel ? (
              <div className="selected-channel-badge">
                {channels.find(c => c.channel_id === selectedChannel || c.id === selectedChannel)?.channel_name ||
                  channels.find(c => c.channel_id === selectedChannel || c.id === selectedChannel)?.snippet?.title ||
                  selectedChannel}
                <span className="channel-badge-check">✓</span>
              </div>
            ) : (
              <p className="no-channels-hint">
                No channel selected. Please <a href="/dashboard">go to Dashboard</a> and select a channel first.
              </p>
            )}
          </div>

          <button
            type="button"
            className="generate-video-btn"
            onClick={handleGenerateVideo}
            disabled={videoCreating || !selectedChannel}
          >
            {videoCreating ? 'Creating project…' : 'Generate Video → Open Video Gen Dashboard'}
          </button>
          <p className="generate-video-hint">
            Creates a video project and opens the dashboard to generate clips per frame or all at once, then compile.
          </p>
        </div>
      )}
    </div>
  );
};

export default StoryResultsScreen;

