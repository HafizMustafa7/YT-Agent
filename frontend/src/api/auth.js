import axios from "axios";
import { supabase } from "../supabaseClient";
import { showErrorToast, showSuccessToast, getFriendlyErrorMessage } from "../lib/errorUtils";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

console.log("[DEBUG] API Base URL:", API_BASE_URL);

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout
});

// 🔹 Attach Supabase access token on every request
api.interceptors.request.use(async (config) => {
  console.log(`[API REQUEST] ${config.method?.toUpperCase()} ${config.url}`);

  // Get session from Supabase (async)
  let session = null;
  try {
    const { data: { session: supabaseSession }, error } = await supabase.auth.getSession();
    if (!error && supabaseSession) {
      session = supabaseSession;
    }
  } catch (err) {
    console.log("[API REQUEST] Could not get session from Supabase:", err.message);
  }

  // If no session from Supabase, try localStorage as fallback
  if (!session) {
    const sessionData = localStorage.getItem('supabase.auth.token');
    if (sessionData) {
      try {
        const parsedSession = JSON.parse(sessionData);
        // Check if session is still valid
        if (parsedSession?.expires_at && Date.now() / 1000 < parsedSession.expires_at) {
          session = parsedSession;
        } else {
          console.log("[API REQUEST] Stored session expired, removing");
          localStorage.removeItem('supabase.auth.token');
        }
      } catch (err) {
        console.error("[FRONTEND ERROR] Failed to parse session data:", err);
        localStorage.removeItem('supabase.auth.token');
      }
    }
  }

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
    console.log("[API REQUEST] Authorization header attached");
  } else {
    console.warn("[API REQUEST] No access token found");
  }

  return config;
});

// 🔹 Handle response errors globally
api.interceptors.response.use(
  (response) => {
    console.log(`[API RESPONSE] ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error(`[API ERROR] ${error.config?.method?.toUpperCase()} ${error.config?.url}:`, error.response?.status, error.response?.data || error.message);

    // Handle 401 Unauthorized - but be more careful about clearing session
    if (error.response?.status === 401) {
      console.warn("[API ERROR] 401 Unauthorized");

      // Only clear session if it's not an OAuth-related request that might be retried
      const url = error.config?.url || '';
      if (!url.includes('/sync') && !url.includes('/me') && !url.includes('/login')) {
        console.warn("[API ERROR] Clearing session due to 401");
        localStorage.removeItem('supabase.auth.token');
        // Optionally redirect to login page
        // window.location.href = '/login';
      } else {
        console.warn("[API ERROR] Not clearing session for OAuth-related or login request");
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Email/Password Signup
 * Calls backend -> which also inserts into "profiles"
 */
export const signup = async (data) => {
  try {
    // Increase timeout for signup due to email sending (60 seconds for slow email delivery)
    const response = await api.post("/api/auth/signup", data, { timeout: 60000 });
    return response.data;
  } catch (err) {
    console.error("[FRONTEND ERROR] Signup failed:", err.response?.data || err.message);

    // If it's a timeout but we got a response, it means signup actually succeeded
    if (err.code === 'ECONNABORTED' && err.message.includes('timeout')) {
      console.warn("[FRONTEND WARNING] Signup timed out on frontend but may have succeeded on backend");
      // Return a special response indicating potential success despite timeout
      return {
        message: "Signup request sent. Please check your email for verification link. If you don't receive it, try logging in or contact support.",
        timeout: true
      };
    }

    throw err;
  }
};

/**
 * Email/Password Login
 * Backend returns tokens, which frontend sets in Supabase
 */
export const login = async (data) => {
  try {
    const response = await api.post("/api/auth/login", data);
    return response.data; // { access_token, refresh_token }
  } catch (err) {
    console.error("[FRONTEND ERROR] Login failed:", err.response?.data || err.message);
    showErrorToast(err);
    throw err;
  }
};

/**
 * After OAuth login completes, Supabase already has the user.
 * This function tells backend to ensure "profiles" row exists.
 */
export const syncOAuthUser = async () => {
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error || !session?.user) {
    throw new Error("No active session found after OAuth login");
  }

  try {
    // Manually attach token for OAuth sync to ensure it works
    const response = await api.post("/api/auth/sync", {
      email: session.user.email,
      full_name:
        session.user.user_metadata?.full_name ||
        session.user.user_metadata?.name ||
        "",
    }, {
      headers: {
        Authorization: `Bearer ${session.access_token}`
      }
    });
    return response.data;
  } catch (err) {
    console.error("[FRONTEND ERROR] OAuth sync failed:", err.response?.data || err.message);
    throw err;
  }
};

/**
 * Get Current User (from backend, with joined profile)
 */
export const getCurrentUser = async () => {
  try {
    // For OAuth users, manually attach token to ensure it works
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error || !session?.user) {
      throw new Error("No active session found");
    }

    const response = await api.get("/api/auth/me", {
      headers: {
        Authorization: `Bearer ${session.access_token}`
      }
    });
    return response.data;
  } catch (err) {
    console.error("[FRONTEND ERROR] Fetching current user failed:", err.response?.data || err.message);
    throw err;
  }
};

/**
 * Start Drive OAuth flow
 */
export const startDriveOAuth = async () => {
  try {
    // Manually attach token to ensure it works
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error || !session?.user) {
      throw new Error("No active session found");
    }

    const response = await api.post("/api/drive/oauth/start", {}, {
      headers: {
        Authorization: `Bearer ${session.access_token}`
      }
    });
    return response.data;
  } catch (err) {
    console.error("[FRONTEND ERROR] Starting Drive OAuth failed:", err.response?.data || err.message);
    throw err;
  }
};

/**
 * Logout
 * Clears Supabase session and tokens
 */
export const logout = async () => {
  try {
    await supabase.auth.signOut();
    return { message: "Logged out successfully" };
  } catch (err) {
    console.error("[FRONTEND ERROR] Logout failed:", err.message);
    throw err;
  }
};

// Export configured axios instance
export default api;
