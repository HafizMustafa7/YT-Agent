import React, { useState } from 'react';
import '../styles/components/CreativeFormScreen.css';

const CREATIVE_OPTIONS = {
  tone: [
    'dynamic',
    'motivational',
    'humorous',
    'dramatic',
    'cinematic',
    'documentary',
    'educational',
    'inspirational',
    'mysterious',
    'heartwarming',
  ],
  target_audience: [
    'General',
    'Gen Z (18-24)',
    'Millennials (25-40)',
    'Gen X (41-56)',
    'Teens (13-17)',
    'Young Adults (18-25)',
    'Adults (26-45)',
    'Seniors (55+)',
    'Content Creators',
    'Entrepreneurs',
    'Students',
    'Fitness Enthusiasts',
  ],
  visual_style: [
    'cinematic realism',
    'animated cartoon',
    'documentary style',
    'surreal artistic',
    'minimalist clean',
    'vibrant colorful',
    'dark moody',
    'bright studio',
    'nature documentary',
    'urban street',
    'futuristic sci-fi',
    'vintage retro',
  ],
  camera_movement: [
    'smooth tracking',
    'dynamic handheld',
    'static shot',
    'push-in zoom',
    'pull-out zoom',
    'pan left',
    'pan right',
    'tilt up',
    'tilt down',
    'aerial drone',
    'whip pan',
    'dolly forward',
    'dolly backward',
    'circular orbit',
  ],
  effects: [
    'subtle transitions',
    'glitch overlays',
    'light leaks',
    'grain texture',
    'color grading',
    'motion blur',
    'depth of field',
    'lens flares',
    'particle effects',
    'kinetic typography',
    'split screen',
    'time remapping',
  ],
  story_format: [
    'narrative',
    'educational',
    'documentary',
    'tutorial',
    'review',
    'comparison',
    'storytelling',
    'interview',
    'vlog style',
    'cinematic',
  ],
  duration_seconds: [
    20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120
  ],
};

const CreativeFormScreen = ({ onSubmit, onBack, loading }) => {
  const [formData, setFormData] = useState({
    tone: CREATIVE_OPTIONS.tone[0],
    target_audience: CREATIVE_OPTIONS.target_audience[0],
    visual_style: CREATIVE_OPTIONS.visual_style[0],
    camera_movement: CREATIVE_OPTIONS.camera_movement[0],
    effects: CREATIVE_OPTIONS.effects[0],
    story_format: CREATIVE_OPTIONS.story_format[0],
    duration_seconds: CREATIVE_OPTIONS.duration_seconds[4], // Default 60 seconds
    constraints: [],
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="creative-form-screen">
      <div className="creative-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <h2>Creative Direction</h2>
        <p className="screen-subtitle">
          Configure your video's creative style and direction using the dropdowns below.
        </p>
      </div>

      <form className="creative-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="tone">Tone / Style</label>
            <select
              id="tone"
              value={formData.tone}
              onChange={(e) => handleChange('tone', e.target.value)}
              className="form-select"
            >
              {CREATIVE_OPTIONS.tone.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="target_audience">Target Audience</label>
            <select
              id="target_audience"
              value={formData.target_audience}
              onChange={(e) => handleChange('target_audience', e.target.value)}
              className="form-select"
            >
              {CREATIVE_OPTIONS.target_audience.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="visual_style">Visual Style</label>
            <select
              id="visual_style"
              value={formData.visual_style}
              onChange={(e) => handleChange('visual_style', e.target.value)}
              className="form-select"
            >
              {CREATIVE_OPTIONS.visual_style.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="camera_movement">Camera Movement</label>
            <select
              id="camera_movement"
              value={formData.camera_movement}
              onChange={(e) => handleChange('camera_movement', e.target.value)}
              className="form-select"
            >
              {CREATIVE_OPTIONS.camera_movement.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="effects">Effects Style</label>
            <select
              id="effects"
              value={formData.effects}
              onChange={(e) => handleChange('effects', e.target.value)}
              className="form-select"
            >
              {CREATIVE_OPTIONS.effects.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="story_format">Story Format</label>
            <select
              id="story_format"
              value={formData.story_format}
              onChange={(e) => handleChange('story_format', e.target.value)}
              className="form-select"
            >
              {CREATIVE_OPTIONS.story_format.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="duration_seconds">Video Duration</label>
            <select
              id="duration_seconds"
              value={formData.duration_seconds}
              onChange={(e) => handleChange('duration_seconds', parseInt(e.target.value))}
              className="form-select"
            >
              {CREATIVE_OPTIONS.duration_seconds.map((duration) => (
                <option key={duration} value={duration}>
                  {duration}s ({Math.floor(duration / 60)}:{(duration % 60).toString().padStart(2, '0')})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-actions">
          <button type="button" className="cancel-btn" onClick={onBack}>
            Cancel
          </button>
          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? 'Generating Story...' : 'Generate Story & Frames'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreativeFormScreen;

