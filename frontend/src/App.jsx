import { Routes, Route, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import AuthPage from "./pages/AuthPage";
import NicheInputPage from "./pages/NicheInputPage";
import ResultsScreen from "./pages/ResultsScreen";
import FrameResults from "./pages/FrameResults";
import WelcomePage from "./pages/WelcomePage";
import Analytics from "./pages/Analytics";
import FinalVideoPage from "./pages/FinalVideoPage";
import { supabase } from "./supabaseClient";


import YTAgentPage from "./pages/YTAgentPage";
import Dashboard from "./pages/Dashboard";
import PricingPage from "./pages/PricingPage";
import CheckoutPage from "./pages/CheckoutPage";
import SuccessPage from "./pages/SuccessPage";
import SettingsPage from "./pages/SettingsPage";
import { ThemeProvider } from "./contexts/ThemeContext";
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

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
            // Synced state removed
          }
        } else {
          setUser(null);
          // Redirect to home if on a protected route
          const protectedRoutes = ["/dashboard", "/analytics", "/niche-input", "/results", "/frame-results", "/generate-video", "/pricing", "/checkout", "/settings", "/final-video"];
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

  // NOTE: do NOT add an early return for loading here.
  // ProtectedRoute handles the loading spinner per-route,
  // so public routes (WelcomePage, AuthPage) are never blocked.

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
          element={<ProtectedRoute user={user} loading={loading}><Dashboard /></ProtectedRoute>}
        />

        {/* Analytics Page (protected) */}
        <Route
          path="/analytics"
          element={<ProtectedRoute user={user} loading={loading}><Analytics /></ProtectedRoute>}
        />

        {/* Niche Input / Generate Flow (New Unified UI) */}
        <Route
          path="/niche-input"
          element={<ProtectedRoute user={user} loading={loading}><NicheInputPage /></ProtectedRoute>}
        />
        <Route
          path="/results"
          element={<ProtectedRoute user={user} loading={loading}><ResultsScreen /></ProtectedRoute>}
        />
        <Route
          path="/frame-results"
          element={<ProtectedRoute user={user} loading={loading}><FrameResults /></ProtectedRoute>}
        />
        <Route
          path="/final-video"
          element={<ProtectedRoute user={user} loading={loading}><FinalVideoPage /></ProtectedRoute>}
        />

        {/* This triggers the new UI directly from Dashboard's "Generate Video" click */}
        <Route
          path="/generate-video"
          element={<ProtectedRoute user={user} loading={loading}><NicheInputPage /></ProtectedRoute>}
        />

        {/* The legacy/advanced generation engine handles step=videoGen */}
        <Route
          path="/video-gen-dashboard"
          element={<ProtectedRoute user={user} loading={loading}><YTAgentPage /></ProtectedRoute>}
        />

        {/* Payment Pages */}
        <Route
          path="/pricing"
          element={<ProtectedRoute user={user} loading={loading}><PricingPage /></ProtectedRoute>}
        />
        <Route
          path="/checkout"
          element={<ProtectedRoute user={user} loading={loading}><CheckoutPage /></ProtectedRoute>}
        />
        <Route path="/success" element={<ProtectedRoute user={user} loading={loading}><SuccessPage /></ProtectedRoute>} />
        <Route
          path="/settings"
          element={<ProtectedRoute user={user} loading={loading}><SettingsPage /></ProtectedRoute>}
        />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
