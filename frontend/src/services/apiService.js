/**
 * API Service - Centralized API communication layer
 * Handles all backend API calls with proper error handling
 */

import { API_BASE_URL, ENDPOINTS, TIMEOUTS } from '../config/constants';

/**
 * Generic API call function
 * @param {string} endpoint - API endpoint path
 * @param {object} payload - Request payload
 * @param {number} timeout - Request timeout in milliseconds
 * @returns {Promise<object>} - API response data
 */
const callApi = async (endpoint, payload, timeout = TIMEOUTS.DEFAULT) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
        TIMEOUTS.STORY_GENERATION  // Longer timeout for AI generation
    );
};

/**
 * Check API health
 * @returns {Promise<object>} - Health status
 */
export const checkHealth = async () => {
    const response = await fetch(`${API_BASE_URL}${ENDPOINTS.HEALTH}`);
    return response.json();
};

/**
 * Create video project from story frames (for Video Gen dashboard)
 * @param {string} title - Project/story title
 * @param {Array<{frame_num, ai_video_prompt, scene_description?, duration_seconds?}>} frames
 * @returns {Promise<object>} - { project_id, total_frames }
 */
export const createVideoProject = async (title, frames) => {
    const response = await fetch(`${API_BASE_URL}${ENDPOINTS.VIDEO_CREATE_PROJECT}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, frames }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
};

/**
 * Get video project with frames and assets
 * @param {string} projectId - UUID
 * @returns {Promise<object>} - { project }
 */
export const getVideoProject = async (projectId) => {
    const response = await fetch(`${API_BASE_URL}${ENDPOINTS.VIDEO_GET_PROJECT(projectId)}`);
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
};

/**
 * Start generating all pending frames (Sora)
 * @param {string} projectId
 * @returns {Promise<object>}
 */
export const startGenerateAllFrames = async (projectId) => {
    const response = await fetch(`${API_BASE_URL}${ENDPOINTS.VIDEO_GENERATE_ALL(projectId)}`, {
        method: 'POST',
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
};

/**
 * Generate a single frame
 * @param {string} projectId
 * @param {string} frameId - UUID of project_frames row
 * @returns {Promise<object>}
 */
export const startGenerateFrame = async (projectId, frameId) => {
    const response = await fetch(`${API_BASE_URL}${ENDPOINTS.VIDEO_GENERATE_FRAME(projectId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame_id: frameId }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
};

/**
 * Combine all completed clips into one video
 * @param {string} projectId
 * @returns {Promise<object>}
 */
export const combineVideoProject = async (projectId) => {
    const response = await fetch(`${API_BASE_URL}${ENDPOINTS.VIDEO_COMBINE(projectId)}`, {
        method: 'POST',
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
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
};

export default apiService;
