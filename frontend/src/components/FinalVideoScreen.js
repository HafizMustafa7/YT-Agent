import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/apiService';
import '../styles/components/FinalVideoScreen.css';

const FinalVideoScreen = ({ projectId, onBack, onStartNew }) => {
    const [project, setProject] = useState(null);
    const [finalVideoUrl, setFinalVideoUrl] = useState(null);
    const [loading, setLoading] = useState(true);
    const [copiedUrl, setCopiedUrl] = useState(false);

    const fetchProject = useCallback(async () => {
        if (!projectId) return;
        try {
            const res = await apiService.getVideoProject(projectId);
            setProject(res.project);
            setFinalVideoUrl(res.final_video_url || null);
        } catch (e) {
            console.error('Failed to fetch project:', e);
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        fetchProject();
    }, [fetchProject]);

    const handleCopyUrl = () => {
        if (!finalVideoUrl) return;
        navigator.clipboard.writeText(finalVideoUrl).then(() => {
            setCopiedUrl(true);
            setTimeout(() => setCopiedUrl(false), 2500);
        }).catch(() => {
            // Fallback: select the input text for manual copy
            const input = document.querySelector('.fvs-url-input');
            if (input) {
                input.select();
                alert('Press Ctrl+C to copy the URL');
            }
        });
    };

    const handleDownload = () => {
        if (!finalVideoUrl) return;
        const link = document.createElement('a');
        link.href = finalVideoUrl;
        link.download = `${project?.project_name || 'video'}_final.mp4`;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Compute stats
    const frames = project?.frames || [];
    const totalFrames = frames.length;
    const totalDuration = frames.reduce((sum, f) => sum + (f.duration_seconds || 0), 0);
    const finalAsset = (project?.assets || []).find(
        (a) => a.file_path && a.file_path.startsWith('final/')
    );
    const fileSizeMB = finalAsset?.file_size
        ? (finalAsset.file_size / (1024 * 1024)).toFixed(1)
        : null;

    if (loading) {
        return (
            <div className="final-video-screen">
                <div className="fvs-header">
                    <span className="fvs-success-icon">🎬</span>
                    <h2>Loading your video…</h2>
                </div>
            </div>
        );
    }

    return (
        <div className="final-video-screen">
            {/* Header */}
            <div className="fvs-header">
                <span className="fvs-success-icon">🎉</span>
                <h2>Your Video is Ready!</h2>
                <p className="fvs-subtitle">
                    <span className="fvs-project-name">{project?.project_name || 'Video Project'}</span>
                    {' '} has been compiled and uploaded successfully
                </p>
            </div>

            {/* Video Player Card */}
            {finalVideoUrl && (
                <div className="fvs-player-card">
                    <div className="fvs-video-wrapper">
                        <video
                            controls
                            autoPlay={false}
                            preload="metadata"
                            className="fvs-video-player"
                            src={finalVideoUrl}
                            poster=""
                        >
                            Your browser does not support the video tag.
                        </video>
                        <div className="fvs-video-overlay" />
                    </div>

                    <div className="fvs-stats-row">
                        <div className="fvs-stat-chip">
                            <span className="fvs-stat-icon">🎞️</span>
                            <span className="fvs-stat-value">{totalFrames}</span> clips
                        </div>
                        <div className="fvs-stat-chip">
                            <span className="fvs-stat-icon">⏱️</span>
                            <span className="fvs-stat-value">{totalDuration}s</span> duration
                        </div>
                        {fileSizeMB && (
                            <div className="fvs-stat-chip">
                                <span className="fvs-stat-icon">💾</span>
                                <span className="fvs-stat-value">{fileSizeMB} MB</span>
                            </div>
                        )}
                        <div className="fvs-stat-chip">
                            <span className="fvs-stat-icon">☁️</span>
                            Cloudflare R2
                        </div>
                    </div>
                </div>
            )}

            {/* URL Section */}
            {finalVideoUrl ? (
                <div className="fvs-url-card">
                    <div className="fvs-url-label">
                        <span>🔗</span> Video URL
                    </div>
                    <div className="fvs-url-row">
                        <input
                            type="text"
                            value={finalVideoUrl}
                            readOnly
                            className="fvs-url-input"
                            onClick={(e) => e.target.select()}
                        />
                        <button
                            type="button"
                            className={`fvs-copy-btn ${copiedUrl ? 'copied' : ''}`}
                            onClick={handleCopyUrl}
                        >
                            {copiedUrl ? '✓ Copied!' : '📋 Copy URL'}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="fvs-no-url">
                    <p>Video compiled but public URL is not available.</p>
                    <p>
                        Set <code>R2_FINAL_PUBLIC_URL</code> in your backend <code>.env</code> file.
                    </p>
                </div>
            )}

            {/* Action Buttons */}
            <div className="fvs-actions">
                {finalVideoUrl && (
                    <button type="button" className="fvs-btn fvs-btn-primary" onClick={handleDownload}>
                        ⬇️ Download Video
                    </button>
                )}
                <button type="button" className="fvs-btn fvs-btn-secondary" onClick={onBack}>
                    ← Back to Generation
                </button>
                <button type="button" className="fvs-btn fvs-btn-success" onClick={onStartNew}>
                    🎬 Create New Video
                </button>
            </div>
        </div>
    );
};

export default FinalVideoScreen;
