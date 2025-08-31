import axios from "axios";
import { supabase } from "../supabaseClient";

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
});

// 🔹 Attach Supabase access token on every request
api.interceptors.request.use(async (config) => {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  } catch (err) {
    console.error("[FRONTEND ERROR] Failed to attach auth token:", err);
  }
  return config;
});

/**
 * Email/Password Signup
 * Calls backend -> which also inserts into "profiles"
 */
export const signup = async (data) => {
  try {
    const response = await api.post("/api/auth/signup", data);
    return response.data;
  } catch (err) {
    console.error("[FRONTEND ERROR] Signup failed:", err.response?.data || err.message);
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
    const response = await api.post("/api/auth/sync", {
      email: session.user.email,
      full_name:
        session.user.user_metadata?.full_name ||
        session.user.user_metadata?.name ||
        "",
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
    const response = await api.get("/api/auth/me");
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
