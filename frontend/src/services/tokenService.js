import { supabase } from '../supabaseClient';
import { toast } from 'sonner';
import api from '../api/auth';

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

      // Clear only auth-related storage (preserve app preferences)
      localStorage.removeItem('supabase.auth.token');
      sessionStorage.removeItem('supabase.auth.token');

      // Sign out from Supabase
      await supabase.auth.signOut();

      // Show user-friendly message
      toast.error(message);

      // Redirect to login
      window.location.href = '/';

    } catch (error) {
      console.error('[TokenService] Error handling expired session:', error);
      // Force redirect even if cleanup fails
      window.location.href = '/';
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
      // FE-1: use the configured axios instance (has API_BASE_URL + auth interceptor)
      // Raw fetch('/api/channels/refresh') resolved to the frontend domain in production
      const response = await api.post('/api/channels/refresh');
      console.log('[TokenService] YouTube token refreshed successfully');
      return response.data;
    } catch (error) {
      console.error('[TokenService] YouTube token refresh failed:', error);
      throw error;
    }
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

      // Clear auth storage (preserve is unnecessary on full logout)
      localStorage.removeItem('supabase.auth.token');
      localStorage.removeItem('selectedChannelId');
      sessionStorage.removeItem('supabase.auth.token');

      // Sign out from Supabase
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('[TokenService] Supabase signOut error:', error);
      }

      // Show message if provided
      if (message) {
        toast.error(message);
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
  tokenService.startSessionValidation();
}
