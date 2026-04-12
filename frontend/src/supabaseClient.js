// src/supabaseClient.js
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

const isDev = import.meta.env.DEV;

if (isDev) {
  console.log("[DEBUG] Supabase URL:", SUPABASE_URL);
  console.log("[DEBUG] Supabase Key:", SUPABASE_ANON_KEY ? "Present" : "Missing");
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    storage: window.localStorage,
    storageKey: 'supabase.auth.token'
  }
});

// Debug auth state changes — only in development
if (isDev) {
  supabase.auth.onAuthStateChange((event, session) => {
    console.log("[DEBUG] Auth state change:", event, session?.user?.email);
  });
}
