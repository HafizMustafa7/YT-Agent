import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/apiService';
import '../styles/components/VideoGenerationScreen.css';

const POLL_INTERVAL_MS = 6000;

const VideoGenerationScreen = ({ projectId, onBack }) => {
  const [project, setProject] = useState(null);
  const [progress, setProgress] = useState(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [generatingFrameId, setGeneratingFrameId] = useState(null);
  const [combining, setCombining] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);

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

  // Auto-poll while generating or combining
  useEffect(() => {
    if (!projectId || !project) return;
    const status = project?.status;
    const isActive = status === 'generating' || status === 'queued';
    if (!isActive && !generatingAll && !combining) return;

    const interval = setInterval(fetchProject, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [projectId, project, fetchProject, generatingAll, combining]);

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
    } catch (e) {
      setError(e.message || 'Failed to generate frame');
    } finally {
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

  const handleCopyUrl = () => {
    if (!finalVideoUrl) return;
    navigator.clipboard.writeText(finalVideoUrl).then(() => {
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2500);
    }).catch(() => {
      setError('Failed to copy URL to clipboard');
    });
  };

  // Determine states
  const frames = project?.frames || [];
  const assets = project?.assets || [];
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
    if (project?.status && project.status !== 'generating' && project.status !== 'queued') {
      setGeneratingAll(false);
    }
    if (hasFinalAsset || finalVideoUrl) {
      setCombining(false);
    }
  }, [project?.status, hasFinalAsset, finalVideoUrl]);

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

      {/* Final video section */}
      {(hasFinalAsset || finalVideoUrl) && (
        <div className="video-gen-final-section">
          <div className="final-section-header">
            <span className="final-badge">🎉 Final Video Ready</span>
            <span className="final-subtitle">Your video has been compiled and uploaded to Cloudflare</span>
          </div>

          {finalVideoUrl && (
            <div className="final-video-content">
              <div className="video-player-wrapper">
                <video
                  controls
                  preload="metadata"
                  className="final-video-player"
                  src={finalVideoUrl}
                >
                  Your browser does not support the video tag.
                </video>
              </div>

              <div className="final-video-url-section">
                <label className="url-label">Video URL (Cloudflare R2):</label>
                <div className="url-copy-row">
                  <input
                    type="text"
                    value={finalVideoUrl}
                    readOnly
                    className="url-input"
                    onClick={(e) => e.target.select()}
                  />
                  <button
                    type="button"
                    className="btn btn-copy-url"
                    onClick={handleCopyUrl}
                  >
                    {copiedUrl ? '✓ Copied!' : '📋 Copy URL'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {!finalVideoUrl && (
            <div className="final-no-url">
              <p>Video is uploaded but the public URL is not available.</p>
              <p className="final-no-url-hint">
                Make sure <code>R2_FINAL_PUBLIC_URL</code> is set in your backend <code>.env</code> file.
              </p>
            </div>
          )}
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
