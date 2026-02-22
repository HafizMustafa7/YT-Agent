import React, { useState } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import Header from '../features/yt-agent/components/Header.jsx';

import ErrorBoundary from '../features/yt-agent/components/ErrorBoundary.jsx';
import HomeScreen from '../features/yt-agent/components/HomeScreen.jsx';
import TrendsScreen from '../features/yt-agent/components/TrendsScreen.jsx';
import TopicValidationScreen from '../features/yt-agent/components/TopicValidationScreen.jsx';
import CreativeFormScreen from '../features/yt-agent/components/CreativeFormScreen.jsx';
import StoryResultsScreen from '../features/yt-agent/components/StoryResultsScreen.jsx';
import VideoGenerationScreen from '../features/yt-agent/components/VideoGenerationScreen.jsx';
import FinalVideoScreen from '../features/yt-agent/components/FinalVideoScreen.jsx';
import apiService from '../features/yt-agent/services/apiService';
import PageLayout from '../components/PageLayout';
import '../features/yt-agent/styles/App.css';

function YTAgentPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const [searchParams, setSearchParams] = useSearchParams();
    const currentScreen = searchParams.get('step') || 'home';
    const [trendsData, setTrendsData] = useState(null);
    const [selectedVideo, setSelectedVideo] = useState(null);
    const [topicInput, setTopicInput] = useState('');
    const [validationResult, setValidationResult] = useState(null);
    const [storyResult, setStoryResult] = useState(null);
    const [videoProjectId, setVideoProjectId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // API calls now handled by apiService

    const handleFetchTrends = async (mode, niche = null) => {
        setLoading(true);
        setError(null);
        try {
            const data = await apiService.fetchTrends(mode, niche);
            setTrendsData(data);
            setSearchParams({ step: 'trends' });
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
        setSearchParams({ step: 'topic' });
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
            // Don't auto-proceed - let user click Proceed button
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleProceedToCreative = () => {
        if (validationResult?.valid) {
            setSearchParams({ step: 'creative' });
        }
    };

    const handleSubmitCreative = (preferences) => {
        setSearchParams({ step: 'generating' });
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
            setSearchParams({ step: 'story' });
        } catch (err) {
            setError(err.message);
            setSearchParams({ step: 'creative' });
        } finally {
            setLoading(false);
        }
    };


    const handleGenerateVideo = async (result, channelId) => {
        setError(null);
        const story = result?.story || {};
        const frames = Array.isArray(story?.frames) ? story.frames : [];
        if (frames.length === 0) {
            setError('No frames to create video project.');
            return;
        }

        const normalizeFrameNumber = (value, fallback) => {
            const n = Number.parseInt(value, 10);
            return Number.isFinite(n) && n >= 1 ? n : fallback;
        };

        const normalizeDuration = (value) => {
            const allowed = [4, 8, 12];
            const raw = Number(value);
            if (!Number.isFinite(raw)) return 8;
            return allowed.reduce((prev, curr) =>
                Math.abs(curr - raw) < Math.abs(prev - raw) ? curr : prev
            );
        };

        const normalizedFrames = frames
            .map((f, idx) => {
                const aiVideoPrompt = String(
                    f?.ai_video_prompt ?? f?.video_prompt ?? f?.prompt ?? ''
                ).trim().slice(0, 5000);

                return {
                    frame_num: normalizeFrameNumber(f?.frame_num, idx + 1),
                    ai_video_prompt: aiVideoPrompt,
                    scene_description: f?.scene_description ? String(f.scene_description) : null,
                    duration_seconds: normalizeDuration(f?.duration_seconds),
                };
            })
            // Backend requires ai_video_prompt min_length=1
            .filter((f) => f.ai_video_prompt.length > 0);

        if (normalizedFrames.length === 0) {
            setError('Generated frames are missing ai_video_prompt. Please regenerate the story.');
            return;
        }

        const normalizedTitle = String(story?.title || 'Story Video').trim();
        const payload = {
            // Backend schema: title max_length=255
            title: (normalizedTitle || 'Story Video').slice(0, 255),
            frames: normalizedFrames,
        };
        try {
            const res = await apiService.createVideoProject(payload.title, payload.frames, channelId);
            setVideoProjectId(res.project_id);
            setSearchParams({ step: 'videoGen', projectId: res.project_id });
        } catch (err) {
            setError(err.message || 'Failed to create video project. Please try again.');
        }
    };

    return (
        <ErrorBoundary>
            <PageLayout className="yt-agent-container">
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
                            setSearchParams({ step: 'topic' });
                        }}
                        loading={loading}
                    />
                )}

                {currentScreen === 'topic' && topicInput && (
                    <TopicValidationScreen
                        topic={topicInput}
                        onTopicChange={setTopicInput}
                        onValidate={handleValidateTopic}
                        validationResult={validationResult}
                        onProceed={handleProceedToCreative}
                        loading={loading}
                    />
                )}

                {currentScreen === 'creative' && validationResult && (
                    <CreativeFormScreen
                        onSubmit={handleSubmitCreative}
                        loading={loading}
                    />
                )}

                {currentScreen === 'story' && storyResult && (
                    <StoryResultsScreen
                        storyResult={storyResult}
                        topic={validationResult?.normalized?.normalized || topicInput}
                        onGenerateVideo={handleGenerateVideo}
                    />
                )}

                {(currentScreen === 'videoGen' || searchParams.get('projectId')) && (
                    <VideoGenerationScreen
                        projectId={videoProjectId || searchParams.get('projectId')}
                        onViewFinalVideo={() => setSearchParams({ step: 'finalVideo', projectId: videoProjectId || searchParams.get('projectId') })}
                    />
                )}

                {currentScreen === 'finalVideo' && (videoProjectId || searchParams.get('projectId')) && (
                    <FinalVideoScreen
                        projectId={videoProjectId || searchParams.get('projectId')}
                        onStartNew={() => navigate('/dashboard')}
                    />
                )}
            </PageLayout>
        </ErrorBoundary>
    );
}

export default YTAgentPage;
