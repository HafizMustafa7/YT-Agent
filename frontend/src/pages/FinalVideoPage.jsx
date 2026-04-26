import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import apiService from '../features/yt-agent/services/apiService';

const Icon = ({ name, filled, className = '', style = {} }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", display: 'inline-block', lineHeight: 1, ...style }}
  >{name}</span>
);

const FinalVideoPage = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // null, 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');

  const videoUrl = location.state?.videoUrl;
  const projectTitle = location.state?.projectTitle || 'Final_Video_Render.mp4';
  const projectId = location.state?.projectId;

  const [videoTitle, setVideoTitle] = useState(projectTitle);
  const [isEditingTitle, setIsEditingTitle] = useState(false);

  if (!videoUrl) {
    return (
      <div style={{ background: '#0c0e17', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#f0f0fd' }}>
        <p style={{ marginBottom: '24px', fontFamily: "'Space Grotesk', sans-serif", fontSize: '20px' }}>No video URL provided.</p>
        <button 
          onClick={() => navigate('/dashboard')} 
          style={{ padding: '12px 24px', background: '#00E5FF', color: '#0c0e17', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div style={{ background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd', fontFamily: "'Inter', sans-serif", display: 'flex', flexDirection: 'column' }}>
      
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 w-full bg-[#0c0e17] shadow-[0_20px_40px_rgba(0,0,0,0.3)] px-4 py-4 md:px-8 flex justify-between items-center">
        <div className="text-[20px] md:text-[24px]" style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 900, color: '#00E5FF', letterSpacing: '-0.05em' }}>
          YOUTOMIZE
        </div>
        <button onClick={() => navigate('/dashboard')} style={{ background: 'transparent', border: 'none', color: '#aaaab7', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color = '#81ecff'} onMouseLeave={e => e.currentTarget.style.color = '#aaaab7'}>
          <span style={{ fontSize: '14px', fontFamily: "'Manrope', sans-serif", fontWeight: 500 }}>Dashboard</span>
          <Icon name="account_circle" />
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-grow flex flex-col items-center px-4 py-8 md:px-6 md:py-12 max-w-[1280px] mx-auto w-full">
        
        <section style={{ width: '100%', position: 'relative' }}>
          {/* Header Label */}
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
            <div style={{ display: 'flex', flexDirection: 'column', flexGrow: 1, marginRight: '24px' }}>
              <span style={{ fontFamily: "'Manrope', sans-serif", color: '#00E5FF', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '4px' }}>Final Rendering Complete</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {isEditingTitle ? (
                  <input
                    type="text"
                    value={videoTitle}
                    onChange={(e) => setVideoTitle(e.target.value)}
                    onBlur={() => setIsEditingTitle(false)}
                    onKeyDown={(e) => e.key === 'Enter' && setIsEditingTitle(false)}
                    autoFocus
                    style={{
                      fontFamily: "'Space Grotesk', sans-serif", fontSize: '24px', fontWeight: 700, 
                      color: '#f0f0fd', background: 'transparent', border: 'none', borderBottom: '2px solid #00E5FF', 
                      outline: 'none', padding: '4px 0', width: '100%', maxWidth: '600px'
                    }}
                  />
                ) : (
                  <>
                    <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '28px', fontWeight: 700, margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '600px' }}>
                      {videoTitle}
                    </h1>
                    <button 
                      onClick={() => setIsEditingTitle(true)}
                      style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#aaaab7', display: 'flex', alignItems: 'center', padding: '4px' }}
                      onMouseEnter={e => e.currentTarget.style.color = '#00E5FF'}
                      onMouseLeave={e => e.currentTarget.style.color = '#aaaab7'}
                    >
                      <Icon name="edit" style={{ fontSize: '20px' }} />
                    </button>
                  </>
                )}
              </div>
            </div>
            <div className="bg-[#1c1f2b] px-4 py-2 rounded-lg flex items-center gap-3 flex-shrink-0 self-start md:self-auto">
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#81ecff', boxShadow: '0 0 10px #81ecff', animation: 'pulse 2s infinite' }}></span>
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#aaaab7' }}>Ready for Export</span>
            </div>
          </div>

          {/* Video Player Box */}
          <div style={{ width: '100%', aspectRatio: '16/9', borderRadius: '12px', overflow: 'hidden', background: '#000', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)', position: 'relative' }}>
            <video 
              src={videoUrl} 
              controls 
              autoPlay 
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>

          {/* Bento Meta Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', marginTop: '32px' }}>
            <div style={{ background: '#11131d', padding: '24px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#737580' }}>Resolution</span>
              <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '20px', fontWeight: 700, color: '#f0f0fd' }}>1080p HD (Shorts)</span>
            </div>
            <div style={{ background: '#11131d', padding: '24px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#737580' }}>Status</span>
              <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '20px', fontWeight: 700, color: '#f0f0fd' }}>Processed & Ready</span>
            </div>
            <div style={{ background: '#11131d', padding: '24px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#737580' }}>Format</span>
              <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '20px', fontWeight: 700, color: '#f0f0fd' }}>H.264 MP4</span>
            </div>
          </div>
        </section>

        {/* Primary Actions */}
        <section style={{ marginTop: '64px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '32px', width: '100%', maxWidth: '600px' }}>
          <div className="flex flex-col sm:flex-row gap-4 w-full">
            
            <button 
              onClick={() => {
                const a = document.createElement('a');
                a.href = videoUrl;
                a.download = 'youtube-short.mp4';
                a.click();
              }}
              className="flex-1 flex items-center justify-center gap-3 p-5 rounded-lg border-none cursor-pointer transition-all duration-300"
              style={{
                background: 'linear-gradient(45deg, #00E5FF, #a68cff)',
                color: '#005762', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em',
                boxShadow: '0 0 25px rgba(129, 236, 255, 0.4)'
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = 0.9}
              onMouseLeave={e => e.currentTarget.style.opacity = 1}
            >
              <Icon name="download" filled style={{ fontSize: '24px' }} />
              Download Video
            </button>
            
            <button 
              onClick={async () => {
                if (!projectId) {
                  setErrorMessage('Project ID missing. Cannot upload.');
                  setUploadStatus('error');
                  return;
                }
                setIsUploading(true);
                setUploadStatus(null);
                setErrorMessage('');
                try {
                  await apiService.uploadProjectToYoutube(projectId, videoTitle.trim());
                  setUploadStatus('success');
                } catch (err) {
                  setErrorMessage(err.message || 'Failed to start YouTube upload.');
                  setUploadStatus('error');
                } finally {
                  setIsUploading(false);
                }
              }}
              disabled={isUploading || uploadStatus === 'success'}
              className="flex-1 sm:flex-none sm:w-[33%] flex items-center justify-center gap-3 p-5 rounded-lg transition-all duration-300"
              style={{
                background: uploadStatus === 'success' ? 'rgba(0,255,136,0.1)' : 'transparent', 
                border: uploadStatus === 'success' ? '1px solid #00ff88' : '1px solid rgba(70,71,82,0.3)', 
                color: uploadStatus === 'success' ? '#00ff88' : '#81ecff', 
                fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em',
                cursor: (isUploading || uploadStatus === 'success') ? 'not-allowed' : 'pointer',
                opacity: (isUploading) ? 0.6 : 1
              }}
              onMouseEnter={e => { if (!isUploading && uploadStatus !== 'success') e.currentTarget.style.background = 'rgba(0,229,255,0.05)' }}
              onMouseLeave={e => { if (!isUploading && uploadStatus !== 'success') e.currentTarget.style.background = 'transparent' }}
            >
              {isUploading ? (
                <Icon name="progress_activity" className="animate-spin" style={{ fontSize: '24px' }} />
              ) : uploadStatus === 'success' ? (
                <Icon name="check_circle" filled style={{ fontSize: '24px' }} />
              ) : (
                <Icon name="upload_file" style={{ fontSize: '24px' }} />
              )}
              {isUploading ? 'Uploading...' : uploadStatus === 'success' ? 'Upload Started' : 'To Youtube'}
            </button>
          </div>
          
          {uploadStatus === 'error' && (
            <div style={{ background: 'rgba(255,113,108,0.1)', color: '#ff716c', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,113,108,0.3)', width: '100%', fontSize: '12px', textAlign: 'center' }}>
              <Icon name="error" style={{ fontSize: '16px', verticalAlign: 'middle', marginRight: '8px' }} />
              {errorMessage}
            </div>
          )}
          {uploadStatus === 'success' && (
            <div style={{ background: 'rgba(0,255,136,0.1)', color: '#00ff88', padding: '12px', borderRadius: '8px', border: '1px solid rgba(0,255,136,0.3)', width: '100%', fontSize: '12px', textAlign: 'center' }}>
              <Icon name="check_circle" style={{ fontSize: '16px', verticalAlign: 'middle', marginRight: '8px' }} />
              Upload process started in the background. Check your YouTube channel studio shortly!
            </div>
          )}

          {/* Status Note */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#464752' }}>
            <Icon name="lock" style={{ fontSize: '14px' }} />
            <span style={{ fontFamily: "'Manrope', sans-serif", fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Connected via secure local instance
            </span>
          </div>
        </section>
      </main>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
      `}</style>
    </div>
  );
};

export default FinalVideoPage;
