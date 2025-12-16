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

// Export all services as default object
const apiService = {
    fetchTrends,
    validateTopic,
    generateStory,
    checkHealth,
};

export default apiService;
