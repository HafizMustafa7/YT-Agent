// src/components/Dashboard/Dashboard.jsx
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Settings, Plus, PlayCircle, BarChart3, Shield, Bot, Zap, HardDrive, Youtube, Users, Video, ChevronDown, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { showErrorToast } from '../lib/errorUtils';
import { tokenService } from '../services/tokenService';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';

// Starfield Background Component
const Starfield = () => {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
      {[...Array(100)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-white rounded-full opacity-20"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, -100, 0],
            opacity: [0.2, 0.8, 0.2],
          }}
          transition={{
            duration: Math.random() * 10 + 10,
            repeat: Infinity,
            delay: Math.random() * 5,
          }}
        />
      ))}
    </div>
  );
};

const Dashboard = () => {
  const [selectedChannel, setSelectedChannel] = useState("Select Channel");
  const [channels, setChannels] = useState([]);
  const [channelStats, setChannelStats] = useState({});
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const [driveStatus, setDriveStatus] = useState({ drive_connected: false, token_valid: false, drive_email: null });
  const [username, setUsername] = useState('User');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(true);
  const [sessionReady, setSessionReady] = useState(false);
  const navigate = useNavigate();
  const dropdownRef = useRef(null);

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

  // ✅ Initialize session and verify token before making API calls
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          navigate("/");
          return;
        }

        // Set username from session
        setUsername(session.user.email?.split('@')[0] || 'User');

        // Mark session as ready
        setSessionReady(true);
        console.log('[Dashboard] Session verified, ready to make API calls');
      } catch (err) {
        console.error('[Dashboard] Session verification failed:', err);
        navigate("/");
      }
    };

    initializeSession();
  }, [navigate]);

  // ✅ Fetch channels from backend with auto-refresh if expired
  useEffect(() => {
    if (!sessionReady) return;

    const fetchChannels = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          navigate("/");
          return;
        }

        const res = await fetch("http://localhost:8000/api/channels/", {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });
        if (!res.ok) throw new Error("Failed to fetch channels");
        const data = await res.json();
        console.log('[Dashboard] Channels data:', data);
        setChannels(data || []);

        // Auto-refresh YouTube tokens if any are expired
        const expiredChannels = data.filter(ch => !ch.token_valid);
        if (expiredChannels.length > 0) {
          console.log('[Dashboard] YouTube tokens expired, attempting refresh...');
          tokenService.refreshYouTubeToken().then(() => {
            // Re-fetch channels after successful refresh
            fetch("http://localhost:8000/api/channels/", {
              headers: {
                Authorization: `Bearer ${session.access_token}`,
              },
            }).then(res => res.ok ? res.json() : null).then(refreshData => {
              if (refreshData) setChannels(refreshData);
            }).catch(err => console.warn('[Dashboard] Failed to re-fetch channels after refresh:', err));
          }).catch(refreshError => {
            console.error('[Dashboard] YouTube token refresh failed:', refreshError);
            // Don't show error toast here to avoid spamming user on every load
            // User can manually reconnect via UI
          });
        }

        // Fetch real-time stats for each channel
        const updatedChannels = await Promise.all(
          data.map(async (channel) => {
            try {
              const statsRes = await fetch(`http://localhost:8000/api/channels/stats/${channel.youtube_channel_id}`, {
                headers: {
                  Authorization: `Bearer ${session.access_token}`,
                },
              });
              if (statsRes.ok) {
                const stats = await statsRes.json();
                return { ...channel, subscriber_count: stats.subscriber_count, video_count: stats.video_count };
              }
            } catch (err) {
              console.warn(`[Dashboard] Failed to fetch stats for channel ${channel.youtube_channel_id}:`, err);
            }
            return channel; // Return original if stats fetch fails
          })
        );

        setChannels(updatedChannels);

        // Set default selected channel if available
        if (updatedChannels.length > 0 && selectedChannel === "Select Channel") {
          setSelectedChannel(updatedChannels[0].youtube_channel_name);
        }
      } catch (err) {
        showErrorToast(err);
      }
    };

    fetchChannels();
  }, [navigate, sessionReady]);

  // ✅ Fetch Drive connection status
  useEffect(() => {
    if (!sessionReady) return;

    const fetchDriveStatus = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          return;
        }

        const res = await fetch("http://localhost:8000/api/drive/status", {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });
        if (!res.ok) throw new Error("Failed to fetch drive status");
        const data = await res.json();
        setDriveStatus(data);

        // Auto-refresh Drive token if expired (non-blocking)
        if (data.drive_connected && !data.token_valid) {
          console.log('[Dashboard] Drive token expired, attempting refresh...');
          tokenService.refreshDriveToken().then(() => {
            // Re-fetch status after successful refresh
            fetch("http://localhost:8000/api/drive/status", {
              headers: {
                Authorization: `Bearer ${session.access_token}`,
              },
            }).then(res => res.ok ? res.json() : null).then(refreshData => {
              if (refreshData) setDriveStatus(refreshData);
            }).catch(err => console.warn('[Dashboard] Failed to re-fetch drive status after refresh:', err));
          }).catch(refreshError => {
            console.error('[Dashboard] Drive token refresh failed:', refreshError);
            // Don't show error toast here to avoid spamming user on every load
            // User can manually reconnect via UI
          });
        }
      } catch (err) {
        showErrorToast(err);
      }
    };

    fetchDriveStatus();
  }, [sessionReady]);

  const handleLogout = async () => {
    await tokenService.logout();
  };

  // ✅ Start OAuth flow
  const handleAddChannel = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      navigate("/");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/api/channels/oauth", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to start OAuth");
      const data = await res.json();
      window.location.href = data.url; // Redirect to Google OAuth
    } catch (err) {
      showErrorToast(err);
    }
  };

  // ✅ Disconnect Drive
  const handleDisconnectDrive = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      navigate("/");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/api/drive/disconnect", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to disconnect Drive");
      // Refresh drive status
      const statusRes = await fetch("http://localhost:8000/api/drive/status", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (statusRes.ok) {
        const data = await statusRes.json();
        setDriveStatus(data);
      }
    } catch (err) {
      showErrorToast(err);
    }
  };

  const handleRefresh = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session || !session.user) return;

    try {
      // Fetch channels
      const channelsRes = await fetch("http://localhost:8000/api/channels/", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (!channelsRes.ok) throw new Error("Failed to fetch channels");
      const channelsData = await channelsRes.json();

      // Fetch real-time stats for each channel
      const updatedChannels = await Promise.all(
        channelsData.map(async (channel) => {
          try {
            const statsRes = await fetch(`http://localhost:8000/api/channels/stats/${channel.youtube_channel_id}`, {
              headers: {
                Authorization: `Bearer ${session.access_token}`,
              },
            });
            if (statsRes.ok) {
              const stats = await statsRes.json();
              return { ...channel, subscriber_count: stats.subscriber_count, video_count: stats.video_count };
            }
          } catch (err) {
            console.warn(`[Dashboard] Failed to fetch stats for channel ${channel.youtube_channel_id}:`, err);
          }
          return channel; // Return original if stats fetch fails
        })
      );

      setChannels(updatedChannels);
    } catch (err) {
      showErrorToast(err);
    }
  };

  const handleGenerateVideo = () => {
    // Navigate to Niche Input Page
    navigate('/generate-video'); // Adjust route as needed
  };

  const handleShowAnalytics = () => {
    // Navigate to Analytics page
    navigate('/analytics');
  };

  // Map channels to display format for grid
  const displayChannels = channels.map(ch => ({
    id: ch.youtube_channel_id,
    name: ch.youtube_channel_name,
    status: 'active',
    subscriberCount: ch.subscriber_count || 0,
    videoCount: ch.video_count || 0,
    thumbnailUrl: ch.thumbnail_url
  }));

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

          {/* Drive Status Indicator */}
          <div
            className="relative cursor-pointer group"
            title={driveStatus.drive_connected ? `Connected to ${driveStatus.drive_email}` : 'Google Drive not connected'}
          >
            <HardDrive
              className={`w-5 h-5 transition-colors ${
                driveStatus.drive_connected
                  ? driveStatus.token_valid
                    ? 'text-green-400'
                    : 'text-yellow-400'
                  : 'text-red-400 opacity-60'
              }`}
            />
            {driveStatus.drive_connected && (
              <div className="absolute w-2 h-2 bg-green-400 rounded-full -top-1 -right-1"></div>
            )}
          </div>

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

                {/* Drive Section */}
                <div className="space-y-3">
                  <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
                    <HardDrive className="w-4 h-4" />
                    Google Drive
                  </h3>
                  
                  {driveStatus.drive_connected ? (
                    <>
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-slate-700/50">
                        <div className={`w-2 h-2 rounded-full ${
                          driveStatus.token_valid ? 'bg-green-400' : 'bg-yellow-400'
                        }`}></div>
                        <span className="text-sm text-white">Connected as: {driveStatus.drive_email}</span>
                      </div>
                      {driveStatus.token_valid ? (
                        <p className="text-xs text-green-400">✓ Access token is valid</p>
                      ) : (
                        <p className="text-xs text-yellow-400">⚠ Token expired - will auto-refresh</p>
                      )}
                      <Button
                        onClick={handleDisconnectDrive}
                        variant="destructive"
                        className="w-full text-white"
                      >
                        Disconnect Drive
                      </Button>
                    </>
                  ) : (
                    <>
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-slate-700/50">
                        <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                        <span className="text-sm text-red-400">Not connected to Google Drive</span>
                      </div>
                      <Button
                        onClick={() => navigate("/connect-drive")}
                        className="w-full text-white bg-blue-500 hover:bg-blue-600"
                      >
                        Connect Drive
                      </Button>
                    </>
                  )}
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
        {/* Top Right Channel Selector */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="flex justify-end mb-8"
        >
          <div className="flex items-center gap-3">
            <label className="font-medium text-white">Active Channel:</label>
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center justify-between text-white bg-gradient-to-r from-slate-800/90 to-slate-700/90 border border-cyan-500/30 rounded-xl px-5 py-3 min-w-[280px] focus:outline-none focus:ring-2 focus:ring-cyan-400/50 hover:border-cyan-400/50 hover:shadow-lg hover:shadow-cyan-500/20 transition-all duration-300 backdrop-blur-sm"
              >
                <span className="font-medium truncate">{selectedChannel}</span>
                <ChevronDown className={`w-5 h-5 text-cyan-400 transition-transform duration-300 ${isDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              {isDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -15, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -15, scale: 0.95 }}
                  transition={{ duration: 0.2, ease: 'easeOut' }}
                  className="absolute z-50 w-full mt-2 overflow-y-auto border shadow-2xl top-full bg-gradient-to-b from-slate-800/95 to-slate-900/95 backdrop-blur-md border-cyan-500/30 rounded-xl shadow-cyan-500/10 max-h-64"
                >
                  <div className="py-2">
                    {channels.map((ch, index) => (
                      <motion.button
                        key={ch.youtube_channel_id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        onClick={() => {
                          setSelectedChannel(ch.youtube_channel_name);
                          setIsDropdownOpen(false);
                        }}
                        className="relative flex items-center justify-between w-full px-5 py-3 text-left text-white transition-all duration-200 hover:bg-gradient-to-r hover:from-cyan-500/20 hover:to-purple-500/20 group"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex items-center justify-center w-8 h-8 overflow-hidden transition-colors rounded-full bg-red-500/20 group-hover:bg-red-500/30">
                            {ch.thumbnail_url ? (
                              <img
                                src={ch.thumbnail_url}
                                alt={`${ch.youtube_channel_name} logo`}
                                className="object-cover w-full h-full"
                                onError={(e) => {
                                  console.error(`[Dashboard] Failed to load thumbnail for ${ch.youtube_channel_name}:`, ch.thumbnail_url, e);
                                  e.target.style.display = 'none';
                                  e.target.nextSibling.style.display = 'flex';
                                }}
                                onLoad={() => console.log(`[Dashboard] Thumbnail loaded for ${ch.youtube_channel_name}:`, ch.thumbnail_url)}
                              />
                            ) : null}
                            <Youtube className="w-4 h-4 text-red-400" style={{ display: ch.thumbnail_url ? 'none' : 'flex' }} />
                          </div>
                          <span className="font-medium truncate transition-colors group-hover:text-cyan-300">{ch.youtube_channel_name}</span>
                        </div>
                        {selectedChannel === ch.youtube_channel_name && (
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="flex items-center justify-center w-5 h-5 rounded-full bg-cyan-500"
                          >
                            <Check className="w-3 h-3 text-white" />
                          </motion.div>
                        )}
                      </motion.button>
                    ))}
                    <div className="mx-3 my-2 border-t border-cyan-500/20"></div>
                    <motion.button
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: channels.length * 0.05 }}
                      onClick={() => {
                        handleAddChannel();
                        setIsDropdownOpen(false);
                      }}
                      className="flex items-center w-full gap-3 px-5 py-3 text-left transition-all duration-200 text-cyan-300 hover:bg-gradient-to-r hover:from-cyan-500/10 hover:to-purple-500/10 group"
                    >
                      <div className="flex items-center justify-center w-8 h-8 transition-colors rounded-full bg-cyan-500/20 group-hover:bg-cyan-500/30">
                        <Plus className="w-4 h-4 text-cyan-400" />
                      </div>
                      <span className="font-medium transition-colors group-hover:text-cyan-200">Add New Channel</span>
                    </motion.button>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
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
            Welcome to <span className="text-cyan-400">YT Agent</span>
          </motion.h2>
          <motion.p
            className="max-w-2xl mx-auto text-xl text-gray-300"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.5 }}
          >
            Your AI-powered YouTube content creation assistant. Manage channels, generate videos, and analyze performance all in one place.
          </motion.p>
        </motion.section>

        {/* Quick Actions */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex flex-col justify-center gap-6 mb-16 sm:flex-row"
        >
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              onClick={handleGenerateVideo}
              className="flex items-center gap-4 px-10 py-6 text-xl font-semibold transition-all duration-300 transform shadow-xl bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 hover:shadow-cyan-500/25 hover:scale-105"
            >
              <PlayCircle className="w-6 h-6" />
              Generate Video
            </Button>
          </motion.div>

          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Button
              onClick={handleShowAnalytics}
              variant="outline"
              className="flex items-center gap-4 px-10 py-6 text-xl text-white border-2 border-white/30 hover:bg-white/10 hover:border-cyan-500/50"
            >
              <BarChart3 className="w-6 h-6" />
              Show Analytics
            </Button>
          </motion.div>
        </motion.section>

        {/* Channel Section */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="mb-16"
        >
          <motion.div
            className="flex items-center justify-between mb-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
          >
            <h3 className="text-3xl font-semibold text-white">Your YouTube Channels</h3>

            <div className="flex items-center space-x-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                className="text-white border-white/20 hover:bg-white/10"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </Button>
            </div>
          </motion.div>



          {/* Channel Grid */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <AnimatePresence>
              {displayChannels.map((channel, index) => (
                <motion.div
                  key={channel.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <Card className="transition-all duration-300 bg-slate-800/60 border-white/20 backdrop-blur-sm hover:border-cyan-500/50 hover:shadow-lg hover:shadow-cyan-500/10 hover:scale-105">
                    <CardHeader className="pb-3">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-12 h-12 overflow-hidden bg-red-500 rounded-full">
                          {channel.thumbnailUrl ? (
                            <img
                              src={channel.thumbnailUrl}
                              alt={`${channel.name} thumbnail`}
                              className="object-cover w-full h-full"
                              onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.nextSibling.style.display = 'flex';
                              }}
                            />
                          ) : null}
                          <Youtube className="w-6 h-6 text-white" style={{ display: channel.thumbnailUrl ? 'none' : 'flex' }} />
                        </div>
                        <CardTitle className="text-lg text-white truncate">
                          {channel.name}
                        </CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1 text-sm text-gray-300">
                          <Users className="w-4 h-4" />
                          {channel.subscriberCount.toLocaleString()} subscribers
                        </div>
                        <div className="flex items-center gap-1 text-sm text-gray-300">
                          <Video className="w-4 h-4" />
                          {channel.videoCount} videos
                        </div>
                      </div>
                      <span className="px-3 py-1 text-sm font-medium text-green-400 rounded-full bg-green-500/20">
                        {channel.status}
                      </span>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </motion.section>


      </main>

            {/* Footer (integrated from old, adapted to theme) */}
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

export default Dashboard;
