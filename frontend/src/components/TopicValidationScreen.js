import React, { useState, useEffect } from 'react';
import './TopicValidationScreen.css';

const TopicValidationScreen = ({
  topic,
  onTopicChange,
  onValidate,
  validationResult,
  onBack,
  loading,
}) => {
  const [localTopic, setLocalTopic] = useState(topic);

  useEffect(() => {
    setLocalTopic(topic);
  }, [topic]);

  const handleTopicChange = (e) => {
    const value = e.target.value;
    setLocalTopic(value);
    onTopicChange(value);
  };

  const handleValidate = () => {
    onTopicChange(localTopic);
    onValidate();
  };

  return (
    <div className="topic-validation-screen">
      <div className="topic-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <h2>Topic Selection & Validation</h2>
        <p className="screen-subtitle">
          Select a topic from the video above, edit it, or enter your custom topic.
        </p>
      </div>

      <div className="topic-workspace">
        <div className="topic-input-section">
          <label htmlFor="topic-input">Your Topic</label>
          <textarea
            id="topic-input"
            className="topic-textarea"
            value={localTopic}
            onChange={handleTopicChange}
            placeholder="Enter or edit your topic here..."
            rows="4"
            disabled={loading}
          />
          <p className="input-hint">
            You can modify the selected video's title or write your own topic from scratch.
          </p>
        </div>

        <button
          className="validate-btn"
          onClick={handleValidate}
          disabled={loading || !localTopic.trim()}
        >
          {loading ? 'Validating...' : 'Validate Topic'}
        </button>
      </div>

      {validationResult && (
        <div className={`validation-result ${validationResult.valid ? 'valid' : 'invalid'}`}>
          <div className="validation-header">
            <span className="validation-icon">
              {validationResult.valid ? '✓' : '✗'}
            </span>
            <h3>
              {validationResult.valid
                ? 'Topic is Valid!'
                : 'Topic Validation Failed'}
            </h3>
          </div>
          
          <p className="validation-message">
            {validationResult.message || validationResult.reason}
          </p>

          {validationResult.valid && (
            <div className="validation-actions">
              <p className="success-message">
                ✓ Topic validated successfully! You can proceed to Creative Direction.
              </p>
            </div>
          )}

          {!validationResult.valid && validationResult.violations && (
            <div className="violations-list">
              <h4>Issues found:</h4>
              <ul>
                {validationResult.violations.map((violation, idx) => (
                  <li key={idx}>{violation}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TopicValidationScreen;

