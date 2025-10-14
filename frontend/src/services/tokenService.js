import { supabase } from '../supabaseClient';
import { showErrorToast } from '../lib/errorUtils';

// Token Service for managing authentication and service tokens
export class TokenService {
  constructor() {
    this.isRefreshing = false;
    this.refreshPromise = null;
  }

  // Check if JWT session is valid
  async checkSession() {
    try {
      const { data: { session }, error } = await supabase.auth.getSession();
      if (error) throw error;

      if (!session || !session.user) {
        return false;
      }

      // Check if token is expired
      const now = Math.floor(Date.now() / 1000);
      const expiresAt = session.expires_at;

      if (expiresAt && now >= expiresAt) {
        console.log('[TokenService] JWT token expired');
        return false;
      }

      return true;
    } catch (error) {
      console.error('[TokenService] Session check failed:', error);
      return false;
    }
  }

  // Handle expired JWT session
  async handleExpiredSession(message = "Your session has expired. Please login again.") {
    try {
      console.log('[TokenService] Handling expired session');

      // Clear all storage
      localStorage.clear();
      sessionStorage.clear();

      // Sign out from Supabase
      await supabase.auth.signOut();

      // Show user-friendly message
      showErrorToast(message);

      // Redirect to login
      window.location.href = '/';

    } catch (error) {
      console.error('[TokenService] Error handling expired session:', error);
      // Force redirect even if cleanup fails
      window.location.href = '/';
    }
  }

  // Refresh Google Drive token (automatic)
  async refreshDriveToken() {
    if (this.isRefreshing) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;

    try {
      this.refreshPromise = this._performDriveRefresh();
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  async _performDriveRefresh() {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('No active session');
      }

      const response = await fetch('http://localhost:8000/api/drive/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to refresh Drive token');
      }

      const data = await response.json();
      console.log('[TokenService] Drive token refreshed successfully');
      return data;

    } catch (error) {
      console.error('[TokenService] Drive token refresh failed:', error);
      throw error;
    }
  }

  // Refresh YouTube token (automatic)
  async refreshYouTubeToken() {
    if (this.isRefreshing) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;

    try {
      this.refreshPromise = this._performYouTubeRefresh();
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  async _performYouTubeRefresh() {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('No active session');
      }

      const response = await fetch('http://localhost:8000/api/channels/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to refresh YouTube token');
      }

      const data = await response.json();
      console.log('[TokenService] YouTube token refreshed successfully');
      return data;

    } catch (error) {
      console.error('[TokenService] YouTube token refresh failed:', error);
      throw error;
    }
  }

  // Global API response interceptor
  setupApiInterceptors() {
    // Store original fetch
    const originalFetch = window.fetch;

    window.fetch = async (...args) => {
      const response = await originalFetch(...args);

      // Check for authentication errors
      if (response.status === 401 || response.status === 403) {
        // Check if it's a JWT expiration (not Drive or YouTube token)
        const url = args[0];
        if (typeof url === 'string' && !url.includes('/drive/') && !url.includes('/channels/')) {
          console.log('[TokenService] JWT expired detected in API response');
          this.handleExpiredSession();
          return response; // Return original response to prevent further processing
        }
      }

      return response;
    };
  }

  // Periodic session validation
  startSessionValidation(intervalMinutes = 5) {
    setInterval(async () => {
      const isValid = await this.checkSession();
      if (!isValid) {
        this.handleExpiredSession("Your session has expired due to inactivity. Please login again.");
      }
    }, intervalMinutes * 60 * 1000);
  }

  // Logout with cleanup
  async logout(message = null) {
    try {
      console.log('[TokenService] Starting logout process');

      // Clear all storage first
      localStorage.clear();
      sessionStorage.clear();

      // Sign out from Supabase
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('[TokenService] Supabase signOut error:', error);
      }

      // Show message if provided
      if (message) {
        showErrorToast(message);
      }

      // Redirect to login
      window.location.href = '/';

    } catch (error) {
      console.error('[TokenService] Logout error:', error);
      // Force redirect
      window.location.href = '/';
    }
  }
}

// Create singleton instance
export const tokenService = new TokenService();

// Initialize interceptors when module loads
if (typeof window !== 'undefined') {
  tokenService.setupApiInterceptors();
  tokenService.startSessionValidation();
}
