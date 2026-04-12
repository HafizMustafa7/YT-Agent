import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import apiService from '../features/yt-agent/services/apiService';

const Icon = ({ name, filled, className = '', style = {} }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", ...style }}
  >{name}</span>
);

const NicheInputPage = () => {
  const [sessionReady, setSessionReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [nicheValue, setNicheValue] = useState('');
  const [error, setError] = useState(null);

  // Results
  const [trends, setTrends] = useState([]);
  const [currentNiche, setCurrentNiche] = useState('Top Trending AI Video');
  const [loadingTopic, setLoadingTopic] = useState('');

  // AI Suggestions
  const [suggestedTopics, setSuggestedTopics] = useState([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalVideo, setModalVideo] = useState(null);
  const [modalTopic, setModalTopic] = useState('');
  const [modalTone, setModalTone] = useState('Professional & Informative');
  const [modalCameraMotion, setModalCameraMotion] = useState('Steady & Static');
  const [modalTargetAudience, setModalTargetAudience] = useState('Gen-Z');
  const [modalVisualStyle, setModalVisualStyle] = useState('Cyberpunk Noir');

  const navigate = useNavigate();

  // Initialize Session
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          navigate('/auth');
          return;
        }
        setSessionReady(true);
      } catch (err) {
        console.error('[NicheInputPage] Session verification failed:', err);
        navigate('/auth');
      }
    };
    initializeSession();
  }, [navigate]);

  // Fetch initial "Top Trending AI Video" trends on mount
  useEffect(() => {
    const fetchInitialTrends = async () => {
      if (!sessionReady) return;
      setIsLoading(true);
      setError(null);
      setIsLoadingSuggestions(true);
      setSuggestionsError(null);

      const trendsPromise = apiService.fetchTrends('analyze_niche', 'Top Trending AI Videos')
        .then(result => setTrends(result?.trends || []))
        .catch(() => setError('Failed to fetch initial trends.'))
        .finally(() => setIsLoading(false));

      const topicsPromise = apiService.suggestTopics('Top Trending AI Videos', 'search_trends', 0.01, 3)
        .then(suggestionsData => setSuggestedTopics(suggestionsData?.topics || []))
        .catch(() => setSuggestionsError('Failed to fetch suggested topics.'))
        .finally(() => setIsLoadingSuggestions(false));

      await Promise.all([trendsPromise, topicsPromise]);
    };
    if (sessionReady) {
      fetchInitialTrends();
    }
  }, [sessionReady]);

  // Handle Search Input
  const handleSearch = async (niche) => {
    if (!niche.trim()) { setError('Please enter a niche or keyword.'); return; }
    if (niche.trim().length < 3) { setError('Input must be at least 3 characters.'); return; }

    setIsLoading(true);
    setError(null);
    setCurrentNiche(niche);

    setIsLoadingSuggestions(true);
    setSuggestionsError(null);

    const trendsPromise = apiService.fetchTrends('analyze_niche', niche)
      .then(result => setTrends(result?.trends || []))
      .catch(() => setError('Failed to fetch trends. Please try again.'))
      .finally(() => setIsLoading(false));

    const topicsPromise = apiService.suggestTopics(niche, 'search_trends', 0.01, 3)
      .then(suggestionsData => setSuggestedTopics(suggestionsData?.topics || []))
      .catch(() => setSuggestionsError('Failed to fetch suggested topics.'))
      .finally(() => setIsLoadingSuggestions(false));

    await Promise.all([trendsPromise, topicsPromise]);
  };

  const openModalForVideo = (videoTitle, videoObj) => {
    setModalVideo(videoObj);
    setModalTopic(videoTitle);
    setIsModalOpen(true);
  };

  const submitModalForm = async () => {
    setError('');
    setIsLoading(true);
    setLoadingTopic(modalTopic);

    try {
      const creativePreferences = {
        duration_seconds: 44,
        target_audience: modalTargetAudience.toLowerCase(),
        tone: modalTone.toLowerCase(),
        visual_style: modalVisualStyle.toLowerCase(),
        camera_movement: modalCameraMotion.toLowerCase(),
        effects: 'subtle',
        story_format: 'shorts'
      };

      const videoData = modalVideo || {
        id: 'custom',
        title: modalTopic,
        description: '',
        views: 0,
        likes: 0,
        tags: [],
        ai_confidence: 0,
      };

      const result = await apiService.generateStory(
        modalTopic.trim(),
        videoData,
        creativePreferences
      );

      if (result.success || result.story) {
        setIsModalOpen(false);
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

  return (
    <div style={{
      background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd',
      fontFamily: "'Inter', sans-serif", display: 'flex', flexDirection: 'column',
      position: 'relative', overflowX: 'hidden'
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } } .animate-spin { animation: spin 1s linear infinite; }`}</style>

      {/* Background Orbs */}
      <div style={{
        position: 'fixed', top: '-10%', left: '-5%', width: '50%', height: '50%',
        borderRadius: '50%', background: 'rgba(129,236,255,0.05)',
        filter: 'blur(120px)', pointerEvents: 'none', zIndex: 0,
      }} />

      {/* HEADER */}
      <header style={{ background: '#11131d', position: 'sticky', top: 0, zIndex: 50, borderBottom: '1px solid rgba(115,117,128,0.1)' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 24px', height: '56px', maxWidth: '1920px', margin: '0 auto', width: '100%'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
            <span
              onClick={() => navigate('/dashboard')}
              style={{
                fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.2rem',
                fontWeight: 700, letterSpacing: '-0.05em', color: '#00E5FF', cursor: 'pointer',
              }}
            >YOUTOMIZE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <button
              onClick={() => navigate('/dashboard')}
              style={{
                background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                color: '#aaaab7', padding: '4px 12px', borderRadius: '6px',
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                fontFamily: "'Inter', sans-serif", fontSize: '11px', transition: 'all 0.3s',
              }}
              onMouseEnter={e => e.currentTarget.style.color = '#81ecff'}
              onMouseLeave={e => e.currentTarget.style.color = '#aaaab7'}
            >
              <Icon name="arrow_back" style={{ fontSize: '14px' }} /> Dashboard
            </button>
          </div>
        </div>
      </header>

      <main style={{
        flexGrow: 1, display: 'flex', flexDirection: 'column', maxWidth: '1920px', margin: '0 auto',
        padding: '16px 24px', gap: '32px', width: '100%', alignItems: 'center',
        position: 'relative', zIndex: 10
      }}>

        {/* Top Search Area */}
        <section style={{ textAlign: 'center', width: '100%', maxWidth: '600px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <h1 style={{
            fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
            fontSize: '28px', letterSpacing: '-0.02em',
            lineHeight: 1.1, marginBottom: '24px',
            background: 'linear-gradient(to bottom, #f0f0fd, #aaaab7)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            Discover What's Viral
          </h1>

          <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ position: 'relative' }}>
              <form
                onSubmit={e => { e.preventDefault(); handleSearch(nicheValue); }}
                style={{
                  display: 'flex', alignItems: 'center', background: '#11131d', borderRadius: '10px',
                  padding: '4px 16px', border: '1px solid rgba(115,117,128,0.15)',
                }}
              >
                <Icon name="search" style={{ color: 'rgba(115,117,128,0.5)', fontSize: '20px', marginRight: '12px' }} />
                <input
                  type="text"
                  value={nicheValue}
                  onChange={e => { setNicheValue(e.target.value); setError(null); }}
                  placeholder="Enter a niche, e.g. AI Workflow..."
                  disabled={isLoading}
                  style={{
                    background: 'transparent', border: 'none', outline: 'none',
                    width: '100%', padding: '12px 0', color: '#f0f0fd', fontFamily: "'Inter', sans-serif", fontSize: '14px',
                  }}
                />
                {nicheValue.trim().length >= 3 && (
                  <button type="submit" disabled={isLoading} style={{ background: 'transparent', border: 'none', color: '#81ecff', cursor: 'pointer' }}>
                    <Icon name="arrow_forward" style={{ fontSize: '20px' }} />
                  </button>
                )}
              </form>
            </div>
          </div>
        </section>

        {/* BOTTOM CONTENT AREA (Grid + Sidebar) */}
        <div style={{ display: 'flex', width: '100%', gap: '24px', alignItems: 'flex-start', justifyContent: 'center' }}>

          {/* Results Area */}
          <div style={{ flexGrow: 1, maxWidth: 'calc(100% - 304px)', display: 'flex', flexDirection: 'column' }}>
            {error && (
              <div style={{
                padding: '10px', background: 'rgba(255,113,108,0.1)', border: '1px solid rgba(255,113,108,0.2)',
                borderRadius: '8px', color: '#ff716c', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px'
              }}>
                <Icon name="error" style={{ fontSize: '16px' }} /> {error}
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '14px', margin: 0 }}>Trending in:</h2>
              <span style={{ background: 'rgba(0, 229, 255, 0.1)', color: '#00E5FF', padding: '2px 8px', borderRadius: '16px', fontSize: '10px', fontWeight: 'bold' }}>
                {currentNiche}
              </span>
            </div>

            {isLoading ? (
              <div style={{ textAlign: 'center', padding: '60px', background: '#171924', borderRadius: '10px', border: '1px dashed rgba(115,117,128,0.2)' }}>
                <Icon name="progress_activity" className="animate-spin" style={{ color: '#81ecff', fontSize: '32px' }} />
              </div>
            ) : trends.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px', background: '#171924', borderRadius: '10px', border: '1px dashed rgba(115,117,128,0.2)' }}>
                <p style={{ color: '#aaaab7', fontSize: '12px' }}>No trending videos found. Try another keyword!</p>
              </div>
            ) : (
              <div style={{
                /* EXACTLY 3 items in one row, but allowing multiple rows */
                display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px'
              }}>
                {trends.slice(0, 15).map((video) => {
                  return (
                    <div key={video.id} className="group" style={{
                      background: '#1c1f2b', borderRadius: '10px', overflow: 'hidden',
                      transition: 'transform 0.3s, box-shadow 0.3s',
                      border: '1px solid rgba(115,117,128,0.1)', display: 'flex', flexDirection: 'column'
                    }}
                      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.5)' }}
                      onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none' }}
                    >
                      {/* Image container using reduced Aspect Ratio or padding */}
                      <div style={{ height: '120px', position: 'relative', overflow: 'hidden' }}>
                        <img
                          src={video.thumbnail} alt={video.title}
                          style={{ width: '100%', height: '100%', objectFit: 'cover', transition: 'transform 0.5s' }}
                          onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'}
                          onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                        />
                        <button
                          onClick={() => window.open(video.url || `https://youtube.com/shorts/${video.id}`, "_blank", "noopener,noreferrer")}
                          title="Open Video in YouTube"
                          style={{
                            position: 'absolute', top: '8px', right: '8px',
                            background: 'rgba(12, 14, 23, 0.7)', backdropFilter: 'blur(4px)',
                            border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px',
                            width: '26px', height: '26px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                            cursor: 'pointer', outline: 'none', color: '#f0f0fd', transition: 'all 0.2s', zIndex: 2
                          }}
                          onMouseEnter={e => { e.currentTarget.style.background = '#81ecff'; e.currentTarget.style.color = '#0c0e17'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'rgba(12, 14, 23, 0.7)'; e.currentTarget.style.color = '#f0f0fd'; }}
                        >
                          <Icon name="north_east" style={{ fontSize: '14px' }} />
                        </button>
                      </div>

                      <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px', flexGrow: 1 }}>
                        <div>
                          <h3 style={{
                            fontFamily: "'Space Grotesk', sans-serif", fontSize: '13px', fontWeight: 600,
                            lineHeight: 1.2, margin: 0, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'
                          }}>{video.title}</h3>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: '#737580', fontFamily: "'Inter', sans-serif", marginTop: '8px' }}>
                            <span style={{ fontWeight: 800, color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', paddingRight: '10px' }}>
                              {video.channel}
                            </span>
                            <span style={{ flexShrink: 0 }}>
                              {video.duration}
                            </span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: 'auto' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }} title="Views">
                            <Icon name="visibility" style={{ fontSize: '12px', color: '#737580' }} />
                            <span style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#aaaab7' }}>{formatNumber(video.views)}</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }} title="Likes">
                            <Icon name="favorite" filled style={{ fontSize: '12px', color: '#737580' }} />
                            <span style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#aaaab7' }}>{formatNumber(video.likes)}</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }} title="Comments">
                            <Icon name="chat_bubble" filled style={{ fontSize: '12px', color: '#737580' }} />
                            <span style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#aaaab7' }}>{formatNumber(video.comments)}</span>
                          </div>
                        </div>

                        <button
                          onClick={() => openModalForVideo(video.title, video)}
                          disabled={isLoading}
                          style={{
                            width: '100%', padding: '8px', borderRadius: '6px',
                            border: '1px solid rgba(0,229,255,0.2)', background: 'rgba(0,229,255,0.05)',
                            color: '#00E5FF', fontFamily: "'Manrope', sans-serif", fontWeight: 700,
                            fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em',
                            cursor: isLoading ? 'not-allowed' : 'pointer', transition: 'all 0.3s',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                            opacity: (isLoading) ? 0.5 : 1, marginTop: '4px'
                          }}
                          onMouseEnter={e => { if (!isLoading) { e.currentTarget.style.background = '#81ecff'; e.currentTarget.style.color = '#005762'; } }}
                          onMouseLeave={e => { if (!isLoading) { e.currentTarget.style.background = 'rgba(0,229,255,0.05)'; e.currentTarget.style.color = '#00E5FF'; } }}
                        >
                          Select Topic
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* RIGHT SIDEBAR */}
          <aside style={{ width: '280px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ background: '#171924', borderRadius: '10px', padding: '16px', border: '1px solid rgba(115,117,128,0.15)' }}>
              <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '16px', color: '#f0f0fd' }}>
                Suggested Concepts
              </h2>

              {isLoadingSuggestions ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '20px 0' }}>
                  <Icon name="progress_activity" className="animate-spin" style={{ color: '#81ecff', fontSize: '24px' }} />
                </div>
              ) : suggestionsError ? (
                <div style={{ color: '#ff716c', fontSize: '11px', textAlign: 'center', padding: '10px' }}>{suggestionsError}</div>
              ) : suggestedTopics.length === 0 ? (
                <div style={{ color: '#aaaab7', fontSize: '11px', textAlign: 'center', padding: '10px' }}>No suggestions available.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {suggestedTopics.map((item, idx) => {
                    const topicStr = typeof item === 'string' ? item : item.topic;
                    return (
                      <div key={idx} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px', borderRadius: '6px', cursor: 'default'
                      }} className="hover:bg-surface-container-high" onMouseEnter={e => e.currentTarget.style.background = '#1c1f2b'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <span style={{ fontSize: '12px', fontWeight: 500, color: '#f0f0fd', cursor: 'pointer' }} onClick={() => { setNicheValue(topicStr); handleSearch(topicStr); }}>{topicStr}</span>
                        <button
                          onClick={() => { setNicheValue(topicStr); handleSearch(topicStr); }} disabled={isLoading}
                          style={{
                            padding: '4px 8px', borderRadius: '4px', background: 'rgba(0,229,255,0.1)', color: '#00E5FF', fontSize: '9px', fontWeight: 700, fontFamily: "'Manrope', sans-serif", textTransform: 'uppercase', border: 'none', cursor: isLoading ? 'not-allowed' : 'pointer', opacity: (isLoading) ? 0.5 : 1
                          }}
                        >
                          {isLoading && currentNiche === topicStr ? <Icon name="progress_activity" className="animate-spin" style={{ fontSize: '10px' }} /> : 'Search'}
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div style={{ background: 'rgba(0,229,255,0.05)', borderRadius: '10px', padding: '16px', border: '1px solid rgba(0,229,255,0.2)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#00E5FF' }}>
                <Icon name="lightbulb" filled style={{ fontSize: '16px' }} />
                <span style={{ fontSize: '10px', fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", textTransform: 'uppercase', letterSpacing: '0.1em' }}>Pro Tip</span>
              </div>
              <p style={{ fontSize: '11px', color: 'rgba(240,240,253,0.7)', lineHeight: 1.5, fontFamily: "'Inter', sans-serif", fontStyle: 'italic', margin: 0 }}>
                Pick a trending video to automatically style your generation around its core audience and tone. High views map to proven formulas.
              </p>
            </div>
          </aside>
        </div>
      </main>

      {/* TOPIC INPUT MODAL */}
      {isModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          background: 'rgba(5, 7, 12, 0.85)', backdropFilter: 'blur(10px)',
          zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: '#11131d', width: '360px', borderRadius: '16px', border: '1px solid rgba(115,117,128,0.2)',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)', padding: '24px', position: 'relative'
          }}>
            {!isLoading && (
              <button
                onClick={() => setIsModalOpen(false)}
                style={{ position: 'absolute', top: '16px', right: '16px', background: 'transparent', border: 'none', color: '#737580', cursor: 'pointer', fontSize: '20px' }}>
                <Icon name="close" />
              </button>
            )}

            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '16px', fontWeight: 700, color: '#f0f0fd', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '24px' }}>
              Topic Input
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#737580', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>Enter Topic</label>
                <div style={{ position: 'relative' }}>
                  <Icon name="search" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#737580', fontSize: '16px' }} />
                  <input
                    type="text" value={modalTopic} onChange={(e) => setModalTopic(e.target.value)} disabled={isLoading}
                    style={{ width: '100%', background: '#1c1f2b', border: '1px solid rgba(115,117,128,0.1)', borderRadius: '8px', padding: '10px 10px 10px 36px', color: '#f0f0fd', fontSize: '12px', outline: 'none' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#737580', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>Tone</label>
                <select value={modalTone} onChange={(e) => setModalTone(e.target.value)} disabled={isLoading}
                  style={{ width: '100%', background: '#1c1f2b', border: 'none', color: '#f0f0fd', padding: '10px 12px', borderRadius: '8px', fontSize: '12px', outline: 'none', cursor: 'pointer' }}>
                  <option>Professional & Informative</option>
                  <option>High-Energy & Viral</option>
                  <option>Dark Cinematic</option>
                  <option>Casual & Relatable</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#737580', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>Camera Motion</label>
                <select value={modalCameraMotion} onChange={(e) => setModalCameraMotion(e.target.value)} disabled={isLoading}
                  style={{ width: '100%', background: '#1c1f2b', border: 'none', color: '#f0f0fd', padding: '10px 12px', borderRadius: '8px', fontSize: '12px', outline: 'none', cursor: 'pointer' }}>
                  <option>Steady & Static</option>
                  <option>Dynamic Handheld</option>
                  <option>FPV Drone Aesthetic</option>
                  <option>Slow Pan / Tilt</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#737580', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>Target Audience</label>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {['Gen-Z', 'Techies', 'Creatives'].map(aud => (
                    <button key={aud} disabled={isLoading} onClick={() => setModalTargetAudience(aud)}
                      style={{
                        padding: '6px 16px', borderRadius: '24px', border: 'none', fontSize: '11px', fontWeight: 700, cursor: isLoading ? 'not-allowed' : 'pointer',
                        background: modalTargetAudience === aud ? 'rgba(0,229,255,0.1)' : '#1c1f2b',
                        color: modalTargetAudience === aud ? '#00E5FF' : '#f0f0fd',
                      }}>
                      {aud}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", color: '#737580', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>Visual Style</label>
                <select value={modalVisualStyle} onChange={(e) => setModalVisualStyle(e.target.value)} disabled={isLoading}
                  style={{ width: '100%', background: '#1c1f2b', border: 'none', color: '#f0f0fd', padding: '10px 12px', borderRadius: '8px', fontSize: '12px', outline: 'none', cursor: 'pointer' }}>
                  <option>Cyberpunk Noir</option>
                  <option>Clean Minimalist</option>
                  <option>Gritty Industrial</option>
                  <option>Retro Synthwave</option>
                </select>
              </div>

              <button
                onClick={submitModalForm} disabled={isLoading}
                style={{
                  width: '100%', padding: '16px', marginTop: '12px', borderRadius: '8px', border: '1px solid rgba(115,117,128,0.2)',
                  background: '#1c1f2b', color: isLoading ? '#81ecff' : '#f0f0fd', fontFamily: "'Manrope', sans-serif", fontSize: '12px',
                  fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', cursor: isLoading ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                }}
                onMouseEnter={e => { if (!isLoading) e.currentTarget.style.background = '#222532' }}
                onMouseLeave={e => { if (!isLoading) e.currentTarget.style.background = '#1c1f2b' }}
              >
                {isLoading ? <Icon name="progress_activity" className="animate-spin" style={{ fontSize: '16px' }} /> : null}
                {isLoading ? 'WAITING...' : 'ENTER TOPIC'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default NicheInputPage;
