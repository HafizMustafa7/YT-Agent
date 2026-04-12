/**
 * SettingsPage — Cinema AI Stitch Design
 * Based on setting.htm stitch source.
 */
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { tokenService } from '../services/tokenService';

/* ── Material icon helper ── */
const Icon = ({ name, filled, style = {} }) => (
  <span
    className="material-symbols-outlined"
    style={{ fontVariationSettings: filled ? "'FILL' 1" : "'FILL' 0", ...style }}
  >{name}</span>
);

/* ── Settings categories ── */
const settingsNav = [
  { label: 'Preferences', items: ['Appearance', 'Accounts', 'Security', 'Billing'] },
];

const sectionNames = ['Appearance', 'Accounts', 'Security', 'Billing'];

const SettingsPage = () => {
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(true);
  const [activeSection, setActiveSection] = useState('Appearance');
  const [credits, setCredits] = useState(null);

  /* Refs for scroll-spy */
  const sectionRefs = useRef({});

  /* Scroll-spy: highlight sidebar item when card reaches top */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.dataset.section);
          }
        });
      },
      { rootMargin: '-30% 0px -60% 0px', threshold: 0 }
    );

    sectionNames.forEach((name) => {
      const el = sectionRefs.current[name];
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  /* Click sidebar → smooth scroll to card */
  const scrollToSection = (name) => {
    setActiveSection(name);
    const el = sectionRefs.current[name];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  useEffect(() => {
    const fetchCredits = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session?.access_token) return;
        const resp = await fetch(
          `${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/api/user/credits`,
          { headers: { Authorization: `Bearer ${session.access_token}` } }
        );
        if (resp.ok) {
          const d = await resp.json();
          setCredits(d.credits);
        }
      } catch (e) {
        console.error('[Settings] Credits fetch failed:', e);
      }
    };
    fetchCredits();
  }, []);

  const handleLogout = async () => {
    await tokenService.logout();
  };

  return (
    <div style={{ background: '#0c0e17', minHeight: '100vh', color: '#f0f0fd', fontFamily: "'Inter', sans-serif" }}>
      {/* ===== TOP NAV BAR ===== */}
      <header style={{
        background: '#0c0e17', position: 'sticky', top: 0, zIndex: 50,
        boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          width: '100%', maxWidth: '1920px', margin: '0 auto',
          padding: '16px 32px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '48px' }}>
            <span
              onClick={() => navigate('/dashboard')}
              style={{
                fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.5rem',
                fontWeight: 700, letterSpacing: '-0.05em', color: '#00E5FF', cursor: 'pointer',
              }}
            >YOUTOMIZE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <button
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8', transition: 'color 0.3s' }}
              onMouseEnter={e => e.currentTarget.style.color = '#81ecff'}
              onMouseLeave={e => e.currentTarget.style.color = '#94a3b8'}
            >
              <Icon name="notifications" style={{ fontSize: '22px' }} />
            </button>
            <button
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#94a3b8', transition: 'color 0.3s' }}
              onMouseEnter={e => e.currentTarget.style.color = '#81ecff'}
              onMouseLeave={e => e.currentTarget.style.color = '#94a3b8'}
            >
              <Icon name="bolt" style={{ fontSize: '22px' }} />
            </button>
            <button
              onClick={handleLogout}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                background: 'transparent', border: 'none', cursor: 'pointer',
                color: '#ff716c', padding: '6px 12px', borderRadius: '8px',
                transition: 'background 0.3s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,113,108,0.1)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <Icon name="logout" style={{ fontSize: '20px', fontWeight: 700 }} />
              <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '14px' }}>Logout</span>
            </button>
            <div style={{
              width: 40, height: 40, borderRadius: '50%', overflow: 'hidden',
              border: '1px solid #464752', background: '#591adc',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#e4daff', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
            }}>U</div>
          </div>
        </div>
      </header>

      {/* ===== MAIN CONTENT ===== */}
      <main style={{
        minHeight: 'calc(100vh - 200px)', paddingTop: '48px', paddingBottom: '80px',
        paddingLeft: '24px', paddingRight: '24px',
        maxWidth: '1024px', margin: '0 auto',
        display: 'flex', flexDirection: 'column', gap: '48px',
      }}>
        {/* Header */}
        <section>
          <h1 style={{
            fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
            fontSize: 'clamp(2.5rem, 4vw, 3rem)', letterSpacing: '-0.05em',
            marginBottom: '8px',
          }}>Settings</h1>
          <p style={{
            fontFamily: "'Manrope', sans-serif", color: '#aaaab7',
            letterSpacing: '0.02em',
          }}>Configure your AI workspace and account security preferences.</p>
        </section>

        {/* Settings Container */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}
          className="md-grid-settings"
        >
          {/* Side Navigation — Sticky */}
          <aside style={{ position: 'sticky', top: '100px', alignSelf: 'start' }}>
            <div style={{
              background: '#171924', borderRadius: '12px', overflow: 'hidden',
              padding: '16px 0',
            }}>
              {settingsNav.map((group, gi) => (
                <div key={gi}>
                  <div style={{
                    padding: '8px 24px', fontSize: '11px', textTransform: 'uppercase',
                    letterSpacing: '0.15em', color: '#737580', fontWeight: 700,
                  }}>{group.label}</div>
                  {group.items.map(item => (
                    <button
                      key={item}
                      onClick={() => scrollToSection(item)}
                      style={{
                        width: '100%', textAlign: 'left', padding: '10px 24px',
                        background: activeSection === item ? 'rgba(129,236,255,0.08)' : 'transparent',
                        border: 'none', color: activeSection === item ? '#81ecff' : '#aaaab7',
                        fontFamily: "'Space Grotesk', sans-serif", fontWeight: 500,
                        fontSize: '14px', cursor: 'pointer', transition: 'all 0.2s',
                        borderLeft: activeSection === item ? '2px solid #81ecff' : '2px solid transparent',
                      }}
                      onMouseEnter={e => { if (activeSection !== item) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                      onMouseLeave={e => { if (activeSection !== item) e.currentTarget.style.background = 'transparent'; }}
                    >{item}</button>
                  ))}
                </div>
              ))}
            </div>
          </aside>

          {/* Main Settings Cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

            {/* Appearance Card */}
            <div data-section="Appearance" ref={el => sectionRefs.current['Appearance'] = el} style={{
              background: '#1c1f2b', borderRadius: '12px', padding: '28px 32px',
              boxShadow: '0 0 40px 0 rgba(129,236,255,0.08)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                <div style={{
                  width: 48, height: 48, borderRadius: '8px', background: '#171924',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon name="dark_mode" style={{ color: '#81ecff', fontSize: '24px' }} />
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '1.125rem', marginBottom: '4px' }}>Appearance</h3>
                  <p style={{ color: '#aaaab7', fontSize: '14px' }}>Switch between cinematic dark mode and high-contrast lab mode.</p>
                </div>
              </div>
              {/* Toggle */}
              <div
                onClick={() => setDarkMode(!darkMode)}
                style={{
                  width: 56, height: 28, borderRadius: '9999px', cursor: 'pointer',
                  background: darkMode ? 'rgba(129,236,255,0.2)' : '#222532',
                  position: 'relative', transition: 'background 0.3s',
                  flexShrink: 0,
                }}
              >
                <div style={{
                  width: 20, height: 20, borderRadius: '50%',
                  background: '#81ecff', position: 'absolute', top: 4,
                  left: darkMode ? 32 : 4, transition: 'left 0.3s',
                }} />
              </div>
            </div>

            {/* Manage Accounts Card */}
            <div
              data-section="Accounts" ref={el => sectionRefs.current['Accounts'] = el}
              onClick={() => navigate('/dashboard')}
              style={{
                background: '#1c1f2b', borderRadius: '12px', padding: '28px 32px',
                boxShadow: '0 0 40px 0 rgba(129,236,255,0.08)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                cursor: 'pointer', transition: 'background 0.3s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#282b3a'}
              onMouseLeave={e => e.currentTarget.style.background = '#1c1f2b'}
            >
              <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                <div style={{
                  width: 48, height: 48, borderRadius: '8px', background: '#171924',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon name="group" style={{ color: '#81ecff', fontSize: '24px' }} />
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '1.125rem', marginBottom: '4px' }}>Manage Accounts</h3>
                  <p style={{ color: '#aaaab7', fontSize: '14px' }}>Link your YouTube, TikTok, and Instagram creator profiles.</p>
                </div>
              </div>
              <Icon name="chevron_right" style={{ color: '#737580', fontSize: '24px', transition: 'all 0.3s' }} />
            </div>

            {/* Change Password Card */}
            <div
              data-section="Security" ref={el => sectionRefs.current['Security'] = el}
              style={{
                background: '#1c1f2b', borderRadius: '12px', padding: '28px 32px',
                boxShadow: '0 0 40px 0 rgba(129,236,255,0.08)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                cursor: 'pointer', transition: 'background 0.3s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#282b3a'}
              onMouseLeave={e => e.currentTarget.style.background = '#1c1f2b'}
            >
              <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                <div style={{
                  width: 48, height: 48, borderRadius: '8px', background: '#171924',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon name="lock" style={{ color: '#81ecff', fontSize: '24px' }} />
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '1.125rem', marginBottom: '4px' }}>Change Password</h3>
                  <p style={{ color: '#aaaab7', fontSize: '14px' }}>Update your security credentials and active sessions.</p>
                </div>
              </div>
              <Icon name="chevron_right" style={{ color: '#737580', fontSize: '24px', transition: 'all 0.3s' }} />
            </div>

            {/* Billings Card — Expanded */}
            <div
              data-section="Billing" ref={el => sectionRefs.current['Billing'] = el}
              style={{
                background: '#1c1f2b', borderRadius: '12px', padding: '28px 32px',
                boxShadow: '0 0 40px 0 rgba(129,236,255,0.08)',
                display: 'flex', flexDirection: 'column', gap: '20px',
              }}
            >
              {/* Top row: icon + info + badge */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: '8px', background: '#171924',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Icon name="credit_card" style={{ color: '#81ecff', fontSize: '24px' }} />
                  </div>
                  <div>
                    <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '1.125rem', marginBottom: '4px' }}>Billings</h3>
                    <p style={{ color: '#aaaab7', fontSize: '14px' }}>Manage subscriptions, view invoices, and payment methods.</p>
                  </div>
                </div>
                <span style={{
                  padding: '4px 12px', borderRadius: '9999px',
                  background: 'rgba(129,236,255,0.1)', color: '#81ecff',
                  fontFamily: "'Manrope', sans-serif", fontSize: '10px',
                  textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.1em',
                  flexShrink: 0,
                }}>Pro Active</span>
              </div>

              {/* Credits + Buy Button row */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: '#171924', borderRadius: '10px', padding: '16px 20px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="toll" style={{ color: '#a68cff', fontSize: '22px' }} />
                  <div>
                    <div style={{ fontFamily: "'Manrope', sans-serif", fontSize: '11px', color: '#737580', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700, marginBottom: '2px' }}>Remaining Credits</div>
                    <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.5rem', fontWeight: 700, color: '#f0f0fd' }}>
                      {credits !== null ? credits : <span style={{ color: '#464752' }}>—</span>}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => navigate('/pricing')}
                  style={{
                    background: 'linear-gradient(45deg, #81ecff, #a68cff)',
                    color: '#003840', fontFamily: "'Space Grotesk', sans-serif",
                    fontWeight: 700, fontSize: '14px',
                    padding: '10px 24px', borderRadius: '8px', border: 'none',
                    cursor: 'pointer', transition: 'all 0.2s',
                    display: 'flex', alignItems: 'center', gap: '8px',
                    boxShadow: '0 4px 16px rgba(129,236,255,0.2)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.05)'; e.currentTarget.style.filter = 'brightness(1.1)'; }}
                  onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.filter = 'brightness(1)'; }}
                >
                  <Icon name="shopping_cart" style={{ fontSize: '18px' }} />
                  Buy Credits
                </button>
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* ===== FOOTER ===== */}
      <footer style={{
        background: '#11131d', padding: '48px 32px', marginTop: '80px',
        borderTop: '1px solid rgba(70,71,82,0.1)',
      }}>
        <div style={{
          maxWidth: '1920px', margin: '0 auto',
          display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '32px',
        }}>
          <div>
            <span style={{
              fontFamily: "'Space Grotesk', sans-serif", fontSize: '1.25rem',
              fontWeight: 700, letterSpacing: '-0.05em', color: '#00E5FF',
              display: 'block', marginBottom: '8px',
            }}>YOUTOMIZE</span>
            <p style={{ color: '#aaaab7', fontSize: '14px' }}>Empowering creators with cinematic intelligence.</p>
          </div>
          <div style={{ display: 'flex', gap: '32px' }}>
            {['Terms of Service', 'Privacy Policy', 'Support', 'API Docs'].map(item => (
              <a key={item} href="#" style={{
                color: '#aaaab7', fontFamily: "'Manrope', sans-serif", fontSize: '14px',
                textDecoration: 'none', transition: 'color 0.3s',
              }}
                onMouseEnter={e => e.target.style.color = '#81ecff'}
                onMouseLeave={e => e.target.style.color = '#aaaab7'}
              >{item}</a>
            ))}
          </div>
        </div>
        <div style={{
          maxWidth: '1920px', margin: '48px auto 0', textAlign: 'center',
          fontSize: '10px', color: '#737580', textTransform: 'uppercase',
          letterSpacing: '0.2em', fontWeight: 700,
        }}>
          © 2024 YOUTOMIZE Studio — All Rights Reserved
        </div>
      </footer>

      {/* Responsive grid */}
      <style>{`
        @media (min-width: 768px) {
          .md-grid-settings {
            grid-template-columns: 200px 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};

export default SettingsPage;
