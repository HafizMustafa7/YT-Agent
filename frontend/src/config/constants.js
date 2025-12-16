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
};

// Application Settings
export const APP_NAME = 'YT-Agent';
export const APP_VERSION = '1.0.0';

// Request Timeouts (in milliseconds)
export const TIMEOUTS = {
  DEFAULT: 30000,  // 30 seconds
  STORY_GENERATION: 120000,  // 2 minutes for AI generation
};
