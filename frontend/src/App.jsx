import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import AuthPage from "./pages/AuthPage";
// import NicheInputPage from "./pages/NicheInputPage";
// import ResultsScreen from "./pages/ResultsScreen";
// import FrameResults from "./pages/FrameResults";
import WelcomePage from "./pages/WelcomePage";
import Analytics from "./pages/Analytics";
import { supabase } from "./supabaseClient";


import YTAgentPage from "./pages/YTAgentPage";
import Dashboard from "./pages/Dashboard";
import { ThemeProvider } from "./contexts/ThemeContext";

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [synced, setSynced] = useState(false);

  useEffect(() => {
    // Initialize session once
    const initAuth = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error) throw error;

        if (session?.user) {
          setUser(session.user);

          // Only redirect if at root or auth page
          const path = window.location.pathname;
          if (path === "/" || path === "/auth") {
            navigate("/dashboard", { replace: true });
          }
        }
      } catch (err) {
        console.error("[App] Auth initialization error:", err);
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    // Listen to all auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (session?.user) {
          setUser(session.user);

          if (event === 'SIGNED_IN') {
            setSynced(false);
          }
        } else {
          setUser(null);
          setSynced(false);
          // Redirect to home if on a protected route
          const protectedRoutes = ["/dashboard", "/analytics", "/niche-input", "/results", "/frame-results"];
          if (protectedRoutes.includes(window.location.pathname)) {
            navigate("/", { replace: true });
          }
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount only

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <ThemeProvider>
      <Routes>
        {/* Welcome Page */}
        <Route path="/" element={<WelcomePage />} />

        {/* Auth Page (Login/Signup/OAuth buttons) */}
        <Route path="/auth" element={<AuthPage />} />

        {/* Dashboard (protected) */}
        <Route
          path="/dashboard"
          element={user ? <Dashboard /> : <AuthPage />}
        />

        {/* Analytics Page (protected) */}
        <Route
          path="/analytics"
          element={user ? <Analytics /> : <AuthPage />}
        />

        {/* YT Agent / Video Gen Page (protected) */}
        <Route
          path="/generate-video"
          element={user ? <YTAgentPage /> : <AuthPage />}
        />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
