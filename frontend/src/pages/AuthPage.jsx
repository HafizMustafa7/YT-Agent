import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Zap, Brain, BarChart, Mail, Lock, User, CheckCircle, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../supabaseClient";
import { signup, login, getCurrentUser, syncOAuthUser } from "../api/auth";
import { showErrorToast, showSuccessToast, getFriendlyErrorMessage } from "../lib/errorUtils";
import { Toaster } from "sonner";
import "../styles/shared.css";
import Starfield from "../components/Starfield";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [passwordCriteria, setPasswordCriteria] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });
  const [sessionReady, setSessionReady] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // 🔹 Initialize session and verify token before making API calls
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          setSessionReady(true); // No session, but ready to show auth form
          return;
        }

        console.log("[FRONTEND DEBUG] Existing session found:", session.user);
        setSessionReady(true);

        // Call backend to get user info including drive_connected
        try {
          const userInfo = await getCurrentUser();
          if (userInfo.user.drive_connected) {
            navigate("/dashboard");
          } else {
            navigate("/connect-drive");
          }
        } catch (err) {
          console.error("[FRONTEND ERROR] Failed to fetch user info:", err);
          navigate("/dashboard");
        }
      } catch (err) {
        console.error("[FRONTEND ERROR] Session verification failed:", err);
        setSessionReady(true); // Allow auth form to show even if session check fails
      }
    };

    initializeSession();

    // 🔹 Listen for OAuth login (email login navigation handled directly)
    const { data: listener } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (session?.user) {
        console.log("[FRONTEND DEBUG] Auth state change:", event, session.user);

        // Only handle OAuth users here
        const provider = session.user.app_metadata?.provider;
        if (provider && provider !== "email") {
          try {
            console.log("[FRONTEND DEBUG] Syncing OAuth user on auth change");
            await syncOAuthUser();

            // Navigate based on drive connection
            const userInfo = await getCurrentUser();
            if (userInfo.user.drive_connected) {
              navigate("/dashboard");
            } else {
              navigate("/connect-drive");
            }
          } catch (err) {
            console.error("[FRONTEND ERROR] Failed to sync OAuth user:", err);
            navigate("/connect-drive");
          }
        }
        // Email login navigation is handled directly in handleSubmit
      }
    });

    return () => listener.subscription.unsubscribe();
  }, [navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });

    if (name === 'password') {
      setPasswordCriteria({
        length: value.length >= 8,
        uppercase: /[A-Z]/.test(value),
        lowercase: /[a-z]/.test(value),
        number: /\d/.test(value),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(value),
      });
    }
  };

  const isStrongPassword = (password) => {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    return password.length >= minLength && hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!isLogin) {
        if (!isStrongPassword(formData.password)) {
          setError("Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character.");
          setLoading(false);
          return;
        }
      }

      if (isLogin) {
        console.log("[FRONTEND DEBUG] Calling backend login API");
        const response = await login({ email: formData.email, password: formData.password });
        console.log("[FRONTEND DEBUG] Backend login response:", response);

        // Expect full token response from backend
        const { access_token, refresh_token, expires_in, token_type, user } = response;

        // Set session in Supabase
        const { error: sessionError } = await supabase.auth.setSession({
          access_token,
          refresh_token,
        });

        if (sessionError) {
          throw sessionError;
        }

        console.log("[FRONTEND DEBUG] Login successful for:", user?.email);

        // Navigate based on drive connection status
        try {
          const userInfo = await getCurrentUser();
          if (userInfo.user.drive_connected) {
            navigate("/dashboard");
          } else {
            navigate("/connect-drive");
          }
        } catch (err) {
          console.error("[FRONTEND ERROR] Failed to fetch user info after login:", err);
          // Default to dashboard for email login
          navigate("/dashboard");
        }
      } else {
        console.log("[FRONTEND DEBUG] Calling backend signup API");
        const response = await signup(formData);
        console.log("[FRONTEND DEBUG] Signup response:", response);

        alert("Signup successful! Check your email to confirm.");
        setIsLogin(true);
        setFormData({ full_name: "", email: "", password: "" });
      }
    } catch (err) {
      console.error(`[FRONTEND ERROR] ${isLogin ? "Login" : "Signup"} failed:`, err);
      // Error toast is now handled in auth.js for login
      if (!isLogin) {
        showErrorToast(err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider) => {
    try {
      console.log(`[FRONTEND DEBUG] Starting OAuth with ${provider}`);
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo: window.location.origin + "/" },
      });

      if (error) {
        showErrorToast({ message: `OAuth login failed: ${error.message}` });
      } else if (data?.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      showErrorToast({ message: `OAuth login failed: ${err.message}` });
    }
  };



  // Form variants for toggle animation
  const formVariants = {
    hidden: { opacity: 0, x: isLogin ? 50 : -50 },
    visible: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: isLogin ? -50 : 50 },
  };

  return (
    <div className="relative flex flex-col min-h-screen overflow-hidden bg-slate-950">
      <Starfield />
      {/* Dynamic Gradient Background */}
      <div className="fixed inset-0 bg-gradient-to-br from-slate-950 via-indigo-950/40 to-slate-950" />

      {/* Animated mesh gradient */}
      <div className="fixed inset-0 opacity-30">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20 blur-3xl"
             style={{
               transform: `translate(${mousePosition.x * 0.02}px, ${mousePosition.y * 0.02}px)`
             }} />
      </div>

      {/* Elegant floating orbs with glow */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[10%] left-[10%] w-[600px] h-[600px] bg-gradient-to-br from-blue-600/30 to-indigo-600/30 rounded-full blur-3xl animate-float-slow opacity-40" />
        <div className="absolute bottom-[10%] right-[5%] w-[700px] h-[700px] bg-gradient-to-br from-violet-600/25 to-purple-600/25 rounded-full blur-3xl animate-float-slower opacity-40" />
        <div className="absolute top-[45%] right-[20%] w-[500px] h-[500px] bg-gradient-to-br from-cyan-600/20 to-blue-600/20 rounded-full blur-3xl animate-float opacity-35" />
        <div className="absolute top-[20%] right-[40%] w-[400px] h-[400px] bg-gradient-to-br from-pink-600/25 to-rose-600/25 rounded-full blur-3xl animate-float-reverse opacity-30" />
        <div className="absolute bottom-[30%] left-[15%] w-[550px] h-[550px] bg-gradient-to-br from-teal-600/20 to-green-600/20 rounded-full blur-3xl animate-wave opacity-35" />
        <div className="absolute top-[60%] left-[50%] w-[300px] h-[300px] bg-gradient-to-br from-yellow-600/15 to-orange-600/15 rounded-full blur-3xl animate-pulse-glow opacity-25" />
      </div>

      {/* Additional drifting shapes */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[15%] left-[70%] w-32 h-32 bg-gradient-to-br from-indigo-500/40 to-purple-500/40 rounded-lg blur-xl animate-drift opacity-50" />
        <div className="absolute bottom-[40%] left-[5%] w-24 h-24 bg-gradient-to-br from-cyan-500/35 to-blue-500/35 rounded-full blur-lg animate-drift opacity-45" style={{ animationDelay: '10s' }} />
        <div className="absolute top-[70%] right-[30%] w-40 h-20 bg-gradient-to-br from-violet-500/30 to-pink-500/30 rounded-2xl blur-2xl animate-drift opacity-40" style={{ animationDelay: '20s' }} />
      </div>

      {/* Subtle grid with glow */}
      <div className="fixed inset-0 opacity-[0.08]"
           style={{
             backgroundImage: `radial-gradient(circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(99, 102, 241, 0.4) 0%, transparent 50%),
                              linear-gradient(rgba(99, 102, 241, 0.05) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(99, 102, 241, 0.05) 1px, transparent 1px)`,
             backgroundSize: 'cover, 48px 48px, 48px 48px'
           }} />

      {/* Header */}
      <header className="relative z-10 w-full py-4 border-b shadow-lg bg-slate-900/40 backdrop-blur-xl border-slate-700/50">
        <div className="flex flex-col items-center justify-center text-center">
          <motion.h1
            className="text-2xl font-bold text-white md:text-3xl drop-shadow-lg"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            Automation
          </motion.h1>
          <motion.p
            className="mt-1 text-sm italic text-white/90"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Smarter growth. AI-powered efficiency 🚀
          </motion.p>
        </div>
      </header>

      {/* Main */}
      <div className="relative z-10 flex items-center justify-center flex-1 px-4 py-8">
        <motion.div
          className="card w-[350px] md:w-[420px] bg-slate-900/40 backdrop-blur-xl border-slate-800/50 shadow-2xl rounded-xl"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          {/* Toggle */}
          <div className="flex mb-6 overflow-hidden border rounded-xl border-slate-600/30">
            <motion.button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-3 px-4 text-sm font-medium transition-all duration-300 ${
                isLogin
                  ? "bg-indigo-600 text-white shadow-lg"
                  : "bg-transparent text-slate-400 hover:text-white"
              }`}
              whileHover={{ scale: isLogin ? 1 : 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Login
            </motion.button>
            <motion.button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-3 px-4 text-sm font-medium transition-all duration-300 ${
                !isLogin
                  ? "bg-indigo-600 text-white shadow-lg"
                  : "bg-transparent text-slate-400 hover:text-white"
              }`}
              whileHover={{ scale: !isLogin ? 1 : 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Signup
            </motion.button>
          </div>

          {error && (
            <motion.p
              className="p-3 text-sm text-red-400 border rounded-lg bg-red-500/10 border-red-500/30"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {error}
            </motion.p>
          )}

          {/* Form */}
          <AnimatePresence mode="wait">
            <motion.form
              key={isLogin ? 'login' : 'signup'}
              variants={formVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              transition={{ duration: 0.3 }}
              onSubmit={handleSubmit}
              className="px-4 pb-4 space-y-4"
            >
              {!isLogin && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <div className="relative">
                    <User className="absolute w-4 h-4 text-slate-400 left-3 top-3" />
                    <input
                      type="text"
                      name="full_name"
                      placeholder="Enter your name"
                      className="w-full py-3 pl-10 pr-4 text-white transition-all duration-300 border rounded-lg placeholder-slate-400 bg-slate-900/40 border-slate-700/50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 hover:bg-slate-800/50 focus-within:shadow-indigo-500/25"
                      value={formData.full_name}
                      onChange={handleChange}
                      whileFocus={{ scale: 1.02 }}
                    />
                  </div>
                </motion.div>
              )}
              <div className="relative">
                <Mail className="absolute w-4 h-4 text-slate-400 left-3 top-3" />
                <input
                  type="email"
                  name="email"
                  placeholder="Enter your email"
                  className="w-full py-3 pl-10 pr-4 text-white transition-all duration-300 border rounded-lg placeholder-slate-400 bg-slate-900/40 border-slate-700/50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 hover:bg-slate-800/50 focus-within:shadow-indigo-500/25"
                  value={formData.email}
                  onChange={handleChange}
                  whileFocus={{ scale: 1.02 }}
                />
              </div>
              <div className="relative">
                <Lock className="absolute w-4 h-4 text-slate-400 left-3 top-3" />
                <input
                  type="password"
                  name="password"
                  placeholder={isLogin ? "Enter your password" : "Create a password"}
                  className="w-full py-3 pl-10 pr-4 text-white transition-all duration-300 border rounded-lg placeholder-slate-400 bg-slate-900/40 border-slate-700/50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 hover:bg-slate-800/50 focus-within:shadow-indigo-500/25"
                  value={formData.password}
                  onChange={handleChange}
                  whileFocus={{ scale: 1.02 }}
                />
              </div>
              {!isLogin && formData.password && (
                <div className="mt-2 space-y-1">
                  <div className="flex items-center gap-2 text-sm">
                    {passwordCriteria.length ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                    <span className={passwordCriteria.length ? 'text-green-400' : 'text-red-400'}>At least 8 characters</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {passwordCriteria.uppercase ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                    <span className={passwordCriteria.uppercase ? 'text-green-400' : 'text-red-400'}>One uppercase letter</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {passwordCriteria.lowercase ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                    <span className={passwordCriteria.lowercase ? 'text-green-400' : 'text-red-400'}>One lowercase letter</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {passwordCriteria.number ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                    <span className={passwordCriteria.number ? 'text-green-400' : 'text-red-400'}>One number</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {passwordCriteria.special ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                    <span className={passwordCriteria.special ? 'text-green-400' : 'text-red-400'}>One special character</span>
                  </div>
                </div>
              )}
              <motion.button
                type="submit"
                disabled={loading}
                className="w-full py-3 font-bold text-white transition-all duration-300 rounded-lg shadow-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 hover:shadow-indigo-500/50 disabled:opacity-50"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {loading ? "Processing..." : (isLogin ? "Login" : "Sign Up")}
              </motion.button>
            </motion.form>
          </AnimatePresence>

          {/* Divider */}
          <div className="flex items-center px-4 my-5">
            <div className="flex-1 h-px bg-white/30"></div>
            <span className="px-3 text-sm text-gray-400">or continue with</span>
            <div className="flex-1 h-px bg-white/30"></div>
          </div>

          {/* OAuth */}
          <div className="flex justify-center gap-4 px-4 pb-4">
            <motion.button
              className="flex items-center justify-center flex-1 gap-2 px-4 py-3 text-white transition-all duration-300 border rounded-lg bg-slate-900/40 border-slate-700/50 hover:bg-slate-800/50 hover:border-indigo-500"
              onClick={() => handleOAuth("google")}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              disabled={loading}
            >
              <img src="https://developers.google.com/identity/images/g-logo.png" alt="Google" className="w-5 h-5" />
              <span className="text-sm font-medium">Google</span>
            </motion.button>
            <motion.button
              className="flex items-center justify-center flex-1 gap-2 px-4 py-3 text-white transition-all duration-300 border rounded-lg bg-slate-900/40 border-slate-700/50 hover:bg-slate-800/50 hover:border-indigo-500"
              onClick={() => handleOAuth("github")}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              disabled={loading}
            >
              <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub" className="w-5 h-5" />
              <span className="text-sm font-medium">GitHub</span>
            </motion.button>
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 px-6 py-3 text-white border-t bg-gradient-to-r from-indigo-600/80 to-purple-600/80 backdrop-blur-sm border-white/20">
        <div className="flex items-center justify-between w-full max-w-5xl mx-auto text-sm">
          <motion.div className="flex items-center gap-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
            <Brain className="w-5 h-5 text-white" /><span>AI Powered</span>
          </motion.div>
          <motion.div className="flex items-center gap-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
            <Shield className="w-5 h-5 text-white" /><span>Secure</span>
          </motion.div>
          <motion.div className="flex items-center gap-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
            <Zap className="w-5 h-5 text-white" /><span>Fast Growth</span>
          </motion.div>
          <motion.div className="flex items-center gap-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
            <BarChart className="w-5 h-5 text-white" /><span>Analytics Ready</span>
          </motion.div>
        </div>
      </footer>

      <Toaster position="top-right" richColors />

    </div>
  );
}
