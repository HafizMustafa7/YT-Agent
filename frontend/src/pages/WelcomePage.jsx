import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, TrendingUp, Clock, Users, ArrowRight, Sparkles } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import PageLayout from '../components/PageLayout';
import '../styles/shared.css';

const LandingPage = () => {
  const navigate = useNavigate();
  const { isDarkTheme } = useTheme();

  const handleGetStarted = () => {
    navigate('/auth');
  };

  return (
    <PageLayout>
      <main className="relative z-10 px-6 pt-16 pb-24 lg:px-12">
        <div className="mx-auto max-w-7xl">
          {/* Hero Section */}
          <div className="mb-24 text-center">
            <div className={`inline-flex items-center px-4 py-2 mb-8 space-x-2 text-sm font-medium transition-all duration-300 border rounded-full shadow-lg cursor-pointer backdrop-blur-xl border-slate-700/50 hover:shadow-blue-500/20 group ${isDarkTheme ? 'bg-slate-800/40 text-blue-300' : 'bg-white/80 text-blue-600'}`}>
              <Sparkles className="w-4 h-4 transition-transform duration-300 group-hover:rotate-12" />
              <span>AI-Powered YouTube Automation</span>
            </div>

            <h2 className={`mb-8 text-4xl font-black leading-tight tracking-tight md:text-5xl lg:text-6xl ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
              Transform Your
              <span className="block mt-2 text-transparent md:mt-3 bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 animate-gradient">
                YouTube Strategy
              </span>
            </h2>

            <p className={`max-w-3xl mx-auto mb-12 text-xl leading-relaxed ${isDarkTheme ? 'text-slate-300' : 'text-slate-600'}`}>
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
              isDark={isDarkTheme}
            />
            <FeatureCard
              icon={<TrendingUp className="w-7 h-7" />}
              title="Performance Analytics"
              description="Track metrics and gain actionable insights to optimize your content strategy effectively."
              gradient="from-indigo-500 to-purple-500"
              isDark={isDarkTheme}
            />
            <FeatureCard
              icon={<Clock className="w-7 h-7" />}
              title="Smart Scheduling"
              description="Publish at optimal times with AI-driven scheduling that maximizes audience engagement."
              gradient="from-violet-500 to-pink-500"
              isDark={isDarkTheme}
            />
            <FeatureCard
              icon={<Users className="w-7 h-7" />}
              title="Audience Growth"
              description="Scale your channel efficiently with tools designed to expand reach and build community."
              gradient="from-purple-500 to-indigo-500"
              isDark={isDarkTheme}
            />
          </div>

          {/* Stats Section */}
          <div className="grid gap-6 md:grid-cols-3">
            <StatCard number="10K+" label="Active Creators" gradient="from-blue-500 to-cyan-500" isDark={isDarkTheme} />
            <StatCard number="2M+" label="Videos Generated" gradient="from-indigo-500 to-purple-500" isDark={isDarkTheme} />
            <StatCard number="98%" label="Satisfaction Rate" gradient="from-violet-500 to-pink-500" isDark={isDarkTheme} />
          </div>
        </div>
      </main>
    </PageLayout>
  );
};

const FeatureCard = ({ icon, title, description, gradient, isDark }) => (
  <div className={`relative p-8 overflow-hidden transition-all duration-500 border group rounded-3xl backdrop-blur-xl hover:scale-105 hover:shadow-2xl ${isDark ? 'bg-slate-900/40 border-slate-800/50 hover:bg-slate-900/60 hover:border-slate-700' : 'bg-white/80 border-slate-200 hover:bg-white hover:border-slate-300'}`}>
    <div className="absolute inset-0 transition-opacity duration-500 opacity-0 group-hover:opacity-100">
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-5 blur-xl`} />
    </div>
    <div className={`relative flex items-center justify-center w-14 h-14 mb-5 rounded-2xl bg-gradient-to-br ${gradient} shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3`}>
      <div className="text-white">{icon}</div>
    </div>
    <h3 className={`relative mb-3 text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>{title}</h3>
    <p className={`relative text-sm leading-relaxed transition-colors duration-300 group-hover:text-slate-300 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{description}</p>
  </div>
);

const StatCard = ({ number, label, gradient, isDark }) => (
  <div className={`relative p-8 overflow-hidden text-center transition-all duration-500 border group rounded-3xl backdrop-blur-xl hover:scale-105 hover:shadow-2xl ${isDark ? 'bg-slate-900/40 border-slate-800/50 hover:bg-slate-900/60 hover:border-slate-700' : 'bg-white/80 border-slate-200 hover:bg-white hover:border-slate-300'}`}>
    <div className="absolute inset-0 transition-opacity duration-500 opacity-0 group-hover:opacity-100">
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-10 blur-2xl`} />
    </div>
    <div className={`relative mb-3 text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r ${gradient} group-hover:scale-110 transition-transform duration-300`}>
      {number}
    </div>
    <div className={`relative text-base font-semibold transition-colors duration-300 group-hover:text-slate-300 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{label}</div>
  </div>
);

export default LandingPage;