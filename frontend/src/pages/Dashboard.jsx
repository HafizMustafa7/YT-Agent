import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Plus, PlayCircle, BarChart3, Youtube, Users, Video, ChevronDown, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import apiService from "../features/yt-agent/services/apiService";
import { showErrorToast } from '../lib/errorUtils';
import { tokenService } from '../services/tokenService';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { useTheme } from '../contexts/ThemeContext';
import PageLayout from '../components/PageLayout';
import Header from '../features/yt-agent/components/Header';
import { useSelectedChannel } from '../contexts/SelectedChannelContext';

const Dashboard = () => {
  const {
    channels,
    selectedChannelId,
    setSelectedChannelId,
    refreshChannels,
    loading: channelsLoading
  } = useSelectedChannel();

  const [channelStats, setChannelStats] = useState({});
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const [username, setUsername] = useState('User');
  const { isDarkTheme } = useTheme();
  const [sessionReady, setSessionReady] = useState(false);
  const navigate = useNavigate();
  const dropdownRef = useRef(null);

  // Derived state: find the selected channel object to get its name
  const activeChannel = channels.find(c => c.channel_id === selectedChannelId || c.id === selectedChannelId);
  const selectedChannelName = activeChannel?.channel_name || activeChannel?.snippet?.title || "Select Channel";

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Initialize session
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          navigate("/");
          return;
        }
        setUsername(session.user.email?.split('@')[0] || 'User');
        setSessionReady(true);
      } catch (err) {
        navigate("/");
      }
    };
    initializeSession();
  }, [navigate]);

  // No longer fatching channels here, SelectiveChannelContext handles it.
  // We can still trigger a refresh on mount if we want to ensure freshness
  useEffect(() => {
    if (sessionReady && channels.length === 0) {
      refreshChannels();
    }
  }, [sessionReady, channels.length, refreshChannels]);

  const handleAddChannel = async () => {
    try {
      const data = await apiService.startYouTubeOAuth();
      window.location.href = data.url;
    } catch (err) {
      showErrorToast(err);
    }
  };

  const handleRefresh = async () => {
    try {
      await refreshChannels();
    } catch (err) {
      showErrorToast(err);
    }
  };

  const handleGenerateVideo = () => {
    navigate('/generate-video');
  };
  const handleShowAnalytics = () => navigate('/analytics');

  const displayChannels = channels.map(ch => ({
    id: ch.channel_id,
    name: ch.channel_name,
    status: 'active',
    subscriberCount: ch.subscriber_count || 0,
    videoCount: ch.video_count || 0,
    thumbnailUrl: ch.thumbnail_url
  }));

  return (
    <PageLayout>
      <Header />

      <main className="relative z-10 px-8 py-12 mx-auto max-w-7xl">
        {/* Top Right Channel Selector */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="flex justify-end mb-8"
        >
          <div className="flex items-center gap-3">
            <label className={`font-medium ${isDarkTheme ? 'text-white' : 'text-slate-700'}`}>Active Channel:</label>
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className={`flex items-center justify-between border rounded-xl px-5 py-3 min-w-[280px] focus:outline-none focus:ring-2 transition-all duration-300 backdrop-blur-sm ${isDarkTheme ? 'bg-slate-800/90 border-cyan-500/30 text-white focus:ring-cyan-400/50 hover:border-cyan-400/50' : 'bg-white/90 border-slate-200 text-slate-800 focus:ring-indigo-400/50 hover:border-indigo-400/50'}`}
              >
                <span className="font-medium truncate">{selectedChannelName}</span>
                <ChevronDown className={`w-5 h-5 transition-transform duration-300 ${isDarkTheme ? 'text-cyan-400' : 'text-indigo-600'} ${isDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              {isDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -15, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -15, scale: 0.95 }}
                  transition={{ duration: 0.2, ease: 'easeOut' }}
                  className={`absolute z-50 w-full mt-2 overflow-y-auto border shadow-2xl top-full backdrop-blur-md rounded-xl max-h-64 ${isDarkTheme ? 'bg-slate-800/95 border-cyan-500/30' : 'bg-white/95 border-slate-200'}`}
                >
                  <div className="py-2">
                    {channels.map((ch, index) => (
                      <button
                        key={ch.channel_id}
                        onClick={() => {
                          setSelectedChannelId(ch.channel_id || ch.id);
                          setIsDropdownOpen(false);
                        }}
                        className={`relative flex items-center justify-between w-full px-5 py-3 text-left transition-all duration-200 group ${isDarkTheme ? 'text-white hover:bg-cyan-500/10' : 'text-slate-800 hover:bg-indigo-50'}`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`flex items-center justify-center w-8 h-8 overflow-hidden rounded-full ${isDarkTheme ? 'bg-red-500/20' : 'bg-red-50'}`}>
                            {ch.thumbnail_url ? (
                              <img src={ch.thumbnail_url} alt={ch.channel_name} className="object-cover w-full h-full" />
                            ) : (
                              <Youtube className="w-4 h-4 text-red-500" />
                            )}
                          </div>
                          <span className={`font-medium truncate ${isDarkTheme ? 'group-hover:text-cyan-300' : 'group-hover:text-indigo-600'}`}>{ch.channel_name || ch.snippet?.title}</span>
                        </div>
                        {selectedChannelId === (ch.channel_id || ch.id) && (
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center ${isDarkTheme ? 'bg-cyan-500' : 'bg-indigo-600'}`}>
                            <Check className="w-3 h-3 text-white" />
                          </div>
                        )}
                      </button>
                    ))}
                    <div className={`mx-3 my-2 border-t ${isDarkTheme ? 'border-cyan-500/20' : 'border-slate-100'}`}></div>
                    <button
                      onClick={() => { handleAddChannel(); setIsDropdownOpen(false); }}
                      className={`flex items-center w-full gap-3 px-5 py-3 text-left transition-all duration-200 group ${isDarkTheme ? 'text-cyan-300 hover:bg-cyan-500/10' : 'text-indigo-600 hover:bg-indigo-50'}`}
                    >
                      <div className={`flex items-center justify-center w-8 h-8 rounded-full ${isDarkTheme ? 'bg-cyan-500/20' : 'bg-indigo-600/10'}`}>
                        <Plus className="w-4 h-4" />
                      </div>
                      <span className="font-medium">Add New Channel</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Hero Section */}
        <section className="mt-16 mb-16 text-center">
          <h2 className={`mb-4 text-4xl font-bold md:text-5xl ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
            Welcome to <span className={isDarkTheme ? 'text-cyan-400' : 'text-indigo-600'}>YT Agent</span>
          </h2>
          <p className={`max-w-2xl mx-auto text-xl ${isDarkTheme ? 'text-gray-300' : 'text-slate-600'}`}>
            Your AI-powered YouTube content creation assistant. Manage channels, generate videos, and analyze performance all in one place.
          </p>
        </section>

        {/* Quick Actions */}
        <section className="flex flex-col justify-center gap-6 mb-16 sm:flex-row">
          <Button
            onClick={handleGenerateVideo}
            className={`flex items-center gap-4 px-10 py-6 text-xl font-semibold transition-all duration-300 shadow-xl ${isDarkTheme ? 'bg-gradient-to-r from-cyan-500 to-purple-600 hover:shadow-cyan-500/25' : 'bg-indigo-600 hover:bg-indigo-700 text-white'}`}
          >
            <PlayCircle className="w-6 h-6" />
            Generate Video
          </Button>

          <Button
            onClick={handleShowAnalytics}
            variant="outline"
            className={`flex items-center gap-4 px-10 py-6 text-xl border-2 transition-all ${isDarkTheme ? 'text-white border-white/30 hover:bg-white/10 hover:border-cyan-500/50' : 'text-slate-700 border-slate-200 hover:bg-slate-50 hover:border-indigo-500/50'}`}
          >
            <BarChart3 className="w-6 h-6" />
            Show Analytics
          </Button>
        </section>

        {/* Channel Grid */}
        <section className="mb-16">
          <div className="flex items-center justify-between mb-8">
            <h3 className={`text-3xl font-semibold ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>Your YouTube Channels</h3>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              className={isDarkTheme ? 'text-white border-white/20 hover:bg-white/10' : 'text-slate-600 border-slate-200'}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {displayChannels.map((channel) => (
              <Card key={channel.id} className={`transition-all duration-300 border backdrop-blur-sm hover:scale-105 ${isDarkTheme ? 'bg-slate-800/60 border-white/10 hover:border-cyan-500/50' : 'bg-white/90 border-slate-200 hover:border-indigo-500/50'}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                    <div className={`flex items-center justify-center w-12 h-12 overflow-hidden rounded-full ${isDarkTheme ? 'bg-red-500/20' : 'bg-red-50'}`}>
                      {channel.thumbnailUrl ? (
                        <img src={channel.thumbnailUrl} alt={channel.name} className="object-cover w-full h-full" />
                      ) : (
                        <Youtube className={`w-6 h-6 ${isDarkTheme ? 'text-white' : 'text-red-500'}`} />
                      )}
                    </div>
                    <CardTitle className={`text-lg truncate ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
                      {channel.name}
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-1 text-slate-500">
                      <Users className="w-4 h-4" />
                      {channel.subscriberCount.toLocaleString()} subs
                    </div>
                    <div className="flex items-center gap-1 text-slate-500">
                      <Video className="w-4 h-4" />
                      {channel.videoCount} videos
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${channel.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                      {channel.status}
                    </span>
                    <Button variant="ghost" size="sm" onClick={() => navigate('/analytics')} className="text-xs hover:text-indigo-600">
                      View Stats
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
            {displayChannels.length === 0 && (
              <div className={`col-span-full py-20 text-center border-2 border-dashed rounded-3xl ${isDarkTheme ? 'border-white/10 text-slate-500' : 'border-slate-200 text-slate-400'}`}>
                <Youtube className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p className="text-xl">No channels connected yet</p>
                <Button onClick={handleAddChannel} variant="link" className="mt-2 text-indigo-500">Connect your first channel</Button>
              </div>
            )}
          </div>
        </section>
      </main>
    </PageLayout>
  );
};

export default Dashboard;
