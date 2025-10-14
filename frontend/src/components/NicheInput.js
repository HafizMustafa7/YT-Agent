// frontend/src/components/NicheInput.js  // Suggested file name
import React, { useState } from 'react';
import './NicheInput.css';  // Assuming this CSS file exists and styles the classes

const NicheInput = ({ onAnalyze, loading }) => {  // Renamed from ChatBot for clarity
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onAnalyze(inputValue.trim());  // Trim here too for consistency
    }
  };

  return (
    <div className="chat-container" role="main">  {/* Added role for accessibility */}
      <div className="chat-bubble">
        <label htmlFor="niche-input" className="sr-only">  {/* Screen-reader only label */}
          Hi there! I'm your YouTube trend assistant. What niche or topic would you like me to 
          analyze for trending video ideas? For example, you could enter "fitness", "cooking", 
          "tech reviews", or any topic you're interested in.
        </label>
        <p className="chat-text" id="chat-instructions">  {/* Added ID for reference */}
          Hi there! I'm your YouTube trend assistant. What niche or topic would you like me to 
          analyze for trending video ideas? For example, you could enter "fitness", "cooking", 
          "tech reviews", or any topic you're interested in.
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="chat-form">
        <div className="input-container">
          <input
            id="niche-input"  // Added ID for label association
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter your niche (e.g., cooking, fitness, tech)"
            className="input-field"
            disabled={loading}
            autoFocus  // Optional: Focus on load for quicker input
            aria-describedby="chat-instructions"  // Links to instructions for screen readers
          />
          <button 
            type="submit" 
            className="submit-button"
            disabled={loading}
            aria-label={loading ? "Analyzing trends, please wait" : "Analyze trends for the entered niche"}  // Accessibility
          >
            {loading ? 'Analyzing...' : 'Analyze Trends'}
          </button>
        </div>
      </form>
      
      {loading && (
        <div className="loading" role="status" aria-live="polite">  {/* Accessibility for dynamic content */}
          <div className="loading-spinner" aria-label="Loading spinner"></div>
          <span className="sr-only">Analyzing trends...</span>  {/* Screen-reader text */}
        </div>
      )}
    </div>
  );
};

export default NicheInput;  // Renamed export