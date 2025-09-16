import { Routes, Route } from "react-router-dom";
import { useEffect, useState } from "react";
import AuthPage from "./pages/AuthPage";
import ConnectDrivePage from "./pages/ConnectDrivePage";
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
      try {
        console.log("[DEBUG] Calling supabase.auth.getSession()");
        const { data: { session }, error } = await supabase.auth.getSession();
        console.log("[DEBUG] Initial session check result:", { session: !!session, error });

        if (error) {
          console.error("[ERROR] getSession error:", error);
          setLoading(false);
          return;
        }

        if (session?.user) {
          console.log("[DEBUG] Session found, setting user:", session.user.email);

          // Check if session is expired
          const now = Math.floor(Date.now() / 1000);
          const expiresAt = session.expires_at;
          if (expiresAt && now > expiresAt) {
            console.log("[DEBUG] Session expired, signing out");
            await supabase.auth.signOut();
            setUser(null);
            setLoading(false);
            return;
          }

          setUser(session.user);

          // Only sync if OAuth user (email/password signup already handled in backend)
          const provider = session.user.app_metadata?.provider;
          if (provider && provider !== "email" && !synced) {
            try {
              console.log("[DEBUG] Syncing OAuth user");
              await syncOAuthUser();
              setSynced(true);
              console.log("[DEBUG] OAuth user synced successfully");
            } catch (err) {
              console.error("[ERROR] Failed to sync OAuth user:", err);
              // Don't set loading to false here, continue
            }
          }
        } else {
          console.log("[DEBUG] No session found");
        }
      } catch (err) {
        console.error("[ERROR] getInitialSession failed:", err);
      } finally {
        console.log("[DEBUG] Setting loading to false");
        setLoading(false);
      }
    };

    // Add timeout to prevent infinite loading
    const timeoutId = setTimeout(() => {
      console.warn("[WARN] getInitialSession timeout - forcing loading to false");
      setLoading(false);
    }, 10000); // 10 seconds timeout

    getInitialSession().then(() => {
      clearTimeout(timeoutId);
    });

    // 🔹 Listen to auth state changes (login, logout, OAuth callback)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log("[DEBUG] Auth state changed:", event, session?.user?.email);

        if (session?.user) {
          setUser(session.user);

          // Note: OAuth sync is handled in AuthPage.jsx to avoid duplicates
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
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <Routes>
      {/* Auth Page (Login/Signup/OAuth buttons) */}
      <Route path="/" element={<AuthPage />} />

      {/* Connect Drive Page */}
      <Route path="/connect-drive" element={<ConnectDrivePage />} />

      {/* Dashboard (protected) */}
      <Route
        path="/dashboard"
        element={user ? <Dashboard /> : <AuthPage />}
      />
    </Routes>
  );
}

export default App;
