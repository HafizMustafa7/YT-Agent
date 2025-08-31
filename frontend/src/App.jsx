import { Routes, Route } from "react-router-dom";
import { useEffect, useState } from "react";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import { supabase } from "./supabaseClient";
import { syncOAuthUser } from "./api/auth";

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [synced, setSynced] = useState(false);

  useEffect(() => {
    console.log("[DEBUG] App mounted - checking for existing session");

    const getInitialSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      console.log("[DEBUG] Initial session check:", session);

      if (session?.user) {
        setUser(session.user);

        // Only sync if OAuth user (email/password signup already handled in backend)
        const provider = session.user.app_metadata?.provider;
        if (provider && provider !== "email" && !synced) {
          try {
            await syncOAuthUser();
            setSynced(true);
          } catch (err) {
            console.error("[ERROR] Failed to sync OAuth user:", err);
          }
        }
      }
      setLoading(false);
    };

    getInitialSession();

    // 🔹 Listen to auth state changes (login, logout, OAuth callback)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log("[DEBUG] Auth state changed:", event, session?.user?.email);

        if (session?.user) {
          setUser(session.user);

          // Sync only if OAuth provider
          const provider = session.user.app_metadata?.provider;
          if (provider && provider !== "email" && !synced) {
            try {
              await syncOAuthUser();
              setSynced(true);
            } catch (err) {
              console.error("[ERROR] Failed to sync OAuth user on state change:", err);
            }
          }
        } else {
          setUser(null);
          setSynced(false); // Reset on logout
        }
        setLoading(false);
      }
    );

    return () => {
      console.log("[DEBUG] Cleaning up auth state change subscription");
      subscription.unsubscribe();
    };
  }, [synced]); // ✅ keep synced in deps so it updates properly

  if (loading) {
    return <div className="flex h-screen items-center justify-center">Loading...</div>;
  }

  return (
    <Routes>
      {/* Auth Page (Login/Signup/OAuth buttons) */}
      <Route path="/" element={<AuthPage />} />

      {/* Dashboard (protected) */}
      <Route
        path="/dashboard"
        element={user ? <Dashboard /> : <AuthPage />}
      />
    </Routes>
  );
}

export default App;
