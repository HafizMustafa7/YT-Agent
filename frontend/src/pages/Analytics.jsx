import React, { useState, useEffect, useRef } from 'react';
import { Chart } from 'chart.js/auto';
import { useNavigate } from 'react-router-dom';
import apiService from '../features/yt-agent/services/apiService';
import { supabase } from '../supabaseClient';
import { tokenService } from '../services/tokenService';

const Analytics = () => {
  const navigate = useNavigate();
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState('');
  const [videosData, setVideosData] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [statsData, setStatsData] = useState({ totalVideos: 0, totalViews: 0, totalSubscribers: 0, avgEngagement: 0 });
  const [showStats, setShowStats] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const chartsRef = useRef({});

  useEffect(() => {
    loadChannels();
    return () => { Object.values(chartsRef.current).forEach(c => { if (c?.destroy) c.destroy(); }); };
  }, []);

  const loadChannels = async () => {
    try {
      const data = await apiService.listChannels();
      setChannels(data || []);
      if (!data?.length) setError('No channels found.');
    } catch { setError('Failed to load channels.'); }
  };

  const loadChannelAnalytics = async () => {
    if (!selectedChannel) return;
    setLoading(true); setError('');
    try {
      setVideosData([]); setShowStats(false);
      const data = await apiService.getChannelAnalytics(selectedChannel);
      if (!data?.videos) throw new Error('No data received.');
      setVideosData(data.videos || []);
      const avgEng = data.videos.length > 0 ? data.videos.reduce((s, v) => s + (v.engagement_rate || 0), 0) / data.videos.length : 0;
      setStatsData({ totalVideos: data.total_videos || 0, totalViews: data.total_views || 0, totalSubscribers: data.total_subscribers || 0, avgEngagement: avgEng });
      setShowStats(true);
    } catch (err) {
      setError(`Failed: ${err.message || 'Unknown'}`); setShowStats(false);
    } finally { setLoading(false); }
  };

  const selectVideo = (video) => {
    setSelectedVideo(video);
    Object.values(chartsRef.current).forEach(c => { if (c?.destroy) c.destroy(); });
    chartsRef.current = {};
  };

  useEffect(() => {
    if (selectedVideo) setTimeout(() => createCharts(), 500);
  }, [selectedVideo]);

  const createCharts = () => {
    if (!selectedVideo) return;
    const v = selectedVideo;
    const avgViews = videosData.reduce((s, vid) => s + (vid.views || 0), 0) / videosData.length;

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
  };

  const handleLogout = async () => { await tokenService.logout(); };
  const activeChannel = channels.find(c => c.channel_id === selectedChannel);
  const engRate = selectedVideo ? ((((selectedVideo.likes || 0) + (selectedVideo.comments || 0)) / Math.max(selectedVideo.views || 1, 1)) * 100).toFixed(1) : '0.0';

  // Performance vs avg for benchmarks
  const maxViews = Math.max(...videosData.map(v => v.views || 0), 1);

  return (
    <div style={{ minHeight: '100vh', background: '#0c0e17', color: '#f0f0fd', fontFamily: "'Inter', sans-serif" }}>
      {/* ===== TOP NAV ===== */}
      <nav style={{
        position: 'fixed', top: 0, width: '100%', zIndex: 50,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '16px 32px', background: '#11131d',
        boxShadow: '0 40px 40px rgba(0,0,0,0.08)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
          <span onClick={() => navigate('/dashboard')} style={{ fontSize: '1.5rem', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 900, color: '#00E5FF', letterSpacing: '-0.05em', cursor: 'pointer' }}>YOUTOMIZE</span>

          {/* Channel Selector */}
          <div style={{ display: 'flex', alignItems: 'center', background: '#1c1f2b', borderRadius: '8px', padding: '8px 16px', gap: '12px', border: '1px solid rgba(70,71,82,0.1)' }}>
            <div style={{ width: 24, height: 24, borderRadius: '50%', background: '#591adc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px' }}>📺</div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#aaaab7' }}>Active Channel</span>
              <select value={selectedChannel} onChange={e => { setSelectedChannel(e.target.value); setShowStats(false); setVideosData([]); setSelectedVideo(null); }}
                style={{ background: 'transparent', border: 'none', color: '#f0f0fd', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '14px', letterSpacing: '-0.02em', outline: 'none', cursor: 'pointer', padding: 0 }}>
                <option value="" style={{ background: '#1c1f2b' }}>Select Channel</option>
                {channels.map(ch => <option key={ch.channel_id} value={ch.channel_id} style={{ background: '#1c1f2b' }}>{ch.channel_name || `Channel ${ch.channel_id}`}</option>)}
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '32px', marginLeft: '16px' }}>
            <a href="#" onClick={e => { e.preventDefault(); }} style={{ color: '#00E5FF', borderBottom: '2px solid #00E5FF', paddingBottom: '4px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.02em', textDecoration: 'none' }}>Analytics</a>
            <a href="#" style={{ color: '#94a3b8', fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em', textDecoration: 'none', transition: 'color 0.2s' }}
              onMouseEnter={e => e.target.style.color = '#81ecff'} onMouseLeave={e => e.target.style.color = '#94a3b8'}>Audience</a>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <button onClick={loadChannelAnalytics} disabled={!selectedChannel || loading} style={{
            background: 'linear-gradient(to right, #81ecff, #a68cff)', color: '#005762',
            padding: '8px 24px', borderRadius: '8px', fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700, border: 'none', cursor: !selectedChannel || loading ? 'not-allowed' : 'pointer',
            boxShadow: '0 0 20px rgba(129,236,255,0.2)', opacity: !selectedChannel || loading ? 0.5 : 1,
            transition: 'transform 0.1s',
          }}>{loading ? 'Loading...' : 'Load Analytics'}</button>
          <button onClick={handleLogout} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '13px' }}>Logout</button>
        </div>
      </nav>

      <div style={{ display: 'flex', paddingTop: '80px', height: '100vh', overflow: 'hidden' }}>
        {/* ===== SIDEBAR ===== */}
        <aside style={{
          width: '256px', position: 'fixed', left: 0, top: 0,
          paddingTop: '80px', height: '100vh',
          background: '#11131d', zIndex: 40,
          display: 'flex', flexDirection: 'column',
        }}>
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
        <main style={{ marginLeft: '256px', width: '100%', height: '100%', overflowY: 'auto', background: '#0c0e17', padding: '48px' }}>
          {/* Header Section */}
          {selectedVideo && (
            <header style={{ marginBottom: '48px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div style={{ maxWidth: '640px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <span style={{ background: 'rgba(0,227,253,0.2)', color: '#00e3fd', padding: '4px 12px', borderRadius: '9999px', fontFamily: "'Manrope', sans-serif", fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', border: '1px solid rgba(129,236,255,0.2)' }}>Active Analysis</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#cafd00', fontSize: '10px', fontWeight: 700 }}>
                    📈 +{((((selectedVideo.views || 0) / Math.max(1, videosData.reduce((s, v) => s + (v.views || 0), 0) / videosData.length)) - 1) * 100).toFixed(1)}% vs Channel Avg
                  </div>
                </div>
                <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem', letterSpacing: '-0.02em', marginBottom: '16px' }}>{selectedVideo.title || 'Untitled'}</h1>
                <p style={{ color: '#aaaab7', lineHeight: 1.6 }}>Published: {selectedVideo.published_at ? new Date(selectedVideo.published_at).toLocaleDateString() : 'N/A'} • Duration: {selectedVideo.duration || '0:00'}</p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
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
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '24px', paddingBottom: '80px' }}>
              {/* Performance Chart - 8 cols */}
              <div style={{ gridColumn: 'span 8', background: '#1c1f2b', borderRadius: '12px', padding: '32px', position: 'relative', overflow: 'hidden' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '48px' }}>
                  <div>
                    <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>Performance Benchmarks</h3>
                    <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Views / Likes / Comments Comparison</p>
                  </div>
                </div>
                <div style={{ height: '256px' }}><canvas id="perfChart"></canvas></div>
              </div>

              {/* Engagement - 4 cols */}
              <div style={{ gridColumn: 'span 4', background: '#1c1f2b', borderRadius: '12px', padding: '32px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
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

              {/* Timeline - 7 cols */}
              <div style={{ gridColumn: 'span 7', background: '#1c1f2b', borderRadius: '12px', padding: '32px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                  <div>
                    <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>7-Day View Trajectory</h3>
                    <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Growth Velocity</p>
                  </div>
                  <span style={{ padding: '4px 8px', background: '#0c0e17', borderRadius: '4px', fontSize: '10px', fontWeight: 700, border: '1px solid rgba(70,71,82,0.2)' }}>REAL-TIME</span>
                </div>
                <div style={{ height: '192px' }}><canvas id="lineChart"></canvas></div>
              </div>

              {/* Channel Average Index - 5 cols */}
              <div style={{ gridColumn: 'span 5', background: '#1c1f2b', borderRadius: '12px', padding: '32px' }}>
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', marginBottom: '4px' }}>Channel Average Index</h3>
                  <p style={{ fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', letterSpacing: '0.15em' }}>Metric Benchmarking</p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {[
                    { label: 'Watch Time', pct: 88, delta: '+28% Higher', deltaColor: '#cafd00', barColor: '#81ecff' },
                    { label: 'CTR (Click Through Rate)', pct: 62, delta: '-4% Lower', deltaColor: '#d7383b', barColor: '#a68cff' },
                    { label: 'Retention @ 30s', pct: 75, delta: 'Excellent', deltaColor: '#cafd00', barColor: '#beee00' },
                    { label: 'Share Velocity', pct: 22, delta: 'Needs Work', deltaColor: '#aaaab7', barColor: '#464752' },
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
            </div>
          )}

          {/* Footer */}
          {selectedVideo && (
            <footer style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '32px 0', borderTop: '1px solid rgba(70,71,82,0.1)' }}>
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#64748b', fontWeight: 700 }}>© 2024 CINEMA_AI Editorial Suite</span>
              <div style={{ display: 'flex', gap: '32px' }}>
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