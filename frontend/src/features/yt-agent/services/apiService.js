/**
 * API Service - Centralized API communication layer
 * Handles all backend API calls with proper error handling and timeouts
 */

import { API_BASE_URL, ENDPOINTS, TIMEOUTS } from '../config/constants';
import { supabase } from '../../../supabaseClient';

const buildApiUrl = (endpoint) => {
    const safeBase = (API_BASE_URL || '').replace(/\/+$/, '');
    const safeEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return safeBase ? `${safeBase}${safeEndpoint}` : safeEndpoint;
};

/**
 * Generic API call function
 * @param {string} endpoint - API endpoint path
 * @param {object} payload - Request payload
 * @param {number} timeout - Request timeout in milliseconds
 * @param {string} method - HTTP method (default: 'POST')
 * @returns {Promise<object>} - API response data
 */
const callApi = async (endpoint, payload, timeout = TIMEOUTS.DEFAULT, method = 'POST') => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    // Get current session for token
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    try {
        const response = await fetch(buildApiUrl(endpoint), {
            method,
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            },
            body: JSON.stringify(payload),
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            let message = `Request failed with status ${response.status}`;

            if (Array.isArray(errorData.detail)) {
                // FastAPI/Pydantic validation errors (422) arrive as an array.
                message = errorData.detail
                    .map((d) => `${(d.loc || []).join('.')} - ${d.msg}`)
                    .join(' | ');
            } else if (typeof errorData.detail === 'string' && errorData.detail.trim()) {
                message = errorData.detail;
            }

            throw new Error(message);
        }

        return response.json();
    } catch (error) {
        clearTimeout(timeoutId);

        if (error.name === 'AbortError') {
            throw new Error('Request timed out. Please try again.');
        }

        throw error;
    }
};

/**
 * Generic API GET call function
 * @param {string} endpoint - API endpoint path
 * @param {number} timeout - Request timeout in milliseconds
 * @returns {Promise<object>} - API response data
 */
const callApiGet = async (endpoint, timeout = TIMEOUTS.DEFAULT) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    // Get current session for token
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    try {
        const response = await fetch(buildApiUrl(endpoint), {
            headers: {
                ...(token && { 'Authorization': `Bearer ${token}` })
            },
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Request failed with status ${response.status}`);
        }

        return response.json();
    } catch (error) {
        clearTimeout(timeoutId);

        if (error.name === 'AbortError') {
            throw new Error('Request timed out. Please try again.');
        }

        throw error;
    }
};

/**
 * Fetch trending videos
 * @param {string} mode - 'search_trends' or 'analyze_niche'
 * @param {string|null} niche - Niche to analyze (required for analyze_niche mode)
 * @returns {Promise<object>} - Trends data
 */
export const fetchTrends = async (mode, niche = null) => {
    return callApi(ENDPOINTS.FETCH_TRENDS, { mode, niche });
};

/**
 * Validate a topic
 * @param {string} topic - Topic to validate
 * @param {string|null} nicheHint - Optional niche hint for context
 * @returns {Promise<object>} - Validation result
 */
export const validateTopic = async (topic, nicheHint = null) => {
    return callApi(ENDPOINTS.VALIDATE_TOPIC, {
        topic: topic.trim(),
        niche_hint: nicheHint,
    });
};

/**
 * Suggest topics based on trending YouTube Shorts in a niche
 * @param {string} niche - Content niche to analyse
 * @param {string} mode  - 'search_trends' | 'analyze_niche'
 * @param {number} minEngagement - Minimum engagement ratio (default 0.01)
 * @param {number} topN - Number of suggestions to return (default 5)
 * @returns {Promise<object>} - { success, niche, topics, trends_analysed }
 */
export const suggestTopics = async (niche, mode = 'search_trends', minEngagement = 0.01, topN = 5) => {
    return callApi(
        ENDPOINTS.SUGGEST_TOPICS,
        { niche: niche.trim(), mode, min_engagement: minEngagement, top_n: topN },
        TIMEOUTS.TOPIC_SUGGESTION
    );
};

/**
 * Generate story and frames
 * @param {string} topic - Topic for the story
 * @param {object} selectedVideo - Selected video data
 * @param {object} creativePreferences - Creative direction preferences
 * @returns {Promise<object>} - Generated story with frames
 */
export const generateStory = async (topic, selectedVideo, creativePreferences) => {
    return callApi(
        ENDPOINTS.GENERATE_STORY,
        {
            topic,
            selected_video: selectedVideo,
            creative_preferences: creativePreferences,
        },
        TIMEOUTS.STORY_GENERATION
    );
};

/**
 * Check API health
 * @returns {Promise<object>} - Health status
 */
export const checkHealth = async () => {
    return callApiGet(ENDPOINTS.HEALTH);
};

/**
 * Create video project from story frames (for Video Gen dashboard)
 * @param {string} title - Project/story title
 * @param {Array<{frame_num, ai_video_prompt, scene_description?, duration_seconds?}>} frames
 * @param {string} [channelId] - Optional YouTube channel ID
 * @param {string} [aspectRatio] - Aspect ratio for Veo generation (default '9:16' for Shorts)
 * @param {string} [resolution] - Video resolution (default '720p')
 * @returns {Promise<object>} - { project_id, total_frames }
 */
export const createVideoProject = async (title, frames, channelId, aspectRatio = '9:16', resolution = '720p') => {
    return callApi(
        ENDPOINTS.VIDEO_CREATE_PROJECT,
        { title, frames, channel_id: channelId, aspect_ratio: aspectRatio, resolution },
        TIMEOUTS.VIDEO_OPERATION
    );
};

/**
 * Get video project with frames and assets
 * @param {string} projectId - UUID
 * @returns {Promise<object>} - { project }
 */
export const getVideoProject = async (projectId) => {
    return callApiGet(
        ENDPOINTS.VIDEO_GET_PROJECT(projectId),
        TIMEOUTS.VIDEO_OPERATION
    );
};

/**
 * Get all video projects for the current user
 * @returns {Promise<object>} - { projects: Array }
 */
export const getUserProjects = async () => {
    return callApiGet(
        '/api/v1/video/projects',
        TIMEOUTS.VIDEO_OPERATION
    );
};

/**
 * Start generating all pending frames sequentially via Veo 3.1
 * @param {string} projectId
 * @returns {Promise<object>}
 */
export const startGenerateAllFrames = async (projectId) => {
    const result = await callApi(
        ENDPOINTS.VIDEO_GENERATE_ALL(projectId),
        {},
        TIMEOUTS.VIDEO_OPERATION
    );
    if (result.success) {
        window.dispatchEvent(new CustomEvent('creditsConsumed'));
    }
    return result;
};

/**
 * Generate a single frame
 * @param {string} projectId
 * @param {string} frameId - UUID of project_frames row
 * @returns {Promise<object>}
 */
export const startGenerateFrame = async (projectId, frameId) => {
    const result = await callApi(
        ENDPOINTS.VIDEO_GENERATE_FRAME(projectId),
        { frame_id: frameId },
        TIMEOUTS.VIDEO_OPERATION
    );
    if (result.success) {
        window.dispatchEvent(new CustomEvent('creditsConsumed'));
    }
    return result;
};

/**
 * Update a single frame's AI video prompt
 * @param {string} projectId 
 * @param {string} frameId 
 * @param {string} prompt 
 * @returns {Promise<object>}
 */
export const updateFramePrompt = async (projectId, frameId, prompt) => {
    return callApi(
        ENDPOINTS.VIDEO_UPDATE_FRAME_PROMPT(projectId, frameId),
        { prompt },
        TIMEOUTS.VIDEO_OPERATION,
        'PATCH'
    );
};

/**
 * Promote the final Veo-generated video to permanent R2 storage.
 * No stitching needed — Veo extend returns the fully merged video on each call.
 * @param {string} projectId
 * @returns {Promise<object>}
 */
export const combineVideoProject = async (projectId) => {
    return callApi(
        ENDPOINTS.VIDEO_COMBINE(projectId),
        {},
        TIMEOUTS.VIDEO_OPERATION
    );
};

/**
 * Fetch all channels for analysis
 * @returns {Promise<object>} - { channels, count }
 */
export const getChannelsForAnalysis = async () => {
    return callApiGet(ENDPOINTS.ANALYSIS_CHANNELS);
};

/**
 * Fetch analytics for a specific channel
 * @param {string} channelId
 * @returns {Promise<object>} - Analytics data
 */
export const getChannelAnalytics = async (channelId) => {
    return callApiGet(ENDPOINTS.ANALYSIS_ANALYTICS(channelId));
};

/**
 * Fetch the current user's credit balance
 */
export const getUserCredits = async () => {
    return callApiGet('/api/user/credits');
};

/**
 * List all YouTube channels for the authenticated user
 */
export const listChannels = async () => {
    return callApiGet(ENDPOINTS.CHANNELS_LIST);
};

/**
 * Get stats for a specific channel
 */
export const getChannelStats = async (channelId) => {
    return callApiGet(ENDPOINTS.CHANNELS_STATS(channelId));
};

/**
 * Start YouTube OAuth flow
 */
export const startYouTubeOAuth = async () => {
    return callApiGet(ENDPOINTS.CHANNELS_OAUTH);
};

/**
 * Upload the combined video to the linked YouTube channel
 * @param {string} projectId
 * @returns {Promise<object>}
 */
export const uploadProjectToYoutube = async (projectId, customTitle = null) => {
    const payload = customTitle ? { custom_title: customTitle } : {};
    return callApi(
        ENDPOINTS.VIDEO_UPLOAD(projectId),
        payload,
        TIMEOUTS.VIDEO_OPERATION
    );
};

// Export all services as default object
const apiService = {
    fetchTrends,
    validateTopic,
    suggestTopics,
    generateStory,
    checkHealth,
    createVideoProject,
    getVideoProject,
    getUserProjects,
    startGenerateAllFrames,
    startGenerateFrame,
    combineVideoProject,
    uploadProjectToYoutube,
    getChannelsForAnalysis,
    getChannelAnalytics,
    listChannels,
    getChannelStats,
    startYouTubeOAuth,
    getUserCredits,
};

export default apiService;
