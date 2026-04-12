import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const Icon = ({ name, filled, className = '', style = {} }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", display: 'inline-block', lineHeight: 1, ...style }}
  >{name}</span>
);

const FinalVideoPage = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const videoUrl = location.state?.videoUrl;
  const projectTitle = location.state?.projectTitle || 'Final_Video_Render.mp4';

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
      <header style={{ background: '#0c0e17', boxShadow: '0 20px 40px rgba(0,0,0,0.3)', position: 'sticky', top: 0, zIndex: 50, padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '24px', fontWeight: 900, color: '#00E5FF', letterSpacing: '-0.05em' }}>
          YOUTOMIZE
        </div>
        <button onClick={() => navigate('/dashboard')} style={{ background: 'transparent', border: 'none', color: '#aaaab7', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color = '#81ecff'} onMouseLeave={e => e.currentTarget.style.color = '#aaaab7'}>
          <span style={{ fontSize: '14px', fontFamily: "'Manrope', sans-serif", fontWeight: 500 }}>Dashboard</span>
          <Icon name="account_circle" />
        </button>
      </header>

      {/* Main Content */}
      <main style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48px 24px', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
        
        <section style={{ width: '100%', position: 'relative' }}>
          {/* Header Label */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontFamily: "'Manrope', sans-serif", color: '#00E5FF', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '4px' }}>Final Rendering Complete</span>
              <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '28px', fontWeight: 700, margin: 0 }}>{projectTitle}</h1>
            </div>
            <div style={{ background: '#1c1f2b', padding: '8px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
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
          <div style={{ display: 'flex', gap: '16px', width: '100%' }}>
            
            <button 
              onClick={() => {
                const a = document.createElement('a');
                a.href = videoUrl;
                a.download = 'youtube-short.mp4';
                a.click();
              }}
              style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
                background: 'linear-gradient(45deg, #00E5FF, #a68cff)', padding: '20px 32px', borderRadius: '8px',
                color: '#005762', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em',
                boxShadow: '0 0 25px rgba(129, 236, 255, 0.4)', border: 'none', cursor: 'pointer', transition: 'all 0.3s'
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = 0.9}
              onMouseLeave={e => e.currentTarget.style.opacity = 1}
            >
              <Icon name="download" filled style={{ fontSize: '24px' }} />
              Download Video
            </button>
            
            <button 
              style={{
                flex: "0 0 33%", display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
                background: 'transparent', border: '1px solid rgba(70,71,82,0.3)', padding: '20px', borderRadius: '8px',
                color: '#81ecff', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em',
                cursor: 'pointer', transition: 'all 0.3s'
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,229,255,0.05)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <Icon name="upload_file" style={{ fontSize: '24px' }} />
              To Youtube
            </button>
          </div>
          
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
