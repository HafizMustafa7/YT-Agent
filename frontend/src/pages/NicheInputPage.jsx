import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Input } from '@/components/ui/input'; // From shadcn/ui
import { Button } from '@/components/ui/button'; // From shadcn/ui
import { Loader2, Settings, Bot, Shield, Zap, ArrowLeft } from 'lucide-react'; // For loader icon and footer icons
import { useToast } from '@/components/ui/use-toast'; // From shadcn/ui for toasts
import { useNavigate } from 'react-router-dom'; // Assuming React Router for navigation
import { Switch } from '@/components/ui/switch'; // From shadcn/ui
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'; // From shadcn/ui
import { supabase } from '../supabaseClient'; // For session management
import Starfield from '@/components/Starfield'; // Consistent starfield component

// Mock API function
const fetchTrendingVideos = async (niche) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Simulate API response with mock data
      resolve({
        data: [
          { title: 'Top 10 Space Gadgets', views: '1.2M' },
          { title: 'Exploring Mars in 2024', views: '850K' },
        ],
      });
    }, 1500); // 1.5 seconds delay
  });
};

const NicheInputPage = () => {
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
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

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
    setError(''); // Clear error on change
  };

  const handleSearch = async () => {
    if (!inputValue.trim()) {
      setError('Input is required.');
      const inputElement = document.getElementById('niche-input');
      if (inputElement) {
        inputElement.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(10px)' }, { transform: 'translateX(-10px)' }, { transform: 'translateX(0)' }], { duration: 300 });
      }
      toast({ title: 'Error', description: 'Input is required.', variant: 'destructive' });
      return;
    }

    if (inputValue.trim().length < 3) {
      setError('Input must be at least 3 characters.');
      toast({ title: 'Error', description: 'Input must be at least 3 characters.', variant: 'destructive' });
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const result = await fetchTrendingVideos(inputValue);
      // On success, navigate to TopicSelectionPage
      setIsLoading(false);
      navigate('/dashboard', { state: { niche: inputValue, trendingData: result.data } }); // Pass data to dashboard for now
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
            className="text-sm opacity-80 hidden md:block"
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
            <DialogContent className="bg-gradient-to-br from-slate-900 to-blue-900 border-cyan-500/50 backdrop-blur-sm max-w-md">
              <DialogHeader>
                <DialogTitle className="text-white">General Settings</DialogTitle>
              </DialogHeader>
              <div className="space-y-6">
                {/* Theme Section */}
                <div className="space-y-2">
                  <h3 className="text-white font-semibold text-lg">Appearance</h3>
                  <div className="flex items-center justify-between">
                    <span className="text-white">Dark Theme</span>
                    <Switch checked={isDarkTheme} onCheckedChange={setIsDarkTheme} />
                  </div>
                </div>

                {/* Account Section */}
                <div className="space-y-3 pt-4 border-t border-white/20">
                  <h3 className="text-white font-semibold text-lg">Account</h3>
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
            className="flex items-center gap-2 text-white hover:text-cyan-400 hover:bg-white/10 transition-all duration-300 rounded-lg px-4 py-2"
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
          className="text-center mb-16 mt-16"
        >
          <motion.h2
            className="text-4xl md:text-5xl font-bold text-white mb-4"
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
          >
            Enter a Niche
          </motion.h2>
          <motion.p
            className="text-xl text-gray-300 max-w-2xl mx-auto"
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
          <div className="w-full max-w-md bg-slate-800/60 backdrop-blur-md border border-cyan-500/30 rounded-xl p-8 shadow-lg shadow-cyan-500/20">
            <div className="space-y-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.4 }}
              >
                <Input
                  id="niche-input"
                  type="text"
                  placeholder="e.g. Tech reviews, Fitness, Travel, etc."
                  value={inputValue}
                  onChange={handleInputChange}
                  className="w-full bg-transparent border-cyan-400 text-white placeholder-gray-400 focus:border-cyan-300 focus:ring-cyan-500 transition-shadow shadow-glow rounded-lg py-6 text-lg"
                />
                {error && <p className="text-red-400 text-sm mt-2 text-center">{error}</p>}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.6 }}
              >
                <Button
                  onClick={handleSearch}
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-glow hover:scale-105 transition-all duration-300 rounded-xl py-6 text-lg font-semibold"
                  whileHover={{ scale: 1.05, boxShadow: '0 0 15px cyan' }}
                  whileTap={{ scale: 0.95 }}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Fetching...
                    </>
                  ) : (
                    'Search'
                  )}
                </Button>
              </motion.div>
            </div>

            {/* Loading State */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="mt-8 flex flex-col items-center"
              >
                <Loader2 className="h-12 w-12 animate-spin text-cyan-400" />
                <p className="mt-4 text-cyan-300 text-lg">Fetching trending videos...</p>
              </motion.div>
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
