import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { supabase } from "../supabaseClient";
import { signup, login } from "../api/auth";
import { showErrorToast, getFriendlyErrorMessage } from "../lib/errorUtils";
import { Toaster } from "sonner";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [passwordCriteria, setPasswordCriteria] = useState({ length: false, uppercase: false, lowercase: false, number: false, special: false });
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    if (name === 'password') {
      setPasswordCriteria({ length: value.length >= 8, uppercase: /[A-Z]/.test(value), lowercase: /[a-z]/.test(value), number: /\d/.test(value), special: /[!@#$%^&*(),.?":{}|<>]/.test(value) });
    }
  };

  const isStrongPassword = (p) => p.length >= 8 && /[A-Z]/.test(p) && /[a-z]/.test(p) && /\d/.test(p) && /[!@#$%^&*(),.?":{}|<>]/.test(p);

  const handleSubmit = async (e) => {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      if (!isLogin && !isStrongPassword(formData.password)) { setError("Password must be at least 8 characters with uppercase, lowercase, number, and special character."); setLoading(false); return; }
      if (isLogin) {
        const response = await login({ email: formData.email, password: formData.password });
        const { access_token, refresh_token } = response;
        const { error: sessionError } = await supabase.auth.setSession({ access_token, refresh_token });
        if (sessionError) throw sessionError;
        navigate("/dashboard");
      } else {
        await signup(formData);
        alert("Signup successful! Check your email to confirm.");
        setIsLogin(true); setFormData({ full_name: "", email: "", password: "" });
      }
    } catch (err) {
      if (!isLogin) showErrorToast(err);
      setError(getFriendlyErrorMessage(err) || "An error occurred");
    } finally { setLoading(false); }
  };

  const handleOAuth = async (provider) => {
    try {
      const { data, error } = await supabase.auth.signInWithOAuth({ provider, options: { redirectTo: window.location.origin + "/" } });
      if (error) showErrorToast({ message: `OAuth login failed: ${error.message}` });
      else if (data?.url) window.location.href = data.url;
    } catch (err) { showErrorToast({ message: `OAuth login failed: ${err.message}` }); }
  };

  const inputStyle = {
    width: '100%', background: '#11131d', border: 'none',
    color: '#f0f0fd', padding: '16px 20px', borderRadius: '8px',
    fontFamily: "'Inter', sans-serif", fontSize: '14px', outline: 'none',
    transition: 'all 0.3s', boxSizing: 'border-box',
  };

  const labelStyle = {
    display: 'block', fontFamily: "'Manrope', sans-serif", fontSize: '12px',
    fontWeight: 700, color: '#aaaab7', textTransform: 'uppercase',
    letterSpacing: '0.08em', marginBottom: '8px', marginLeft: '4px',
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0c0e17', color: '#f0f0fd', fontFamily: "'Inter', sans-serif", position: 'relative', overflow: 'hidden' }}>
      {/* Mesh Background */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, backgroundImage: 'radial-gradient(at 0% 0%, rgba(129,236,255,0.05) 0px, transparent 50%), radial-gradient(at 100% 0%, rgba(166,140,255,0.05) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(129,236,255,0.05) 0px, transparent 50%), radial-gradient(at 0% 100%, rgba(166,140,255,0.05) 0px, transparent 50%)' }} />

      {/* Cinematic Orbs */}
      <div style={{ position: 'fixed', top: '10%', left: '5%', width: '384px', height: '384px', background: 'rgba(129,236,255,0.1)', borderRadius: '9999px', filter: 'blur(120px)', pointerEvents: 'none' }} />
      <div style={{ position: 'fixed', bottom: '10%', right: '5%', width: '384px', height: '384px', background: 'rgba(166,140,255,0.1)', borderRadius: '9999px', filter: 'blur(120px)', pointerEvents: 'none' }} />

      {/* Side Decoration */}
      <div style={{ position: 'fixed', left: 48, bottom: 48, zIndex: 20, display: 'flex', flexDirection: 'column', gap: '24px', opacity: 0.3 }}>
        <div style={{ height: 4, width: 96, background: 'rgba(129,236,255,0.5)', borderRadius: '9999px' }} />
        <p style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '3rem', fontWeight: 900, color: 'rgba(255,255,255,0.05)', letterSpacing: '-0.05em', writingMode: 'vertical-rl', userSelect: 'none' }}>AUTHENTICATION_PROTOCOL</p>
      </div>

      {/* Right dots */}
      <div style={{ position: 'fixed', right: 48, top: '50%', transform: 'translateY(-50%)', zIndex: 20, display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {[0, 1, 2, 3].map(i => (
          <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: i === 1 ? '#81ecff' : '#464752', animation: i === 1 ? 'pulse 2s ease-in-out infinite' : 'none' }} />
        ))}
      </div>

      <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px 48px', position: 'relative', zIndex: 10 }}>
        {/* Branding */}
        <div style={{ marginBottom: '40px', textAlign: 'center' }}>
          <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 900, fontSize: '2.5rem', letterSpacing: '-0.05em', color: '#00e3fd', textTransform: 'uppercase' }}>YOUTOMIZE</h1>
          <p style={{ fontFamily: "'Manrope', sans-serif", color: '#aaaab7', fontSize: '14px', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: '8px' }}>
            {isLogin ? 'Cinematic Automation' : 'Architecting Cinematic Intelligence'}
          </p>
        </div>

        {/* Central Card */}
        <AnimatePresence mode="wait">
          <motion.div key={isLogin ? 'login' : 'signup'}
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.3 }}
            style={{
              width: '100%', maxWidth: '448px',
              background: 'rgba(23,25,36,0.6)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
              padding: '40px', borderRadius: '12px',
              boxShadow: '0 40px 100px rgba(0,0,0,0.5)',
              border: '1px solid rgba(70,71,82,0.1)',
            }}
          >
            <div style={{ marginBottom: '32px' }}>
              <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.5rem', letterSpacing: '-0.02em', marginBottom: '8px' }}>
                {isLogin ? 'Welcome Back' : 'Create your account'}
              </h2>
              <p style={{ color: '#aaaab7', fontSize: '14px' }}>
                {isLogin ? 'Log in to your AI workstation.' : 'Join the network of AI creators.'}
              </p>
            </div>

            {error && (
              <div style={{ background: 'rgba(255,113,108,0.1)', border: '1px solid rgba(255,113,108,0.3)', borderRadius: '8px', padding: '12px', marginBottom: '16px', fontSize: '13px', color: '#ff716c' }}>{error}</div>
            )}

            {/* Google OAuth */}
            <button onClick={() => handleOAuth("google")} disabled={loading} style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
              background: '#222532', color: '#f0f0fd', fontFamily: "'Manrope', sans-serif", fontWeight: 600,
              padding: '16px 24px', borderRadius: '8px', border: 'none', cursor: 'pointer',
              transition: 'all 0.3s', fontSize: '14px',
            }}
              onMouseEnter={e => e.currentTarget.style.background = '#282b3a'}
              onMouseLeave={e => e.currentTarget.style.background = '#222532'}
            >
              <svg width="20" height="20" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="currentColor"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="currentColor"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="currentColor"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 12-4.53z" fill="currentColor"/></svg>
              Continue with Google
            </button>

            {/* Separator */}
            <div style={{ display: 'flex', alignItems: 'center', margin: '32px 0' }}>
              <div style={{ flex: 1, height: 1, background: 'rgba(70,71,82,0.2)' }} />
              <span style={{ margin: '0 16px', fontSize: '12px', fontFamily: "'Manrope', sans-serif", color: '#737580', textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                {isLogin ? 'or' : 'or register manually'}
              </span>
              <div style={{ flex: 1, height: 1, background: 'rgba(70,71,82,0.2)' }} />
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {!isLogin && (
                <div>
                  <label style={labelStyle}>Full Name</label>
                  <input type="text" name="full_name" placeholder="Alex Sterling" value={formData.full_name} onChange={handleChange} required style={inputStyle}
                    onFocus={e => e.target.style.boxShadow = '0 0 0 2px rgba(129,236,255,0.5)'} onBlur={e => e.target.style.boxShadow = 'none'} />
                </div>
              )}
              <div>
                <label style={labelStyle}>Email Address</label>
                <input type="email" name="email" placeholder={isLogin ? "name@studio.com" : "alex@cinema.ai"} value={formData.email} onChange={handleChange} required style={inputStyle}
                  onFocus={e => e.target.style.boxShadow = '0 0 0 2px rgba(0,227,253,0.5)'} onBlur={e => e.target.style.boxShadow = 'none'} />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <label style={labelStyle}>Password</label>
                  {isLogin && <a href="#" style={{ fontSize: '12px', fontWeight: 500, color: '#81ecff', textDecoration: 'none', marginBottom: '8px', transition: 'color 0.3s' }}>Forgot password?</a>}
                </div>
                <input type="password" name="password" placeholder="••••••••" value={formData.password} onChange={handleChange} required style={inputStyle}
                  onFocus={e => e.target.style.boxShadow = '0 0 0 2px rgba(129,236,255,0.5)'} onBlur={e => e.target.style.boxShadow = 'none'} />
              </div>

              {/* Password Criteria (signup only) */}
              {!isLogin && formData.password && (
                <div style={{ background: 'rgba(17,19,29,0.5)', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    { key: 'length', text: 'At least 8 characters' },
                    { key: 'uppercase', text: 'Uppercase & Lowercase' },
                    { key: 'number', text: 'One Number' },
                    { key: 'special', text: 'One Special Character' },
                  ].map(c => (
                    <div key={c.key} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', fontWeight: 500, color: passwordCriteria[c.key] ? '#81ecff' : 'rgba(170,170,183,0.6)' }}>
                      <span style={{ fontSize: '16px' }}>{passwordCriteria[c.key] ? '✓' : '○'}</span>
                      {c.text}
                    </div>
                  ))}
                </div>
              )}

              <button type="submit" disabled={loading} style={{
                width: '100%', marginTop: '8px', padding: '16px 24px', borderRadius: '8px',
                background: 'linear-gradient(45deg, #81ecff 0%, #a68cff 100%)',
                color: '#004d57', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                fontSize: '1rem', border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: '0 10px 30px rgba(129,236,255,0.2)',
                transition: 'all 0.3s', opacity: loading ? 0.6 : 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
              }}
                onMouseEnter={e => { if (!loading) e.currentTarget.style.boxShadow = '0 15px 40px rgba(129,236,255,0.3)'; }}
                onMouseLeave={e => e.currentTarget.style.boxShadow = '0 10px 30px rgba(129,236,255,0.2)'}
              >
                {loading ? "Processing..." : (isLogin ? "Enter Workstation" : "Create Account →")}
              </button>
            </form>

            {/* Toggle */}
            <div style={{ marginTop: '40px', textAlign: 'center' }}>
              <p style={{ fontSize: '14px', color: '#aaaab7' }}>
                {isLogin ? "Don't have an account? " : "Already have an account? "}
                <span onClick={() => { setIsLogin(!isLogin); setError(''); setFormData({ full_name: '', email: '', password: '' }); }}
                  style={{ color: isLogin ? '#a68cff' : '#81ecff', fontWeight: 600, cursor: 'pointer', transition: 'color 0.3s' }}>
                  {isLogin ? 'Sign up' : 'Log in'}
                </span>
              </p>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Legal Footer */}
        <div style={{ marginTop: '48px', display: 'flex', gap: '32px' }}>
          {['Privacy Policy', 'Terms of Service'].map(item => (
            <a key={item} href="#" style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#737580', textDecoration: 'none', transition: 'color 0.3s' }}
              onMouseEnter={e => e.target.style.color = '#aaaab7'} onMouseLeave={e => e.target.style.color = '#737580'}>{item}</a>
          ))}
        </div>
      </main>

      <Toaster position="top-right" richColors />
    </div>
  );
}
