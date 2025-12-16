import React, { useState } from 'react';
import Header from './components/Header';
import HomeScreen from './components/HomeScreen';
import TrendsScreen from './components/TrendsScreen';
import TopicValidationScreen from './components/TopicValidationScreen';
import CreativeFormScreen from './components/CreativeFormScreen';
import StoryResultsScreen from './components/StoryResultsScreen';
import apiService from './services/apiService';
import './styles/App.css';

function App() {
  const [currentScreen, setCurrentScreen] = useState('home');
  const [trendsData, setTrendsData] = useState(null);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [topicInput, setTopicInput] = useState('');
  const [validationResult, setValidationResult] = useState(null);
  const [storyResult, setStoryResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // API calls now handled by apiService

  const handleFetchTrends = async (mode, niche = null) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.fetchTrends(mode, niche);
      setTrendsData(data);
      setCurrentScreen('trends');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectVideo = (video) => {
    setSelectedVideo(video);
    setTopicInput(video.title);
    setValidationResult(null);
    setCurrentScreen('topic');
  };

  const handleValidateTopic = async () => {
    if (!topicInput.trim()) {
      setError('Please enter a topic.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.validateTopic(
        topicInput.trim(),
        selectedVideo?.title
      );
      setValidationResult(result);
      // Auto-proceed if valid
      if (result.valid) {
        setTimeout(() => {
          setCurrentScreen('creative');
        }, 1000);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitCreative = (preferences) => {
    setCurrentScreen('generating');
    generateStory(preferences);
  };

  const generateStory = async (preferences) => {
    setLoading(true);
    setError(null);
    try {
      // Create a dummy video object if no video was selected (custom topic)
      const videoData = selectedVideo || {
        id: 'custom',
        title: topicInput,
        description: '',
        views: 0,
        likes: 0,
        tags: [],
        ai_confidence: 0,
      };

      const result = await apiService.generateStory(
        validationResult?.normalized?.normalized || topicInput,
        videoData,
        preferences
      );
      setStoryResult(result);
      setCurrentScreen('story');
    } catch (err) {
      setError(err.message);
      setCurrentScreen('creative');
    } finally {
      setLoading(false);
    }
  };

  const resetApp = () => {
    setCurrentScreen('home');
    setTrendsData(null);
    setSelectedVideo(null);
    setTopicInput('');
    setValidationResult(null);
    setStoryResult(null);
    setError(null);
  };

  return (
    <div className="App">
      <Header />

      {error && (
        <div className="global-error" role="alert">
          <div className="error-content">
            <span className="error-icon">⚠️</span>
            <p>{error}</p>
          </div>
          <button onClick={() => setError(null)} className="error-dismiss">×</button>
        </div>
      )}

      {loading && currentScreen === 'generating' && (
        <div className="global-loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner-large"></div>
            <p>Generating your story and frames...</p>
          </div>
        </div>
      )}

      {currentScreen === 'home' && (
        <HomeScreen
          onAnalyzeTrends={() => handleFetchTrends('search_trends')}
          onSearchNiche={(niche) => handleFetchTrends('analyze_niche', niche)}
          loading={loading}
        />
      )}

      {currentScreen === 'trends' && trendsData && (
        <TrendsScreen
          trendsData={trendsData}
          onSelectVideo={handleSelectVideo}
          onCustomTopic={(topic) => {
            setTopicInput(topic);
            setSelectedVideo(null);
            setValidationResult(null);
            setCurrentScreen('topic');
          }}
          onBack={resetApp}
          loading={loading}
        />
      )}

      {currentScreen === 'topic' && topicInput && (
        <TopicValidationScreen
          topic={topicInput}
          onTopicChange={setTopicInput}
          onValidate={handleValidateTopic}
          validationResult={validationResult}
          onBack={() => setCurrentScreen('trends')}
          loading={loading}
        />
      )}

      {currentScreen === 'creative' && validationResult && (
        <CreativeFormScreen
          onSubmit={handleSubmitCreative}
          onBack={() => setCurrentScreen('topic')}
          loading={loading}
        />
      )}

      {currentScreen === 'story' && storyResult && (
        <StoryResultsScreen
          storyResult={storyResult}
          topic={validationResult?.normalized?.normalized || topicInput}
          onBack={resetApp}
        />
      )}
    </div>
  );
}

export default App;
