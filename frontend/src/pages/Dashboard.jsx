import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import apiService from "../features/yt-agent/services/apiService";
import { showErrorToast } from '../lib/errorUtils';
import { useSelectedChannel } from '../contexts/SelectedChannelContext';
import dashboardBg from '../assets/dashboard_bg.jpg';

const Dashboard = () => {
  const {
    channels, selectedChannelId, setSelectedChannelId,
    refreshChannels, credits
  } = useSelectedChannel();
  const [isSidebarHovered, setIsSidebarHovered] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isChannelDropdownOpen, setIsChannelDropdownOpen] = useState(false);
  // remove unused useTheme and toggleTheme
  const [sessionReady, setSessionReady] = useState(false);
  const [recentProjects, setRecentProjects] = useState([]);
  const navigate = useNavigate();
  const channelDropdownRef = useRef(null);

  const activeChannel = channels.find(c => c.channel_id === selectedChannelId || c.id === selectedChannelId);
  const selectedChannelName = activeChannel?.channel_name || activeChannel?.snippet?.title || "Switch Channel";

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (channelDropdownRef.current && !channelDropdownRef.current.contains(e.target)) setIsChannelDropdownOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session?.user) { navigate("/"); return; }
        setSessionReady(true);
        
        // Fetch project history
        try {
          const res = await apiService.getUserProjects();
          if (res.success) {
            setRecentProjects(res.projects.slice(0, 5)); // Show top 5
          }
        } catch (err) {
          console.error("Failed to load project history", err);
        }
      } catch { navigate("/"); }
    };
    initializeSession();
  }, [navigate]);


  const handleAddChannel = async () => {
    try {
      const data = await apiService.startYouTubeOAuth();
      window.location.href = data.url;
    } catch (err) { showErrorToast(err); }
  };

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden font-inter text-[#f0f0fd] bg-[#0c0e17]">
      {/* ===== TOP NAV BAR ===== */}
      <nav className="sticky top-0 z-50 flex justify-between items-center w-full px-4 py-3 md:px-8 md:py-4 transition-all" style={{
        background: 'rgba(12, 14, 23, 0.6)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        boxShadow: '0 40px 40px rgba(0,229,255,0.08)',
      }}>
        <div className="flex items-center gap-3">
          {/* Hamburger Menu for Mobile */}
          <button 
            className="md:hidden text-[#00E5FF] flex items-center justify-center p-1"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            <span className="material-symbols-outlined text-2xl">{isMobileMenuOpen ? 'close' : 'menu'}</span>
          </button>

          {/* Logo */}
          <div className="text-xl md:text-2xl cursor-pointer" style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700, letterSpacing: '-0.05em', color: '#00E5FF',
          }} onClick={() => navigate('/dashboard')}>YOUTOMIZE</div>
        </div>

        {/* Center Nav Links */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#" onClick={e => { e.preventDefault(); navigate('/dashboard'); }} style={{
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em',
            color: '#00E5FF', fontWeight: 700,
            borderBottom: '2px solid #00E5FF', paddingBottom: '4px',
            textDecoration: 'none',
          }}>Dashboard</a>
          <div style={{
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em',
            color: '#00E5FF', fontWeight: 700, padding: '4px 12px',
            background: 'rgba(0, 229, 255, 0.1)', borderRadius: '8px',
            border: '1px solid rgba(0, 229, 255, 0.2)', display: 'flex', alignItems: 'center'
          }}>
            Credits: {credits ?? '...'}
          </div>
        </div>

        {/* Right: Channel Switcher + Settings */}
        <div className="flex items-center gap-3 md:gap-6">
          {/* Upgrade Button */}
          <button onClick={() => navigate('/pricing')} className="hidden sm:block" style={{
            background: 'linear-gradient(45deg, #81ecff 0%, #a68cff 100%)',
            color: '#3b00a0', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
            fontSize: '14px', padding: '8px 16px', borderRadius: '8px',
            border: 'none', cursor: 'pointer', transition: 'transform 0.2s',
            boxShadow: '0 4px 15px rgba(129,236,255,0.2)',
          }}
            onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
          >
            Upgrade
          </button>

          {/* Channel Switcher */}
          <div ref={channelDropdownRef} style={{ position: 'relative' }}>
            <div onClick={() => setIsChannelDropdownOpen(!isChannelDropdownOpen)} className="flex items-center gap-2 md:gap-3 p-1.5 md:p-2 px-2 md:px-4 rounded-lg cursor-pointer transition-all bg-[#1c1f2b]"
              onMouseEnter={e => { e.currentTarget.style.background = '#222532'; e.currentTarget.style.transform = 'scale(1.02)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = '#1c1f2b'; e.currentTarget.style.transform = 'scale(1)'; }}
            >
              <div style={{
                width: 32, height: 32, borderRadius: '50%',
                background: '#591adc', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '16px',
              }}>👤</div>
              <div className="hidden sm:flex flex-col">
                <span style={{
                  fontSize: '10px', fontFamily: "'Manrope', sans-serif",
                  textTransform: 'uppercase', letterSpacing: '0.15em',
                  color: '#aaaab7', fontWeight: 500,
                }}>Connected</span>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#f0f0fd' }}>
                  {selectedChannelName}
                </span>
              </div>
            </div>

            {/* Channel Dropdown */}
            {isChannelDropdownOpen && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 8px)', right: 0,
                minWidth: '260px', background: '#1c1f2b',
                backdropFilter: 'blur(20px)',
                borderRadius: '12px', overflow: 'hidden', zIndex: 60,
                boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
                border: '1px solid rgba(255,255,255,0.05)',
              }}>
                {channels.map(ch => (
                  <button key={ch.channel_id} onClick={() => { setSelectedChannelId(ch.channel_id || ch.id); setIsChannelDropdownOpen(false); }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      width: '100%', padding: '12px 16px',
                      background: selectedChannelId === (ch.channel_id || ch.id) ? 'rgba(0, 229, 255, 0.08)' : 'transparent',
                      border: 'none', color: '#f0f0fd', cursor: 'pointer',
                      fontFamily: "'Inter', sans-serif", fontSize: '13px',
                      textAlign: 'left', transition: 'background 0.2s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(0, 229, 255, 0.05)'}
                    onMouseLeave={e => e.currentTarget.style.background = selectedChannelId === (ch.channel_id || ch.id) ? 'rgba(0, 229, 255, 0.08)' : 'transparent'}
                  >
                    {ch.thumbnail_url ? (
                      <img src={ch.thumbnail_url} alt="" style={{ width: 24, height: 24, borderRadius: '50%', objectFit: 'cover' }} />
                    ) : (
                      <div style={{ width: 24, height: 24, borderRadius: '50%', background: '#591adc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px' }}>📺</div>
                    )}
                    <span>{ch.channel_name || ch.snippet?.title}</span>
                    {selectedChannelId === (ch.channel_id || ch.id) && <span style={{ marginLeft: 'auto', color: '#00E5FF', fontSize: '14px' }}>✓</span>}
                  </button>
                ))}
                <button onClick={() => { handleAddChannel(); setIsChannelDropdownOpen(false); }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    width: '100%', padding: '12px 16px',
                    background: 'transparent', border: 'none',
                    color: '#00E5FF', cursor: 'pointer',
                    fontFamily: "'Manrope', sans-serif", fontSize: '13px',
                    fontWeight: 600, textAlign: 'left',
                    borderTop: '1px solid rgba(255,255,255,0.05)',
                  }}
                >＋ Add New Channel</button>
              </div>
            )}
          </div>

          {/* Settings */}
          <button onClick={() => navigate('/settings')} style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: '#94a3b8', transition: 'color 0.3s',
            display: 'flex', alignItems: 'center',
          }}
            onMouseEnter={e => e.currentTarget.style.color = '#81ecff'}
            onMouseLeave={e => e.currentTarget.style.color = '#94a3b8'}
            title="Settings"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '24px' }}>settings</span>
          </button>
        </div>
      </nav>

      <div className="flex flex-1 relative">
        {/* ===== SIDE NAV BAR ===== */}
        {/* Mobile Overlay */}
        {isMobileMenuOpen && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-60 z-30 md:hidden" 
            onClick={() => setIsMobileMenuOpen(false)} 
          />
        )}
        <aside
          onMouseEnter={() => setIsSidebarHovered(true)}
          onMouseLeave={() => setIsSidebarHovered(false)}
          className={`fixed left-0 top-0 h-screen z-40 flex flex-col overflow-hidden transition-all duration-300 ${
            isMobileMenuOpen ? 'translate-x-0 w-64' : '-translate-x-full md:translate-x-0'
          }`}
          style={{
            width: isMobileMenuOpen ? '256px' : (isSidebarHovered ? '256px' : '64px'),
            paddingTop: '80px',
            background: '#11131d',
            borderRight: '1px solid rgba(255,255,255,0.05)',
          }}
        >
          {/* History Header */}
          <div style={{ padding: '0 16px', marginBottom: '32px', whiteSpace: 'nowrap', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', color: '#00E5FF' }}>
              <span className="material-symbols-outlined" style={{ fontSize: '24px', flexShrink: 0 }}>history</span>
              <span style={{
                fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                opacity: (isSidebarHovered || isMobileMenuOpen) ? 1 : 0, transition: 'opacity 0.3s',
              }}>Project History</span>
            </div>
            <div style={{
              marginTop: '8px', color: '#64748b', fontSize: '10px',
              fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase',
              letterSpacing: '0.15em', fontWeight: 500,
              opacity: (isSidebarHovered || isMobileMenuOpen) ? 1 : 0, transition: 'opacity 0.3s',
            }}>Recent Automations</div>

            {/* History List */}
            <div style={{
              display: 'flex', flexDirection: 'column', gap: '4px',
              opacity: (isSidebarHovered || isMobileMenuOpen) ? 1 : 0,
              transition: 'opacity 0.3s', pointerEvents: (isSidebarHovered || isMobileMenuOpen) ? 'auto' : 'none'
            }}>
              {recentProjects.length === 0 ? (
                <div style={{ color: '#475569', fontSize: '12px', marginTop: '8px', fontStyle: 'italic' }}>No recent projects</div>
              ) : (
                recentProjects.map(proj => {
                  const title = proj.project_name || proj.input_value || 'Untitled Project';
                  const isFinished = proj.status === 'completed';
                  return (
                    <div 
                      key={proj.id} 
                      onClick={() => navigate('/frame-results', { state: { data: null } })} // Will be intercepted by projectId in session if we set it, or we can just navigate and it will load. Wait, if we navigate to FrameResults we need to set the projectId in sessionStorage.
                      style={{
                        padding: '8px 0', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '4px',
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        transition: 'background 0.2s', paddingLeft: '8px', borderRadius: '4px'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                      onMouseDown={() => sessionStorage.setItem('yt_frame_project_id', proj.id)}
                    >
                      <div style={{ fontSize: '13px', color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontSize: '9px', fontWeight: 700, padding: '2px 4px', borderRadius: '4px',
                          background: isFinished ? 'rgba(0,255,136,0.1)' : 'rgba(0,229,255,0.1)',
                          color: isFinished ? '#00ff88' : '#00E5FF', textTransform: 'uppercase'
                        }}>{proj.status}</span>
                        {proj.channels && (
                          <span style={{ fontSize: '10px', color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            📺 {proj.channels.channel_name || 'Channel'}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Mobile Only Credits */}
          <div className="md:hidden px-4 mb-6">
             <div style={{
                fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em',
                color: '#00E5FF', fontWeight: 700, padding: '8px 12px',
                background: 'rgba(0, 229, 255, 0.1)', borderRadius: '8px',
                border: '1px solid rgba(0, 229, 255, 0.2)', display: 'flex', alignItems: 'center'
              }}>
                Credits: {credits ?? '...'}
             </div>
          </div>

          {/* Nav Items */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {/* Generate Video - Active */}
            <div onClick={() => navigate('/niche-input')} style={{
              background: '#1c1f2b', color: '#00E5FF', borderRadius: '8px',
              margin: '0 8px', display: 'flex', alignItems: 'center',
              padding: '12px 8px', cursor: 'pointer', whiteSpace: 'nowrap', overflow: 'hidden',
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: '24px', flexShrink: 0, width: '48px', display: 'flex', justifyContent: 'center' }}>movie</span>
              <span style={{
                fontFamily: "'Inter', sans-serif", fontSize: '14px',
                opacity: (isSidebarHovered || isMobileMenuOpen) ? 1 : 0, transition: 'opacity 0.3s',
              }}>Generate Video</span>
            </div>

            {/* Analytics */}
            <div onClick={() => navigate('/analytics')} style={{
              color: '#64748b', display: 'flex', alignItems: 'center',
              padding: '12px 16px', cursor: 'pointer',
              transition: 'all 0.2s', whiteSpace: 'nowrap', overflow: 'hidden',
            }}
              onMouseEnter={e => { e.currentTarget.style.color = '#e2e8f0'; e.currentTarget.style.background = '#171924'; e.currentTarget.style.transform = 'translateX(4px)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.background = 'transparent'; e.currentTarget.style.transform = 'translateX(0)'; }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '24px', flexShrink: 0, width: '48px', display: 'flex', justifyContent: 'center' }}>bar_chart</span>
              <span style={{
                fontFamily: "'Inter', sans-serif", fontSize: '14px',
                opacity: (isSidebarHovered || isMobileMenuOpen) ? 1 : 0, transition: 'opacity 0.3s',
              }}>Analytics</span>
            </div>
          </div>

          {/* Bottom Nav Items */}
          <div style={{
            marginTop: 'auto', borderTop: '1px solid rgba(255,255,255,0.05)',
            paddingTop: '16px', paddingBottom: '32px',
            display: 'flex', flexDirection: 'column', gap: '8px',
          }}>
            <div style={{
              color: '#64748b', display: 'flex', alignItems: 'center',
              padding: '12px 16px', cursor: 'pointer', transition: 'all 0.2s',
              whiteSpace: 'nowrap', overflow: 'hidden',
            }}
              onMouseEnter={e => { e.currentTarget.style.color = '#e2e8f0'; e.currentTarget.style.background = '#171924'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.background = 'transparent'; }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '24px', flexShrink: 0, width: '48px', display: 'flex', justifyContent: 'center' }}>inventory_2</span>
              <span style={{
                fontFamily: "'Inter', sans-serif", fontSize: '14px',
                opacity: (isSidebarHovered || isMobileMenuOpen) ? 1 : 0, transition: 'opacity 0.3s',
              }}>Archive</span>
            </div>
            <div style={{
              color: '#64748b', display: 'flex', alignItems: 'center',
              padding: '12px 16px', cursor: 'pointer', transition: 'all 0.2s',
              whiteSpace: 'nowrap', overflow: 'hidden',
            }}
              onMouseEnter={e => { e.currentTarget.style.color = '#e2e8f0'; e.currentTarget.style.background = '#171924'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#64748b'; e.currentTarget.style.background = 'transparent'; }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '24px', flexShrink: 0, width: '48px', display: 'flex', justifyContent: 'center' }}>delete</span>
              <span style={{
                fontFamily: "'Inter', sans-serif", fontSize: '14px',
                opacity: (isSidebarHovered || isMobileMenuOpen) ? 1 : 0, transition: 'opacity 0.3s',
              }}>Trash</span>
            </div>
          </div>
        </aside>

        {/* ===== MAIN CANVAS ===== */}
        <main className="flex-1 flex flex-col w-full md:ml-[64px] p-4 sm:p-6 md:p-8 lg:p-10 gap-8 md:gap-12 min-w-0" style={{
           overflowX: 'hidden'
        }}>
          {/* ===== HERO SECTION ===== */}
          <section className="relative rounded-3xl overflow-hidden min-h-[300px] sm:min-h-[400px] md:min-h-[450px] flex items-center" style={{
            background: '#11131d',
          }}>
            {/* Background Image */}
            <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
              <img
                alt="abstract flowing liquid metal textures in deep electric cyan and dark purple with cinematic lighting"
                src={dashboardBg}
                style={{
                  width: '100%', height: '100%', objectFit: 'cover',
                  opacity: 0.4, mixBlendMode: 'overlay',
                }}
              />
              {/* Gradient overlays */}
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(to top, #0c0e17, transparent, transparent)',
              }} />
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(to right, rgba(12,14,23,0.8), transparent)',
              }} />
            </div>

            {/* Hero Content */}
            <div className="relative z-10 p-6 md:p-12 max-w-2xl">
              <span style={{
                fontFamily: "'Manrope', sans-serif",
                color: '#81ecff', fontSize: '12px', fontWeight: 800,
                textTransform: 'uppercase', letterSpacing: '0.3em',
                marginBottom: '16px', display: 'block',
              }}>Next-Gen Automation</span>

              <h1 style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 700, fontSize: 'clamp(2.2rem, 5vw, 4.5rem)',
                letterSpacing: '-0.02em', marginBottom: '24px',
                lineHeight: 1.1,
              }}>
                Cinematic{' '}
                <span style={{
                  color: 'transparent',
                  backgroundImage: 'linear-gradient(45deg, #81ecff 0%, #a68cff 100%)',
                  WebkitBackgroundClip: 'text', backgroundClip: 'text',
                }}>Intelligence</span>{' '}
                for Creators.
              </h1>

              <p style={{
                fontFamily: "'Inter', sans-serif",
                color: '#aaaab7', fontSize: '1rem',
                marginBottom: '32px', maxWidth: '560px', lineHeight: 1.6,
              }}>
                Synthesize high-performing YouTube content in seconds using our proprietary neural editing engine. Your channel, automated.
              </p>

              <div className="flex flex-col sm:flex-row flex-wrap gap-4">
                <button onClick={() => navigate('/generate-video')} style={{
                  background: 'linear-gradient(45deg, #81ecff 0%, #a68cff 100%)',
                  color: '#3b00a0', padding: '16px 32px', borderRadius: '12px',
                  fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                  fontSize: '1rem', border: 'none', cursor: 'pointer',
                  boxShadow: '0 0 20px rgba(129,236,255,0.3)',
                  transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                }}
                  onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'}
                  onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                >
                  Generate Video
                </button>

                <button onClick={() => navigate('/analytics')} style={{
                  background: '#1c1f2b',
                  border: '1px solid rgba(70, 71, 82, 0.3)',
                  color: '#81ecff', padding: '16px 32px', borderRadius: '12px',
                  fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                  fontSize: '1rem', cursor: 'pointer',
                  transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                }}
                  onMouseEnter={e => e.currentTarget.style.background = '#222532'}
                  onMouseLeave={e => e.currentTarget.style.background = '#1c1f2b'}
                >
                  View Analytics
                </button>
              </div>
            </div>
          </section>

          {/* ===== QUICK ACTIONS GRID ===== */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            {[
              { icon: '📈', iconBg: 'rgba(129,236,255,0.1)', iconColor: '#81ecff', hoverBg: '#81ecff', title: 'Trend Analysis', desc: "AI-optimized scripts based on your niche's trending topics." },
              { icon: '📝', iconBg: 'rgba(166,140,255,0.1)', iconColor: '#a68cff', hoverBg: '#a68cff', title: 'Smart Scripting', desc: 'Neural clones for natural, high-retention narration.' },
              { icon: '🎨', iconBg: 'rgba(243,255,202,0.1)', iconColor: '#f3ffca', hoverBg: '#f3ffca', title: 'High Visual Video', desc: 'Apply cinematic color grading and brand assets instantly.' },
              { icon: '🚀', iconBg: 'rgba(255,113,108,0.1)', iconColor: '#ff716c', hoverBg: '#ff716c', title: 'Auto Uploading', desc: 'Schedule and deploy content across multiple channels.' },
            ].map((card, i) => (
              <div key={i}
                style={{
                  background: '#1c1f2b', padding: '24px', borderRadius: '16px',
                  transition: 'all 0.2s',
                  border: '1px solid rgba(255,255,255,0.05)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.transform = 'scale(1.02)';
                  // Swap icon bg
                  const iconEl = e.currentTarget.querySelector('.card-icon');
                  if (iconEl) { iconEl.style.background = card.hoverBg; iconEl.style.color = '#0c0e17'; }
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform = 'scale(1)';
                  const iconEl = e.currentTarget.querySelector('.card-icon');
                  if (iconEl) { iconEl.style.background = card.iconBg; iconEl.style.color = card.iconColor; }
                }}
              >
                <div className="card-icon" style={{
                  width: '48px', height: '48px', borderRadius: '12px',
                  background: card.iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: card.iconColor, fontSize: '24px',
                  marginBottom: '24px', transition: 'all 0.3s',
                }}>{card.icon}</div>
                <h5 style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 700, fontSize: '1rem', marginBottom: '8px',
                }}>{card.title}</h5>
                <p style={{
                  color: '#aaaab7', fontSize: '12px',
                  lineHeight: 1.6,
                }}>{card.desc}</p>
              </div>
            ))}
          </section>

          {/* ===== CHANNELS SECTION (App Logic) ===== */}
          {channels.length > 0 && (
            <section>
              <h3 style={{
                fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                fontSize: '1.5rem', marginBottom: '24px', letterSpacing: '-0.02em',
              }}>Your Channels</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6">
                {channels.map(ch => (
                  <div key={ch.channel_id} onClick={() => setSelectedChannelId(ch.channel_id || ch.id)} className="p-5 md:p-6" style={{
                    background: '#171924', borderRadius: '16px',
                    transition: 'all 0.2s', cursor: 'pointer',
                    border: selectedChannelId === (ch.channel_id || ch.id) ? '1px solid rgba(0,229,255,0.3)' : '1px solid rgba(255,255,255,0.05)',
                  }}
                    onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.02)'; }}
                    onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                      {ch.thumbnail_url ? (
                        <img src={ch.thumbnail_url} alt={ch.channel_name} style={{ width: 44, height: 44, borderRadius: '50%', objectFit: 'cover' }} />
                      ) : (
                        <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'rgba(255,0,0,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>📺</div>
                      )}
                      <div>
                        <h4 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '1rem', marginBottom: '2px' }}>
                          {ch.channel_name || ch.snippet?.title}
                        </h4>
                        <span style={{
                          fontSize: '10px', fontFamily: "'Manrope', sans-serif", fontWeight: 700,
                          padding: '2px 8px', borderRadius: '4px',
                          background: 'rgba(190,238,0,0.1)', color: '#beee00',
                          textTransform: 'uppercase', letterSpacing: '0.05em',
                        }}>Active</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '24px' }}>
                      <div>
                        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.125rem' }}>
                          {(ch.subscriber_count || 0).toLocaleString()}
                        </div>
                        <div style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Subscribers</div>
                      </div>
                      <div>
                        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.125rem' }}>
                          {(ch.video_count || 0)}
                        </div>
                        <div style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Videos</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {channels.length === 0 && sessionReady && (
            <section style={{ textAlign: 'center' }}>
              <div style={{
                background: '#171924', borderRadius: '2rem',
                padding: '40px 20px',
                border: '2px dashed rgba(70,71,82,0.2)',
              }}>
                <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.3 }}>📺</div>
                <p style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.25rem', marginBottom: '8px' }}>No channels connected yet</p>
                <p style={{ color: '#aaaab7', fontSize: '14px', marginBottom: '24px' }}>
                  Connect your YouTube channel to get started with AI automation.
                </p>
                <button onClick={handleAddChannel} style={{
                  background: 'linear-gradient(45deg, #81ecff, #a68cff)',
                  color: '#3b00a0', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                  fontSize: '14px', padding: '14px 32px', borderRadius: '12px',
                  border: 'none', cursor: 'pointer',
                }}>Connect Channel →</button>
              </div>
            </section>
          )}
        </main>
      </div>

      {/* ===== FOOTER ===== */}
      <footer className="w-full p-6 md:p-8 mt-auto flex flex-col sm:flex-row justify-between items-center gap-4 text-center sm:text-left opacity-60 border-t border-white/5 bg-[#0c0e17]">
        <div style={{
          fontFamily: "'Manrope', sans-serif", fontSize: '11px',
          textTransform: 'uppercase', letterSpacing: '0.15em', color: '#475569',
        }}>© 2024 YOUTOMIZE Cinematic Intelligence</div>
        <div className="flex flex-wrap justify-center gap-4 sm:gap-8">
          {['Terms', 'Privacy', 'API Status', 'Support'].map(item => (
            <a key={item} href="#" style={{
              fontFamily: "'Manrope', sans-serif", fontSize: '11px',
              textTransform: 'uppercase', letterSpacing: '0.15em',
              color: '#475569', textDecoration: 'none', transition: 'color 0.3s',
            }}
              onMouseEnter={e => e.target.style.color = '#81ecff'}
              onMouseLeave={e => e.target.style.color = '#475569'}
            >{item}</a>
          ))}
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;
