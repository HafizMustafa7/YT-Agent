import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Loader2, ArrowLeft, Check, Sparkles, Users, Video, Eye, ThumbsUp, MessageCircle, Youtube, Zap } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { useNavigate, useLocation } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Starfield from '@/components/Starfield';
import apiService from '../features/yt-agent/services/apiService';
import './ResultsScreen.css';

const ResultsScreen = () => {
  const [selectedVideoId, setSelectedVideoId] = useState(null);
  const [topic, setTopic] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  // Get data from navigation state
  const data = location.state?.trendingData;
  const niche = location.state?.niche;

  // Initialize session
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          navigate("/auth");
          return;
        }
        setSessionReady(true);
      } catch (err) {
        console.error('[ResultsScreen] Session verification failed:', err);
        navigate("/auth");
      }
    };

    initializeSession();
  }, [navigate]);

  // Auto-fill topic when a video is selected
  useEffect(() => {
    if (selectedVideoId && data?.trends) {
      const selectedVideo = data.trends.find(v => v.id === selectedVideoId);
      if (selectedVideo) {
        setTopic(selectedVideo.title);
      }
    }
  }, [selectedVideoId, data?.trends]);

  if (!sessionReady) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-purple-900">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!data || !data.trends || data.trends.length === 0) {
    return (
      <div className="relative min-h-screen overflow-hidden text-white bg-gradient-to-br from-slate-900 via-blue-900 to-purple-900">
        <Starfield />
        <div className="relative z-10 px-8 py-12 mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center"
          >
            <h2 className="mb-4 text-2xl font-bold text-white">
              No Trending Videos Found for "{niche || 'your niche'}"
            </h2>
            <p className="mb-8 text-gray-300">Try a different niche or check your connection.</p>
            <Button
              onClick={() => navigate('/niche-input')}
              className="text-white bg-cyan-500 hover:bg-cyan-400"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Search
            </Button>
          </motion.div>
        </div>
      </div>
    );
  }

  const handleSelectVideo = (videoId) => {
    setSelectedVideoId(videoId);
    setError('');
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError('');

    if (!selectedVideoId) {
      setError('Please select a video topic first.');
      return;
    }

    if (!topic.trim()) {
      setError('Please enter a topic for story generation.');
      return;
    }

    setIsLoading(true);
    try {
      const selectedVideo = data.trends.find(v => v.id === selectedVideoId);

      // Call the story generation API via central service
      const creativePreferences = {
        duration_seconds: 60, // Default for shorts
        target_audience: 'general',
        tone: 'engaging'
      };

      const result = await apiService.generateStory(
        topic.trim(),
        selectedVideo,
        creativePreferences
      );

      if (result.success) {
        toast({
          title: "Story Generated Successfully!",
          description: "Your AI story and video frames are ready.",
        });

        // Navigate to the FrameResults page with the generated data
        // Note: The backend returns 'story' object, we pass it as 'data' for compatibility
        navigate('/frame-results', { state: { data: result.story } });
      } else {
        throw new Error('Story generation failed');
      }
    } catch (err) {
      console.error('Story generation failed:', err);
      toast({
        title: "Error",
        description: err.message || "Failed to generate story. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div className="relative min-h-screen overflow-hidden text-white bg-gradient-to-br from-slate-900 via-blue-900 to-purple-900">
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
            className="text-sm opacity-80"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            Trending Results for "{niche}"
          </motion.span>
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
            onClick={() => navigate('/niche-input')}
            variant="ghost"
            className="flex items-center gap-2 px-4 py-2 text-white transition-all duration-300 rounded-lg hover:text-cyan-400 hover:bg-white/10"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Back to Search</span>
          </Button>
        </motion.div>

        {/* Hero Section */}
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mb-16 text-center"
        >
          <motion.h2
            className="mb-4 text-4xl font-bold text-white md:text-5xl"
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
          >
            Trending AI Videos in <span className="text-cyan-400">"{niche}"</span>
          </motion.h2>
          <motion.p
            className="max-w-2xl mx-auto text-xl text-gray-300"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5 }}
          >
            Select a trending video to generate your AI-powered story and video frames.
          </motion.p>
        </motion.section>

        {/* Stats Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="grid grid-cols-1 gap-6 mb-12 md:grid-cols-3"
        >
          <div className="p-6 text-center border bg-gradient-to-r from-cyan-500/20 to-purple-500/20 backdrop-blur-sm border-cyan-500/30 rounded-xl">
            <Video className="w-8 h-8 mx-auto mb-2 text-cyan-400" />
            <div className="text-2xl font-bold text-white">{data.trends.length}</div>
            <div className="text-sm text-gray-300">Videos Found</div>
          </div>
          <div className="p-6 text-center border bg-gradient-to-r from-cyan-500/20 to-purple-500/20 backdrop-blur-sm border-cyan-500/30 rounded-xl">
            <Eye className="w-8 h-8 mx-auto mb-2 text-cyan-400" />
            <div className="text-2xl font-bold text-white">{formatNumber(Math.round(data.averageViews))}</div>
            <div className="text-sm text-gray-300">Avg Views</div>
          </div>
          <div className="p-6 text-center border bg-gradient-to-r from-cyan-500/20 to-purple-500/20 backdrop-blur-sm border-cyan-500/30 rounded-xl">
            <Check className="w-8 h-8 mx-auto mb-2 text-cyan-400" />
            <div className="text-2xl font-bold text-white">{selectedVideoId ? '1' : '0'}</div>
            <div className="text-sm text-gray-300">Selected</div>
          </div>
        </motion.div>

        {/* Video Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="grid grid-cols-1 gap-8 mb-16 md:grid-cols-2 lg:grid-cols-3"
        >
          {data.trends.map((video, index) => {
            const isSelected = selectedVideoId === video.id;

            return (
              <motion.div
                key={video.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className={`bg-slate-800/60 backdrop-blur-sm border rounded-xl overflow-hidden transition-all duration-300 hover:scale-105 ${isSelected ? 'border-cyan-500 shadow-lg shadow-cyan-500/25' : 'border-white/20 hover:border-cyan-500/50'
                  }`}
              >
                <div className="relative bg-black aspect-video">
                  <img
                    src={video.thumbnail}
                    alt={video.title}
                    className="object-cover w-full h-full"
                  />
                  <div className="absolute px-2 py-1 text-xs text-white rounded bottom-2 right-2 bg-black/80">
                    {video.duration}
                  </div>
                  {video.ai_confidence && (
                    <div className="absolute px-2 py-1 text-xs font-semibold text-white rounded-full top-2 left-2 bg-gradient-to-r from-cyan-500 to-purple-600">
                      AI: {video.ai_confidence}%
                    </div>
                  )}
                </div>

                <div className="p-4">
                  <h3 className="mb-2 text-lg font-semibold text-white line-clamp-2">{video.title}</h3>

                  <div className="flex items-center gap-2 mb-3 text-sm text-gray-300">
                    <Youtube className="w-4 h-4" />
                    <span className="truncate">{video.channel}</span>
                  </div>

                  <div className="flex items-center justify-between mb-4 text-sm text-gray-300">
                    <div className="flex items-center gap-1">
                      <Eye className="w-4 h-4" />
                      <span>{formatNumber(video.views)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <ThumbsUp className="w-4 h-4" />
                      <span>{formatNumber(video.likes)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <MessageCircle className="w-4 h-4" />
                      <span>{formatNumber(video.comments)}</span>
                    </div>
                  </div>

                  {video.description && (
                    <p className="mb-4 text-sm text-gray-400 line-clamp-3">
                      {video.description.length > 120
                        ? `${video.description.substring(0, 120)}...`
                        : video.description}
                    </p>
                  )}

                  {video.tags && video.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {video.tags.slice(0, 3).map((tag, idx) => (
                        <span key={idx} className="px-2 py-1 text-xs rounded-full bg-cyan-500/20 text-cyan-300">
                          #{tag}
                        </span>
                      ))}
                      {video.tags.length > 3 && (
                        <span className="px-2 py-1 text-xs text-gray-400 rounded-full bg-gray-500/20">
                          +{video.tags.length - 3}
                        </span>
                      )}
                    </div>
                  )}

                  <Button
                    onClick={() => handleSelectVideo(video.id)}
                    disabled={isLoading}
                    className={`w-full ${isSelected ? 'bg-green-600 hover:bg-green-500' : 'bg-cyan-600 hover:bg-cyan-500'} text-white`}
                  >
                    {isSelected ? (
                      <>
                        <Check className="w-4 h-4 mr-2" />
                        Selected
                      </>
                    ) : (
                      'Select Topic'
                    )}
                  </Button>
                </div>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Story Generation Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="p-8 border bg-gradient-to-r from-cyan-500/10 to-purple-500/10 backdrop-blur-sm border-cyan-500/30 rounded-xl"
        >
          <div className="mb-8 text-center">
            <h3 className="mb-2 text-2xl font-bold text-white">Generate Your Story</h3>
            <p className="text-gray-300">Select a video above or enter your custom topic</p>
          </div>

          <form onSubmit={handleGenerate} className="max-w-md mx-auto">
            <div className="mb-6">
              <label htmlFor="topic-input" className="block mb-2 font-medium text-white">
                Story Topic
              </label>
              <input
                id="topic-input"
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Enter your topic or modify the selected one..."
                className="w-full px-4 py-3 text-white placeholder-gray-400 border rounded-lg bg-slate-800/50 border-cyan-500/30 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                disabled={isLoading}
              />
              {selectedVideoId && (
                <p className="mt-2 text-xs text-cyan-300">
                  Topic auto-filled from selected video. You can edit it.
                </p>
              )}
            </div>

            {error && (
              <div className="px-4 py-3 mb-6 text-red-300 border rounded-lg bg-red-500/20 border-red-500/30">
                <div className="flex items-center gap-2">
                  <span>⚠️</span>
                  <span>{error}</span>
                </div>
              </div>
            )}

            <Button
              type="submit"
              disabled={!topic.trim() || isLoading}
              className="w-full py-3 text-lg font-semibold text-white bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 mr-2" />
                  Generate Story & Frames
                </>
              )}
            </Button>
          </form>
        </motion.div>
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
            <Zap className="w-5 h-5 text-cyan-400" />
            <span className="text-white">AI Powered</span>
          </div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            <span className="text-white">Creative Generation</span>
          </div>
          <div className="flex items-center gap-2">
            <Video className="w-5 h-5 text-cyan-400" />
            <span className="text-white">Video Creation</span>
          </div>
        </div>
      </motion.footer>
    </div>
  );
};

export default ResultsScreen;