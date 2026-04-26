/**
 * CheckoutPage — Cinema AI Stitch Design
 * Reads package from URL params, initiates Paddle checkout using JWT from Supabase session.
 * Visual design from buy credits.htm stitch source.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import api from '../api/auth';

/* ── Material icon helper ── */
const Icon = ({ name, filled, style = {} }) => (
  <span
    className="material-symbols-outlined"
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", ...style }}
  >{name}</span>
);

/* ── Load Paddle.js once ── */
const initializePaddle = () =>
  new Promise((resolve) => {
    if (window.Paddle) { resolve(window.Paddle); return; }
    const script = document.createElement('script');
    script.src = 'https://cdn.paddle.com/paddle/v2/paddle.js';
    script.async = true;
    script.onload = () => {
      if (window.Paddle) {
        const env = import.meta.env.VITE_PADDLE_ENVIRONMENT || 'sandbox';
        const token = import.meta.env.VITE_PADDLE_CLIENT_TOKEN || 'test_fd9e78a92d5bc0c7f69d021fc39';
        window.Paddle.Environment.set(env);
        window.Paddle.Initialize({ token });
        resolve(window.Paddle);
      }
    };
    document.body.appendChild(script);
  });

const CheckoutPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const packageName = searchParams.get('package');
  const packageId = searchParams.get('package_id');

  const [loading, setLoading] = useState(false);
  const [paddleReady, setPaddleReady] = useState(false);
  const [error, setError] = useState(null);
  const [pkg, setPkg] = useState(null);

  useEffect(() => {
    initializePaddle().then(() => setPaddleReady(true));
    fetchPackage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchPackage = async () => {
    if (!packageId) return;
    try {
      const res = await api.get('/api/pricing');
      const found = (res.data.packages || []).find((p) => p.id === packageId);
      if (found) setPkg(found);
    } catch (err) {
      console.error('[CHECKOUT] Failed to load package:', err);
    }
  };

  const handleCheckout = async (e) => {
    e?.preventDefault();
    if (!paddleReady) {
      setError('Payment system is still loading. Please try again.');
      return;
    }
    if (!packageId) {
      setError('No package selected. Please go back and select a package.');
      return;
    }

    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) {
      setError('You must be logged in to make a purchase.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/api/paddle/create-checkout', {
        package_id: packageId,
        success_url: `${window.location.origin}/success`,
        cancel_url: `${window.location.origin}/pricing`,
      });

      if (response.data?.transactionId && window.Paddle) {
        sessionStorage.setItem('paddle_transaction_id', response.data.transactionId);
        window.Paddle.Checkout.open({
          transactionId: response.data.transactionId,
          settings: { successUrl: response.data.success_url },
        });
      } else {
        setError('Failed to initialize checkout — missing transaction ID. Please try again.');
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Failed to create order. Please try again.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const displayPkg = pkg || { name: packageName || 'Selected Package', price: '—', credits: '—' };
  const displayPrice = displayPkg.price !== '—' ? `$${Number(displayPkg.price).toFixed(2)}` : '—';

  /* ── Shared input styles ── */
  const inputStyle = {
    width: '100%', background: '#11131d', border: 'none', borderRadius: '8px',
    padding: '16px 20px', color: '#f0f0fd', fontSize: '14px',
    fontFamily: "'Inter', sans-serif", outline: 'none',
    transition: 'box-shadow 0.3s',
  };

  return (
    <div style={{ background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd', fontFamily: "'Inter', sans-serif", display: 'flex', flexDirection: 'column' }}>

      {/* ===== HEADER ===== */}
      <header style={{
        background: '#0c0e17', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        width: '100%', padding: '24px 32px', zIndex: 50,
      }}>
        <div
          onClick={() => navigate('/dashboard')}
          style={{
            fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.05em',
            fontSize: '1.5rem', fontWeight: 700, color: '#00E5FF', cursor: 'pointer',
          }}
        >YOUTOMIZE</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Icon name="account_circle" style={{ color: '#94a3b8', fontSize: '28px', cursor: 'pointer' }} />
        </div>
      </header>

      {/* ===== MAIN CONTENT ===== */}
      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px 16px 48px' }}>
        <div style={{
          maxWidth: '960px', width: '100%',
          display: 'grid', gridTemplateColumns: '1fr', gap: '24px', alignItems: 'start',
        }}
          className="lg:grid-cols-12"
        >
          {/* ── LEFT COLUMN: Summary ── */}
          <div style={{ gridColumn: 'span 5' }} className="lg:col-span-5">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

              {/* Title */}
              <div>
                <h1 style={{
                  fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                  fontSize: '2rem', letterSpacing: '-0.02em', marginBottom: '6px',
                }}>Secure Checkout</h1>
                <p style={{
                  color: '#aaaab7', fontFamily: "'Manrope', sans-serif", fontSize: '14px',
                }}>Review your cinematic intelligence upgrade.</p>
              </div>

              {/* Plan Summary Card */}
              <div style={{
                background: '#11131d', borderRadius: '12px', padding: '24px',
                position: 'relative', overflow: 'hidden',
              }}>
                {/* Glow */}
                <div style={{
                  position: 'absolute', top: 0, right: 0, width: 128, height: 128,
                  background: 'rgba(166,140,255,0.1)', filter: 'blur(48px)',
                  borderRadius: '50%', marginRight: '-64px', marginTop: '-64px',
                }} />

                <div style={{ position: 'relative', zIndex: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                    <div>
                      <span style={{
                        background: '#591adc', color: '#e4daff',
                        padding: '4px 12px', borderRadius: '9999px',
                        fontSize: '12px', fontWeight: 700, fontFamily: "'Manrope', sans-serif",
                        letterSpacing: '0.08em', display: 'inline-block', marginBottom: '8px',
                      }}>PREMIUM PLAN</span>
                      <h2 style={{
                        fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.5rem', fontWeight: 700,
                      }}>{displayPkg.name}</h2>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{
                        fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.5rem',
                        fontWeight: 700, color: '#81ecff',
                      }}>{displayPrice}</div>
                      <div style={{
                        fontSize: '12px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif",
                      }}>Per month</div>
                    </div>
                  </div>

                  {/* Features */}
                  <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
                    {['4K Cinematic AI Upscaling', 'Unlimited Voice Clones', 'Real-time Style Transfer'].map((feat, i) => (
                      <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '14px', color: '#aaaab7' }}>
                        <Icon name="check_circle" style={{ color: '#81ecff', fontSize: '18px' }} />
                        {feat}
                      </li>
                    ))}
                  </ul>

                  {/* Total */}
                  <div style={{
                    paddingTop: '24px', borderTop: '1px solid rgba(70,71,82,0.2)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <span style={{ fontFamily: "'Manrope', sans-serif", color: '#aaaab7' }}>Total Due Today</span>
                    <span style={{
                      fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.875rem', fontWeight: 700,
                    }}>{displayPrice}</span>
                  </div>
                </div>
              </div>

              {/* Security Badge */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: '16px',
                padding: '16px', borderRadius: '8px',
                background: 'rgba(23,25,36,0.5)', borderLeft: '4px solid rgba(129,236,255,0.3)',
              }}>
                <Icon name="security" filled style={{ color: '#81ecff', fontSize: '24px' }} />
                <p style={{ fontSize: '12px', color: '#aaaab7', lineHeight: 1.6 }}>
                  Your transaction is secured with bank-grade 256-bit encryption. We do not store your full card details.
                </p>
              </div>
            </div>
          </div>

          {/* ── RIGHT COLUMN: Payment Form ── */}
          <div style={{ gridColumn: 'span 7' }} className="lg:col-span-7">
            <div style={{
              background: 'rgba(34,37,50,0.6)', backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
              padding: '24px 28px', borderRadius: '12px',
              boxShadow: '0 25px 50px rgba(0,0,0,0.3)',
              position: 'relative', overflow: 'hidden',
            }}>
              {/* Subtle glow */}
              <div style={{
                position: 'absolute', bottom: '-96px', right: '-96px',
                width: 256, height: 256, background: 'rgba(129,236,255,0.05)',
                filter: 'blur(100px)', borderRadius: '50%',
              }} />

              <form onSubmit={handleCheckout} style={{ display: 'flex', flexDirection: 'column', gap: '18px', position: 'relative', zIndex: 10 }}>
                {/* Back link */}
                <button
                  type="button"
                  onClick={() => navigate('/pricing')}
                  style={{
                    background: 'transparent', border: 'none', color: '#aaaab7',
                    fontSize: '14px', cursor: 'pointer', textAlign: 'left',
                    fontFamily: "'Inter', sans-serif", display: 'flex', alignItems: 'center', gap: '4px',
                    transition: 'color 0.3s', padding: 0, marginBottom: '8px',
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = '#81ecff'}
                  onMouseLeave={e => e.currentTarget.style.color = '#aaaab7'}
                >← Back to Pricing</button>

                <div style={{
                  padding: '24px', borderRadius: '8px',
                  background: 'rgba(129,236,255,0.05)', border: '1px dashed rgba(129,236,255,0.2)',
                  textAlign: 'center', marginBottom: '8px'
                }}>
                  <Icon name="lock" style={{ fontSize: '32px', color: '#81ecff', marginBottom: '12px' }} />
                  <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f0fd', marginBottom: '8px', fontFamily: "'Space Grotesk', sans-serif" }}>Secure Payment</h3>
                  <p style={{ fontSize: '14px', color: '#aaaab7', fontFamily: "'Manrope', sans-serif", lineHeight: 1.5 }}>
                    Click the button below to open our secure Paddle payment gateway. You will enter your card details in the encrypted overlay.
                  </p>
                </div>

                {/* Error */}
                {error && (
                  <div style={{
                    padding: '12px', borderRadius: '8px',
                    background: 'rgba(255,113,108,0.1)', border: '1px solid rgba(255,113,108,0.3)',
                    color: '#ff716c', fontSize: '14px',
                  }}>{error}</div>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading || !packageId}
                  style={{
                    position: 'relative', width: '100%', marginTop: '16px',
                    background: 'linear-gradient(to right, #81ecff, #a68cff)',
                    color: '#003840',
                    fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
                    fontSize: '1rem', padding: '20px',
                    borderRadius: '8px', border: 'none', cursor: loading ? 'wait' : 'pointer',
                    overflow: 'hidden',
                    boxShadow: '0 0 20px rgba(129,236,255,0.3)',
                    transition: 'all 0.3s',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
                    opacity: (loading || !packageId) ? 0.7 : 1,
                  }}
                  onMouseEnter={e => { if (!loading) e.currentTarget.style.boxShadow = '0 0 30px rgba(129,236,255,0.5)'; }}
                  onMouseLeave={e => e.currentTarget.style.boxShadow = '0 0 20px rgba(129,236,255,0.3)'}
                >
                  <Icon name="lock" filled style={{ fontSize: '18px' }} />
                  {loading ? 'Processing…' : 'Complete Payment'}
                  {/* Shimmer overlay */}
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)',
                    backgroundSize: '200% 100%',
                    pointerEvents: 'none', opacity: 0.5,
                    animation: 'shimmer-slide 2s infinite',
                  }} />
                </button>

                <p style={{
                  textAlign: 'center', fontSize: '12px',
                  color: 'rgba(170,170,183,0.6)', fontFamily: "'Manrope', sans-serif",
                }}>
                  By completing this purchase, you agree to our{' '}
                  <a href="#" style={{ textDecoration: 'underline', color: 'inherit', transition: 'color 0.3s' }}
                    onMouseEnter={e => e.target.style.color = '#81ecff'}
                    onMouseLeave={e => e.target.style.color = 'rgba(170,170,183,0.6)'}
                  >Terms of Service</a>.
                </p>
              </form>
            </div>
          </div>
        </div>
      </main>

      {/* ===== FOOTER ===== */}
      <footer style={{
        background: '#0c0e17', padding: '48px 32px',
        borderTop: 'none',
      }}>
        <div style={{
          maxWidth: '1280px', margin: '0 auto',
          display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '24px',
        }}>
          <div style={{
            fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.125rem',
            fontWeight: 700, color: '#cbd5e1',
          }}>YOUTOMIZE</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '24px' }}>
            {['Terms of Service', 'Privacy Policy', 'Support', 'API Docs'].map(item => (
              <a key={item} href="#" style={{
                fontFamily: "'Inter', sans-serif", fontSize: '14px',
                color: '#64748b', textDecoration: 'none', transition: 'color 0.3s',
              }}
                onMouseEnter={e => e.target.style.color = '#00E5FF'}
                onMouseLeave={e => e.target.style.color = '#64748b'}
              >{item}</a>
            ))}
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '14px', color: '#64748b' }}>
            © 2024 YOUTOMIZE. Cinematic Intelligence for Creators.
          </div>
        </div>
      </footer>

      {/* Inline responsive grid styles */}
      <style>{`
        @media (min-width: 1024px) {
          .lg\\:grid-cols-12 { grid-template-columns: repeat(12, minmax(0, 1fr)) !important; }
          .lg\\:col-span-5 { grid-column: span 5 / span 5 !important; }
          .lg\\:col-span-7 { grid-column: span 7 / span 7 !important; }
        }
      `}</style>
    </div>
  );
};

export default CheckoutPage;
