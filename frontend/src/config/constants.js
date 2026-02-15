/**
 * Application constants and configuration
 */

// API Configuration
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
export const API_VERSION = 'v1';
export const API_PREFIX = `/api/${API_VERSION}`;

// API Endpoints
export const ENDPOINTS = {
  HEALTH: `${API_PREFIX}/health`,
  FETCH_TRENDS: `${API_PREFIX}/trends/fetch`,
  VALIDATE_TOPIC: `${API_PREFIX}/topics/validate`,
  GENERATE_STORY: `${API_PREFIX}/stories/generate`,
  VIDEO_CREATE_PROJECT: `${API_PREFIX}/video/projects`,
  VIDEO_GET_PROJECT: (id) => `${API_PREFIX}/video/projects/${id}`,
  VIDEO_GENERATE_ALL: (id) => `${API_PREFIX}/video/projects/${id}/generate`,
  VIDEO_GENERATE_FRAME: (id) => `${API_PREFIX}/video/projects/${id}/generate-frame`,
  VIDEO_COMBINE: (id) => `${API_PREFIX}/video/projects/${id}/combine`,
};

// Application Settings
export const APP_NAME = 'YT-Agent';
export const APP_VERSION = '1.0.0';

// Request Timeouts (in milliseconds)
export const TIMEOUTS = {
  DEFAULT: 30000,  // 30 seconds
  STORY_GENERATION: 300000,  // 5 minutes for AI generation
  VIDEO_OPERATION: 60000,    // 1 minute for video API calls
};
