import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import apiService from '../features/yt-agent/services/apiService';

const POLL_BASE_MS = 4000;
const POLL_MAX_MS = 15000;

const Icon = ({ name, filled, className = '', style = {} }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", ...style }}
  >{name}</span>
);

const FrameResults = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  const [error, setError] = useState(null);
  // Restore projectId from sessionStorage on refresh so completed frames survive reloads
  const [projectId, setProjectId] = useState(() => sessionStorage.getItem('yt_frame_project_id') || null);
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  // Generation specific states
  // generatingAll is persisted to sessionStorage so a page refresh during Generate All
  // correctly resumes rather than leaving pending frames orphaned.
  const [generatingAll, _setGeneratingAll] = useState(
    () => sessionStorage.getItem('yt_generating_all') === 'true'
  );
  // Stable wrapper: syncs generatingAll to sessionStorage on every change.
  // useCallback ensures a stable reference so it can safely be used in effects.
  const setGeneratingAll = useCallback((val) => {
    if (val) {
      sessionStorage.setItem('yt_generating_all', 'true');
    } else {
      sessionStorage.removeItem('yt_generating_all');
    }
    _setGeneratingAll(val);
  }, []);

  const [generatingFrameId, setGeneratingFrameId] = useState(null);
  const [combining, setCombining] = useState(false);
  const [finalVideoUrl, setFinalVideoUrl] = useState(null);
  // Per-frame retry-attempt count shown in status badge
  const [retryAttempts, setRetryAttempts] = useState({});  // { frameId: attemptN }
  const pollCountRef = useRef(0);
  const isCreatingRef = useRef(false);
  // Prevents the sequential driver from firing duplicate API requests
  // when the effect re-runs before the previous request completes.
  const isTriggering = useRef(false);
  // Flag to stop sequential generation if user cancelled or frame fatally failed
  const stopSequentialRef = useRef(false);

  const [editingPromptId, setEditingPromptId] = useState(null);
  const [editedPromptValue, setEditedPromptValue] = useState("");
  const [savingPromptId, setSavingPromptId] = useState(null);

  // Original raw story data passed from navigation state
  const storyResultRaw = location.state?.data;
  const rawStory = useMemo(() => storyResultRaw?.story || storyResultRaw || {}, [storyResultRaw]);
  const rawFrames = useMemo(() => Array.isArray(rawStory?.frames) ? rawStory.frames : [], [rawStory]);
  // Creative preferences passed through from NicheInput → YTAgentPage → navigate state
  const creativePrefs = useMemo(() => location.state?.creative_preferences || {}, [location.state]);
  const aspectRatio = useMemo(() => creativePrefs?.aspect_ratio || '9:16', [creativePrefs]);

  const getPollInterval = () => {
    const count = pollCountRef.current;
    if (count < 10) return POLL_BASE_MS;
    if (count < 30) return 8000;
    if (count < 60) return 12000;
    return POLL_MAX_MS;
  };

  const fetchProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const res = await apiService.getVideoProject(projectId);
      setProject(res.project);
      if (res.final_video_url) setFinalVideoUrl(res.final_video_url);
      setError(null);
    } catch (e) {
      console.error('Failed to fetch project', e);
    }
  }, [projectId]);

  // Project Creation exactly once on mount
  useEffect(() => {
    if (!storyResultRaw || projectId || project || isCreatingRef.current) return;
    
    const createProjectBackend = async () => {
      isCreatingRef.current = true;
      setError(null);
      setLoading(true);

      const normalizeFrameNumber = (value, fallback) => {
        const n = Number.parseInt(value, 10);
        return Number.isFinite(n) && n >= 1 ? n : fallback;
      };

      const normalizeDuration = (value) => {
        const raw = Number(value);
        // Accept any positive whole number ≥ 1 (Veo first frame = story duration, extensions = 7s)
        return (Number.isFinite(raw) && raw >= 1) ? Math.max(1, Math.floor(raw)) : 8;
      };

      const normalizedFrames = rawFrames
        .map((f, idx) => ({
          frame_num: normalizeFrameNumber(f?.frame_num ?? f?.frame_number, idx + 1),
          ai_video_prompt: String(f?.prompt ?? f?.ai_video_prompt ?? f?.video_prompt ?? '').trim().slice(0, 5000),
          scene_description: f?.scene_description ? String(f.scene_description) : null,
          duration_seconds: Number(f?.duration ?? f?.duration_seconds ?? 8),
        }))
        .filter((f) => f.ai_video_prompt.length > 0);

      if (normalizedFrames.length === 0) {
        setError('No valid frames generated. Please go back and try another topic.');
        setLoading(false);
        return;
      }

      // Use topic as title (new story JSON), fallback to legacy title or default
      const normalizedTitle = String(rawStory?.topic || rawStory?.title || 'Story Video').trim();
      const payloadTitle = (normalizedTitle || 'Story Video').slice(0, 255);

      try {
        const res = await apiService.createVideoProject(
            payloadTitle,
            normalizedFrames,
            null,          // channelId — supplied later at upload time
            aspectRatio,   // from creative preferences
            '720p',        // resolution always 720p for Veo 3.1
          );
          // Persist so the project survives a page refresh
          sessionStorage.setItem('yt_frame_project_id', res.project_id);
          setProjectId(res.project_id);
      } catch (err) {
        setError(err.message || 'Failed to initialize backend video project.');
        setLoading(false);
        isCreatingRef.current = false;
      }
    };
    
    createProjectBackend();
  // Only run if there is no existing projectId (either from state or sessionStorage)
  }, [storyResultRaw, projectId, project, rawFrames, rawStory]);

  // Whenever projectId is obtained, load it once
  useEffect(() => {
    if (projectId && !project) {
      fetchProject().then(() => setLoading(false));
    }
  }, [projectId, project, fetchProject]);

  // Clear sessionStorage when navigating away (browser back, link click, etc.)
  // so the next story session starts fresh instead of reloading this project.
  useEffect(() => {
    return () => {
      sessionStorage.removeItem('yt_frame_project_id');
      sessionStorage.removeItem('yt_generating_all');
    };
  }, []);

  // Auto-resume: when the page reloads mid-generation (generatingAll was persisted as true)
  // AND the project has loaded AND there's no frame actively generating on the backend,
  // the sequential driver is already enabled via sessionStorage restore. We just need to
  // make sure polling is active by ensuring the project status triggers the poll effect.
  // If generatingAll=true but all remaining frames are pending and nothing is 'generating',
  // the sequential driver useEffect will fire and trigger the next pending frame automatically.
  //
  // Edge case: generatingAll=true restored from sessionStorage but backend already finished
  // (e.g. user left browser open for hours). The driver will find no pending frames and
  // call setGeneratingAll(false), cleaning up sessionStorage.

  // Adaptive Polling
  useEffect(() => {
    if (!projectId || !project) return;
    const status = project?.status;
    const isActive = status === 'generating' || status === 'queued' || status === 'clips_ready';
    const hasActiveFrames = (project?.frames || []).some((f) => f.status === 'generating');
    
    if (!isActive && !hasActiveFrames && !generatingAll && !generatingFrameId && !combining) {
      pollCountRef.current = 0;
      return;
    }

    const tick = () => {
      pollCountRef.current += 1;
      fetchProject();
    };

    let timeoutId = setTimeout(function poll() {
      tick();
      timeoutId = setTimeout(poll, getPollInterval());
    }, getPollInterval());

    return () => clearTimeout(timeoutId);
  }, [projectId, project, fetchProject, generatingAll, generatingFrameId, combining]);

  // Engine Status Checking
  const liveFrames = useMemo(() => project?.frames || [], [project?.frames]);
  const liveAssets = useMemo(() => project?.assets || [], [project?.assets]);
  
  const completedCount = liveFrames.filter((f) => f.status === 'completed').length;
  const isGeneratingFull = project?.status === 'generating';
  const allCompleted = liveFrames.length > 0 && completedCount === liveFrames.length;

  useEffect(() => {
    // Only clear generatingAll on terminal project states.
    // Do NOT clear on 'pending' — that would kill the restored flag on page refresh
    // before the sequential driver gets a chance to fire.
    const terminalStates = ['failed', 'completed', 'cancelled'];
    if (project?.status && terminalStates.includes(project.status)) {
      setGeneratingAll(false);
    }
    if (finalVideoUrl) {
      setCombining(false);
    }
    if (generatingFrameId) {
      const targetFrame = liveFrames.find((f) => f.id === generatingFrameId);
      if (targetFrame && targetFrame.status !== 'generating') {
        setGeneratingFrameId(null);
      }
    }
  }, [project?.status, finalVideoUrl, generatingFrameId, liveFrames, setGeneratingAll]);

  // -----------------------------------------------------------------------
  // Sequential "Generate All" driver
  // Runs entirely on the frontend using polling data.
  // After each frame reaches SUCCESS it triggers the next frame.
  // Stops if a frame becomes 'failed' (FATAL on backend) or all done.
  // Survives page refresh: generatingAll is persisted to sessionStorage.
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!generatingAll || !projectId || !liveFrames.length) return;
    // Prevent re-entrant calls (effect may re-run while a request is in-flight)
    if (isTriggering.current) return;

    // Only auto-advance 'pending' frames. Failed frames halt the chain — they
    // require explicit user action (manual retry button) to avoid infinite loops.
    const pendingFrame = liveFrames.find((f) => f.status === 'pending');
    const anyGenerating = liveFrames.some((f) => f.status === 'generating');

    if (anyGenerating) return;  // Backend is processing — wait for next poll

    if (!pendingFrame) {
      // No more pending frames — either all done or a frame failed and halted the chain
      const anyFailed = liveFrames.some((f) => f.status === 'failed');
      if (anyFailed) {
        setError('A frame failed during generation. You can retry individual frames manually.');
      }
      setGeneratingAll(false);
      return;
    }

    const pendingIndex = liveFrames.findIndex((f) => f.id === pendingFrame.id);
    const prevFrame = pendingIndex > 0 ? liveFrames[pendingIndex - 1] : null;

    if (prevFrame && prevFrame.status !== 'completed') {
      // Sequence broken — previous frame failed, stop auto-sequential
      setGeneratingAll(false);
      return;
    }

    // Trigger the next frame — guard with isTriggering to prevent duplicate calls
    isTriggering.current = true;
    apiService.startGenerateFrame(projectId, pendingFrame.id)
      .then(() => fetchProject())
      .catch((e) => {
        const msg = e.message || '';
        setError(msg.toLowerCase().includes('insufficient')
          ? 'Not enough credits to continue generation. Please purchase more credits.'
          : (msg || 'Generation failed. Please try again.'));
        setGeneratingAll(false);  // Always reset so button re-enables
      })
      .finally(() => {
        isTriggering.current = false;  // Release lock regardless of outcome
      });
  }, [generatingAll, liveFrames, projectId, fetchProject]);

  // "Generate All" button: set flag so the sequential useEffect drives frame-by-frame generation.
  // We deliberately do NOT call startGenerateAllFrames (which fires a separate bulk backend task)
  // because the sequential useEffect already handles orchestration from the frontend.
  // The backend's /generate endpoint is only used for credit-checking and status bookkeeping.
  const handleGenerateAll = async () => {
    if (!projectId || generatingAll) return;
    setError(null);
    try {
      // Call backend to deduct credits and set project status to 'generating'
      const res = await apiService.startGenerateAllFrames(projectId);
      if (res.pending_count === 0) {
        return;  // nothing to do — button stays enabled, which is correct
      }
      // Enable the sequential driver — it will pick up liveFrames and start Frame 1
      setGeneratingAll(true);
      await fetchProject();
    } catch (e) {
      // Show a user-friendly message for 402 insufficient credits
      const msg = e.message || 'Failed to start bulk generation';
      setError(msg.toLowerCase().includes('insufficient') 
        ? 'Not enough credits. Please purchase credits to generate video.' 
        : msg);
      setGeneratingAll(false);  // Ensure button re-enables on any failure
    }
  };

  const handleGenerateFrame = async (frameId) => {
    if (!projectId) return;
    setGeneratingFrameId(frameId);
    setError(null);
    try {
      await apiService.startGenerateFrame(projectId, frameId);
      await fetchProject();
    } catch (e) {
      setError(e.message || 'Failed to generate specific frame');
      setGeneratingFrameId(null);
    }
  };

  const handleCompileVideo = async () => {
    if (!projectId) return;
    setCombining(true);
    setError(null);
    try {
      const res = await apiService.combineVideoProject(projectId);
      if (res.video_url) {
        setFinalVideoUrl(res.video_url);
        // Clear persisted state — this project is complete, next story starts fresh
        sessionStorage.removeItem('yt_frame_project_id');
        sessionStorage.removeItem('yt_generating_all');
        navigate('/final-video', { 
          state: { 
            videoUrl: res.video_url, 
            projectTitle: project?.project_name || 'Generated Video',
            projectId: projectId
          } 
        });
        return; // Navigation handled — combining stays true until unmount
      }
      // Backend returned success but no video_url — show error
      setError('Video was processed but no URL was returned. Temp files may have been cleared on restart. Please retry.');
    } catch (e) {
      setError(e.message || 'Failed to promote final video');
    } finally {
      // Always reset the spinner — prevents infinite lock if video_url is missing
      setCombining(false);
    }
  };

  if (!storyResultRaw && !projectId && !project) {
    return (
      <div style={{ background: '#0c0e17', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f0f0fd' }}>
        <p>No story context available. Please return to the Dashboard.</p>
        <button onClick={() => navigate('/dashboard')} style={{ padding: '8px 16px', background: '#00E5FF', color: '#0c0e17', border: 'none', borderRadius: '4px', marginLeft: '16px', cursor: 'pointer', fontWeight: 'bold' }}>Dashboard</button>
      </div>
    );
  }

  return (
    <div style={{ background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd', fontFamily: "'Inter', sans-serif" }}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } } 
        .animate-spin { animation: spin 1s linear infinite; }
        .glass-panel { background: rgba(34, 37, 50, 0.6); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }
        .prompt-overlay { opacity: 0; transition: opacity 0.3s ease; }
        .prompt-overlay.show { opacity: 1; pointer-events: auto; }
      `}</style>
      
      {/* Top Navigation Anchor */}
      <header className="sticky top-0 z-50 w-full bg-[#11131d] px-4 py-3 md:px-8 md:py-4 flex justify-between items-center border-b border-[#737580]/10">
        <div className="text-[20px] md:text-[24px]" style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 900, color: '#00E5FF', letterSpacing: '-0.05em' }}>
          YOUTOMIZE
        </div>
        <button className="px-3 py-1.5 md:px-4 md:py-1.5" onClick={() => navigate('/dashboard')} style={{ background: 'rgba(255,255,255,0.05)', color: '#aaaab7', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Icon name="arrow_back" style={{ fontSize: '14px' }} /> <span className="hidden sm:inline">Dashboard</span>
        </button>
      </header>

      <main className="px-4 py-8 md:px-6 md:py-12 max-w-[1280px] mx-auto w-full">
        
        {error && (
          <div style={{ padding: '16px', background: 'rgba(255,113,108,0.1)', border: '1px solid rgba(255,113,108,0.2)', color: '#ff716c', borderRadius: '8px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="error" /> {error}
          </div>
        )}

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', margin: '100px 0', color: '#81ecff' }}>
            <Icon name="progress_activity" className="animate-spin" style={{ fontSize: '48px', marginBottom: '16px' }} />
            <h2 className="text-center px-4" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>Initializing Project & Loading Layout...</h2>
          </div>
        ) : (
          <>
            {/* Generated Full Story Section */}
            <section style={{ marginBottom: '48px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
                <Icon name="auto_awesome" style={{ color: '#00E5FF' }} />
                <h2 className="text-[20px] md:text-[24px]" style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, margin: 0 }}>Generated Full Story</h2>
              </div>
              <div className="glass-panel relative overflow-hidden rounded-xl border border-[#737580]/10 p-5 md:p-8">
                <div style={{ position: 'absolute', top: '-100px', right: '-100px', width: '256px', height: '256px', background: 'rgba(0,229,255,0.05)', filter: 'blur(100px)', pointerEvents: 'none' }}></div>
                
                <div style={{ color: '#aaaab7', lineHeight: 1.8, fontSize: '18px', fontWeight: 300, fontStyle: 'italic', display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {rawStory?.full_story ? (
                    <p>{rawStory.full_story}</p>
                  ) : rawStory?.content ? (
                    rawStory.content.split('\n').map((para, i) => para.trim() ? <p key={i}>{para}</p> : null)
                  ) : (
                    <p>{rawStory?.topic || rawStory?.title || 'Story script...'}</p>
                  )}
                </div>
              </div>
            </section>

            {/* Frame Storyboard Grid */}
            <section style={{ marginBottom: '64px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="dashboard_customize" style={{ color: '#00E5FF' }} />
                  <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '24px', fontWeight: 700, margin: 0 }}>Frame Storyboard</h2>
                </div>
                <div style={{ fontSize: '14px', fontFamily: "'Manrope', sans-serif", color: '#737580', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700 }}>
                  {liveFrames.length} Total Frames
                </div>
              </div>

              {/* Master Generate Button */}
              {!allCompleted && (
                <div style={{ display: 'flex', justifyContent: 'center', margin: '32px 0 48px 0' }}>
                  <button
                    onClick={handleGenerateAll}
                    disabled={generatingAll || isGeneratingFull}
                    style={{
                      background: 'linear-gradient(45deg, #00E5FF, #a68cff)', padding: '16px 48px', borderRadius: '12px', border: 'none',
                      color: '#005762', fontFamily: "'Space Grotesk', sans-serif", fontSize: '16px', fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '0.1em', cursor: (generatingAll || isGeneratingFull) ? 'not-allowed' : 'pointer', transition: 'all 0.3s',
                      boxShadow: '0 0 40px rgba(0,229,255,0.2)', display: 'flex', alignItems: 'center', gap: '12px', opacity: (generatingAll || isGeneratingFull) ? 0.7 : 1
                    }}
                  >
                    {(generatingAll || isGeneratingFull) ? <Icon name="progress_activity" className="animate-spin" /> : <Icon name="movie" />}
                    {(generatingAll || isGeneratingFull) ? 'Generating Scene Flow...' : 'Generate All Frames'}
                  </button>
                </div>
              )}

              {/* Grid Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 md:gap-8">
                {liveFrames.map((frame) => {
                  const isThisGenerating = generatingFrameId === frame.id || frame.status === 'generating';
                  const isFailed = frame.status === 'failed';
                  const isCompleted = frame.status === 'completed';
                  
                  // Sequence-lock helpers (Veo: each frame depends on the previous)
                  const frameIndex = liveFrames.findIndex((f) => f.id === frame.id);
                  const prevFrame = frameIndex > 0 ? liveFrames[frameIndex - 1] : null;
                  const nextFrame = frameIndex < liveFrames.length - 1 ? liveFrames[frameIndex + 1] : null;
                  
                  // GENERATE is unlocked only if all previous frames are SUCCESS
                  const prevReady = !prevFrame || prevFrame.status === 'completed';
                  const canGenerate = !isCompleted && !isThisGenerating && prevReady;
                  // REGENERATE is unlocked only if this frame is SUCCESS AND next frame is PENDING/FAILED
                  const nextIsPending = !nextFrame || nextFrame.status === 'pending' || nextFrame.status === 'failed';
                  const canRegenerate = isCompleted && nextIsPending;
                  
                  const asset = liveAssets.find((a) => a.id === frame.asset_id);
                  const clipUrl = asset?.file_url;

                  // Status badge colour / label
                  const statusColor = isCompleted ? '#00E5FF' : isFailed ? '#ff3b3b' : isThisGenerating ? '#4dabf7' : '#aaaab7';
                  const statusLabel = isCompleted ? 'Done' : isFailed ? 'Failed' : isThisGenerating ? 'Generating...' : 'Pending';

                  return (
                    <div key={frame.id} className="flex flex-col overflow-hidden transition-all duration-300 rounded-xl bg-[#1c1f2b] border border-[#737580]/10" style={{
                      boxShadow: isThisGenerating ? '0 0 20px rgba(0,229,255,0.1)' : 'none',
                      borderColor: isThisGenerating ? 'rgba(0,229,255,0.3)' : 'rgba(115,117,128,0.1)'
                    }}>
                      <div className="p-4 sm:p-5 flex justify-between items-center bg-[#11131d]/50 border-b border-white/5">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '12px', fontWeight: 900, fontFamily: "'Space Grotesk', sans-serif", color: '#00E5FF', padding: '4px 8px', background: 'rgba(0,229,255,0.1)', borderRadius: '4px' }}>FRAME {frame.frame_num}</span>
                          <span style={{ color: '#f0f0fd', fontWeight: 500, fontSize: '14px' }}>{frame.duration_seconds}s Clip</span>
                          <span style={{
                            fontSize: '12px', fontWeight: 600, color: statusColor, textTransform: 'uppercase',
                            padding: '2px 6px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px'
                          }}>
                            {statusLabel}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <button 
                            title="Edit Prompt"
                            onClick={() => {
                              setEditingPromptId(frame.id);
                              setEditedPromptValue(frame.ai_video_prompt);
                            }}
                            disabled={isThisGenerating}
                            style={{ background: 'transparent', border: 'none', color: '#737580', cursor: isThisGenerating ? 'not-allowed' : 'pointer', transition: 'color 0.3s', padding: '4px', opacity: isThisGenerating ? 0.3 : 1 }}
                            onMouseEnter={(e) => !isThisGenerating && (e.currentTarget.style.color = '#00E5FF')}
                            onMouseLeave={(e) => !isThisGenerating && (e.currentTarget.style.color = '#737580')}>
                            <Icon name="edit" style={{ fontSize: '18px' }} />
                          </button>
                          <button 
                            title="Copy Prompt"
                            onClick={() => navigator.clipboard.writeText(frame.ai_video_prompt)}
                            style={{ background: 'transparent', border: 'none', color: '#737580', cursor: 'pointer', transition: 'color 0.3s', padding: '4px' }}
                            onMouseEnter={(e) => e.currentTarget.style.color = '#00E5FF'}
                            onMouseLeave={(e) => e.currentTarget.style.color = '#737580'}>
                            <Icon name="content_copy" style={{ fontSize: '18px' }} />
                          </button>
                        </div>
                      </div>

                      <div className="p-4 sm:p-6 flex-grow flex flex-col">
                        {editingPromptId === frame.id ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                            <textarea 
                              value={editedPromptValue} 
                              onChange={(e) => setEditedPromptValue(e.target.value)} 
                              disabled={savingPromptId === frame.id}
                              style={{ width: '100%', minHeight: '120px', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid #00E5FF', borderRadius: '4px', padding: '12px', fontSize: '14px', lineHeight: 1.6, resize: 'vertical' }} 
                            />
                            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                              <button onClick={() => setEditingPromptId(null)} disabled={savingPromptId === frame.id} style={{ background: 'transparent', color: '#aaaab7', border: 'none', cursor: 'pointer', fontSize: '14px', fontWeight: 600 }}>Cancel</button>
                              <button onClick={async () => {
                                  try {
                                    setSavingPromptId(frame.id);
                                    await apiService.updateFramePrompt(projectId, frame.id, editedPromptValue);
                                    const projData = await apiService.getVideoProject(projectId);
                                    setProject(projData.project);
                                    setEditingPromptId(null);
                                  } catch (err) {
                                    console.error('Failed to save prompt', err);
                                  } finally {
                                    setSavingPromptId(null);
                                  }
                              }} disabled={savingPromptId === frame.id} style={{ background: '#00E5FF', color: '#000', border: 'none', borderRadius: '4px', padding: '6px 16px', fontWeight: 700, cursor: 'pointer', fontSize: '14px' }}>
                                {savingPromptId === frame.id ? 'Saving...' : 'Save'}
                              </button>
                            </div>
                          </div>
                        ) : (
                          <p style={{ color: '#aaaab7', fontSize: '14px', lineHeight: 1.6, marginBottom: '24px', minHeight: '66px' }}>
                            {frame.ai_video_prompt}
                          </p>
                        )}

                        <div 
                          className="relative"
                          style={{
                               aspectRatio: '16/9', borderRadius: '8px', overflow: 'hidden', marginBottom: '24px', position: 'relative',
                               background: '#000', border: isCompleted ? '1px solid rgba(0,229,255,0.2)' : '2px dashed rgba(115,117,128,0.3)',
                               display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
                          }}
                        >
                        {isCompleted && clipUrl ? (
                            <video
                              src={clipUrl}
                              autoPlay loop muted playsInline
                              style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.8 }}
                              title={`Merged video up to frame ${frame.frame_num}`}
                            />
                          ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', color: '#737580' }}>
                              <Icon name={isThisGenerating ? 'movie_edit' : 'video_call'} style={{ fontSize: '40px' }} />
                              <span style={{ fontSize: '10px', fontFamily: "'Manrope', sans-serif", uppercase: true, fontWeight: 700, letterSpacing: '0.1em' }}>
                                {isThisGenerating ? 'Rendering Engine Active' : 'No Video Generated'}
                              </span>
                            </div>
                          )}

                          
                          {/* Progress Badge */}
                          {isThisGenerating && (
                            <div style={{ position: 'absolute', bottom: '12px', left: '12px', padding: '4px 12px', background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', borderRadius: '4px', border: '1px solid rgba(0,229,255,0.2)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                               <span className="pulse-dot" style={{ width: '6px', height: '6px', background: '#00E5FF', borderRadius: '50%', boxShadow: '0 0 10px #00E5FF', animation: 'pulse 1s infinite' }}></span>
                               <span style={{ fontSize: '10px', color: '#00E5FF', fontFamily: "'Manrope', sans-serif", fontWeight: 700, textTransform: 'uppercase' }}>Generating</span>
                            </div>
                          )}
                        </div>

                        {isFailed && <p style={{ color: '#ff716c', fontSize: '12px', marginBottom: '16px' }}>Error: {frame.error_message}</p>}

                        <button
                          onClick={() => handleGenerateFrame(frame.id)}
                          disabled={isThisGenerating || generatingAll || isGeneratingFull || (isCompleted ? !canRegenerate : !canGenerate)}
                          style={{
                            width: '100%', padding: '16px', borderRadius: '8px', border: 'none',
                            background: isCompleted
                              ? (canRegenerate ? 'rgba(255,255,255,0.07)' : 'rgba(255,255,255,0.03)')
                              : (isThisGenerating ? '#1c1f2b' : canGenerate ? 'linear-gradient(45deg, #00E5FF, #a68cff)' : 'rgba(255,255,255,0.03)'),
                            color: isCompleted ? '#aaaab7' : (isThisGenerating ? '#00E5FF' : canGenerate ? '#005762' : '#4a4a5a'),
                            fontFamily: "'Space Grotesk', sans-serif", fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em',
                            cursor: (isThisGenerating || generatingAll || isGeneratingFull || (isCompleted ? !canRegenerate : !canGenerate)) ? 'not-allowed' : 'pointer',
                            transition: 'all 0.3s',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                            borderStyle: 'solid', borderWidth: '1px',
                            borderColor: isCompleted ? 'rgba(255,255,255,0.1)' : (isThisGenerating ? 'rgba(0,229,255,0.3)' : canGenerate ? 'transparent' : 'rgba(255,255,255,0.05)')
                          }}
                        >
                          <Icon name={isThisGenerating ? 'progress_activity' : (isCompleted ? 'movie_filter' : 'movie')} className={isThisGenerating ? 'animate-spin' : ''} style={{ fontSize: '18px' }} />
                          {isThisGenerating ? 'Generating...' : (isCompleted ? (canRegenerate ? 'Regenerate Video' : 'Locked (Next Frame Active)') : (canGenerate ? 'Generate Video' : 'Waiting for Previous Frame'))}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Final Action Button (Combine) */}
            {allCompleted && !finalVideoUrl && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '64px', marginBottom: '80px', position: 'relative' }}>
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '300px', height: '100px', background: 'rgba(0,229,255,0.1)', filter: 'blur(60px)', pointerEvents: 'none' }}></div>
                
                <button
                  onClick={handleCompileVideo}
                  disabled={combining}
                  style={{
                    width: '100%', maxWidth: '900px', padding: '24px', borderRadius: '16px', border: 'none',
                    background: 'linear-gradient(90deg, #00E5FF, #a68cff, #00E5FF)', backgroundSize: '200% auto',
                    color: '#003840', fontFamily: "'Space Grotesk', sans-serif", fontSize: '20px', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.2em',
                    cursor: combining ? 'not-allowed' : 'pointer', transition: 'all 0.3s', boxShadow: '0 0 50px rgba(0,229,255,0.3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', opacity: combining ? 0.8 : 1
                  }}
                >
                  {combining ? <Icon name="progress_activity" className="animate-spin" style={{ fontSize: '28px' }} /> : <Icon name="auto_videocam" style={{ fontSize: '28px' }} />}
                  {combining ? 'Uploading Final Video...' : 'Preview Final Video'}
                </button>
              </div>
            )}

            {/* View Final Video Button (Already Combined) */}
            {allCompleted && finalVideoUrl && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '64px', marginBottom: '80px', position: 'relative' }}>
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '300px', height: '100px', background: 'rgba(0,255,136,0.1)', filter: 'blur(60px)', pointerEvents: 'none' }}></div>
                
                <button
                  onClick={() => navigate('/final-video', { 
                    state: { 
                      videoUrl: finalVideoUrl, 
                      projectTitle: project?.project_name || 'Generated Video',
                      projectId: projectId
                    } 
                  })}
                  style={{
                    width: '100%', maxWidth: '900px', padding: '24px', borderRadius: '16px', border: 'none',
                    background: 'linear-gradient(90deg, #00ff88, #00E5FF)',
                    color: '#003840', fontFamily: "'Space Grotesk', sans-serif", fontSize: '20px', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.2em',
                    cursor: 'pointer', transition: 'all 0.3s', boxShadow: '0 0 50px rgba(0,255,136,0.3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px'
                  }}
                >
                  <Icon name="play_circle" style={{ fontSize: '28px' }} />
                  View Final Video
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* FULL SCREEN COMPILE BLOCKER */}
      {combining && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          background: 'rgba(5, 7, 12, 0.9)', backdropFilter: 'blur(12px)',
          zIndex: 9999, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            width: '120px', height: '120px', borderRadius: '50%', border: '2px solid rgba(0,229,255,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '32px',
            boxShadow: '0 0 50px rgba(0,229,255,0.1)', position: 'relative'
          }}>
             <div className="absolute inset-0 border-t-2 border-primary rounded-full animate-spin" style={{ borderTopColor: '#00E5FF' }}></div>
             <Icon name="movie" style={{ fontSize: '40px', color: '#00E5FF' }} />
          </div>
          
          <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '28px', fontWeight: 900, color: '#f0f0fd', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 16px 0' }}>
            Uploading Final Video
          </h2>
          <p style={{ color: '#aaaab7', fontFamily: "'Inter', sans-serif", fontSize: '16px', maxWidth: '400px', textAlign: 'center', lineHeight: 1.6 }}>
            Uploading your Veo-generated video to permanent storage. No stitching needed — this is your complete video.
          </p>
        </div>
      )}
    </div>
  );
};

export default FrameResults;
