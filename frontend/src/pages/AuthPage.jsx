import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Zap, Brain, BarChart, Mail, Lock, User, CheckCircle, XCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../supabaseClient";
import { signup, login } from "../api/auth";
import { showErrorToast } from "../lib/errorUtils";
import { Toaster } from "sonner";
import { useTheme } from "../contexts/ThemeContext";
import PageLayout from "../components/PageLayout";
import "../styles/shared.css";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { isDarkTheme } = useTheme();

  const [passwordCriteria, setPasswordCriteria] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });
  const navigate = useNavigate();

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
        const response = await login({ email: formData.email, password: formData.password });
        const { access_token, refresh_token } = response;

        const { error: sessionError } = await supabase.auth.setSession({
          access_token,
          refresh_token,
        });

        if (sessionError) throw sessionError;
        navigate("/dashboard");
      } else {
        await signup(formData);
        alert("Signup successful! Check your email to confirm.");
        setIsLogin(true);
        setFormData({ full_name: "", email: "", password: "" });
      }
    } catch (err) {
      console.error(`[FRONTEND ERROR] ${isLogin ? "Login" : "Signup"} failed:`, err);
      if (!isLogin) {
        showErrorToast(err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider) => {
    try {
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

  const formVariants = {
    hidden: { opacity: 0, x: isLogin ? 50 : -50 },
    visible: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: isLogin ? -50 : 50 },
  };

  return (
    <PageLayout>
      {/* Header Snippet */}
      <header className={`relative z-10 w-full py-6 border-b shadow-lg backdrop-blur-xl transition-colors duration-500 ${isDarkTheme ? 'bg-slate-900/40 border-slate-700/50' : 'bg-white/80 border-slate-200'}`}>
        <div className="flex flex-col items-center justify-center text-center">
          <motion.h1
            className={`text-2xl font-bold md:text-3xl drop-shadow-lg ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            AI Trend Analyzer
          </motion.h1>
          <motion.p
            className={`mt-1 text-sm italic ${isDarkTheme ? 'text-white/90' : 'text-slate-600'}`}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Smarter growth. AI-powered efficiency 🚀
          </motion.p>
        </div>
      </header>

      {/* Main Content */}
      <div className="relative z-10 flex items-center justify-center flex-1 px-4 py-12 min-h-[calc(100vh-200px)]">
        <motion.div
          className={`card w-[350px] md:w-[420px] shadow-2xl rounded-2xl p-6 ${isDarkTheme ? 'bg-slate-900/60' : 'bg-white/95'}`}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          {/* Toggle Buttons */}
          <div className={`flex mb-6 overflow-hidden border rounded-xl ${isDarkTheme ? 'border-slate-600/30' : 'border-slate-200'}`}>
            <motion.button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-3 px-4 text-sm font-medium transition-all duration-300 ${isLogin
                ? "bg-indigo-600 text-white shadow-lg"
                : `bg-transparent ${isDarkTheme ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-900'}`
                }`}
              whileHover={{ scale: isLogin ? 1 : 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Login
            </motion.button>
            <motion.button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-3 px-4 text-sm font-medium transition-all duration-300 ${!isLogin
                ? "bg-indigo-600 text-white shadow-lg"
                : `bg-transparent ${isDarkTheme ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-900'}`
                }`}
              whileHover={{ scale: !isLogin ? 1 : 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Signup
            </motion.button>
          </div>

          {error && (
            <motion.p
              className="p-3 mb-4 text-sm text-red-500 border rounded-lg bg-red-500/10 border-red-500/30"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {error}
            </motion.p>
          )}

          {/* Dynamic Form Content */}
          <AnimatePresence mode="wait">
            <motion.form
              key={isLogin ? 'login' : 'signup'}
              variants={formVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              transition={{ duration: 0.3 }}
              onSubmit={handleSubmit}
              className="space-y-4"
            >
              {!isLogin && (
                <div className="relative group">
                  <User className="absolute w-4 h-4 text-slate-400 left-3.5 top-1/2 -translate-y-1/2 transition-colors group-focus-within:text-indigo-500" />
                  <input
                    type="text"
                    name="full_name"
                    placeholder="Enter your name"
                    className="input pl-14"
                    value={formData.full_name}
                    onChange={handleChange}
                    required
                  />
                </div>
              )}
              <div className="relative group">
                <Mail className="absolute w-4 h-4 text-slate-400 left-3.5 top-1/2 -translate-y-1/2 transition-colors group-focus-within:text-indigo-500" />
                <input
                  type="email"
                  name="email"
                  placeholder="Enter your email"
                  className="input pl-14"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="relative group">
                <Lock className="absolute w-4 h-4 text-slate-400 left-3.5 top-1/2 -translate-y-1/2 transition-colors group-focus-within:text-indigo-500" />
                <input
                  type="password"
                  name="password"
                  placeholder={isLogin ? "Enter your password" : "Create a password"}
                  className="input pl-14"
                  value={formData.password}
                  onChange={handleChange}
                  required
                />
              </div>

              {!isLogin && formData.password && (
                <div className="mt-2 space-y-1">
                  {[
                    { key: 'length', text: 'At least 8 characters' },
                    { key: 'uppercase', text: 'One uppercase letter' },
                    { key: 'lowercase', text: 'One lowercase letter' },
                    { key: 'number', text: 'One number' },
                    { key: 'special', text: 'One special character' }
                  ].map(c => (
                    <div key={c.key} className="flex items-center gap-2 text-xs">
                      {passwordCriteria[c.key] ? <CheckCircle className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                      <span className={passwordCriteria[c.key] ? 'text-green-500' : 'text-red-500'}>{c.text}</span>
                    </div>
                  ))}
                </div>
              )}

              <motion.button
                type="submit"
                disabled={loading}
                className="btn-primary mt-2"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {loading ? "Processing..." : (isLogin ? "Login" : "Sign Up")}
              </motion.button>
            </motion.form>
          </AnimatePresence>

          {/* Social Divider */}
          <div className="flex items-center my-6">
            <div className={`flex-1 h-px ${isDarkTheme ? 'bg-white/10' : 'bg-slate-200'}`}></div>
            <span className="px-3 text-xs text-slate-500 font-medium">OR CONTINUE WITH</span>
            <div className={`flex-1 h-px ${isDarkTheme ? 'bg-white/10' : 'bg-slate-200'}`}></div>
          </div>

          {/* OAuth Buttons */}
          <div className="flex gap-4">
            <button
              className="flex-1 flex items-center justify-center gap-2 py-3 px-4 border rounded-xl transition-all duration-300 hover:bg-slate-50 dark:hover:bg-slate-800"
              style={{ borderColor: isDarkTheme ? 'rgba(255,255,255,0.1)' : '#e2e8f0' }}
              onClick={() => handleOAuth("google")}
              disabled={loading}
            >
              <img src="https://developers.google.com/identity/images/g-logo.png" alt="Google" className="w-5 h-5" />
              <span className={`text-sm font-semibold ${isDarkTheme ? 'text-white' : 'text-slate-700'}`}>Google</span>
            </button>
            <button
              className="flex-1 flex items-center justify-center gap-2 py-3 px-4 border rounded-xl transition-all duration-300 hover:bg-slate-50 dark:hover:bg-slate-800"
              style={{ borderColor: isDarkTheme ? 'rgba(255,255,255,0.1)' : '#e2e8f0' }}
              onClick={() => handleOAuth("github")}
              disabled={loading}
            >
              <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub" className="w-5 h-5" />
              <span className={`text-sm font-semibold ${isDarkTheme ? 'text-white' : 'text-slate-700'}`}>GitHub</span>
            </button>
          </div>
        </motion.div>
      </div>

      {/* Footer Branding */}
      <footer className={`relative z-10 px-6 py-4 border-t transition-colors duration-500 ${isDarkTheme ? 'bg-slate-900/60 border-slate-700/50' : 'bg-white/90 border-slate-200'}`}>
        <div className="flex flex-wrap items-center justify-around w-full max-w-5xl mx-auto gap-4">
          {[
            { Icon: Brain, label: 'AI Powered' },
            { Icon: Shield, label: 'Secure' },
            { Icon: Zap, label: 'Fast Growth' },
            { Icon: BarChart, label: 'Analytics' }
          ].map((item, i) => (
            <motion.div
              key={i}
              className={`flex items-center gap-2 text-sm font-medium ${isDarkTheme ? 'text-indigo-400' : 'text-indigo-600'}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 + i * 0.1 }}
            >
              <item.Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </motion.div>
          ))}
        </div>
      </footer>

      <Toaster position="top-right" richColors />
    </PageLayout>
  );
}
