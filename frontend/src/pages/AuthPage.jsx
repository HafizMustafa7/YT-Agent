import { useState, useEffect } from "react";
import { Shield, Zap, Brain, BarChart } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../supabaseClient";
import { signup, login } from "../api/auth";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // 🔹 Check if user already logged in
  useEffect(() => {
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        console.log("[FRONTEND DEBUG] Existing session found:", session.user);
        navigate("/dashboard");
      }
    };
    checkSession();

    // 🔹 Listen for OAuth or email login
    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user) {
        console.log("[FRONTEND DEBUG] Auth state change:", event, session.user);
        navigate("/dashboard");
      }
    });

    return () => listener.subscription.unsubscribe();
  }, [navigate]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
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
        navigate("/dashboard");
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
      setError(err.response?.data?.detail || err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider) => {
    try {
      console.log(`[FRONTEND DEBUG] Starting OAuth with ${provider}`);
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo: window.location.origin },
      });

      if (error) {
        setError(`OAuth login failed: ${error.message}`);
      } else if (data?.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(`OAuth login failed: ${err.message}`);
    }
  };

  return (
    <div className="relative flex flex-col min-h-screen overflow-hidden bg-app">
      {/* Header */}
      <header className="w-full py-4 shadow-md bg-gradient-to-r from-blue-600 to-cyan-500">
        <div className="flex flex-col items-center justify-center text-center">
          <h1 className="text-2xl font-bold text-white md:text-3xl drop-shadow-lg">
            Automation
          </h1>
          <p className="mt-1 text-sm italic text-white/90">
            Smarter growth. AI-powered efficiency 🚀
          </p>
        </div>
      </header>

      {/* Main */}
      <div className="flex items-center justify-center flex-1 px-4 py-8">
        <div className="card w-[350px] md:w-[420px] max-h-[80vh] overflow-y-auto animate-fade-in">

          {/* Toggle */}
          <div className="flex mb-6 overflow-hidden border rounded-xl border-white/30">
            <button
              onClick={() => setIsLogin(true)}
              className={isLogin ? "btn-toggle-active" : "btn-toggle-inactive"}
            >
              Login
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={!isLogin ? "btn-toggle-active" : "btn-toggle-inactive"}
            >
              Signup
            </button>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <input
                type="text"
                name="full_name"
                placeholder="Enter your name"
                className="input"
                value={formData.full_name}
                onChange={handleChange}
              />
            )}
            <input
              type="email"
              name="email"
              placeholder="Enter your email"
              className="input"
              value={formData.email}
              onChange={handleChange}
            />
            <input
              type="password"
              name="password"
              placeholder={isLogin ? "Enter your password" : "Create a password"}
              className="input"
              value={formData.password}
              onChange={handleChange}
            />
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Processing..." : (isLogin ? "Login" : "Sign Up")}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center my-5">
            <div className="flex-1 h-px bg-white/30"></div>
            <span className="px-3 text-sm text-gray-600">or continue with</span>
            <div className="flex-1 h-px bg-white/30"></div>
          </div>

          {/* OAuth */}
          <div className="flex justify-center gap-4">
            <button className="btn-oauth" onClick={() => handleOAuth("google")}>
              <img src="https://developers.google.com/identity/images/g-logo.png" alt="Google" className="w-5 h-5" />
              <span className="text-sm font-medium">Google</span>
            </button>
            <button className="btn-oauth" onClick={() => handleOAuth("github")}>
              <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub" className="w-5 h-5" />
              <span className="text-sm font-medium">GitHub</span>
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="px-6 py-3 text-white border-t bg-gradient-to-r from-blue-600 to-cyan-500 border-white/20">
        <div className="flex items-center justify-between w-full max-w-5xl mx-auto text-sm">
          <div className="flex items-center gap-2"><Brain className="w-5 h-5 text-white" /><span>AI Powered</span></div>
          <div className="flex items-center gap-2"><Shield className="w-5 h-5 text-white" /><span>Secure</span></div>
          <div className="flex items-center gap-2"><Zap className="w-5 h-5 text-white" /><span>Fast Growth</span></div>
          <div className="flex items-center gap-2"><BarChart className="w-5 h-5 text-white" /><span>Analytics Ready</span></div>
        </div>
      </footer>
    </div>
  );
}
