/**
 * ProtectedRoute — FE-2 fix
 *
 * Problem: the old pattern `user ? <Page /> : <AuthPage />` rendered <AuthPage>
 * instantly while the async Supabase session check was still in flight, causing a
 * visible flash of the login screen before the user was redirected to their page.
 *
 * Solution: show a centred spinner while `loading` is true (session is being resolved),
 * redirect to `/auth` when unauthenticated, and render the child page only once we
 * know for certain the user is logged in.
 */
import { Navigate } from "react-router-dom";

/**
 * @param {object} props
 * @param {object|null} props.user    - Supabase user object (null = unauthenticated)
 * @param {boolean}     props.loading - True while the initial session check is in flight
 * @param {JSX.Element} props.children - The protected page component
 */
export default function ProtectedRoute({ user, loading, children }) {
  // Still resolving session — show a neutral loading screen to prevent flash
  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          background: "#0a0a0a",
          color: "#888",
          fontFamily: "Inter, sans-serif",
          fontSize: "14px",
          gap: "12px",
        }}
      >
        <div
          style={{
            width: 20,
            height: 20,
            borderRadius: "50%",
            border: "2px solid #333",
            borderTop: "2px solid #6366f1",
            animation: "spin 0.8s linear infinite",
          }}
        />
        Loading...
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // Session resolved — unauthenticated, redirect to auth page
  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  // Authenticated — render the protected page
  return children;
}
