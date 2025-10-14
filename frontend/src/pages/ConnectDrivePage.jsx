// ConnectDrivePage.jsx
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Settings, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button"; // Assuming shadcn/ui Button
import { Card, CardContent } from "@/components/ui/card"; // Assuming shadcn/ui Card
import { ThemeToggle } from "@/components/ThemeToggle"; // Assuming shared ThemeToggle component
import { GeneralSettingsModal } from "@/components/GeneralSettingsModal"; // Assuming shared modal component
import { startDriveOAuth } from "../api/auth";
import { supabase } from "../supabaseClient";

// Simple ProgressLoader component using Framer Motion (orbit animation for connection)
const ProgressLoader = () => (
  <motion.div
    className="relative w-16 h-16 mx-auto"
    animate={{ rotate: 360 }}
    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
  >
    <motion.div
      className="absolute inset-0 w-16 h-16 border-4 rounded-full border-cyan-500 border-t-transparent"
      style={{ borderRadius: "50%" }}
      animate={{ rotate: -360 }}
      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
    />
    {/* Orbiting dot symbolizing connection */}
    <motion.div
      className="absolute top-0 w-2 h-2 rounded-full left-1/2 bg-cyan-400"
      style={{ translateX: "-50%" }}
      animate={{
        rotate: 360,
        scale: [1, 1.2, 1],
      }}
      transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
    />
  </motion.div>
);

// Starfield background component (simple animated particles)
const StarfieldBackground = () => {
  const stars = Array.from({ length: 50 }, (_, i) => ({
    id: i,
    top: Math.random() * 100,
    left: Math.random() * 100,
    size: Math.random() * 2 + 1,
    delay: Math.random() * 2,
    duration: Math.random() * 3 + 2,
  }));

  return (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
      {stars.map((star) => (
        <motion.div
          key={star.id}
          className="absolute bg-white rounded-full opacity-60"
          style={{
            top: `${star.top}%`,
            left: `${star.left}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
          }}
          animate={{
            y: [0, -20, 0],
            opacity: [0.6, 1, 0.6],
          }}
          transition={{
            duration: star.duration,
            repeat: Infinity,
            delay: star.delay,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
};

export default function ConnectDrivePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const navigate = useNavigate();

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

  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          console.error("[CONNECT DRIVE] No session found, redirecting to login");
          navigate("/");
          return;
        }
        setSessionReady(true);
        initiateOAuth();
      } catch (err) {
        console.error("[CONNECT DRIVE] Session verification failed:", err);
        navigate("/");
      }
    };

    initializeSession();
  }, [navigate]);

  const handleRetry = () => {
    setError("");
    setLoading(true);
    initiateOAuth();
  };

  if (loading) {
    return (
      <div className="relative flex items-center justify-center min-h-screen p-4 overflow-hidden bg-gradient-to-br from-black via-blue-900 to-black">
        <StarfieldBackground />

        {/* Top-right controls */}
        <div className="fixed z-50 flex gap-2 top-4 right-4">
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsModalOpen(true)}
            className="w-10 h-10 text-white hover:text-cyan-400"
          >
            <Settings className="w-5 h-5" />
          </Button>
        </div>

        {/* Centered Card */}
        <motion.div
          className="relative z-10 w-full max-w-md"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <Card className="shadow-2xl bg-black/20 backdrop-blur-sm border-cyan-500/30">
            <CardContent className="p-8 text-center">
              {/* Title */}
              <motion.h1
                className="text-3xl font-bold text-white mb-4 drop-shadow-lg [text-shadow:0_0_10px_rgba(6,182,212,0.5)]"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.2 }}
              >
                Connecting to Google Drive
              </motion.h1>

              {/* Description */}
              <motion.p
                className="mb-6 text-sm leading-relaxed text-gray-300"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.4 }}
              >
                Please wait while we redirect you to Google...
              </motion.p>

              {/* Progress Loader */}
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 0.6 }}
              >
                <ProgressLoader />
              </motion.div>

              {/* Status Message */}
              <motion.p
                className="mt-4 text-sm font-medium text-cyan-400"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.8 }}
              >
                Initializing connection...
              </motion.p>
            </CardContent>
          </Card>
        </motion.div>

        {/* General Settings Modal */}
        <GeneralSettingsModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="relative flex items-center justify-center min-h-screen p-4 overflow-hidden bg-gradient-to-br from-black via-blue-900 to-black">
        <StarfieldBackground />

        {/* Top-right controls */}
        <div className="fixed z-50 flex gap-2 top-4 right-4">
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsModalOpen(true)}
            className="w-10 h-10 text-white hover:text-cyan-400"
          >
            <Settings className="w-5 h-5" />
          </Button>
        </div>

        {/* Centered Card */}
        <motion.div
          className="relative z-10 w-full max-w-md"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <Card className="shadow-2xl bg-black/20 backdrop-blur-sm border-red-500/30">
            <CardContent className="p-8 text-center">
              {/* Error Icon */}
              <motion.div
                className="mx-auto mb-4 text-red-500"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
              >
                <AlertCircle className="w-12 h-12" />
              </motion.div>

              {/* Title */}
              <motion.h2
                className="text-2xl font-bold text-white mb-2 drop-shadow-lg [text-shadow:0_0_10px_rgba(239,68,68,0.5)]"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.1 }}
              >
                Connection Failed
              </motion.h2>

              {/* Description */}
              <motion.p
                className="mb-6 text-sm leading-relaxed text-gray-300"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.2 }}
              >
                {error}
              </motion.p>

              {/* Retry Button */}
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: 0.4 }}
              >
                <Button
                  onClick={handleRetry}
                  className="flex items-center gap-2 mx-auto text-red-400 transition-all duration-200 border-2 border-red-500 hover:bg-red-500/10 hover:scale-105"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </Button>
              </motion.div>
            </CardContent>
          </Card>
        </motion.div>

        {/* General Settings Modal */}
        <GeneralSettingsModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      </div>
    );
  }

  return null;
}
