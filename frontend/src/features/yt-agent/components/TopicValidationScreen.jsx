import React, { useState, useEffect } from 'react';
import '../styles/components/TopicValidationScreen.css';

const TopicValidationScreen = ({
  topic,
  onTopicChange,
  onValidate,
  validationResult,
  onProceed,
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
        <h2>Topic Selection & Validation</h2>
        <p className="screen-subtitle">
          Enter your topic and our AI will validate it for YouTube Shorts.
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
            Our AI will analyze your topic for clarity, engagement potential, and policy compliance.
          </p>
        </div>

        <button
          className="validate-btn"
          onClick={handleValidate}
          disabled={loading || !localTopic.trim()}
        >
          {loading ? (
            <>
              <span className="loading-spinner-small"></span>
              Analyzing with AI...
            </>
          ) : (
            '🤖 Validate with AI'
          )}
        </button>
      </div>

      {validationResult && (
        <div className={`validation-result ${validationResult.valid ? 'valid' : 'invalid'}`}>
          <div className="validation-header">
            <span className="validation-icon">
              {validationResult.valid ? '✓' : '✗'}
            </span>
            <div className="validation-title">
              <h3>
                {validationResult.valid
                  ? 'Topic Approved!'
                  : 'Topic Needs Improvement'}
              </h3>
              {validationResult.score !== undefined && (
                <span className={`validation-score ${validationResult.score >= 70 ? 'good' : 'low'}`}>
                  Quality Score: {validationResult.score}/100
                </span>
              )}
            </div>
          </div>

          {/* AI Analysis Section */}
          {validationResult.reason && (
            <div className="ai-analysis-card">
              <div className="ai-analysis-header">
                <span className="ai-icon">🤖</span>
                <span>AI Analysis</span>
              </div>
              <p className="ai-analysis-text">{validationResult.reason}</p>
            </div>
          )}

          {/* Issues Section - Only for invalid topics */}
          {!validationResult.valid && validationResult.issues && validationResult.issues.length > 0 && (
            <div className="feedback-card issues-card">
              <h4><span className="card-icon">⚠️</span> Issues Found</h4>
              <ul>
                {validationResult.issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggestions Section */}
          {validationResult.suggestions && validationResult.suggestions.length > 0 && (
            <div className="feedback-card suggestions-card">
              <h4><span className="card-icon">💡</span> Suggestions to Improve</h4>
              <ul>
                {validationResult.suggestions.map((suggestion, idx) => (
                  <li key={idx}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Action Buttons */}
          <div className="validation-actions">
            {validationResult.valid ? (
              <button className="proceed-btn" onClick={onProceed}>
                Continue to Creative Direction →
              </button>
            ) : (
              <p className="retry-hint">
                Please update your topic based on the suggestions above and try again.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TopicValidationScreen;
