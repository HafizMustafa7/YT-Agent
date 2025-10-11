import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, TrendingUp, Clock, Users, ArrowRight, Sparkles } from 'lucide-react';
import './WelcomePage.css';

const LandingPage = () => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

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

  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/auth');
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950">
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



      {/* Main Content */}
      <main className="relative z-10 px-6 pt-16 pb-24 lg:px-12">
        <div className="mx-auto max-w-7xl">
          {/* Hero Section */}
          <div className="mb-24 text-center">
            <div className="inline-flex items-center px-4 py-2 mb-8 space-x-2 text-sm font-medium text-blue-300 transition-all duration-300 border rounded-full shadow-lg cursor-pointer bg-slate-800/40 backdrop-blur-xl border-slate-700/50 hover:shadow-blue-500/20 group">
              <Sparkles className="w-4 h-4 transition-transform duration-300 group-hover:rotate-12" />
              <span>AI-Powered YouTube Automation</span>
            </div>
            
            <h2 className="mb-8 text-6xl font-black leading-tight tracking-tight text-white lg:text-7xl">
              Transform Your
              <span className="block mt-3 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 animate-gradient">
                YouTube Strategy
              </span>
            </h2>
            
            <p className="max-w-3xl mx-auto mb-12 text-xl leading-relaxed text-slate-300">
              Leverage cutting-edge AI to automate content creation, optimize performance, 
              and scale your channel with professional-grade tools trusted by top creators worldwide.
            </p>

            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <button
                onClick={handleGetStarted}
                className="relative px-10 py-5 overflow-hidden text-base font-bold text-white transition-all duration-300 shadow-2xl group rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-600/40 hover:shadow-blue-500/60 hover:scale-105"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Get Started Free
                  <ArrowRight className="w-5 h-5 transition-transform duration-300 group-hover:translate-x-1" />
                </span>
                <div className="absolute inset-0 transition-opacity duration-300 opacity-0 bg-gradient-to-r from-blue-400 to-indigo-400 group-hover:opacity-20" />
              </button>
            </div>
          </div>

          {/* Feature Cards */}
          <div className="grid gap-6 mb-24 md:grid-cols-2 lg:grid-cols-4">
            <FeatureCard
              icon={<Zap className="w-7 h-7" />}
              title="AI Content Generation"
              description="Create compelling videos with intelligent automation tailored to your brand voice and style."
              gradient="from-blue-500 to-cyan-500"
            />
            <FeatureCard
              icon={<TrendingUp className="w-7 h-7" />}
              title="Performance Analytics"
              description="Track metrics and gain actionable insights to optimize your content strategy effectively."
              gradient="from-indigo-500 to-purple-500"
            />
            <FeatureCard
              icon={<Clock className="w-7 h-7" />}
              title="Smart Scheduling"
              description="Publish at optimal times with AI-driven scheduling that maximizes audience engagement."
              gradient="from-violet-500 to-pink-500"
            />
            <FeatureCard
              icon={<Users className="w-7 h-7" />}
              title="Audience Growth"
              description="Scale your channel efficiently with tools designed to expand reach and build community."
              gradient="from-purple-500 to-indigo-500"
            />
          </div>

          {/* Stats Section */}
          <div className="grid gap-6 md:grid-cols-3">
            <StatCard number="10K+" label="Active Creators" gradient="from-blue-500 to-cyan-500" />
            <StatCard number="2M+" label="Videos Generated" gradient="from-indigo-500 to-purple-500" />
            <StatCard number="98%" label="Satisfaction Rate" gradient="from-violet-500 to-pink-500" />
          </div>
        </div>
      </main>




    </div>
  );
};

const FeatureCard = ({ icon, title, description, gradient }) => (
  <div className="relative p-8 overflow-hidden transition-all duration-500 border group rounded-3xl bg-slate-900/40 backdrop-blur-xl border-slate-800/50 hover:bg-slate-900/60 hover:border-slate-700 hover:scale-105 hover:shadow-2xl">
    <div className="absolute inset-0 transition-opacity duration-500 opacity-0 group-hover:opacity-100">
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-5 blur-xl`} />
    </div>
    <div className={`relative flex items-center justify-center w-14 h-14 mb-5 rounded-2xl bg-gradient-to-br ${gradient} shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3`}>
      <div className="text-white">{icon}</div>
    </div>
    <h3 className="relative mb-3 text-xl font-bold text-white">{title}</h3>
    <p className="relative text-sm leading-relaxed transition-colors duration-300 text-slate-400 group-hover:text-slate-300">{description}</p>
  </div>
);

const StatCard = ({ number, label, gradient }) => (
  <div className="relative p-8 overflow-hidden text-center transition-all duration-500 border group rounded-3xl bg-slate-900/40 backdrop-blur-xl border-slate-800/50 hover:bg-slate-900/60 hover:border-slate-700 hover:scale-105 hover:shadow-2xl">
    <div className="absolute inset-0 transition-opacity duration-500 opacity-0 group-hover:opacity-100">
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-10 blur-2xl`} />
    </div>
    <div className={`relative mb-3 text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r ${gradient} group-hover:scale-110 transition-transform duration-300`}>
      {number}
    </div>
    <div className="relative text-base font-semibold transition-colors duration-300 text-slate-400 group-hover:text-slate-300">{label}</div>
  </div>
);



export default LandingPage;