import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button'; // From shadcn/ui
import { Loader2, Settings, Bot, Shield, Zap, ArrowLeft } from 'lucide-react'; // For loader icon and footer icons
import { useToast } from '@/components/ui/use-toast'; // From shadcn/ui for toasts
import { useNavigate } from 'react-router-dom'; // Assuming React Router for navigation
import { Switch } from '@/components/ui/switch'; // From shadcn/ui
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'; // From shadcn/ui
import { supabase } from '../supabaseClient'; // For session management
import Starfield from '@/components/Starfield'; // Consistent starfield component
import './NicheInput.css'; // Import the CSS for the NicheInput component
import api from '../api/auth'; // Import the configured API instance

// API function to fetch trending videos
const fetchTrendingVideos = async (niche) => {
  try {
    const response = await api.post('/api/trends/analyze-trends', { niche });
    return response.data; // Returns { niche, trends, averageViews, averageLikes, total_trends }
  } catch (error) {
    console.error('[NicheInputPage] Error fetching trends:', error);
    throw error;
  }
};

const NicheInputPage = () => {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(true);
  const [username, setUsername] = useState('User');
  const [sessionReady, setSessionReady] = useState(false);

  // Initialize session and verify token before making API calls
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          navigate("/auth");
          return;
        }

        // Set username from session
        setUsername(session.user.email?.split('@')[0] || 'User');

        // Mark session as ready
        setSessionReady(true);
      } catch (err) {
        console.error('[NicheInputPage] Session verification failed:', err);
        navigate("/auth");
      }
    };

    initializeSession();
  }, [navigate]);

  const handleLogout = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) return;
    await supabase.auth.signOut();
    navigate("/");
  };

  const handleSearch = async (niche) => {
    if (!niche.trim()) {
      toast({ title: 'Error', description: 'Input is required.', variant: 'destructive' });
      return;
    }

    if (niche.trim().length < 3) {
      toast({ title: 'Error', description: 'Input must be at least 3 characters.', variant: 'destructive' });
      return;
    }

    setIsLoading(true);

    try {
      const result = await fetchTrendingVideos(niche);
      // On success, navigate to TopicSelectionPage
      setIsLoading(false);
      navigate('/results', { state: { niche: niche, trendingData: result } }); // Pass full result to results page
    } catch (err) {
      setIsLoading(false);
      toast({ title: 'Error', description: 'Failed to fetch data. Please try again.', variant: 'destructive' });
    }
  };

  return (
    <div className={`min-h-screen relative bg-gradient-to-br from-slate-900 via-blue-900 to-purple-900 text-white overflow-hidden ${isDarkTheme ? '' : 'bg-white text-black'}`}>
      <Starfield />

      {/* Header */}
      <motion.header
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="relative z-10 flex items-center justify-between px-8 py-6 border-b border-white/10 bg-slate-900/20 backdrop-blur-sm"
      >
        <motion.h1
          className="text-3xl font-bold text-cyan-400 drop-shadow-lg"
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          YT Agent
        </motion.h1>

        <div className="flex items-center space-x-6">
          <motion.span
            className="hidden text-sm opacity-80 md:block"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            Welcome, {username}
          </motion.span>

          {/* Theme Toggle */}
          <Switch
            checked={isDarkTheme}
            onCheckedChange={setIsDarkTheme}
            className="data-[state=checked]:bg-cyan-500"
          />

          {/* Settings Dialog */}
          <Dialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen}>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="text-white hover:text-cyan-400 hover:bg-white/10">
                <Settings className="w-5 h-5" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md bg-gradient-to-br from-slate-900 to-blue-900 border-cyan-500/50 backdrop-blur-sm">
              <DialogHeader>
                <DialogTitle className="text-white">General Settings</DialogTitle>
              </DialogHeader>
              <div className="space-y-6">
                {/* Theme Section */}
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold text-white">Appearance</h3>
                  <div className="flex items-center justify-between">
                    <span className="text-white">Dark Theme</span>
                    <Switch checked={isDarkTheme} onCheckedChange={setIsDarkTheme} />
                  </div>
                </div>

                {/* Account Section */}
                <div className="pt-4 space-y-3 border-t border-white/20">
                  <h3 className="text-lg font-semibold text-white">Account</h3>
                  <Button variant="destructive" className="w-full text-white" onClick={handleLogout}>
                    Logout
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </motion.header>

      <main className="relative z-10 px-8 py-12 mx-auto max-w-7xl">
        {/* Back Button */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mb-8"
        >
          <Button
            onClick={() => navigate('/dashboard')}
            variant="ghost"
            className="flex items-center gap-2 px-4 py-2 text-white transition-all duration-300 rounded-lg hover:text-cyan-400 hover:bg-white/10"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Back to Dashboard</span>
          </Button>
        </motion.div>

        {/* Hero Section */}
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mt-16 mb-16 text-center"
        >
          <motion.h2
            className="mb-4 text-4xl font-bold text-white md:text-5xl"
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
          >
            Enter a Niche
          </motion.h2>
          <motion.p
            className="max-w-2xl mx-auto text-xl text-gray-300"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5 }}
          >
            Search trending YouTube topics or input your own niche to generate AI video ideas.
          </motion.p>
        </motion.section>

        {/* Input Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex justify-center mb-16"
        >
          <div className="chat-container" role="main">
            <div className="chat-bubble">
              <label htmlFor="niche-input" className="sr-only">
                Hi there! I'm your YouTube trend assistant. What niche or topic would you like me to
                analyze for trending video ideas? For example, you could enter "fitness", "cooking",
                "tech reviews", or any topic you're interested in.
              </label>
              <p className="chat-text" id="chat-instructions">
                Hi there! I'm your YouTube trend assistant. What niche or topic would you like me to
                analyze for trending video ideas? For example, you could enter "fitness", "cooking",
                "tech reviews", or any topic you're interested in.
              </p>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); handleSearch(e.target.elements['niche-input'].value); }} className="chat-form">
              <div className="input-container">
                <input
                  id="niche-input"
                  type="text"
                  placeholder="Enter your niche (e.g., cooking, fitness, tech)"
                  className="input-field"
                  disabled={isLoading}
                  autoFocus
                  aria-describedby="chat-instructions"
                />
                <button
                  type="submit"
                  className="submit-button"
                  disabled={isLoading}
                  aria-label={isLoading ? "Analyzing trends, please wait" : "Analyze trends for the entered niche"}
                >
                  {isLoading ? 'Analyzing...' : 'Analyze Trends'}
                </button>
              </div>
            </form>

            {isLoading && (
              <div className="loading" role="status" aria-live="polite">
                <div className="loading-spinner" aria-label="Loading spinner"></div>
                <span className="sr-only">Analyzing trends...</span>
              </div>
            )}
          </div>
        </motion.section>
      </main>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1 }}
        className="relative z-10 px-6 py-4 text-white border-t bg-gradient-to-r from-slate-900 to-blue-900 border-white/20"
      >
        <div className="flex items-center justify-between w-full max-w-5xl mx-auto text-sm">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-white" />
            <span className="text-white">AI Powered</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-white" />
            <span className="text-white">Secure</span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-white" />
            <span className="text-white">Fast Performance</span>
          </div>
        </div>
      </motion.footer>
    </div>
  );
};

export default NicheInputPage;
