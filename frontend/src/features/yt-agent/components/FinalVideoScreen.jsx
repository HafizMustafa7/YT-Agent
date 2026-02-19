import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/apiService';
import '../styles/components/FinalVideoScreen.css';

const FinalVideoScreen = ({ projectId, onStartNew }) => {
    const [project, setProject] = useState(null);
    const [finalVideoUrl, setFinalVideoUrl] = useState(null);
    const [loading, setLoading] = useState(true);
    const [copiedUrl, setCopiedUrl] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadMessage, setUploadMessage] = useState(null);
    const [uploadError, setUploadError] = useState(null);

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

    const handleUpload = async () => {
        if (!projectId) return;
        setIsUploading(true);
        setUploadMessage(null);
        setUploadError(null);

        try {
            const res = await apiService.uploadProjectToYoutube(projectId);
            if (res.success) {
                setUploadMessage('Upload started! Refreshing to link your video...');
                // Refresh project after a short delay to see if metadata is updated
                setTimeout(() => fetchProject(), 3000);
            }
        } catch (e) {
            console.error('Upload failed:', e);
            setUploadError(e.message || 'Failed to start upload.');
        } finally {
            setIsUploading(false);
        }
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

    const youtubeUrl = project?.metadata?.youtube_url;

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
                    {' '} {youtubeUrl ? 'is live on YouTube!' : 'has been compiled and is ready for upload'}
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
            {finalVideoUrl && (
                <div className="fvs-url-card">
                    <div className="fvs-url-label">
                        <span>🔗</span> Project Video URL (R2)
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
            )}

            {/* YouTube Link Section */}
            {youtubeUrl && (
                <div className="fvs-url-card youtube-link-card">
                    <div className="fvs-url-label">
                        <span>📺</span> YouTube Video Link
                    </div>
                    <div className="fvs-url-row">
                        <input
                            type="text"
                            value={youtubeUrl}
                            readOnly
                            className="fvs-url-input"
                        />
                        <a
                            href={youtubeUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="fvs-view-youtube-btn"
                        >
                            View on YouTube
                        </a>
                    </div>
                </div>
            )}

            {!finalVideoUrl && (
                <div className="fvs-no-url">
                    <p>Video compiled but public URL is not available.</p>
                    <p>
                        Set <code>R2_FINAL_PUBLIC_URL</code> in your backend <code>.env</code> file.
                    </p>
                </div>
            )}

            {/* Upload Status Messages */}
            {uploadMessage && (
                <div className="fvs-upload-status success">
                    <span>✅ {uploadMessage}</span>
                </div>
            )}
            {uploadError && (
                <div className="fvs-upload-status error">
                    <span>⚠️ {uploadError}</span>
                </div>
            )}

            {/* Action Buttons */}
            <div className="fvs-actions">
                {finalVideoUrl && (
                    <button type="button" className="fvs-btn fvs-btn-primary" onClick={handleDownload}>
                        ⬇️ Download Video
                    </button>
                )}
                {finalVideoUrl && !youtubeUrl && (
                    <button
                        type="button"
                        className="fvs-btn fvs-btn-youtube"
                        onClick={handleUpload}
                        disabled={isUploading}
                    >
                        {isUploading ? '⏳ Uploading...' : '📺 Upload to YouTube'}
                    </button>
                )}
                <button type="button" className="fvs-btn fvs-btn-success" onClick={onStartNew}>
                    🎬 Create New Video
                </button>
            </div>
        </div>
    );
};

export default FinalVideoScreen;
