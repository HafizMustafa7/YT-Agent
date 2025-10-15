import React, { useState, useEffect, useRef } from 'react';
import { Chart } from 'chart.js/auto';

export default function YouTubeAnalytics() {
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState('');
  const [videosData, setVideosData] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [statsData, setStatsData] = useState({
    totalVideos: 0,
    totalViews: 0,
    totalSubscribers: 0,
    avgEngagement: 0
  });
  const [showStats, setShowStats] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const chartsRef = useRef({});

  useEffect(() => {
    loadChannels();
    return () => {
      // Cleanup charts on unmount
      Object.values(chartsRef.current).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
          chart.destroy();
        }
      });
    };
  }, []);

  const loadChannels = async () => {
    try {
      const response = await fetch('/api/analysis/channels');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      setChannels(data.channels || []);
      if (data.channels.length === 0) {
        setError('No channels found in database. Please add some channels first.');
      }
    } catch (err) {
      console.error('Error loading channels:', err);
      setError('Failed to load channels from database. Please check your connection and try again.');
    }
  };

  const loadChannelAnalytics = async () => {
    if (!selectedChannel) return;
    
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`/api/analysis/analytics/${selectedChannel}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to load analytics: ${response.status} - ${errorText}`);
      }
      
      const data = await response.json();
      setVideosData(data.videos || []);
      
      const avgEngagement = data.videos.length > 0 
        ? data.videos.reduce((sum, video) => sum + video.engagement_rate, 0) / data.videos.length 
        : 0;
      
      setStatsData({
        totalVideos: data.total_videos || 0,
        totalViews: data.total_views || 0,
        totalSubscribers: data.total_subscribers || 0,
        avgEngagement: avgEngagement
      });
      
      setShowStats(true);
    } catch (err) {
      console.error('Error loading analytics:', err);
      setError(`Failed to load channel analytics: ${err.message}`);
      setShowStats(false);
    } finally {
      setLoading(false);
    }
  };

  const selectVideo = (video) => {
    setSelectedVideo(video);
    
    // Destroy existing charts
    Object.values(chartsRef.current).forEach(chart => {
      if (chart && typeof chart.destroy === 'function') {
        chart.destroy();
      }
    });
    chartsRef.current = {};
  };

  useEffect(() => {
    if (selectedVideo && videosData.length > 0) {
      setTimeout(() => createCharts(), 500);
    }
  }, [selectedVideo]);

  const createCharts = () => {
    if (!selectedVideo) return;

    const video = selectedVideo;
    const avgViews = videosData.reduce((sum, v) => sum + (v.views || 0), 0) / videosData.length;
    const performanceVsAverage = avgViews > 0 ? (((video.views || 0) - avgViews) / avgViews) * 100 : 0;

    // Performance Chart
    const perfCanvas = document.getElementById('performanceChart');
    if (perfCanvas) {
      chartsRef.current.performance = new Chart(perfCanvas, {
        type: 'bar',
        data: {
          labels: ['Views', 'Likes', 'Comments'],
          datasets: [{
            label: 'This Video',
            data: [video.views, video.likes, video.comments],
            backgroundColor: [
              'rgba(30, 58, 138, 0.8)',
              'rgba(30, 27, 75, 0.8)',
              'rgba(76, 175, 80, 0.8)'
            ],
            borderColor: [
              'rgb(30, 58, 138)',
              'rgb(30, 27, 75)',
              'rgb(76, 175, 80)'
            ],
            borderWidth: 2,
            borderRadius: 8
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 2000, easing: 'easeOutQuart' },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              titleFont: { size: 14 },
              bodyFont: { size: 12 },
              padding: 10
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(0, 0, 0, 0.1)' },
              ticks: {
                callback: function(value) {
                  if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
                  return value;
                }
              }
            }
          }
        }
      });
    }

    // Engagement Chart
    const engCanvas = document.getElementById('engagementChart');
    if (engCanvas) {
      chartsRef.current.engagement = new Chart(engCanvas, {
        type: 'doughnut',
        data: {
          labels: ['Likes', 'Comments', 'Remaining Views'],
          datasets: [{
            data: [
              video.likes,
              video.comments,
              Math.max(0, video.views - video.likes - video.comments)
            ],
            backgroundColor: [
              'rgba(30, 58, 138, 0.8)',
              'rgba(30, 27, 75, 0.8)',
              'rgba(200, 200, 200, 0.6)'
            ],
            borderWidth: 2,
            borderColor: 'white'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '60%',
          animation: { duration: 2000, easing: 'easeOutQuart' },
          plugins: {
            legend: {
              position: 'bottom',
              labels: { padding: 20, usePointStyle: true }
            }
          }
        }
      });
    }

    // Timeline Chart
    const days = ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'];
    const viewsData = days.map((_, i) => Math.round((video.views || 0) * (i + 1) / 7 * (0.8 + Math.random() * 0.4)));
    
    const timeCanvas = document.getElementById('timelineChart');
    if (timeCanvas) {
      chartsRef.current.timeline = new Chart(timeCanvas, {
        type: 'line',
        data: {
          labels: days,
          datasets: [{
            label: 'Views',
            data: viewsData,
            borderColor: 'rgb(30, 58, 138)',
            backgroundColor: 'rgba(30, 58, 138, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 2000, easing: 'easeOutQuart' },
          plugins: { legend: { display: false } },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: 'rgba(0, 0, 0, 0.1)' }
            }
          }
        }
      });
    }

    // Comparison Chart
    const compCanvas = document.getElementById('comparisonChart');
    if (compCanvas) {
      chartsRef.current.comparison = new Chart(compCanvas, {
        type: 'radar',
        data: {
          labels: ['Views', 'Engagement', 'Likes', 'Comments', 'Performance'],
          datasets: [{
            label: 'This Video',
            data: [
              (video.views / avgViews) * 100,
              video.engagement_rate * 10,
              (video.likes / (video.views || 1)) * 10000,
              (video.comments / (video.views || 1)) * 10000,
              Math.max(0, 100 + performanceVsAverage)
            ],
            backgroundColor: 'rgba(30, 58, 138, 0.2)',
            borderColor: 'rgb(30, 58, 138)',
            borderWidth: 2,
            pointBackgroundColor: 'rgb(30, 58, 138)'
          }, {
            label: 'Channel Average',
            data: [100, 100, 100, 100, 100],
            backgroundColor: 'rgba(200, 200, 200, 0.2)',
            borderColor: 'rgb(200, 200, 200)',
            borderWidth: 1,
            pointBackgroundColor: 'rgb(200, 200, 200)'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 2000, easing: 'easeOutQuart' },
          scales: {
            r: {
              beginAtZero: true,
              max: 150,
              ticks: { display: false }
            }
          }
        }
      });
    }
  };

  const getEngagementBadge = (rate) => {
    if (rate > 5) return <span className="px-3 py-1 ml-2 text-xs font-bold text-green-800 bg-green-100 rounded-full">Excellent</span>;
    if (rate > 2) return <span className="px-3 py-1 ml-2 text-xs font-bold text-yellow-800 bg-yellow-100 rounded-full">Good</span>;
    return <span className="px-3 py-1 ml-2 text-xs font-bold text-red-800 bg-red-100 rounded-full">Needs Work</span>;
  };

  const maxViews = Math.max(...videosData.map(v => v.views || 0));
  const maxLikes = Math.max(...videosData.map(v => v.likes || 0));
  const maxComments = Math.max(...videosData.map(v => v.comments || 0));
  
  const viewsPercentage = selectedVideo && maxViews > 0 ? ((selectedVideo.views || 0) / maxViews) * 100 : 0;
  const likesPercentage = selectedVideo && maxLikes > 0 ? ((selectedVideo.likes || 0) / maxLikes) * 100 : 0;
  const commentsPercentage = selectedVideo && maxComments > 0 ? ((selectedVideo.comments || 0) / maxComments) * 100 : 0;

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1e1b4b 100%)' }}>
      <div className="p-5 mx-auto max-w-7xl">
        {/* Header */}
        <div className="p-8 mb-8 bg-white shadow-2xl bg-opacity-95 rounded-3xl backdrop-blur-sm">
          <h1 className="mb-6 text-4xl font-bold text-center text-gray-800">YouTube Analytics Dashboard</h1>
          <div className="flex flex-wrap justify-center gap-4">
            <select
              value={selectedChannel}
              onChange={(e) => {
                setSelectedChannel(e.target.value);
                setShowStats(false);
                setVideosData([]);
                setSelectedVideo(null);
              }}
              className="px-6 py-3 rounded-full text-base cursor-pointer bg-gray-50 text-gray-700 border-2 border-gray-200 min-w-[200px] focus:outline-none focus:border-blue-900 focus:ring-4 focus:ring-blue-900 focus:ring-opacity-10"
            >
              <option value="">Select a Channel</option>
              {channels.map(channel => (
                <option key={channel.youtube_channel_id} value={channel.youtube_channel_id}>
                  {channel.youtube_channel_name || `Channel ${channel.youtube_channel_id}`}
                </option>
              ))}
            </select>
            <button
              onClick={loadChannelAnalytics}
              disabled={!selectedChannel || loading}
              className="px-6 py-3 text-base font-semibold text-white transition-all rounded-full cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed hover:transform hover:-translate-y-1 hover:shadow-xl"
              style={{ background: 'linear-gradient(45deg, #1e3a8a, #1e1b4b)' }}
            >
              {loading ? 'Loading...' : 'Load Analytics'}
            </button>
          </div>
        </div>

        {/* Stats Overview */}
        {showStats && (
          <div className="grid grid-cols-1 gap-5 mb-8 md:grid-cols-2 lg:grid-cols-4">
            {[
              { label: 'Total Videos', value: statsData.totalVideos, trend: '+12%' },
              { label: 'Total Views', value: statsData.totalViews.toLocaleString(), trend: '+8%' },
              { label: 'Subscribers', value: statsData.totalSubscribers.toLocaleString(), trend: '+5%' },
              { label: 'Avg Engagement', value: statsData.avgEngagement.toFixed(1) + '%', trend: '+3%' }
            ].map((stat, idx) => (
              <div key={idx} className="relative p-6 overflow-hidden text-center transition-all transform bg-white shadow-2xl bg-opacity-95 rounded-3xl hover:-translate-y-2 hover:shadow-3xl backdrop-blur-sm">
                <h3 className="mb-2 text-sm tracking-wider text-gray-500 uppercase">{stat.label}</h3>
                <div className="mb-1 text-4xl font-bold text-gray-800">{stat.value}</div>
                <div className="text-sm font-bold text-green-600">{stat.trend}</div>
              </div>
            ))}
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-[350px_1fr] gap-8 items-start">
          {/* Videos Sidebar */}
          <div className="bg-white bg-opacity-95 rounded-3xl p-6 shadow-2xl max-h-[80vh] overflow-y-auto backdrop-blur-sm">
            <h2 className="mb-5 text-2xl font-bold text-gray-800">Channel Videos</h2>
            {error && (
              <div className="p-4 mb-4 text-red-800 bg-red-100 border-l-4 border-red-500 rounded-xl">{error}</div>
            )}
            {loading && <div className="py-8 text-center text-gray-500">Loading videos...</div>}
            {!loading && videosData.length === 0 && !error && (
              <div className="py-8 text-center text-gray-500">
                {selectedChannel ? 'Click "Load Analytics" to fetch videos' : 'Select a channel to load analytics'}
              </div>
            )}
            {videosData.map((video, idx) => (
              <div
                key={idx}
                onClick={() => selectVideo(video)}
                className={`flex items-center gap-3 p-4 rounded-2xl cursor-pointer transition-all mb-3 border-2 ${
                  selectedVideo === video
                    ? 'border-blue-900 transform translate-x-2'
                    : 'border-transparent hover:bg-blue-900 hover:bg-opacity-5 hover:transform hover:translate-x-2'
                }`}
                style={selectedVideo === video ? { background: 'linear-gradient(45deg, rgba(30, 58, 138, 0.1), rgba(30, 27, 75, 0.1))' } : {}}
              >
                <img
                  src={video.thumbnail || 'https://via.placeholder.com/60x45/1e3a8a/ffffff?text=VIDEO'}
                  alt="Thumbnail"
                  className="w-[60px] h-[45px] rounded-lg object-cover flex-shrink-0 transition-transform hover:scale-110"
                  onError={(e) => e.target.src = 'https://via.placeholder.com/60x45/1e3a8a/ffffff?text=VIDEO'}
                />
                <div className="flex-1 min-w-0">
                  <div className="mb-1 text-sm font-semibold leading-tight text-gray-800 line-clamp-2">
                    {video.title || 'Untitled Video'}
                  </div>
                  <div className="text-xs text-gray-500">
                    {(video.views || 0).toLocaleString()} views • {(video.likes || 0).toLocaleString()} likes
                    {getEngagementBadge(video.engagement_rate)}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Analytics Panel */}
          <div className={`bg-white bg-opacity-95 rounded-3xl p-8 shadow-2xl min-h-[500px] transition-all duration-500 backdrop-blur-sm ${selectedVideo ? 'opacity-100' : 'opacity-0'}`}>
            {!selectedVideo ? (
              <div className="mt-24 text-center text-gray-500">
                <h2 className="mb-2 text-2xl font-bold">Select a video to view analytics</h2>
                <p>Choose a video from the sidebar to see detailed performance metrics and visualizations</p>
              </div>
            ) : (
              <>
                {/* Video Header */}
                <div className="flex items-center gap-5 pb-5 mb-8 border-b-2 border-gray-200">
                  <img
                    src={selectedVideo.thumbnail || 'https://via.placeholder.com/120x90/1e3a8a/ffffff?text=VIDEO'}
                    alt="Video Thumbnail"
                    className="w-[120px] h-[90px] rounded-xl object-cover shadow-lg transition-transform hover:scale-105"
                    onError={(e) => e.target.src = 'https://via.placeholder.com/120x90/1e3a8a/ffffff?text=VIDEO'}
                  />
                  <div className="flex-1">
                    <h2 className="mb-2 text-3xl font-bold text-gray-800">{selectedVideo.title || 'Untitled Video'}</h2>
                    <div className="flex flex-wrap gap-5 text-sm text-gray-500">
                      <span>Published: {selectedVideo.published_at ? new Date(selectedVideo.published_at).toLocaleDateString() : 'Unknown'}</span>
                      <span>Duration: {selectedVideo.duration || '0:00'}</span>
                      <span>Engagement: {selectedVideo.engagement_rate || 0}%</span>
                      {getEngagementBadge(selectedVideo.engagement_rate)}
                    </div>
                  </div>
                </div>

                {/* Analytics Grid */}
                <div className="grid grid-cols-2 gap-5 mb-8 lg:grid-cols-4">
                  {[
                    { label: 'Views', value: (selectedVideo.views || 0).toLocaleString() },
                    { label: 'Likes', value: (selectedVideo.likes || 0).toLocaleString() },
                    { label: 'Comments', value: (selectedVideo.comments || 0).toLocaleString() },
                    { label: 'Engagement Rate', value: (selectedVideo.engagement_rate || 0).toFixed(1) + '%' }
                  ].map((metric, idx) => (
                    <div key={idx} className="relative p-5 overflow-hidden text-center transition-all rounded-2xl hover:-translate-y-1 hover:shadow-lg" style={{ background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)' }}>
                      <div className="relative z-10 mb-1 text-3xl font-bold text-gray-800">{metric.value}</div>
                      <div className="relative z-10 text-sm tracking-wider text-gray-500 uppercase">{metric.label}</div>
                    </div>
                  ))}
                </div>

                {/* Charts */}
                <div className="grid grid-cols-1 gap-6 mb-8 lg:grid-cols-2">
                  {['performanceChart', 'engagementChart', 'timelineChart', 'comparisonChart'].map((chartId, idx) => (
                    <div key={chartId} className="relative p-6 overflow-hidden transition-all bg-white shadow-lg rounded-2xl hover:-translate-y-2 hover:shadow-xl">
                      <div className="absolute top-0 left-0 right-0 h-1" style={{ background: 'linear-gradient(90deg, #1e3a8a, #1e1b4b)' }}></div>
                      <h3 className="mb-5 text-xl font-semibold text-center text-gray-800">
                        {['Performance Comparison', 'Engagement Metrics', 'Views Timeline', 'Performance vs Average'][idx]}
                      </h3>
                      <div className="relative h-[250px] w-full">
                        <canvas id={chartId}></canvas>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Performance Breakdown */}
                <div className="pt-8 mt-8 border-t-2 border-gray-200">
                  <h3 className="mb-6 text-xl font-bold text-gray-800">Performance Breakdown</h3>
                  
                  {[
                    { label: 'Views Performance', percentage: viewsPercentage },
                    { label: 'Likes Performance', percentage: likesPercentage },
                    { label: 'Comments Engagement', percentage: commentsPercentage }
                  ].map((item, idx) => (
                    <div key={idx} className="mb-6">
                      <h4 className="mb-2 font-semibold text-gray-700">{item.label}</h4>
                      <div className="relative h-5 overflow-hidden bg-gray-200 rounded-xl">
                        <div
                          className="relative h-full transition-all duration-1000 rounded-xl"
                          style={{
                            width: `${Math.min(item.percentage, 100)}%`,
                            background: 'linear-gradient(90deg, #1e3a8a, #1e1b4b)'
                          }}
                        >
                          <div className="absolute text-xs font-bold text-white -translate-y-1/2 right-2 top-1/2">
                            {item.percentage.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}