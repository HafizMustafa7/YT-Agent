import React, { useState, useEffect, useCallback, useMemo } from 'react';
import apiService from '../services/apiService';
import '../styles/components/VideoGenerationScreen.css';

const POLL_BASE_MS = 4000;      // Start polling every 4s
const POLL_MAX_MS = 15000;      // Slow down to 15s max

const VideoGenerationScreen = ({ projectId, onBack, onViewFinalVideo }) => {
  const [project, setProject] = useState(null);
  const [progress, setProgress] = useState(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [generatingFrameId, setGeneratingFrameId] = useState(null);
  const [combining, setCombining] = useState(false);
  const pollCountRef = React.useRef(0);

  // Adaptive poll interval: starts fast, slows over time
  const getPollInterval = () => {
    const count = pollCountRef.current;
    if (count < 10) return POLL_BASE_MS;           // First ~40s: 4s
    if (count < 30) return 8000;                    // Next ~2.5 min: 8s
    if (count < 60) return 12000;                   // Next ~6 min: 12s
    return POLL_MAX_MS;                             // After that: 15s
  };

  const fetchProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const res = await apiService.getVideoProject(projectId);
      setProject(res.project);
      setProgress(res.progress || null);
      setFinalVideoUrl(res.final_video_url || null);
      setError(null);
    } catch (e) {
      setError(e.message || 'Failed to fetch project');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  // Auto-poll while generating or combining — adaptive interval
  useEffect(() => {
    if (!projectId || !project) return;
    const status = project?.status;
    const isActive = status === 'generating' || status === 'queued' || status === 'clips_ready';
    // Also poll if ANY frame is still generating (handles single-frame retries)
    const hasActiveFrames = (project?.frames || []).some((f) => f.status === 'generating');
    if (!isActive && !hasActiveFrames && !generatingAll && !generatingFrameId && !combining) {
      pollCountRef.current = 0;  // Reset when idle
      return;
    }

    const tick = () => {
      pollCountRef.current += 1;
      fetchProject();
    };

    // Use recursive setTimeout so each tick recalculates the delay
    let timeoutId = setTimeout(function poll() {
      tick();
      timeoutId = setTimeout(poll, getPollInterval());
    }, getPollInterval());

    return () => clearTimeout(timeoutId);
  }, [projectId, project, fetchProject, generatingAll, generatingFrameId, combining]);

  const handleGenerateAll = async () => {
    setGeneratingAll(true);
    setError(null);
    try {
      const res = await apiService.startGenerateAllFrames(projectId);
      if (res.pending_count === 0) {
        setError('No pending frames to generate.');
        setGeneratingAll(false);
        return;
      }
      await fetchProject();
    } catch (e) {
      setError(e.message || 'Failed to start generation');
      setGeneratingAll(false);
    }
  };

  const handleGenerateFrame = async (frameId) => {
    setGeneratingFrameId(frameId);
    setError(null);
    try {
      await apiService.startGenerateFrame(projectId, frameId);
      await fetchProject();
      // Don't reset generatingFrameId here — let polling continue
      // It will be cleared by the useEffect below when frame status changes
    } catch (e) {
      setError(e.message || 'Failed to generate frame');
      setGeneratingFrameId(null);
    }
  };

  const handleCombine = async () => {
    setCombining(true);
    setError(null);
    try {
      const res = await apiService.combineVideoProject(projectId);
      if (res.video_url) {
        setFinalVideoUrl(res.video_url);
      }
      if (res.already_combined && res.video_url) {
        setFinalVideoUrl(res.video_url);
      }
      await fetchProject();
    } catch (e) {
      setError(e.message || 'Failed to combine clips');
    } finally {
      setCombining(false);
    }
  };

  // Determine states
  const frames = useMemo(() => project?.frames || [], [project?.frames]);
  const assets = useMemo(() => project?.assets || [], [project?.assets]);
  const completedCount = frames.filter((f) => f.status === 'completed').length;
  const generatingCount = frames.filter((f) => f.status === 'generating').length;
  const failedCount = frames.filter((f) => f.status === 'failed').length;
  const allCompleted = frames.length > 0 && completedCount === frames.length;
  const hasFinalAsset = (project?.assets || []).some(
    (a) => a.file_path && a.file_path.startsWith('final/')
  );
  const isGenerating = project?.status === 'generating' || generatingCount > 0;
  const progressPercent = progress?.percent ?? (frames.length > 0 ? Math.round((completedCount / frames.length) * 100) : 0);

  // Reset generatingAll flag when project status changes from generating
  useEffect(() => {
    if (project?.status && project.status !== 'generating' && project.status !== 'queued' && project.status !== 'clips_ready') {
      setGeneratingAll(false);
    }
    if (hasFinalAsset || finalVideoUrl) {
      setCombining(false);
    }
    // Clear generatingFrameId when the frame is no longer generating
    if (generatingFrameId) {
      const targetFrame = frames.find((f) => f.id === generatingFrameId);
      if (targetFrame && targetFrame.status !== 'generating') {
        setGeneratingFrameId(null);
      }
    }
  }, [project?.status, hasFinalAsset, finalVideoUrl, generatingFrameId, frames]);

  // Auto-navigate to final video screen when combine completes
  useEffect(() => {
    if ((hasFinalAsset || finalVideoUrl) && onViewFinalVideo) {
      onViewFinalVideo();
    }
  }, [hasFinalAsset, finalVideoUrl, onViewFinalVideo]);

  // Loading state
  if (loading && !project) {
    return (
      <div className="video-gen-screen">
        <div className="video-gen-header">
          <button type="button" className="back-btn" onClick={onBack}>← Back</button>
          <h2>Video Generation Dashboard</h2>
        </div>
        <div className="video-gen-loading">
          <div className="loading-spinner"></div>
          <p>Loading project…</p>
        </div>
      </div>
    );
  }

  // Error only state
  if (error && !project) {
    return (
      <div className="video-gen-screen">
        <div className="video-gen-header">
          <button type="button" className="back-btn" onClick={onBack}>← Back</button>
          <h2>Video Generation Dashboard</h2>
        </div>
        <div className="video-gen-error-container">
          <span className="error-icon">⚠️</span>
          <p className="video-gen-error">{error}</p>
          <button type="button" className="btn btn-retry" onClick={fetchProject}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="video-gen-screen">
      {/* Header */}
      <div className="video-gen-header">
        <button type="button" className="back-btn" onClick={onBack}>← Back</button>
        <h2>Video Generation Dashboard</h2>
        <p className="video-gen-subtitle">
          {project?.project_name || 'Video Project'} · {completedCount}/{frames.length} clips ready
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="video-gen-error-banner" role="alert">
          <span className="error-icon-sm">⚠️</span>
          <span>{error}</span>
          <button type="button" className="error-dismiss" onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Progress bar */}
      {frames.length > 0 && (
        <div className="video-gen-progress-section">
          <div className="progress-bar-container">
            <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }}>
              {progressPercent > 10 && <span className="progress-text">{progressPercent}%</span>}
            </div>
          </div>
          <div className="progress-stats">
            <span className="stat-item stat-completed">✓ {completedCount} completed</span>
            {generatingCount > 0 && <span className="stat-item stat-generating">⟳ {generatingCount} generating</span>}
            {failedCount > 0 && <span className="stat-item stat-failed">✗ {failedCount} failed</span>}
            <span className="stat-item stat-total">{frames.length} total</span>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="video-gen-actions-bar">
        <button
          type="button"
          className="btn btn-generate-all"
          onClick={handleGenerateAll}
          disabled={generatingAll || isGenerating || completedCount === frames.length}
        >
          {generatingAll || isGenerating ? (
            <><span className="btn-spinner"></span> Generating…</>
          ) : completedCount === frames.length ? (
            '✓ All clips generated'
          ) : (
            '🎬 Generate all videos'
          )}
        </button>

        {allCompleted && !hasFinalAsset && !finalVideoUrl && (
          <button
            type="button"
            className="btn btn-combine"
            onClick={handleCombine}
            disabled={combining}
          >
            {combining ? (
              <><span className="btn-spinner"></span> Compiling…</>
            ) : (
              '🎞️ Compile final video'
            )}
          </button>
        )}
      </div>

      {/* Final video ready — navigate to dedicated screen */}
      {(hasFinalAsset || finalVideoUrl) && (
        <div className="video-gen-final-section">
          <div className="final-section-header">
            <span className="final-badge">🎉 Final Video Ready</span>
            <span className="final-subtitle">Your video has been compiled and uploaded successfully</span>
          </div>
          <button
            type="button"
            className="btn btn-view-final"
            onClick={onViewFinalVideo}
          >
            ▶ View Final Video
          </button>
        </div>
      )}

      {/* Frame list */}
      <div className="video-gen-frames">
        <h3>Frames</h3>
        {frames.length === 0 ? (
          <p className="video-gen-empty">No frames in this project.</p>
        ) : (
          <ul className="frame-list">
            {frames.map((frame) => (
              <li key={frame.id} className={`frame-item frame-status-${frame.status}`}>
                <div className="frame-info">
                  <div className="frame-info-top">
                    <span className="frame-num">Frame {frame.frame_num}</span>
                    <span className={`frame-status-badge badge-${frame.status}`}>
                      {frame.status === 'completed' && '✓ '}
                      {frame.status === 'generating' && '⟳ '}
                      {frame.status === 'failed' && '✗ '}
                      {frame.status}
                    </span>
                    <span className="frame-duration">{frame.duration_seconds}s</span>
                  </div>
                  {frame.scene_description && (
                    <p className="frame-scene">{frame.scene_description}</p>
                  )}
                  {frame.error_message && frame.status === 'failed' && (
                    <p className="frame-error-msg">Error: {frame.error_message}</p>
                  )}
                  {/* Clip preview for completed frames */}
                  {frame.status === 'completed' && (() => {
                    const asset = assets.find((a) => a.id === frame.asset_id);
                    const clipUrl = asset?.file_url;
                    return clipUrl ? (
                      <div className="frame-clip-preview">
                        <video
                          controls
                          preload="metadata"
                          className="frame-clip-player"
                          src={clipUrl}
                        >
                          Your browser does not support the video tag.
                        </video>
                      </div>
                    ) : null;
                  })()}
                </div>
                <div className="frame-actions">
                  {(frame.status === 'pending' || frame.status === 'failed') && (
                    <button
                      type="button"
                      className="btn btn-generate-one"
                      onClick={() => handleGenerateFrame(frame.id)}
                      disabled={generatingFrameId === frame.id || generatingAll || isGenerating}
                    >
                      {generatingFrameId === frame.id ? (
                        <><span className="btn-spinner-sm"></span> Generating…</>
                      ) : frame.status === 'failed' ? (
                        '🔄 Retry'
                      ) : (
                        '▶ Generate'
                      )}
                    </button>
                  )}
                  {frame.status === 'generating' && (
                    <span className="frame-busy">
                      <span className="pulse-dot"></span> Generating…
                    </span>
                  )}
                  {frame.status === 'completed' && (
                    <span className="frame-done">✓ Done</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default VideoGenerationScreen;
