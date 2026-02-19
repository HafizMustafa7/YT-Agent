/**
 * API Service - Centralized API communication layer
 * Handles all backend API calls with proper error handling and timeouts
 */

import { API_BASE_URL, ENDPOINTS, TIMEOUTS } from '../config/constants';
import { supabase } from '../../../supabaseClient';

/**
 * Generic API POST call function
 * @param {string} endpoint - API endpoint path
 * @param {object} payload - Request payload
 * @param {number} timeout - Request timeout in milliseconds
 * @returns {Promise<object>} - API response data
 */
const callApi = async (endpoint, payload, timeout = TIMEOUTS.DEFAULT) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    // Get current session for token
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
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
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
 * @returns {Promise<object>} - { project_id, total_frames }
 */
export const createVideoProject = async (title, frames, channelId) => {
    return callApi(
        ENDPOINTS.VIDEO_CREATE_PROJECT,
        { title, frames, channel_id: channelId },
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
 * Start generating all pending frames (Sora)
 * @param {string} projectId
 * @returns {Promise<object>}
 */
export const startGenerateAllFrames = async (projectId) => {
    return callApi(
        ENDPOINTS.VIDEO_GENERATE_ALL(projectId),
        {},
        TIMEOUTS.VIDEO_OPERATION
    );
};

/**
 * Generate a single frame
 * @param {string} projectId
 * @param {string} frameId - UUID of project_frames row
 * @returns {Promise<object>}
 */
export const startGenerateFrame = async (projectId, frameId) => {
    return callApi(
        ENDPOINTS.VIDEO_GENERATE_FRAME(projectId),
        { frame_id: frameId },
        TIMEOUTS.VIDEO_OPERATION
    );
};

/**
 * Combine all completed clips into one video
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
export const uploadProjectToYoutube = async (projectId) => {
    return callApi(
        ENDPOINTS.VIDEO_UPLOAD(projectId),
        {},
        TIMEOUTS.VIDEO_OPERATION
    );
};

// Export all services as default object
const apiService = {
    fetchTrends,
    validateTopic,
    generateStory,
    checkHealth,
    createVideoProject,
    getVideoProject,
    startGenerateAllFrames,
    startGenerateFrame,
    combineVideoProject,
    uploadProjectToYoutube,
    getChannelsForAnalysis,
    getChannelAnalytics,
    listChannels,
    getChannelStats,
    startYouTubeOAuth,
};

export default apiService;
