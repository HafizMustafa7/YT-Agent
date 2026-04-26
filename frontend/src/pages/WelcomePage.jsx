import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import dashboardPreview from '../assets/dashboard_preview.jpg';
import analysisPreview from '../assets/analysis_preview.jpg';
import trendsPreview from '../assets/trends_preview.jpg';
import scriptingPreview from '../assets/scripting_preview.jpg';
import cinematicPreview from '../assets/cinematic_preview.jpg';
import uploadPreview from '../assets/upload_preview.jpg';
import icon1 from '../assets/icon_1.jpg';
import icon2 from '../assets/icon_2.jpg';
import icon3 from '../assets/icon_3.jpg';

const WelcomePage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');

  return (
    <div style={{ background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd', fontFamily: "'Inter', sans-serif" }}>
      {/* ===== TOP NAV BAR ===== */}
      <nav className="sticky top-0 z-50 flex justify-between items-center px-4 py-4 md:px-8 shadow-2xl" style={{
        background: 'rgba(12,14,23,0.6)', backdropFilter: 'blur(24px)',
      }}>
        <div style={{ fontSize: '1.5rem', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.05em', color: '#00E5FF', cursor: 'pointer' }}
          onClick={() => navigate('/')}>YOUTOMIZE</div>
        <div className="hidden md:flex items-center gap-10">
          <a href="#home" style={{ color: '#00E5FF', fontWeight: 700, borderBottom: '2px solid #00E5FF', paddingBottom: '4px', textDecoration: 'none', fontFamily: "'Space Grotesk', sans-serif", transition: 'all 0.3s' }}>Home</a>
          {['Features', 'Pricing'].map(item => (
            <a key={item} href={`#${item.toLowerCase()}`} style={{ color: '#94a3b8', fontWeight: 500, textDecoration: 'none', fontFamily: "'Space Grotesk', sans-serif", transition: 'all 0.3s' }}
              onMouseEnter={e => e.target.style.color = '#fff'} onMouseLeave={e => e.target.style.color = '#94a3b8'}>{item}</a>
          ))}
          <a href="#" onClick={e => { e.preventDefault(); navigate('/auth'); }} style={{ color: '#94a3b8', fontWeight: 500, textDecoration: 'none', fontFamily: "'Space Grotesk', sans-serif", transition: 'all 0.3s' }}
            onMouseEnter={e => e.target.style.color = '#fff'} onMouseLeave={e => e.target.style.color = '#94a3b8'}>Sign In</a>
        </div>
        <button onClick={() => navigate('/auth')} style={{
          background: 'linear-gradient(to right, #81ecff, #a68cff)', color: '#3b00a0',
          fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
          padding: '10px 24px', borderRadius: '8px', border: 'none', cursor: 'pointer',
          transition: 'all 0.3s',
        }}
          onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.05)'; e.currentTarget.style.filter = 'brightness(1.1)'; }}
          onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.filter = 'brightness(1)'; }}
        >Try Now</button>
      </nav>

      {/* ===== HERO ===== */}
      <header id="home" style={{
        position: 'relative', minHeight: '90vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        overflow: 'hidden', padding: '20px 32px 0',
      }}>
        <div style={{ position: 'absolute', inset: 0, zIndex: 0, background: 'radial-gradient(circle at 50% 50%, rgba(129,236,255,0.15) 0%, rgba(166,140,255,0.05) 50%, transparent 100%)' }} />
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: '100%', height: '100%', opacity: 0.2, pointerEvents: 'none' }}>
          <div style={{ width: '100%', height: '100%', backgroundImage: "url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=2000')", backgroundSize: 'cover', backgroundPosition: 'center', mixBlendMode: 'overlay' }} />
        </div>
        <div style={{ position: 'relative', zIndex: 10, textAlign: 'center', maxWidth: '1100px' }}>
          <span style={{ display: 'inline-block', padding: '6px 16px', borderRadius: '9999px', background: '#1c1f2b', color: '#81ecff', fontFamily: "'Manrope', sans-serif", fontSize: '14px', fontWeight: 600, marginBottom: '24px', border: '1px solid rgba(129,236,255,0.1)', letterSpacing: '0.08em' }}>POWERED BY NEXT-GEN AI</span>
          <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(2.5rem, 5vw, 4rem)', letterSpacing: '-0.03em', marginBottom: '24px', lineHeight: 1.1 }}>
            Automate Your <br />
            <span style={{ color: 'transparent', backgroundImage: 'linear-gradient(to right, #81ecff, #00e3fd, #a68cff)', WebkitBackgroundClip: 'text', backgroundClip: 'text' }}>YouTube Growth</span> with AI
          </h1>
          <p style={{ color: '#aaaab7', fontSize: '1rem', maxWidth: '600px', margin: '0 auto 36px', fontWeight: 300, lineHeight: 1.7 }}>
            Unlock high-performance channel automation. From cinematic AI generation to real-time trend analysis, scale your presence without the manual grind.
          </p>
          <div style={{ display: 'flex', flexDirection: 'row', gap: '16px', justifyContent: 'center' }}>
            <button onClick={() => navigate('/auth')} style={{
              padding: '14px 28px', background: 'linear-gradient(135deg, #81ecff, #a68cff)', color: '#3b00a0',
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1rem',
              borderRadius: '10px', border: 'none', cursor: 'pointer',
              boxShadow: '0 10px 30px rgba(0,229,255,0.3)', transition: 'all 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.05)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
            >Get Started</button>
            <button style={{
              padding: '14px 28px', background: 'rgba(34,37,50,0.6)', backdropFilter: 'blur(20px)',
              border: '1px solid rgba(70,71,82,0.3)', color: '#81ecff',
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1rem',
              borderRadius: '10px', cursor: 'pointer', transition: 'all 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.background = '#222532'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(34,37,50,0.6)'}
            >Watch Demo</button>
          </div>
        </div>
      </header>

      {/* ===== FEATURES ===== */}
      <section id="features" style={{ padding: '128px 32px', maxWidth: '1280px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '160px' }}>
        {/* Feature 1: YouTube Growth */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', inset: '-16px', background: 'rgba(129,236,255,0.1)', filter: 'blur(48px)', borderRadius: '9999px' }} />
            <div style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', border: '1px solid rgba(70,71,82,0.2)', aspectRatio: '16/9', boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
              <img src={dashboardPreview} alt="Dashboard" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>
          <div>
            <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem', color: '#81ecff', letterSpacing: '-0.02em', marginBottom: '24px' }}>YouTube Growth</h3>
            <p style={{ color: '#aaaab7', fontSize: '1.125rem', lineHeight: 1.7, marginBottom: '32px' }}>Gain deep insights into your audience's behavior. Our AI analyzes millions of data points to provide actionable channel insights that drive organic discovery.</p>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px', fontFamily: "'Manrope', sans-serif", color: 'rgba(240,240,253,0.8)' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><span style={{ color: '#81ecff' }}>✓</span> Demographic profiling</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><span style={{ color: '#81ecff' }}>✓</span> Retention optimization curves</li>
            </ul>
          </div>
        </div>

        {/* Feature 2: Performance Analysis */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
          <div>
            <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem', color: '#a68cff', letterSpacing: '-0.02em', marginBottom: '24px' }}>Performance Analysis</h3>
            <p style={{ color: '#aaaab7', fontSize: '1.125rem', lineHeight: 1.7, marginBottom: '32px' }}>Monitor your success as it happens. Real-time metrics visualization allows you to pivot strategies instantly based on what's resonating with your viewers.</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{ background: '#171924', padding: '24px', borderRadius: '16px', border: '1px solid rgba(70,71,82,0.1)' }}>
                <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.5rem', color: '#81ecff' }}>1.2M+</div>
                <div style={{ fontSize: '12px', fontFamily: "'Manrope', sans-serif", color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.15em', marginTop: '4px' }}>Data Points/Sec</div>
              </div>
              <div style={{ background: '#171924', padding: '24px', borderRadius: '16px', border: '1px solid rgba(70,71,82,0.1)' }}>
                <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.5rem', color: '#a68cff' }}>0.1ms</div>
                <div style={{ fontSize: '12px', fontFamily: "'Manrope', sans-serif", color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.15em', marginTop: '4px' }}>Latent Sync</div>
              </div>
            </div>
          </div>
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', inset: '-16px', background: 'rgba(166,140,255,0.1)', filter: 'blur(48px)', borderRadius: '9999px' }} />
            <div style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', border: '1px solid rgba(70,71,82,0.2)', aspectRatio: '16/9', boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
              <img src={analysisPreview} alt="Analysis" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>
        </div>

        {/* Feature 3: Content Trends */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', border: '1px solid rgba(70,71,82,0.2)', aspectRatio: '16/9', boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
              <img src={trendsPreview} alt="Trends" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>
          <div>
            <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem', color: '#81ecff', letterSpacing: '-0.02em', marginBottom: '24px' }}>Content Trends</h3>
            <p style={{ color: '#aaaab7', fontSize: '1.125rem', lineHeight: 1.7, marginBottom: '32px' }}>Never miss a viral moment. Our predictive engine identifies emerging content trends before they peak, giving you the first-mover advantage.</p>
            <button style={{ color: '#81ecff', fontWeight: 700, background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', transition: 'gap 0.3s' }}
              onMouseEnter={e => e.currentTarget.style.gap = '16px'}
              onMouseLeave={e => e.currentTarget.style.gap = '8px'}
            >Explore Trend Engine →</button>
          </div>
        </div>

        {/* Feature 4: Auto Scripting */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
          <div>
            <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem', color: '#a68cff', letterSpacing: '-0.02em', marginBottom: '24px' }}>Auto Scripting</h3>
            <p style={{ color: '#aaaab7', fontSize: '1.125rem', lineHeight: 1.7, marginBottom: '32px' }}>Our specialized LLM crafts high-retention scripts tailored to your niche's unique voice and pacing. Stop staring at blank pages and start producing hits.</p>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px', fontFamily: "'Manrope', sans-serif", color: 'rgba(240,240,253,0.8)' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><span style={{ color: '#a68cff' }}>📝</span> Niche-aware tone matching</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><span style={{ color: '#a68cff' }}>🧠</span> Psychological hook placement</li>
            </ul>
          </div>
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', inset: '-16px', background: 'rgba(166,140,255,0.1)', filter: 'blur(48px)', borderRadius: '9999px' }} />
            <div style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', border: '1px solid rgba(70,71,82,0.2)', aspectRatio: '16/9', boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
              <img src={scriptingPreview} alt="Scripting" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>
        </div>

        {/* Feature 5: Cinematic Generation */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', inset: '-16px', background: 'rgba(129,236,255,0.1)', filter: 'blur(48px)', borderRadius: '9999px' }} />
            <div style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', border: '1px solid rgba(70,71,82,0.2)', aspectRatio: '16/9', boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
              <img src={cinematicPreview} alt="Cinematic" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>
          <div>
            <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem', color: '#81ecff', letterSpacing: '-0.02em', marginBottom: '24px' }}>Cinematic Generation</h3>
            <p style={{ color: '#aaaab7', fontSize: '1.125rem', lineHeight: 1.7, marginBottom: '32px' }}>Convert scripts into stunning 4K visuals automatically. Our proprietary diffusion models create high-impact b-roll and custom animations in seconds.</p>
            <div style={{ background: '#171924', padding: '24px', borderRadius: '16px', border: '1px solid rgba(70,71,82,0.1)', display: 'inline-block' }}>
              <span style={{ fontSize: '2rem' }}>🎬</span>
              <p style={{ fontSize: '12px', fontFamily: "'Manrope', sans-serif", color: '#64748b', marginTop: '8px', textTransform: 'uppercase', letterSpacing: '0.15em' }}>4K Rendered Output</p>
            </div>
          </div>
        </div>

        {/* Feature 6: Auto Upload */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 items-center">
          <div>
            <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem', color: '#a68cff', letterSpacing: '-0.02em', marginBottom: '24px' }}>Auto Upload & Integration</h3>
            <p style={{ color: '#aaaab7', fontSize: '1.125rem', lineHeight: 1.7, marginBottom: '32px' }}>Set and forget. Instant multi-channel integration schedules your content for optimal peak viewing times globally across all major social platforms.</p>
            <div style={{ display: 'flex', gap: '16px' }}>
              {[icon1, icon2, icon3].map((src, i) => (
                <div key={i} style={{
                  width: 64, height: 64, borderRadius: '16px',
                  background: 'rgba(34,37,50,0.6)', backdropFilter: 'blur(20px)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: '1px solid rgba(70,71,82,0.2)', boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
                }}>
                  <img src={src} alt="" style={{ width: 32, height: 32, opacity: 0.6 }} />
                </div>
              ))}
            </div>
          </div>
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', inset: '-16px', background: 'rgba(166,140,255,0.1)', filter: 'blur(48px)', borderRadius: '9999px' }} />
            <div style={{ position: 'relative', borderRadius: '24px', overflow: 'hidden', border: '1px solid rgba(70,71,82,0.2)', aspectRatio: '16/9', boxShadow: '0 25px 50px rgba(0,0,0,0.3)' }}>
              <img src={uploadPreview} alt="Upload" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>
        </div>
      </section>

      {/* ===== PRICING ===== */}
      <section id="pricing" style={{ padding: '128px 32px', background: '#11131d' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', textAlign: 'center', marginBottom: '80px' }}>
          <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '3rem', marginBottom: '24px' }}>Scale Your Empire</h2>
          <p style={{ color: '#aaaab7', maxWidth: '560px', margin: '0 auto' }}>Flexible plans for every stage of your creator journey. Upgrade or downgrade anytime.<br />1 Credit = 4 second AI Video</p>
        </div>
        <div className="max-w-[1280px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
          {/* Starter */}
          <div style={{ background: '#0c0e17', borderRadius: '24px', padding: '40px', border: '1px solid rgba(70,71,82,0.1)', display: 'flex', flexDirection: 'column', transition: 'all 0.5s' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(129,236,255,0.3)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(70,71,82,0.1)'}
          >
            <div style={{ marginBottom: '32px' }}>
              <h3 style={{ fontFamily: "'Manrope', sans-serif", color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.15em', fontSize: '12px', marginBottom: '16px' }}>Starter</h3>
              <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem' }}>$29.99<span style={{ fontSize: '1.125rem', fontWeight: 400, color: '#64748b' }}>/mo</span></div>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '40px', flex: 1 }}>
              {['1 YouTube Channel', 'Script Generation', '50 Video Generation Credits', 'Standard Analytics', 'Community Support'].map((f, i) => (
                <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '14px', color: 'rgba(240,240,253,0.8)' }}>
                  <span style={{ color: '#81ecff' }}>✓</span> {f}
                </li>
              ))}
            </ul>
            <button onClick={() => navigate('/auth')} style={{ width: '100%', padding: '16px', borderRadius: '12px', border: '1px solid #464752', background: 'transparent', color: '#f0f0fd', fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.background = '#171924'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >Get Started</button>
          </div>
          {/* Creator */}
          <div style={{ background: '#1c1f2b', borderRadius: '24px', padding: '40px', border: '2px solid #81ecff', display: 'flex', flexDirection: 'column', position: 'relative', boxShadow: '0 20px 50px rgba(0,229,255,0.15)', transform: 'scale(1.05)', zIndex: 10 }}>
            <div style={{ position: 'absolute', top: '-16px', left: '50%', transform: 'translateX(-50%)', background: '#81ecff', color: '#003840', padding: '4px 24px', borderRadius: '9999px', fontFamily: "'Manrope', sans-serif", fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.15em' }}>Most Popular</div>
            <div style={{ marginBottom: '32px' }}>
              <h3 style={{ fontFamily: "'Manrope', sans-serif", color: '#81ecff', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.15em', fontSize: '12px', marginBottom: '16px' }}>Creator</h3>
              <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem' }}>$50.99<span style={{ fontSize: '1.125rem', fontWeight: 400, color: '#64748b' }}>/mo</span></div>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '40px', flex: 1 }}>
              {['5 YouTube Channels', '85 Video Generation Credits', 'Cinematic Generation (HD)', 'Real-time Performance Dash', 'Priority AI Processing', 'Email Support'].map((f, i) => (
                <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '14px', color: i === 0 ? '#f0f0fd' : 'rgba(240,240,253,0.8)', fontWeight: i === 0 ? 500 : 400 }}>
                  <span style={{ color: '#81ecff' }}>{i === 0 ? '⭐' : '✓'}</span> {f}
                </li>
              ))}
            </ul>
            <button onClick={() => navigate('/auth')} style={{ width: '100%', padding: '16px', borderRadius: '12px', border: 'none', background: 'linear-gradient(to right, #81ecff, #a68cff)', color: '#3b00a0', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, cursor: 'pointer', boxShadow: '0 10px 30px rgba(129,236,255,0.2)', transition: 'all 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.filter = 'brightness(1.1)'}
              onMouseLeave={e => e.currentTarget.style.filter = 'brightness(1)'}
            >Choose Creator</button>
          </div>
          {/* Professional */}
          <div style={{ background: '#0c0e17', borderRadius: '24px', padding: '40px', border: '1px solid rgba(70,71,82,0.1)', display: 'flex', flexDirection: 'column', transition: 'all 0.5s' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(166,140,255,0.3)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(70,71,82,0.1)'}
          >
            <div style={{ marginBottom: '32px' }}>
              <h3 style={{ fontFamily: "'Manrope', sans-serif", color: '#64748b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.15em', fontSize: '12px', marginBottom: '16px' }}>Professional</h3>
              <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '2.5rem' }}>$74.99<span style={{ fontSize: '1.125rem', fontWeight: 400, color: '#64748b' }}>/mo</span></div>
            </div>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '40px', flex: 1 }}>
              {['Unlimited Channels', '125 Video Generation Credits', '4K Cinematic Generation', 'White-label Reports', 'API Access', 'Dedicated Account Manager'].map((f, i) => (
                <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '14px', color: 'rgba(240,240,253,0.8)' }}>
                  <span style={{ color: '#a68cff' }}>✓</span> {f}
                </li>
              ))}
            </ul>
            <button onClick={() => navigate('/auth')} style={{ width: '100%', padding: '16px', borderRadius: '12px', border: '1px solid #464752', background: 'transparent', color: '#f0f0fd', fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.background = '#171924'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >Go Pro</button>
          </div>
        </div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer className="bg-[#0c0e17] px-6 py-12 md:px-8 md:py-16 border-t border-[#1c1f2b]">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-12 max-w-[1280px] mx-auto">
          <div>
            <span style={{ display: 'block', fontSize: '1.25rem', fontWeight: 700, color: '#00E5FF', marginBottom: '16px' }}>YOUTOMIZE</span>
            <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.6 }}>The next-generation platform for YouTube automation. Built by creators, powered by intelligence.</p>
          </div>
          <div>
            <h4 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, marginBottom: '24px' }}>Product</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {['Features', 'Pricing', 'API Documentation'].map(item => (
                <li key={item}><a href="#" style={{ fontSize: '14px', color: '#64748b', textDecoration: 'none', transition: 'color 0.3s' }}
                  onMouseEnter={e => e.target.style.color = '#00E5FF'} onMouseLeave={e => e.target.style.color = '#64748b'}>{item}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, marginBottom: '24px' }}>Company</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {['Contact', 'Affiliates', 'Privacy Policy', 'Terms of Service'].map(item => (
                <li key={item}><a href="#" style={{ fontSize: '14px', color: '#64748b', textDecoration: 'none', transition: 'color 0.3s' }}
                  onMouseEnter={e => e.target.style.color = '#00E5FF'} onMouseLeave={e => e.target.style.color = '#64748b'}>{item}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, marginBottom: '24px' }}>Newsletter</h4>
            <div style={{ background: '#1c1f2b', borderRadius: '12px', padding: '8px', display: 'flex', border: '1px solid rgba(70,71,82,0.1)' }}>
              <input type="email" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)}
                style={{ flex: 1, minWidth: 0, background: 'transparent', border: 'none', color: '#f0f0fd', fontSize: '14px', padding: '0 8px', outline: 'none' }} />
              <button style={{ background: '#81ecff', color: '#003840', padding: '8px', borderRadius: '8px', border: 'none', cursor: 'pointer', fontSize: '16px' }}>→</button>
            </div>
          </div>
        </div>
        <div style={{ maxWidth: '1280px', margin: '64px auto 0', paddingTop: '32px', borderTop: '1px solid rgba(70,71,82,0.05)', textAlign: 'center' }}>
          <p style={{ fontSize: '14px', color: '#94a3b8' }}>© 2024 YOUTOMIZE. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default WelcomePage;