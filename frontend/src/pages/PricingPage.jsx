/**
 * PricingPage — Cinema AI Stitch Design
 * Fetches packages dynamically from backend API, renders in Stitch design layout.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/auth';
import pricingBg from '../assets/pricing_bg.jpg';

/* ── Material icon helper ── */
const Icon = ({ name, filled, className = '', style = {} }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", ...style }}
  >{name}</span>
);

/* ── Fallback feature lists per tier index ── */
const tierMeta = [
  {
    label: 'Foundational',
    labelColor: '#81ecff',
    iconName: 'check_circle',
    iconColor: '#81ecff',
    features: ['AI Scripting Engine', 'Cinematic Generation', 'Auto Upload (YT/TikTok)'],
    disabledFeatures: ['Multi-track Editing', 'Priority Rendering'],
    btnClass: 'bg-[#222532] border border-[rgba(70,71,82,0.2)] hover:border-[rgba(129,236,255,0.5)]',
    btnText: 'text-[#f0f0fd]',
    cardBg: 'bg-[#11131d]',
  },
  {
    label: 'Professional Grade',
    labelColor: '#81ecff',
    iconName: 'verified',
    iconColor: '#81ecff',
    features: ['Advanced AI Scripting', '4K Cinematic Generation', 'Auto Upload & Scheduling', 'Multi-track Voice AI', 'Custom Brand Presets'],
    disabledFeatures: [],
    btnClass: 'btn-gradient shadow-lg shadow-[rgba(129,236,255,0.2)] hover:brightness-110',
    btnText: 'text-[#005762]',
    cardBg: 'bg-[#1c1f2b]',
    featured: true,
  },
  {
    label: 'Studio Tier',
    labelColor: '#a68cff',
    iconName: 'auto_awesome',
    iconColor: '#a68cff',
    features: ['Elite AI Orchestration', 'Unlimited 4K Exporting', 'Multi-Platform Cloud Sync', 'Priority Server Access', 'API Developer Access'],
    disabledFeatures: [],
    btnClass: 'bg-[#222532] border border-[rgba(70,71,82,0.2)] hover:border-[rgba(166,140,255,0.5)]',
    btnText: 'text-[#f0f0fd]',
    cardBg: 'bg-[#11131d]',
  },
];

const PricingPage = () => {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => { fetchPackages(); }, []);

  const fetchPackages = async () => {
    try {
      const res = await api.get('/api/pricing');
      setPackages(res.data.packages || []);
    } catch (err) {
      console.error('[PRICING] Failed to load packages:', err);
      setError('Failed to load pricing. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleBuy = (pkg) => {
    navigate(`/checkout?package=${encodeURIComponent(pkg.name)}&package_id=${pkg.id}`);
  };

  return (
    <div style={{ background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd', fontFamily: "'Inter', sans-serif" }}>
      {/* ===== HEADER ===== */}
      <header style={{
        background: '#0c0e17', position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '16px 32px',
      }}>
        <div
          onClick={() => navigate('/dashboard')}
          style={{
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.05em',
            fontSize: '1.5rem', fontWeight: 700, color: '#00E5FF', cursor: 'pointer',
          }}
        >YOUTOMIZE</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={() => navigate('/dashboard')}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8', transition: 'color 0.3s' }}
            onMouseEnter={e => e.currentTarget.style.color = '#81ecff'}
            onMouseLeave={e => e.currentTarget.style.color = '#94a3b8'}
          >
            <Icon name="account_circle" style={{ fontSize: '28px' }} />
          </button>
        </div>
      </header>

      {/* ===== MAIN ===== */}
      <main style={{ paddingTop: '128px', paddingBottom: '96px', paddingLeft: '24px', paddingRight: '24px', minHeight: '100vh' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>

          {/* Hero Title */}
          <div style={{ textAlign: 'center', marginBottom: '80px' }}>
            <h1 style={{
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
              fontSize: 'clamp(2.5rem, 5vw, 3.75rem)', letterSpacing: '-0.05em',
              marginBottom: '16px',
            }}>Choose Your Plan</h1>
            <p style={{
              fontFamily: "'Inter', sans-serif", color: '#aaaab7',
              maxWidth: '640px', margin: '0 auto', fontSize: '1.125rem', lineHeight: 1.6,
            }}>
              Scale your content production with cinematic AI intelligence. Select the precision engine that fits your vision.
            </p>
          </div>

          {/* Loading */}
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '80px 0' }}>
              <div style={{
                width: 40, height: 40, border: '4px solid #81ecff', borderTopColor: 'transparent',
                borderRadius: '50%', animation: 'spin 1s linear infinite',
              }} />
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <p style={{ color: '#ff716c', marginBottom: '16px' }}>{error}</p>
              <button onClick={fetchPackages} style={{
                background: 'linear-gradient(45deg, #81ecff, #a68cff)', color: '#005762',
                fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                padding: '12px 32px', borderRadius: '8px', border: 'none', cursor: 'pointer',
              }}>Retry</button>
            </div>
          )}

          {/* Pricing Grid */}
          {!loading && !error && packages.length > 0 && (
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
              gap: '32px', alignItems: 'end',
            }}>
              {packages.map((pkg, index) => {
                const meta = tierMeta[index] || tierMeta[0];
                const isFeatured = meta.featured;

                return (
                  <div key={pkg.id} style={{ position: 'relative' }}>
                    {/* "MOST POPULAR" badge */}
                    {isFeatured && (
                      <div style={{
                        position: 'absolute', top: '-16px', left: '50%', transform: 'translateX(-50%)',
                        background: 'linear-gradient(to right, #81ecff, #a68cff)',
                        color: '#004d57', padding: '4px 16px', borderRadius: '9999px',
                        fontSize: '12px', fontWeight: 700, fontFamily: "'Manrope', sans-serif",
                        zIndex: 10, boxShadow: '0 4px 20px rgba(129,236,255,0.2)',
                        letterSpacing: '0.05em',
                      }}>MOST POPULAR</div>
                    )}

                    <div
                      style={{
                        background: isFeatured ? '#1c1f2b' : '#11131d',
                        borderRadius: '12px', padding: '32px',
                        display: 'flex', flexDirection: 'column', height: '100%',
                        border: isFeatured ? '1px solid rgba(129,236,255,0.2)' : 'none',
                        boxShadow: isFeatured ? '0 25px 50px rgba(129,236,255,0.05)' : 'none',
                        transform: isFeatured ? 'scale(1.05)' : 'none',
                        position: 'relative', overflow: 'hidden',
                        transition: 'transform 0.3s ease',
                      }}
                      onMouseEnter={e => { if (!isFeatured) e.currentTarget.style.transform = 'translateY(-4px)'; }}
                      onMouseLeave={e => { if (!isFeatured) e.currentTarget.style.transform = 'translateY(0)'; }}
                    >
                      {/* Featured shimmer bg */}
                      {isFeatured && (
                        <div style={{
                          position: 'absolute', inset: 0, pointerEvents: 'none',
                          background: 'linear-gradient(135deg, rgba(129,236,255,0.05), rgba(166,140,255,0.05))',
                        }} />
                      )}

                      <div style={{ position: 'relative', zIndex: 10 }}>
                        {/* Tier label */}
                        <div style={{ marginBottom: '32px' }}>
                          <span style={{
                            fontFamily: "'Manrope', sans-serif", fontSize: '12px',
                            textTransform: 'uppercase', letterSpacing: '0.15em',
                            color: meta.labelColor, fontWeight: 700,
                            marginBottom: '8px', display: 'block',
                          }}>{meta.label}</span>
                          <h3 style={{
                            fontFamily: "'Space Grotesk', sans-serif",
                            fontSize: isFeatured ? '1.875rem' : '1.5rem', fontWeight: 700,
                            marginBottom: '4px',
                          }}>{pkg.name}</h3>
                          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginTop: '16px' }}>
                            <span style={{
                              fontFamily: "'Space Grotesk', sans-serif",
                              fontSize: isFeatured ? '3rem' : '2.5rem', fontWeight: 700,
                            }}>${Number(pkg.price).toFixed(2)}</span>
                            <span style={{ color: '#aaaab7', fontSize: '14px' }}>/mo</span>
                          </div>
                          <p style={{ color: '#aaaab7', fontSize: '14px', marginTop: '8px', fontWeight: isFeatured ? 500 : 400 }}>
                            {pkg.credits} Monthly Credits
                          </p>
                        </div>

                        {/* Features */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '40px', flex: 1 }}>
                          {meta.features.map((feat, i) => (
                            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <Icon name={meta.iconName} style={{ color: meta.iconColor, fontSize: '14px' }} />
                              <span style={{
                                fontSize: '14px',
                                color: isFeatured ? '#f0f0fd' : 'rgba(240,240,253,0.8)',
                                fontWeight: isFeatured ? 500 : 400,
                              }}>{feat}</span>
                            </div>
                          ))}
                          {meta.disabledFeatures.map((feat, i) => (
                            <div key={`d-${i}`} style={{ display: 'flex', alignItems: 'center', gap: '12px', opacity: 0.4 }}>
                              <Icon name="block" style={{ fontSize: '14px' }} />
                              <span style={{ fontSize: '14px', color: 'rgba(240,240,253,0.8)' }}>{feat}</span>
                            </div>
                          ))}
                        </div>

                        {/* CTA Button */}
                        <button
                          onClick={() => handleBuy(pkg)}
                          style={{
                            width: '100%', padding: '16px', borderRadius: '8px',
                            fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                            fontSize: '1rem', cursor: 'pointer',
                            transition: 'all 0.2s',
                            ...(isFeatured
                              ? {
                                  background: 'linear-gradient(45deg, #81ecff, #a68cff)',
                                  color: '#005762', border: 'none',
                                  boxShadow: '0 10px 30px rgba(129,236,255,0.2)',
                                }
                              : {
                                  background: '#222532',
                                  color: '#f0f0fd', border: '1px solid rgba(70,71,82,0.2)',
                                }),
                          }}
                          onMouseEnter={e => {
                            if (isFeatured) {
                              e.currentTarget.style.filter = 'brightness(1.1)';
                            } else {
                              e.currentTarget.style.borderColor = index === 2 ? 'rgba(166,140,255,0.5)' : 'rgba(129,236,255,0.5)';
                            }
                          }}
                          onMouseLeave={e => {
                            e.currentTarget.style.filter = 'brightness(1)';
                            e.currentTarget.style.borderColor = 'rgba(70,71,82,0.2)';
                          }}
                        >Select Package</button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && packages.length === 0 && (
            <p style={{ textAlign: 'center', padding: '64px 0', color: '#aaaab7' }}>
              No packages available at the moment. Please check back later.
            </p>
          )}

          {/* ===== Precision for Creators Section ===== */}
          {!loading && !error && packages.length > 0 && (
            <div style={{
              marginTop: '96px', background: '#171924', borderRadius: '24px',
              padding: '48px', overflow: 'hidden', position: 'relative',
              border: '1px solid rgba(70,71,82,0.1)',
            }}>
              {/* Background image */}
              <div style={{
                position: 'absolute', top: 0, right: 0, width: '50%', height: '100%',
                opacity: 0.2, pointerEvents: 'none',
              }}>
                <img
                  alt="Cinematic abstract"
                  src={pricingBg}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '24px 0 0 24px' }}
                />
              </div>
              <div style={{ position: 'relative', zIndex: 10, maxWidth: '560px' }}>
                <h2 style={{
                  fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                  fontSize: '1.875rem', marginBottom: '24px',
                }}>Precision for Creators</h2>
                <p style={{ color: '#aaaab7', marginBottom: '32px', lineHeight: 1.7 }}>
                  Every package includes our core Cinematic Intelligence engine. Our credits never expire as long as you have an active subscription, allowing you to bank your creativity for big projects.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px' }}>
                  <div style={{
                    background: '#222532', padding: '8px 16px', borderRadius: '9999px',
                    display: 'flex', alignItems: 'center', gap: '8px',
                  }}>
                    <Icon name="security" style={{ color: '#81ecff', fontSize: '18px' }} />
                    <span style={{ fontSize: '14px', fontFamily: "'Manrope', sans-serif" }}>Secure Payments</span>
                  </div>
                  <div style={{
                    background: '#222532', padding: '8px 16px', borderRadius: '9999px',
                    display: 'flex', alignItems: 'center', gap: '8px',
                  }}>
                    <Icon name="history" style={{ color: '#81ecff', fontSize: '18px' }} />
                    <span style={{ fontSize: '14px', fontFamily: "'Manrope', sans-serif" }}>No Long-term Contracts</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ===== FOOTER ===== */}
      <footer style={{
        background: '#0c0e17', padding: '48px 32px',
        borderTop: '1px solid rgba(70,71,82,0.05)',
      }}>
        <div style={{
          maxWidth: '1280px', margin: '0 auto',
          display: 'flex', flexDirection: 'row', flexWrap: 'wrap',
          justifyContent: 'space-between', alignItems: 'center', gap: '24px',
        }}>
          <div style={{
            fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.125rem',
            fontWeight: 700, color: '#cbd5e1',
          }}>YOUTOMIZE</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '32px' }}>
            {['Terms of Service', 'Privacy Policy', 'Support', 'API Docs'].map(item => (
              <a key={item} href="#" style={{
                fontFamily: "'Inter', sans-serif", fontSize: '14px',
                color: '#64748b', textDecoration: 'none', opacity: 0.8,
                transition: 'all 0.3s',
              }}
                onMouseEnter={e => { e.target.style.color = '#00E5FF'; e.target.style.opacity = 1; }}
                onMouseLeave={e => { e.target.style.color = '#64748b'; e.target.style.opacity = 0.8; }}
              >{item}</a>
            ))}
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '14px', color: '#64748b' }}>
            © 2024 YOUTOMIZE. Cinematic Intelligence for Creators.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PricingPage;
