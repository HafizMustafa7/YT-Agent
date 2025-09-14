// frontend/src/components/ChatBot.js
import React, { useState } from 'react';
import './NicheInput.css';

const ChatBot = ({ onAnalyze, loading }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onAnalyze(inputValue);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-bubble">
        <p className="chat-text">
          Hi there! I'm your YouTube trend assistant. What niche or topic would you like me to 
          analyze for trending video ideas? For example, you could enter "fitness", "cooking", 
          "tech reviews", or any topic you're interested in.
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="chat-form">
        <div className="input-container">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter your niche (e.g., cooking, fitness, tech)"
            className="input-field"
            disabled={loading}
          />
          <button 
            type="submit" 
            className="submit-button"
            disabled={loading}
          >
            {loading ? 'Analyzing...' : 'Analyze Trends'}
          </button>
        </div>
      </form>
      
      {loading && (
        <div className="loading">
          <div className="loading-spinner"></div>
        </div>
      )}
    </div>
  );
};

export default ChatBot;