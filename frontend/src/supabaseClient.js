// src/supabaseClient.js
import { createClient } from "@supabase/supabase-js";

// ✅ Replace with your Supabase project values
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

console.log("[DEBUG] Supabase Client Configuration:");
console.log("[DEBUG] SUPABASE_URL:", SUPABASE_URL);
console.log("[DEBUG] SUPABASE_ANON_KEY:", SUPABASE_ANON_KEY ? "Present" : "Missing");

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
});
