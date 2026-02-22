import axios from "axios";
import { supabase } from "../supabaseClient";
import { showErrorToast, showSuccessToast, getFriendlyErrorMessage } from "../lib/errorUtils";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout
});

// 🔹 Attach Supabase access token on every request
api.interceptors.request.use(async (config) => {
  try {
    const { data: { session }, error } = await supabase.auth.getSession();

    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  } catch (err) {
    console.error("[API REQUEST] Auth interceptor error:", err.message);
  }
  return config;
});

// 🔹 Handle response errors globally
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';

    if (status === 401) {
      console.warn("[API ERROR] 401 Unauthorized at", url);

      // If it's a 401, the session might be truly invalid
      // We don't sign out automatically here to avoid clearing state on transient 401s
      // but we log it for debugging.
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
