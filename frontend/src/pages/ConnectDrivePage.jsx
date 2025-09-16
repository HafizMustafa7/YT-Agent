import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { startDriveOAuth } from "../api/auth";

export default function ConnectDrivePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const initiateOAuth = async () => {
      try {
        console.log("[CONNECT DRIVE] Starting OAuth flow");
        const response = await startDriveOAuth();
        console.log("[CONNECT DRIVE] Got OAuth URL:", response.url);

        // Redirect to Google OAuth
        window.location.href = response.url;
      } catch (err) {
        console.error("[CONNECT DRIVE] Failed to start OAuth:", err);
        setError("Failed to connect to Google Drive. Please try again.");
        setLoading(false);
      }
    };

    initiateOAuth();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4 bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="w-full max-w-md p-8 text-center bg-white rounded-lg shadow-lg">
          <div className="w-12 h-12 mx-auto mb-4 border-b-2 border-blue-600 rounded-full animate-spin"></div>
          <h2 className="mb-2 text-xl font-semibold text-gray-800">Connecting to Google Drive</h2>
          <p className="text-gray-600">Please wait while we redirect you to Google...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4 bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="w-full max-w-md p-8 text-center bg-white rounded-lg shadow-lg">
          <div className="mb-4 text-red-500">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="mb-2 text-xl font-semibold text-gray-800">Connection Failed</h2>
          <p className="mb-4 text-gray-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 text-white transition-colors bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return null;
}
