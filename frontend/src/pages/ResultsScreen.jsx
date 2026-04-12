import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import apiService from '../features/yt-agent/services/apiService';

const Icon = ({ name, filled, className = '', style = {} }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", ...style }}
  >{name}</span>
);

const ResultsScreen = () => {
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingTopic, setLoadingTopic] = useState('');
  const [sessionReady, setSessionReady] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const data = location.state?.trendingData;
  const niche = location.state?.niche;

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

  const handleGenerate = async (selectedTopic, videoObj = null) => {
    setError('');
    setIsLoading(true);
    setLoadingTopic(selectedTopic);

    try {
      const creativePreferences = {
        duration_seconds: 44, 
        target_audience: 'general',
        tone: 'engaging'
      };

      // Ensure video data has required fields
      const videoData = videoObj || {
          id: 'custom',
          title: selectedTopic,
          description: '',
          views: 0,
          likes: 0,
          tags: [],
          ai_confidence: 0,
      };

      const result = await apiService.generateStory(
        selectedTopic.trim(),
        videoData,
        creativePreferences
      );

      if (result.success || result.story) {
        navigate('/frame-results', { state: { data: result.story || result } });
      } else {
        throw new Error('Story generation failed');
      }
    } catch (err) {
      console.error('Story generation failed:', err);
      setError(err.message || "Failed to generate story. Please try again.");
    } finally {
      setIsLoading(false);
      setLoadingTopic('');
    }
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num?.toString() || '0';
  };

  if (!sessionReady) {
    return (
      <div style={{ background: '#0c0e17', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon name="progress_activity" className="animate-spin" style={{ color: '#81ecff', fontSize: '32px' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } } .animate-spin { animation: spin 1s linear infinite; }`}</style>
      </div>
    );
  }

  const trends = data?.trends || [];

  return (
    <div style={{
      background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd',
      fontFamily: "'Inter', sans-serif", display: 'flex', flexDirection: 'column',
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } } .animate-spin { animation: spin 1s linear infinite; }`}</style>
      
      {/* HEADER */}
      <header style={{ background: '#11131d', position: 'sticky', top: 0, zIndex: 50, borderBottom: '1px solid rgba(115,117,128,0.1)' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 32px', height: '64px', maxWidth: '1920px', margin: '0 auto',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
             <span
              onClick={() => navigate('/dashboard')}
              style={{
                fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.25rem',
                fontWeight: 700, letterSpacing: '-0.05em', color: '#00E5FF', cursor: 'pointer',
              }}
            >YOUTOMIZE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
             <button
              onClick={() => navigate('/niche-input')}
              style={{
                background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', 
                color: '#aaaab7', padding: '6px 16px', borderRadius: '8px',
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: "'Inter', sans-serif", fontSize: '12px', transition: 'all 0.3s',
              }}
              onMouseEnter={e => e.currentTarget.style.color = '#81ecff'}
              onMouseLeave={e => e.currentTarget.style.color = '#aaaab7'}
            >
              <Icon name="arrow_back" style={{ fontSize: '16px' }} /> Search Again
            </button>
          </div>
        </div>
      </header>

      <main style={{
        flexGrow: 1, display: 'flex', maxWidth: '1920px', margin: '0 auto',
        padding: '32px', gap: '48px', width: '100%', alignItems: 'flex-start'
      }}>
        {/* CENTER CONTENT: YOUTUBE API TRENDS GRID */}
        <div style={{ flexGrow: 1 }}>
          <section style={{ marginBottom: '40px' }}>
            <h1 style={{
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
              fontSize: '2rem', letterSpacing: '-0.02em',
              marginBottom: '8px', color: '#f0f0fd'
            }}>
              Discover What's Viral
            </h1>
            <p style={{ color: '#aaaab7', fontSize: '14px' }}>
              Trending results for topic: <span style={{ color: '#00E5FF', fontWeight: 600 }}>{niche || 'General'}</span>
            </p>
          </section>

          {error && (
            <div style={{
              padding: '16px', background: 'rgba(255,113,108,0.1)', border: '1px solid rgba(255,113,108,0.2)',
              borderRadius: '8px', color: '#ff716c', marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '8px'
            }}>
              <Icon name="error" /> {error}
            </div>
          )}

          {trends.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px' }}>
              <p style={{ color: '#aaaab7' }}>No trending videos found. Please try another niche.</p>
            </div>
          ) : (
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px'
            }}>
              {trends.slice(0, 9).map((video, index) => {
                const badgeThemes = [
                  { text: 'TRENDING #1', bg: 'rgba(0,229,255,0.1)', color: '#00E5FF' },
                  { text: 'RISING FAST', bg: 'rgba(166,140,255,0.1)', color: '#a68cff' },
                  { text: 'DEEP DIVE', bg: 'rgba(190,238,0,0.1)', color: '#beee00' },
                  { text: 'VIRAL HIT', bg: 'rgba(255,113,108,0.1)', color: '#ff716c' },
                ];
                const badgeTheme = badgeThemes[index % 4];

                const isGeneratingThis = isLoading && loadingTopic === video.title;

                return (
                  <div key={video.id} className="group" style={{
                    background: '#1c1f2b', borderRadius: '12px', overflow: 'hidden',
                    transition: 'transform 0.3s, box-shadow 0.3s',
                    border: '1px solid rgba(115,117,128,0.1)',
                    display: 'flex', flexDirection: 'column'
                  }}
                  onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)' }}
                  onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none' }}
                  >
                    <div style={{ aspectRatio: '16/9', position: 'relative', overflow: 'hidden' }}>
                      <img 
                        src={video.thumbnail} 
                        alt={video.title} 
                        style={{ width: '100%', height: '100%', objectFit: 'cover', transition: 'transform 0.5s' }}
                        onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'}
                        onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                      />
                      <div style={{
                          position: 'absolute', top: '12px', left: '12px',
                          background: 'rgba(12, 14, 23, 0.8)', backdropFilter: 'blur(8px)',
                          padding: '4px 8px', borderRadius: '4px', fontSize: '10px',
                          fontFamily: "'Manrope', sans-serif", fontWeight: 700,
                          color: badgeTheme.color, textTransform: 'uppercase', letterSpacing: '-0.05em'
                      }}>
                        {badgeTheme.text}
                      </div>
                      
                      {video.duration && (
                        <div style={{
                           position: 'absolute', bottom: '12px', right: '12px',
                           background: 'rgba(12, 14, 23, 0.8)', backdropFilter: 'blur(8px)',
                           padding: '4px 8px', borderRadius: '4px', fontSize: '10px',
                           fontFamily: "'Manrope', sans-serif", fontWeight: 700,
                           color: '#f0f0fd'
                        }}>
                          {video.duration}
                        </div>
                      )}
                    </div>

                    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', flexGrow: 1 }}>
                      <h3 style={{
                        fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.125rem', fontWeight: 700,
                        lineHeight: 1.2, margin: 0, transition: 'color 0.3s',
                        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'
                      }}
                      onMouseEnter={e => e.currentTarget.style.color = '#00E5FF'}
                      onMouseLeave={e => e.currentTarget.style.color = '#f0f0fd'}
                      >
                        {video.title}
                      </h3>
                      
                      <div style={{ display: 'flex', alignItems: 'center', gap: '24px', marginTop: 'auto' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Icon name="visibility" style={{ fontSize: '14px', color: '#737580' }} />
                          <span style={{ fontSize: '12px', fontFamily: "'Manrope', sans-serif", color: '#aaaab7' }}>
                            {formatNumber(video.views)} views
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Icon name="favorite" filled style={{ fontSize: '14px', color: '#737580' }} />
                          <span style={{ fontSize: '12px', fontFamily: "'Manrope', sans-serif", color: '#aaaab7' }}>
                            {formatNumber(video.likes)} likes
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleGenerate(video.title, video)}
                        disabled={isLoading}
                        style={{
                          width: '100%', padding: '12px', borderRadius: '8px',
                          border: '1px solid rgba(0,229,255,0.2)', background: 'rgba(0,229,255,0.05)',
                          color: '#00E5FF', fontFamily: "'Manrope', sans-serif", fontWeight: 700,
                          fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.1em',
                          cursor: isLoading ? 'not-allowed' : 'pointer', transition: 'all 0.3s',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                          opacity: (isLoading && !isGeneratingThis) ? 0.5 : 1
                        }}
                        onMouseEnter={e => {
                          if(!isLoading) {
                            e.currentTarget.style.background = '#81ecff';
                            e.currentTarget.style.color = '#005762';
                          }
                        }}
                        onMouseLeave={e => {
                          if(!isLoading) {
                            e.currentTarget.style.background = 'rgba(0,229,255,0.05)';
                            e.currentTarget.style.color = '#00E5FF';
                          }
                        }}
                      >
                        {isGeneratingThis ? <Icon name="progress_activity" className="animate-spin" style={{ fontSize: '16px' }} /> : null}
                        {isGeneratingThis ? 'Generating...' : 'Select Topic'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* RIGHT SIDEBAR (Without Input Box) */}
        <aside style={{ width: '320px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '32px' }}>
           
           {/* Suggested Topics Box (moved up) */}
           <div style={{
              background: '#171924', borderRadius: '12px', padding: '24px',
              border: '1px solid rgba(115,117,128,0.15)'
           }}>
             <h2 style={{
               fontFamily: "'Space Grotesk', sans-serif", fontSize: '14px', fontWeight: 700,
               textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '24px',
               color: '#f0f0fd'
             }}>
               Suggested Concepts
             </h2>
             <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[
                  { topic: `${niche || 'AI Video'} Masterclass`, growth: '+140%' },
                  { topic: `The Truth About ${niche || 'Aesthetics'}`, growth: '+85%' },
                  { topic: `${niche || 'Minimalist'} Approaches`, growth: '+112%' },
                ].map((item, idx) => {
                  const isGeneratingThis = isLoading && loadingTopic === item.topic;
                  return (
                  <div key={idx} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px', borderRadius: '8px',
                    transition: 'background 0.3s', cursor: 'default'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#1c1f2b'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '14px', fontWeight: 500, color: '#f0f0fd', transition: 'color 0.3s' }}>
                        {item.topic}
                      </span>
                      <span style={{ fontSize: '10px', color: '#737580' }}>
                        Growth: {item.growth}
                      </span>
                    </div>
                    <button
                      onClick={() => handleGenerate(item.topic)}
                      disabled={isLoading}
                      style={{
                        padding: '6px 12px', borderRadius: '4px',
                        background: 'rgba(0,229,255,0.1)', color: '#00E5FF',
                        fontSize: '10px', fontWeight: 700, fontFamily: "'Manrope', sans-serif",
                        textTransform: 'uppercase', border: 'none', cursor: isLoading ? 'not-allowed' : 'pointer',
                        transition: 'all 0.3s', display: 'flex', alignItems: 'center', gap: '4px',
                        opacity: (isLoading && !isGeneratingThis) ? 0.5 : 1
                      }}
                      onMouseEnter={e => { if(!isLoading) { e.currentTarget.style.background = '#81ecff'; e.currentTarget.style.color = '#005762'; } }}
                      onMouseLeave={e => { if(!isLoading) { e.currentTarget.style.background = 'rgba(0,229,255,0.1)'; e.currentTarget.style.color = '#00E5FF'; } }}
                    >
                      {isGeneratingThis ? <Icon name="progress_activity" className="animate-spin" style={{ fontSize: '12px' }} /> : 'Select'}
                    </button>
                  </div>
                )})}
             </div>
           </div>

           {/* Pro Tip Box */}
           <div style={{
              background: 'rgba(0,229,255,0.05)', borderRadius: '12px', padding: '20px',
              border: '1px solid rgba(0,229,255,0.2)', display: 'flex', flexDirection: 'column', gap: '12px'
           }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#00E5FF' }}>
               <Icon name="lightbulb" filled style={{ fontSize: '20px' }} />
               <span style={{ fontSize: '10px', fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                 Pro Tip
               </span>
             </div>
             <p style={{
               fontSize: '12px', color: 'rgba(240,240,253,0.7)', lineHeight: 1.6,
               fontFamily: "'Inter', sans-serif", fontStyle: 'italic', margin: 0
             }}>
               Pick a trending video to automatically style your AI generation around its core audience and tone. High views and likes map to proven engagement formulas.
             </p>
           </div>
        </aside>
      </main>

       {/* Floating Action Visual Element */}
       <div style={{
        position: 'fixed', bottom: 0, right: 0, padding: '48px', pointerEvents: 'none', zIndex: 0
      }}>
        <div style={{
          width: '500px', height: '500px', borderRadius: '50%',
          background: 'rgba(0,229,255,0.05)', filter: 'blur(100px)'
        }} />
      </div>
    </div>
  );
};

export default ResultsScreen;