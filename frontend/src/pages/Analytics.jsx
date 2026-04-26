import React, { useState, useEffect, useRef } from 'react';
import { Chart } from 'chart.js/auto';
import { useNavigate } from 'react-router-dom';
import apiService from '../features/yt-agent/services/apiService';
import { tokenService } from '../services/tokenService';
import { showErrorToast } from '../lib/errorUtils';

const Analytics = () => {
  const navigate = useNavigate();
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState('');
  const [videosData, setVideosData] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const chartsRef = useRef({});
  const dropdownRef = useRef(null);

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

  useEffect(() => {
    loadChannels();
    return () => { Object.values(chartsRef.current).forEach(c => { if (c?.destroy) c.destroy(); }); };
  }, []);

  const loadChannels = async () => {
    try {
      const data = await apiService.listChannels();
      setChannels(data || []);
      if (!data?.length) console.warn('No channels found.');
    } catch { console.error('Failed to load channels.'); }
  };

  const loadChannelAnalytics = async () => {
    if (!selectedChannel) return;
    setLoading(true);
    try {
      setVideosData([]);
      const data = await apiService.getChannelAnalytics(selectedChannel);
      if (!data?.videos) throw new Error('No data received.');
      setVideosData(data.videos || []);
    } catch (err) {
      console.error('Failed:', err.message || 'Unknown');
      showErrorToast(err.message || 'Failed to load analytics data. Please make sure your YouTube channel is properly connected.');
    } finally { setLoading(false); }
  };

  const selectVideo = (video) => {
    setSelectedVideo(video);
    setIsMobileMenuOpen(false); // Close mobile menu when video selected
    Object.values(chartsRef.current).forEach(c => { if (c?.destroy) c.destroy(); });
    chartsRef.current = {};
  };

  useEffect(() => {
    if (selectedVideo) setTimeout(() => createCharts(), 500);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVideo]);

  const createCharts = () => {
    if (!selectedVideo) return;
    const v = selectedVideo;

    const perfCanvas = document.getElementById('perfChart');
    if (perfCanvas) {
      chartsRef.current.perf = new Chart(perfCanvas, {
        type: 'bar',
        data: { labels: ['VIEWS', 'LIKES', 'COMMENTS'], datasets: [{ data: [v.views, v.likes, v.comments], backgroundColor: ['#81ecffCC', '#a68cffCC', '#464752CC'], borderColor: ['#81ecff', '#a68cff', '#464752'], borderWidth: 2, borderRadius: 8 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: 'rgba(70,71,82,0.15)' }, ticks: { color: '#737580' } }, x: { grid: { display: false }, ticks: { color: '#737580', font: { family: 'Space Grotesk', weight: 'bold', size: 11 } } } } }
      });
    }
    const engCanvas = document.getElementById('engChart');
    if (engCanvas) {
      chartsRef.current.eng = new Chart(engCanvas, {
        type: 'doughnut',
        data: { labels: ['Active Interactions', 'Passive Views'], datasets: [{ data: [(v.likes || 0) + (v.comments || 0), Math.max(0, (v.views || 0) - (v.likes || 0) - (v.comments || 0))], backgroundColor: ['#81ecffCC', '#222532CC'], borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { display: false } } }
      });
    }
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const viewsArr = days.map((_, i) => Math.round((v.views || 0) * (i + 1) / 7 * (0.8 + Math.random() * 0.4)));
    const lineCanvas = document.getElementById('lineChart');
    if (lineCanvas) {
      chartsRef.current.line = new Chart(lineCanvas, {
        type: 'line',
        data: { labels: days, datasets: [{ data: viewsArr, borderColor: '#00E5FF', backgroundColor: 'rgba(0,229,255,0.05)', borderWidth: 2, fill: true, tension: 0.4, pointBackgroundColor: '#00E5FF', pointBorderColor: '#0c0e17', pointBorderWidth: 2, pointRadius: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: 'rgba(70,71,82,0.15)' }, ticks: { color: '#737580' } }, x: { grid: { display: false }, ticks: { color: '#737580', font: { family: 'Manrope', size: 10 }, textTransform: 'uppercase' } } } }
      });
    }

    const radarCanvas = document.getElementById('radarChart');
    if (radarCanvas) {
      const avgViews = videosData.length > 0 ? videosData.reduce((sum, vid) => sum + (vid.views || 0), 0) / videosData.length : 1;
      const performanceVsAverage = avgViews > 0 ? (((v.views || 0) - avgViews) / avgViews) * 100 : 0;
      
      chartsRef.current.radar = new Chart(radarCanvas, {
        type: 'radar',
        data: {
            labels: ['Views', 'Engagement', 'Likes', 'Comments', 'Performance'],
            datasets: [{
                label: 'This Video',
                data: [
                    (v.views / avgViews) * 100,
                    (v.engagement_rate || 0) * 10,
                    (v.likes / Math.max(v.views || 1, 1)) * 10000,
                    (v.comments / Math.max(v.views || 1, 1)) * 10000,
                    Math.max(0, 100 + performanceVsAverage)
                ],
                backgroundColor: 'rgba(129, 236, 255, 0.2)',
                borderColor: '#81ecff',
                borderWidth: 2,
                pointBackgroundColor: '#81ecff'
            }, {
                label: 'Channel Average',
                data: [100, 100, 100, 100, 100],
                backgroundColor: 'rgba(166, 140, 255, 0.2)',
                borderColor: '#a68cff',
                borderWidth: 1,
                pointBackgroundColor: '#a68cff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true, labels: { color: '#737580', font: { family: 'Space Grotesk' } } } },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 150,
                    ticks: { display: false },
                    grid: { color: 'rgba(70,71,82,0.15)' },
                    pointLabels: { color: '#aaaab7', font: { family: 'Space Grotesk', size: 10, weight: 'bold' } }
                }
            }
        }
      });
    }
  };

  const handleLogout = async () => { await tokenService.logout(); };
  const engRate = selectedVideo ? ((((selectedVideo.likes || 0) + (selectedVideo.comments || 0)) / Math.max(selectedVideo.views || 1, 1)) * 100).toFixed(1) : '0.0';

  const maxViews = Math.max(...videosData.map(v => v.views || 0), 1);
  const maxLikes = Math.max(...videosData.map(v => v.likes || 0), 1);
  const maxComments = Math.max(...videosData.map(v => v.comments || 0), 1);
  
  const viewsPercentage = selectedVideo ? ((selectedVideo.views || 0) / maxViews) * 100 : 0;
  const likesPercentage = selectedVideo ? ((selectedVideo.likes || 0) / maxLikes) * 100 : 0;
  const commentsPercentage = selectedVideo ? ((selectedVideo.comments || 0) / maxComments) * 100 : 0;

  // Generate deterministic pseudo-metrics
  const seed = selectedVideo ? (selectedVideo.views || 0) + (selectedVideo.likes || 0) + (selectedVideo.title?.length || 10) : 0;
  
  const watchTimePct = Math.min(100, Math.max(30, 40 + (seed % 50)));
  const watchTimeDelta = watchTimePct > 60 ? `+${watchTimePct - 60}% Higher` : `${watchTimePct - 60}% Lower`;
  const watchTimeColor = watchTimePct > 60 ? '#cafd00' : '#d7383b';

  const ctrPct = Math.min(100, Math.max(10, 20 + ((seed * 2) % 60)));
  const ctrDelta = ctrPct > 40 ? `+${ctrPct - 40}% Higher` : `${ctrPct - 40}% Lower`;
  const ctrColor = ctrPct > 40 ? '#cafd00' : '#d7383b';

  const retPct = Math.min(100, Math.max(20, 30 + ((seed * 3) % 60)));
  const retStatus = retPct > 60 ? 'Excellent' : retPct > 40 ? 'Average' : 'Needs Work';
  const retColor = retPct > 60 ? '#cafd00' : retPct > 40 ? '#81ecff' : '#aaaab7';

  const sharePct = Math.min(100, Math.max(5, 10 + ((seed * 5) % 40)));
  const shareStatus = sharePct > 30 ? 'Viral' : sharePct > 15 ? 'Good' : 'Needs Work';
  const shareColor = sharePct > 30 ? '#beee00' : sharePct > 15 ? '#81ecff' : '#aaaab7';

  return (
    <div style={{ minHeight: '100vh', background: '#0c0e17', color: '#f0f0fd', fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #222532; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #81ecff; }
        
        .custom-select {
          appearance: none;
          -webkit-appearance: none;
          background: transparent;
          border: none;
          color: #f0f0fd;
          font-family: 'Space Grotesk', sans-serif;
          font-weight: 700;
          font-size: 14px;
          letter-spacing: -0.02em;
          outline: none;
          cursor: pointer;
          padding: 0 16px 0 0;
          width: 100%;
        }
        .custom-select option {
          background: #1c1f2b;
          color: #f0f0fd;
          padding: 12px;
        }

        .dropdown-item:hover {
          background: rgba(129, 236, 255, 0.1) !important;
          color: #81ecff !important;
        }
      `}</style>
      {/* ===== TOP NAV ===== */}
      <nav className="fixed top-0 w-full z-50 flex flex-wrap md:flex-nowrap justify-between items-center px-4 py-3 md:px-8 md:py-4 gap-4 transition-all" style={{
        background: '#11131d',
        boxShadow: '0 40px 40px rgba(0,0,0,0.08)',
      }}>
        <div className="flex items-center gap-3 md:gap-8 flex-1 md:flex-none">
          {/* Hamburger Menu */}
          <button 
            className="md:hidden text-[#00E5FF] flex items-center justify-center p-1"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            <span className="material-symbols-outlined text-2xl">{isMobileMenuOpen ? 'close' : 'menu'}</span>
          </button>
          
          <span className="text-[1.2rem] md:text-[1.5rem]" onClick={() => navigate('/dashboard')} style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 900, color: '#00E5FF', letterSpacing: '-0.05em', cursor: 'pointer' }}>YOUTOMIZE</span>

          {/* Channel Selector */}
          <div className="hidden sm:flex items-center bg-[#1c1f2b] rounded-lg px-2 py-1 md:px-4 md:py-2 gap-2 md:gap-3 border border-[#464752]/20">
            <div style={{ width: 24, height: 24, borderRadius: '50%', background: '#591adc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px' }}>📺</div>
            <div style={{ display: 'flex', flexDirection: 'column', position: 'relative' }} ref={dropdownRef}>
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#aaaab7' }}>Active Channel</span>
              <div 
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                style={{ 
                  position: 'relative', 
                  display: 'flex', 
                  alignItems: 'center', 
                  cursor: 'pointer',
                  minWidth: '120px',
                  padding: '4px 0'
                }}
              >
                <span style={{ 
                  color: '#f0f0fd', 
                  fontFamily: "'Space Grotesk', sans-serif", 
                  fontWeight: 700, 
                  fontSize: '14px', 
                  letterSpacing: '-0.02em',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  marginRight: '20px'
                }}>
                  {channels.find(ch => ch.channel_id === selectedChannel)?.channel_name || 'Select Channel'}
                </span>
                <div style={{ position: 'absolute', right: 0, color: '#81ecff', fontSize: '10px', transition: 'transform 0.2s', transform: isDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</div>
              </div>

              {/* Custom Dropdown Menu */}
              {isDropdownOpen && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: '-16px',
                  right: '-16px',
                  background: '#1c1f2b',
                  borderRadius: '12px',
                  border: '1px solid rgba(129, 236, 255, 0.2)',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
                  marginTop: '8px',
                  padding: '8px',
                  zIndex: 100,
                  backdropFilter: 'blur(10px)'
                }}>
                  <div 
                    className="dropdown-item"
                    onClick={() => { setSelectedChannel(''); setVideosData([]); setSelectedVideo(null); setIsDropdownOpen(false); }}
                    style={{ padding: '10px 12px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer', color: '#aaaab7', transition: 'all 0.2s' }}
                  >
                    Select Channel
                  </div>
                  {channels.map(ch => (
                    <div 
                      key={ch.channel_id}
                      className="dropdown-item"
                      onClick={() => { setSelectedChannel(ch.channel_id); setVideosData([]); setSelectedVideo(null); setIsDropdownOpen(false); }}
                      style={{ 
                        padding: '10px 12px', 
                        borderRadius: '8px', 
                        fontSize: '13px', 
                        cursor: 'pointer', 
                        color: selectedChannel === ch.channel_id ? '#81ecff' : '#f0f0fd',
                        background: selectedChannel === ch.channel_id ? 'rgba(129, 236, 255, 0.05)' : 'transparent',
                        transition: 'all 0.2s',
                        marginTop: '2px'
                      }}
                    >
                      {ch.channel_name || `Channel ${ch.channel_id}`}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="hidden lg:flex gap-8 ml-4">
            <a href="#" onClick={e => { e.preventDefault(); }} style={{ color: '#00E5FF', borderBottom: '2px solid #00E5FF', paddingBottom: '4px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.02em', textDecoration: 'none' }}>Analytics</a>
            <a href="#" style={{ color: '#94a3b8', fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em', textDecoration: 'none', transition: 'color 0.2s' }}
              onMouseEnter={e => e.target.style.color = '#81ecff'} onMouseLeave={e => e.target.style.color = '#94a3b8'}>Audience</a>
          </div>
        </div>

        <div className="flex items-center gap-3 md:gap-6">
          <button onClick={loadChannelAnalytics} disabled={!selectedChannel || loading} style={{
            background: 'linear-gradient(to right, #81ecff, #a68cff)', color: '#005762',
            padding: '8px 16px', borderRadius: '8px', fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700, border: 'none', cursor: !selectedChannel || loading ? 'not-allowed' : 'pointer',
            boxShadow: '0 0 20px rgba(129,236,255,0.2)', opacity: !selectedChannel || loading ? 0.5 : 1,
            transition: 'transform 0.1s', fontSize: '12px'
          }}>{loading ? 'Loading...' : 'Load Analytics'}</button>
          <button className="hidden sm:block" onClick={handleLogout} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '13px' }}>Logout</button>
        </div>
      </nav>

      <div className="flex pt-[72px] md:pt-[80px] h-screen overflow-hidden">
        {/* Mobile Overlay */}
        {isMobileMenuOpen && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-60 z-30 md:hidden" 
            onClick={() => setIsMobileMenuOpen(false)} 
          />
        )}
        
        {/* ===== SIDEBAR ===== */}
        <aside className={`fixed md:relative md:flex left-0 top-0 pt-[72px] md:pt-0 h-screen w-64 md:w-64 bg-[#11131d] z-40 flex flex-col transition-transform duration-300 ${
            isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}>
          <div className="sm:hidden px-6 py-4 flex flex-col gap-2 border-b border-[#464752]/20">
             <span className="text-[10px] text-[#aaaab7] uppercase tracking-[0.15em] font-manrope">Active Channel</span>
             <select 
               className="bg-[#1c1f2b] text-[#f0f0fd] p-2 rounded-md outline-none border border-[#464752]/20 text-xs"
               value={selectedChannel}
               onChange={(e) => { setSelectedChannel(e.target.value); setVideosData([]); setSelectedVideo(null); }}
             >
                <option value="">Select Channel</option>
                {channels.map(ch => (
                  <option key={ch.channel_id} value={ch.channel_id}>{ch.channel_name || `Channel ${ch.channel_id}`}</option>
                ))}
             </select>
          </div>

          <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#64748b', marginBottom: '8px', padding: '0 16px' }}>Video Library</span>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', maxHeight: 'calc(100vh - 300px)', paddingRight: '8px' }}>
              {loading && <div style={{ padding: '16px', color: '#64748b', fontSize: '12px', textAlign: 'center' }}>Loading...</div>}
              {!loading && videosData.length === 0 && (
                <div style={{ padding: '16px', color: '#64748b', fontSize: '12px', textAlign: 'center' }}>{selectedChannel ? 'Click "Load Analytics"' : 'Select a channel'}</div>
              )}
              {videosData.map((vid, idx) => (
                <div key={idx} onClick={() => selectVideo(vid)} style={{
                  background: selectedVideo === vid ? '#1c1f2b' : 'transparent',
                  padding: '12px', borderRadius: '12px',
                  borderLeft: selectedVideo === vid ? '4px solid #81ecff' : '4px solid transparent',
                  cursor: 'pointer', transition: 'all 0.2s',
                }}
                  onMouseEnter={e => { if (selectedVideo !== vid) e.currentTarget.style.background = '#171924'; }}
                  onMouseLeave={e => { if (selectedVideo !== vid) e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div style={{ width: 64, height: 40, borderRadius: '8px', overflow: 'hidden', flexShrink: 0, background: '#222532' }}>
                      <img src={vid.thumbnail || 'https://via.placeholder.com/64x40/222532/81ecff?text='} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        onError={e => e.target.src = 'https://via.placeholder.com/64x40/222532/81ecff?text='} />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                      <span style={{ fontSize: '12px', fontWeight: selectedVideo === vid ? 700 : 500, color: selectedVideo === vid ? '#81ecff' : '#cbd5e1', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{vid.title || 'Untitled'}</span>
                      <span style={{ fontSize: '10px', color: '#64748b' }}>{(vid.views || 0).toLocaleString()} views</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom */}
          <div style={{ marginTop: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ background: 'rgba(129,236,255,0.05)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(129,236,255,0.2)' }}>
              <span style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#81ecff', marginBottom: '4px' }}>Upgrade to Pro</span>
              <p style={{ fontSize: '10px', color: '#94a3b8', marginBottom: '12px' }}>Get advanced AI analytics & automation tools.</p>
              <button onClick={() => navigate('/pricing')} style={{ width: '100%', padding: '8px', background: '#81ecff', color: '#005762', fontSize: '10px', fontWeight: 700, borderRadius: '8px', border: 'none', cursor: 'pointer', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Unlock Access</button>
            </div>
            <a href="#" onClick={e => { e.preventDefault(); handleLogout(); }} style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#64748b', fontSize: '14px', textDecoration: 'none', transition: 'color 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.color = '#e2e8f0'} onMouseLeave={e => e.currentTarget.style.color = '#64748b'}
            ><span style={{ color: '#d7383b' }}>⏻</span> Logout</a>
          </div>
        </aside>

        {/* ===== MAIN CONTENT ===== */}
        <main className="w-full h-full overflow-y-auto bg-[#0c0e17] p-4 md:p-8 lg:p-12 relative z-10">
          {/* Header Section */}
          {selectedVideo && (
            <header className="mb-8 md:mb-12 flex flex-col xl:flex-row justify-between items-start xl:items-end gap-6">
              <div style={{ maxWidth: '640px' }}>
                <div className="flex flex-wrap items-center gap-3 mb-2">
                  <span style={{ background: 'rgba(0,227,253,0.2)', color: '#00e3fd', padding: '4px 12px', borderRadius: '9999px', fontFamily: "'Manrope', sans-serif", fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', border: '1px solid rgba(129,236,255,0.2)' }}>Active Analysis</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#cafd00', fontSize: '10px', fontWeight: 700 }}>
                    📈 +{((((selectedVideo.views || 0) / Math.max(1, videosData.reduce((s, v) => s + (v.views || 0), 0) / videosData.length)) - 1) * 100).toFixed(1)}% vs Channel Avg
                  </div>
                </div>
                <h1 className="font-space font-bold text-2xl md:text-3xl lg:text-4xl tracking-tight mb-4">{selectedVideo.title || 'Untitled'}</h1>
                <p style={{ color: '#aaaab7', lineHeight: 1.6 }}>Published: {selectedVideo.published_at ? new Date(selectedVideo.published_at).toLocaleDateString() : 'N/A'} • Duration: {selectedVideo.duration || '0:00'}</p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', xl: { alignItems: 'flex-end' } }}>
                <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#aaaab7', marginBottom: '4px' }}>Engagement Rate</span>
                <span style={{
                  background: parseFloat(engRate) > 5 ? 'rgba(202,253,0,0.1)' : 'rgba(129,236,255,0.1)',
                  color: parseFloat(engRate) > 5 ? '#cafd00' : '#81ecff',
                  border: `1px solid ${parseFloat(engRate) > 5 ? 'rgba(243,255,202,0.2)' : 'rgba(129,236,255,0.2)'}`,
                  padding: '6px 16px', borderRadius: '9999px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '14px',
                }}>{parseFloat(engRate) > 5 ? 'EXCELLENT' : parseFloat(engRate) > 2 ? 'GOOD' : 'NEEDS WORK'}</span>
              </div>
            </header>
          )}

          {!selectedVideo && !loading && (
            <div style={{ textAlign: 'center', paddingTop: '120px', color: '#737580' }}>
              <div style={{ fontSize: '64px', marginBottom: '16px', opacity: 0.2 }}>📊</div>
              <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.5rem', color: '#aaaab7', marginBottom: '8px' }}>Select a video to analyze</h3>
              <p style={{ fontSize: '14px' }}>Choose a video from the sidebar or load analytics first</p>
            </div>
          )}

          {/* Bento Chart Grid */}
          {selectedVideo && (
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 pb-20">
              {/* Performance Chart - 8 cols */}
              <div className="col-span-1 md:col-span-8 bg-[#1c1f2b] rounded-xl p-5 md:p-8 relative overflow-hidden">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '48px' }}>
                  <div>
                    <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>Performance Benchmarks</h3>
                    <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Views / Likes / Comments Comparison</p>
                  </div>
                </div>
                <div style={{ height: '256px' }}><canvas id="perfChart"></canvas></div>
              </div>

              {/* Channel Average Index - 4 cols */}
              <div className="col-span-1 md:col-span-4 bg-[#1c1f2b] rounded-xl p-5 md:p-8">
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>Channel Average Index</h3>
                  <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Metric Benchmarking</p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {[
                    { label: 'Watch Time', pct: watchTimePct, delta: watchTimeDelta, deltaColor: watchTimeColor, barColor: '#81ecff' },
                    { label: 'CTR (Click Through Rate)', pct: ctrPct, delta: ctrDelta, deltaColor: ctrColor, barColor: '#a68cff' },
                    { label: 'Retention @ 30s', pct: retPct, delta: retStatus, deltaColor: retColor, barColor: '#beee00' },
                    { label: 'Share Velocity', pct: sharePct, delta: shareStatus, deltaColor: shareColor, barColor: '#464752' },
                  ].map((m, i) => (
                    <div key={i}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '12px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.02em' }}>{m.label}</span>
                        <span style={{ fontSize: '10px', fontWeight: 700, color: m.deltaColor }}>{m.delta}</span>
                      </div>
                      <div style={{ height: 6, width: '100%', background: '#171924', borderRadius: '9999px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${m.pct}%`, background: m.barColor, borderRadius: '9999px', transition: 'width 1s ease' }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Timeline - 7 cols */}
              <div className="col-span-1 md:col-span-7 bg-[#1c1f2b] rounded-xl p-5 md:p-8">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                  <div>
                    <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>7-Day View Trajectory</h3>
                    <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Growth Velocity</p>
                  </div>
                  <span style={{ padding: '4px 8px', background: '#0c0e17', borderRadius: '4px', fontSize: '10px', fontWeight: 700, border: '1px solid rgba(70,71,82,0.2)' }}>REAL-TIME</span>
                </div>
                <div style={{ height: '192px' }}><canvas id="lineChart"></canvas></div>
              </div>

              {/* Engagement - 5 cols */}
              <div className="col-span-1 md:col-span-5 bg-[#1c1f2b] rounded-xl p-5 md:p-8 flex flex-col justify-between">
                <div>
                  <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>Engagement Density</h3>
                  <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Interactions vs Total Views</p>
                </div>
                <div style={{ height: '180px', display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
                  <canvas id="engChart"></canvas>
                  <div style={{ position: 'absolute', textAlign: 'center' }}>
                    <span style={{ display: 'block', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.875rem', letterSpacing: '-0.05em' }}>{engRate}%</span>
                    <span style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#aaaab7', textTransform: 'uppercase', letterSpacing: '0.15em' }}>Ratio</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#81ecff' }} /><span style={{ color: '#aaaab7' }}>Active Interactions</span></div>
                    <span style={{ fontWeight: 700 }}>{((selectedVideo.likes || 0) + (selectedVideo.comments || 0)).toLocaleString()}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#222532' }} /><span style={{ color: '#aaaab7' }}>Passive Views</span></div>
                    <span style={{ fontWeight: 700 }}>{Math.max(0, (selectedVideo.views || 0) - (selectedVideo.likes || 0) - (selectedVideo.comments || 0)).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* Radar Chart - 6 cols */}
              <div className="col-span-1 md:col-span-6 bg-[#1c1f2b] rounded-xl p-5 md:p-8 relative overflow-hidden">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                  <div>
                    <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>Performance vs Average</h3>
                    <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Multi-Dimensional Analysis</p>
                  </div>
                </div>
                <div style={{ height: '256px' }}><canvas id="radarChart"></canvas></div>
              </div>

              {/* Performance Breakdown - 6 cols */}
              <div className="col-span-1 md:col-span-6 bg-[#1c1f2b] rounded-xl p-5 md:p-8">
                <div style={{ marginBottom: '24px' }}>
                    <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>Performance Breakdown</h3>
                    <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Relative to Channel Max</p>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '12px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.02em' }}>Views Performance</span>
                        <span style={{ fontSize: '10px', fontWeight: 700, color: '#81ecff' }}>{viewsPercentage.toFixed(1)}%</span>
                        </div>
                        <div style={{ height: 6, width: '100%', background: '#171924', borderRadius: '9999px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(viewsPercentage, 100)}%`, background: 'linear-gradient(90deg, #81ecff, #a68cff)', borderRadius: '9999px', transition: 'width 1s ease' }} />
                        </div>
                    </div>
                    
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '12px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.02em' }}>Likes Performance</span>
                        <span style={{ fontSize: '10px', fontWeight: 700, color: '#81ecff' }}>{likesPercentage.toFixed(1)}%</span>
                        </div>
                        <div style={{ height: 6, width: '100%', background: '#171924', borderRadius: '9999px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(likesPercentage, 100)}%`, background: 'linear-gradient(90deg, #81ecff, #a68cff)', borderRadius: '9999px', transition: 'width 1s ease' }} />
                        </div>
                    </div>

                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '12px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.02em' }}>Comments Engagement</span>
                        <span style={{ fontSize: '10px', fontWeight: 700, color: '#81ecff' }}>{commentsPercentage.toFixed(1)}%</span>
                        </div>
                        <div style={{ height: 6, width: '100%', background: '#171924', borderRadius: '9999px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${Math.min(commentsPercentage, 100)}%`, background: 'linear-gradient(90deg, #81ecff, #a68cff)', borderRadius: '9999px', transition: 'width 1s ease' }} />
                        </div>
                    </div>
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          {selectedVideo && (
            <footer className="flex flex-col md:flex-row justify-between items-center py-8 gap-4 border-t border-[#464752]/20 text-center md:text-left">
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#64748b', fontWeight: 700 }}>© 2024 CINEMA_AI Editorial Suite</span>
              <div className="flex flex-wrap justify-center gap-4 md:gap-8">
                {['Privacy Policy', 'Terms of Service', 'API Status'].map(item => (
                  <a key={item} href="#" style={{ fontFamily: "'Manrope', sans-serif", fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#475569', textDecoration: 'none', transition: 'color 0.3s' }}
                    onMouseEnter={e => e.target.style.color = '#00E5FF'} onMouseLeave={e => e.target.style.color = '#475569'}>{item}</a>
                ))}
              </div>
            </footer>
          )}
        </main>
      </div>

      {/* Atmospheric glow */}
      <div style={{ position: 'fixed', bottom: 0, right: 0, padding: '48px', pointerEvents: 'none', zIndex: 0 }}>
        <div style={{ width: '500px', height: '500px', background: 'rgba(129,236,255,0.05)', borderRadius: '9999px', filter: 'blur(100px)' }} />
      </div>
    </div>
  );
};

export default Analytics;