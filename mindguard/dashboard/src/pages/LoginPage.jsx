import React, { useState, useEffect, useRef } from 'react';
import './LoginPage.css';

// ── ICONS ─────────────────────────────────────────────────────
const Icons = {
  Brain: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2a2.5 2.5 0 0 1 5 0"/>
      <path d="M4 8a4 4 0 0 1 7-2.65"/><path d="M20 8a4 4 0 0 0-7-2.65"/>
      <path d="M3.5 13a4 4 0 0 0 7 2.65"/><path d="M20.5 13a4 4 0 0 1-7 2.65"/>
      <path d="M9 15.4V22"/><path d="M15 15.4V22"/><path d="M9 22h6"/>
      <circle cx="12" cy="13" r="2"/>
    </svg>
  ),
  Mail: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  ),
  Lock: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  ),
  Eye: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  EyeOff: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  ),
  Alert: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  ),
  Pulse: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Shield: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  ArrowRight: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
    </svg>
  ),
};

// ── CANVAS NEURAL NET ANIMATION ───────────────────────────────
const NeuralCanvas = () => {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let raf;
    const nodes = [];
    const N = 28;

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < N; i++) {
      nodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 2 + 1,
        pulse: Math.random() * Math.PI * 2,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      nodes.forEach(n => {
        n.x += n.vx; n.y += n.vy; n.pulse += 0.025;
        if (n.x < 0 || n.x > canvas.width)  n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
      });
      // edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const d  = Math.sqrt(dx*dx + dy*dy);
          if (d < 130) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(0,229,255,${0.12 * (1 - d/130)})`;
            ctx.lineWidth = 0.6;
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }
      // nodes
      nodes.forEach(n => {
        const glow = Math.sin(n.pulse) * 0.4 + 0.6;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r * glow, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0,229,255,${0.5 * glow})`;
        ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
  }, []);
  return <canvas ref={canvasRef} className="neural-canvas" />;
};

// ── STAT TICKER ────────────────────────────────────────────────
const STATS = [
  { val: '1.5s',  label: 'Detection cycle' },
  { val: '4',     label: 'Sensor streams'  },
  { val: '95%',   label: 'Accuracy rate'   },
  { val: '100%',  label: 'Local & private' },
];

// ═════════════════════════════════════════════════════════════
// LOGIN PAGE
// Place at: dashboard/src/pages/LoginPage.jsx
// ═════════════════════════════════════════════════════════════
const LoginPage = ({ onLogin, onGoToSignUp }) => {
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const [focused,  setFocused]  = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim())    { setError('Email address is required.');  return; }
    if (!password.trim()) { setError('Password is required.');        return; }
    setLoading(true);
    try {
      await new Promise(r => setTimeout(r, 850));
      const stored = JSON.parse(localStorage.getItem('mg_registered_users') || '[]');
      const found  = stored.find(u => u.email === email.trim().toLowerCase() && u.password === password);
      if (!found) throw new Error('Incorrect email or password. Please try again.');
      const userObj = { ...found, loginAt: Date.now() };
      localStorage.setItem('mg_user', JSON.stringify(userObj));
      onLogin(userObj);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="lp-root">
      {/* ── ANIMATED LEFT PANEL ───────────────────────────── */}
      <div className="lp-left">
        <NeuralCanvas />

        <div className="lp-left-content">
          {/* Brand */}
          <div className="lp-brand">
            <div className="lp-brand-icon">
              <Icons.Brain />
            </div>
            <div className="lp-brand-text">
              <span className="lp-brand-name">MindGuard<span>AI</span></span>
              <span className="lp-brand-tagline">Cognitive Load Prevention</span>
            </div>
          </div>

          {/* Headline */}
          <div className="lp-headline">
            <div className="lp-headline-label">Real-time monitoring</div>
            <h1>
              Your brain<br />
              <span className="lp-headline-accent">deserves</span><br />
              protection.
            </h1>
            <p className="lp-headline-body">
              MindGuard watches your eyes, keystrokes, voice and screen
              to detect cognitive fatigue before it affects your work.
            </p>
          </div>

          {/* Stats row */}
          <div className="lp-stats">
            {STATS.map(s => (
              <div className="lp-stat" key={s.label}>
                <div className="lp-stat-val">{s.val}</div>
                <div className="lp-stat-label">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Trust badges */}
          <div className="lp-badges">
            <div className="lp-badge"><Icons.Shield /><span>Local processing only</span></div>
            <div className="lp-badge"><Icons.Pulse /><span>Live fatigue scoring</span></div>
          </div>
        </div>
      </div>

      {/* ── RIGHT FORM PANEL ──────────────────────────────── */}
      <div className="lp-right">
        <div className="lp-form-box">

          {/* Header */}
          <div className="lp-form-header">
            <div className="lp-form-eyebrow">Welcome back</div>
            <h2 className="lp-form-title">Sign in to your account</h2>
            <p className="lp-form-sub">Monitor your cognitive health in real time.</p>
          </div>

          {/* Form */}
          <form className="lp-form" onSubmit={handleSubmit} noValidate>

            {/* Email field */}
            <div className={`lp-field${focused === 'email' ? ' lp-field-focused' : ''}${error && !password ? ' lp-field-error' : ''}`}>
              <label className="lp-label">Email address</label>
              <div className="lp-input-wrap">
                <span className="lp-input-icon"><Icons.Mail /></span>
                <input
                  className="lp-input"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={e => { setEmail(e.target.value); setError(''); }}
                  onFocus={() => setFocused('email')}
                  onBlur={() => setFocused('')}
                  autoComplete="email"
                  autoFocus
                />
              </div>
            </div>

            {/* Password field */}
            <div className={`lp-field${focused === 'password' ? ' lp-field-focused' : ''}${error ? ' lp-field-error' : ''}`}>
              <div className="lp-label-row">
                <label className="lp-label">Password</label>
                <button type="button" className="lp-forgot">Forgot password?</button>
              </div>
              <div className="lp-input-wrap">
                <span className="lp-input-icon"><Icons.Lock /></span>
                <input
                  className="lp-input"
                  type={showPw ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={e => { setPassword(e.target.value); setError(''); }}
                  onFocus={() => setFocused('password')}
                  onBlur={() => setFocused('')}
                  autoComplete="current-password"
                />
                <button type="button" className="lp-eye" onClick={() => setShowPw(!showPw)}>
                  {showPw ? <Icons.EyeOff /> : <Icons.Eye />}
                </button>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="lp-error">
                <Icons.Alert />
                <span>{error}</span>
              </div>
            )}

            {/* Submit */}
            <button type="submit" className={`lp-submit${loading ? ' lp-loading' : ''}`} disabled={loading}>
              <span className="lp-submit-text">
                {loading ? 'Signing in…' : 'Sign in'}
              </span>
              {loading
                ? <span className="lp-spinner" />
                : <span className="lp-submit-arrow"><Icons.ArrowRight /></span>
              }
            </button>

          </form>

          {/* Divider */}
          <div className="lp-divider"><span>or continue with</span></div>

          {/* Social-style demo login */}
          <div className="lp-demo-row">
            {[
              { name: 'Dr. Priya Sharma',  role: 'Researcher',  email: 'researcher@mindguard.ai', pw: 'demo123', initial: 'P', color: '#a78bfa' },
              { name: 'Arjun Reddy',       role: 'Engineer',    email: 'engineer@mindguard.ai',   pw: 'demo123', initial: 'A', color: '#00e5ff' },
              { name: 'Sneha Patel',       role: 'Analyst',     email: 'analyst@mindguard.ai',    pw: 'demo123', initial: 'S', color: '#00ff9d' },
            ].map(a => (
              <button
                key={a.email}
                className="lp-demo-btn"
                onClick={() => { setEmail(a.email); setPassword(a.pw); }}
                title={`${a.name} · ${a.role}`}
              >
                <div className="lp-demo-avatar" style={{ background: `linear-gradient(135deg, ${a.color}40, ${a.color}20)`, borderColor: `${a.color}50`, color: a.color }}>
                  {a.initial}
                </div>
                <div className="lp-demo-info">
                  <div className="lp-demo-name">{a.name}</div>
                  <div className="lp-demo-role">{a.role}</div>
                </div>
              </button>
            ))}
          </div>

          {/* Switch to signup */}
          <p className="lp-switch">
            New to MindGuard?{' '}
            <button className="lp-switch-link" onClick={onGoToSignUp}>
              Create a free account
            </button>
          </p>

        </div>
      </div>
    </div>
  );
};

export default LoginPage;