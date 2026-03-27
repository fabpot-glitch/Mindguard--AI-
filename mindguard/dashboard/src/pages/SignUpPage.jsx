import React, { useState, useEffect, useCallback, useMemo } from 'react';
import './SignUpPage.css';

// ════════════════════════════════════════════════════════════════
// ICONS
// ════════════════════════════════════════════════════════════════
const Ic = {
  Brain: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M9.5 2a2.5 2.5 0 0 1 5 0"/>
      <path d="M4 8a4 4 0 0 1 7-2.65"/><path d="M20 8a4 4 0 0 0-7-2.65"/>
      <path d="M3.5 13a4 4 0 0 0 7 2.65"/><path d="M20.5 13a4 4 0 0 1-7 2.65"/>
      <path d="M9 15.4V22"/><path d="M15 15.4V22"/><path d="M9 22h6"/>
      <circle cx="12" cy="13" r="2"/>
    </svg>
  ),
  User: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  ),
  Mail: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
      <polyline points="22,6 12,13 2,6"/>
    </svg>
  ),
  Lock: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  ),
  Eye: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  EyeOff: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  ),
  Building: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
  Alert: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  ),
  ChevronLeft: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="15 18 9 12 15 6"/>
    </svg>
  ),
  Sparkle: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>
      <path d="M5 3l.9 2.1L8 6l-2.1.9L5 9l-.9-2.1L2 6l2.1-.9z"/>
      <path d="M19 17l.9 2.1L22 20l-2.1.9L19 23l-.9-2.1L16 20l2.1-.9z"/>
    </svg>
  ),
  Shield: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  Zap: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  ),
};

// ════════════════════════════════════════════════════════════════
// SIMPLE STATIC BACKGROUND (No animation glitches)
// ════════════════════════════════════════════════════════════════
const StaticBackground = () => {
  return (
    <div className="sp-static-bg">
      <div className="sp-gradient-1"></div>
      <div className="sp-gradient-2"></div>
      <div className="sp-gradient-3"></div>
    </div>
  );
};

// ════════════════════════════════════════════════════════════════
// CONSTANTS
// ════════════════════════════════════════════════════════════════
const ROLES = [
  { value: 'Software Engineer', icon: '💻', color: '#00e5ff', sub: 'Development & coding' },
  { value: 'Researcher', icon: '🔬', color: '#a78bfa', sub: 'Cognitive sciences' },
  { value: 'Data Analyst', icon: '📊', color: '#00ff9d', sub: 'Analytics & data' },
  { value: 'Designer', icon: '🎨', color: '#ff9838', sub: 'UX / visual design' },
  { value: 'Student', icon: '🎓', color: '#ffe566', sub: 'Academic study' },
  { value: 'Other', icon: '👤', color: '#6a8a9e', sub: 'General user' },
];

const STEPS = [
  { num: 1, label: 'Identity', desc: 'Your personal info' },
  { num: 2, label: 'Role', desc: 'Your work context' },
  { num: 3, label: 'Security', desc: 'Set your password' },
];

const getPasswordStrength = (pw) => {
  if (!pw) return { score: 0, label: '', color: '#1e3040', bars: 0 };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { score, label: 'Too weak', color: '#ff3b5c', bars: 1 };
  if (score === 2) return { score, label: 'Weak', color: '#ff9838', bars: 2 };
  if (score === 3) return { score, label: 'Fair', color: '#ffe566', bars: 3 };
  if (score === 4) return { score, label: 'Strong', color: '#00e5ff', bars: 4 };
  return { score, label: 'Very strong', color: '#00ff9d', bars: 5 };
};

// ════════════════════════════════════════════════════════════════
// STEP COMPONENTS
// ════════════════════════════════════════════════════════════════
const StepOne = ({ form, setForm, onNext, error, setError }) => {
  const [focused, setFocused] = useState('');

  const validate = useCallback(() => {
    if (!form.firstName.trim()) return 'First name is required.';
    if (!form.lastName.trim()) return 'Last name is required.';
    if (!form.email.trim()) return 'Email address is required.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      return 'Please enter a valid email address.';
    return null;
  }, [form.firstName, form.lastName, form.email]);

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    const err = validate();
    if (err) {
      setError(err);
      return;
    }
    setError('');
    onNext();
  }, [validate, onNext, setError]);

  const handleChange = useCallback((field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (error) setError('');
  }, [setForm, error, setError]);

  return (
    <form className="sp-step-form" onSubmit={handleSubmit}>
      <div className="sp-step-intro">
        <div className="sp-step-intro-icon"><Ic.User /></div>
        <div>
          <div className="sp-step-intro-title">Personal information</div>
          <div className="sp-step-intro-sub">Tell us who you are so we can personalise your experience.</div>
        </div>
      </div>

      <div className="sp-field-row">
        <div className={`sp-field${focused === 'first' ? ' sp-field--focused' : ''}`}>
          <label className="sp-label">First name</label>
          <div className="sp-input-wrap">
            <span className="sp-input-icon"><Ic.User /></span>
            <input
              className="sp-input"
              type="text"
              placeholder="Arjun"
              value={form.firstName}
              onChange={(e) => handleChange('firstName', e.target.value)}
              onFocus={() => setFocused('first')}
              onBlur={() => setFocused('')}
              autoComplete="given-name"
            />
          </div>
        </div>
        
        <div className={`sp-field${focused === 'last' ? ' sp-field--focused' : ''}`}>
          <label className="sp-label">Last name</label>
          <div className="sp-input-wrap">
            <span className="sp-input-icon"><Ic.User /></span>
            <input
              className="sp-input"
              type="text"
              placeholder="Reddy"
              value={form.lastName}
              onChange={(e) => handleChange('lastName', e.target.value)}
              onFocus={() => setFocused('last')}
              onBlur={() => setFocused('')}
              autoComplete="family-name"
            />
          </div>
        </div>
      </div>
      
      <div className={`sp-field${focused === 'email' ? ' sp-field--focused' : ''}`}>
        <label className="sp-label">Email address</label>
        <div className="sp-input-wrap">
          <span className="sp-input-icon"><Ic.Mail /></span>
          <input
            className="sp-input"
            type="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={(e) => handleChange('email', e.target.value)}
            onFocus={() => setFocused('email')}
            onBlur={() => setFocused('')}
            autoComplete="email"
          />
        </div>
      </div>

      {error && (
        <div className="sp-error">
          <Ic.Alert />
          <span>{error}</span>
        </div>
      )}

      <button type="submit" className="sp-btn-primary">
        Continue to Role <span className="sp-btn-step">2 of 3</span>
      </button>
    </form>
  );
};

const StepTwo = ({ form, setForm, onNext, onBack, error, setError }) => {
  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    if (!form.role) {
      setError('Please select your role to continue.');
      return;
    }
    setError('');
    onNext();
  }, [form.role, onNext, setError]);

  const handleRoleSelect = useCallback((roleValue) => {
    setForm(prev => ({ ...prev, role: roleValue }));
    if (error) setError('');
  }, [setForm, error, setError]);

  const handleDepartmentChange = useCallback((e) => {
    setForm(prev => ({ ...prev, department: e.target.value }));
  }, [setForm]);

  return (
    <form className="sp-step-form" onSubmit={handleSubmit}>
      <div className="sp-step-intro">
        <div className="sp-step-intro-icon"><Ic.Sparkle /></div>
        <div>
          <div className="sp-step-intro-title">Your work context</div>
          <div className="sp-step-intro-sub">MindGuard tailors interventions based on your role and workflow.</div>
        </div>
      </div>

      <div className="sp-field">
        <label className="sp-label">Select your role</label>
        <div className="sp-role-grid">
          {ROLES.map(r => (
            <button
              key={r.value}
              type="button"
              className={`sp-role-card${form.role === r.value ? ' sp-role-card--selected' : ''}`}
              style={form.role === r.value ? { '--role-color': r.color } : {}}
              onClick={() => handleRoleSelect(r.value)}
            >
              <span className="sp-role-icon">{r.icon}</span>
              <span className="sp-role-name">{r.value}</span>
              <span className="sp-role-sub">{r.sub}</span>
              {form.role === r.value && (
                <span className="sp-role-check"><Ic.Check /></span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="sp-field">
        <label className="sp-label">Department <span className="sp-optional">(optional)</span></label>
        <div className="sp-input-wrap">
          <span className="sp-input-icon"><Ic.Building /></span>
          <input
            className="sp-input"
            type="text"
            placeholder="e.g. Engineering, Research, Design…"
            value={form.department}
            onChange={handleDepartmentChange}
          />
        </div>
      </div>

      {error && (
        <div className="sp-error">
          <Ic.Alert />
          <span>{error}</span>
        </div>
      )}

      <div className="sp-btn-row">
        <button type="button" className="sp-btn-back" onClick={onBack}>
          <Ic.ChevronLeft /> Back
        </button>
        <button type="submit" className="sp-btn-primary sp-btn-primary--grow">
          Continue to Security <span className="sp-btn-step">3 of 3</span>
        </button>
      </div>
    </form>
  );
};

const StepThree = ({ form, setForm, onSubmit, onBack, error, loading, success }) => {
  const [focused, setFocused] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [agreed, setAgreed] = useState(false);
  
  const strength = useMemo(() => getPasswordStrength(form.password), [form.password]);
  const pwMatch = form.password && form.confirmPassword && form.password === form.confirmPassword;
  const pwNoMatch = form.confirmPassword && form.password !== form.confirmPassword;

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    if (!agreed) return;
    onSubmit();
  }, [agreed, onSubmit]);

  const handlePasswordChange = useCallback((e) => {
    setForm(prev => ({ ...prev, password: e.target.value }));
  }, [setForm]);

  const handleConfirmPasswordChange = useCallback((e) => {
    setForm(prev => ({ ...prev, confirmPassword: e.target.value }));
  }, [setForm]);

  return (
    <form className="sp-step-form" onSubmit={handleSubmit}>
      <div className="sp-step-intro">
        <div className="sp-step-intro-icon"><Ic.Shield /></div>
        <div>
          <div className="sp-step-intro-title">Secure your account</div>
          <div className="sp-step-intro-sub">Choose a strong password to protect your cognitive data.</div>
        </div>
      </div>

      <div className={`sp-field${focused === 'pw' ? ' sp-field--focused' : ''}`}>
        <label className="sp-label">Password</label>
        <div className="sp-input-wrap">
          <span className="sp-input-icon"><Ic.Lock /></span>
          <input
            className="sp-input"
            type={showPw ? 'text' : 'password'}
            placeholder="Min. 8 characters"
            value={form.password}
            onChange={handlePasswordChange}
            onFocus={() => setFocused('pw')}
            onBlur={() => setFocused('')}
            autoComplete="new-password"
          />
          <button type="button" className="sp-eye" onClick={() => setShowPw(p => !p)}>
            {showPw ? <Ic.EyeOff /> : <Ic.Eye />}
          </button>
        </div>

        {form.password && (
          <div className="sp-strength-wrap">
            <div className="sp-strength-bars">
              {[1, 2, 3, 4, 5].map(i => (
                <div
                  key={i}
                  className="sp-strength-bar"
                  style={{ background: i <= strength.bars ? strength.color : 'rgba(255,255,255,0.07)' }}
                />
              ))}
            </div>
            <span className="sp-strength-label" style={{ color: strength.color }}>
              {strength.label}
            </span>
          </div>
        )}

        <div className="sp-pw-rules">
          {[
            { label: '8+ characters', pass: form.password.length >= 8 },
            { label: 'Uppercase letter', pass: /[A-Z]/.test(form.password) },
            { label: 'Number', pass: /[0-9]/.test(form.password) },
            { label: 'Special character', pass: /[^A-Za-z0-9]/.test(form.password) },
          ].map(r => (
            <div key={r.label} className={`sp-pw-rule${r.pass ? ' sp-pw-rule--pass' : ''}`}>
              <span className="sp-pw-rule-dot" />
              {r.label}
            </div>
          ))}
        </div>
      </div>

      <div className={`sp-field${focused === 'confirm' ? ' sp-field--focused' : ''}${pwNoMatch ? ' sp-field--error' : ''}`}>
        <label className="sp-label">Confirm password</label>
        <div className="sp-input-wrap">
          <span className="sp-input-icon" style={{ color: pwMatch ? '#00ff9d' : undefined }}>
            {pwMatch ? <Ic.Check /> : <Ic.Lock />}
          </span>
          <input
            className="sp-input"
            type={showConfirm ? 'text' : 'password'}
            placeholder="Repeat your password"
            value={form.confirmPassword}
            onChange={handleConfirmPasswordChange}
            onFocus={() => setFocused('confirm')}
            onBlur={() => setFocused('')}
            autoComplete="new-password"
          />
          <button type="button" className="sp-eye" onClick={() => setShowConfirm(p => !p)}>
            {showConfirm ? <Ic.EyeOff /> : <Ic.Eye />}
          </button>
        </div>
        {pwNoMatch && <div className="sp-field-msg sp-field-msg--error">Passwords don't match</div>}
        {pwMatch && form.confirmPassword && <div className="sp-field-msg sp-field-msg--ok">Passwords match ✓</div>}
      </div>

      <div className="sp-terms" onClick={() => setAgreed(a => !a)}>
        <div className={`sp-checkbox${agreed ? ' sp-checkbox--checked' : ''}`}>
          {agreed && <Ic.Check />}
        </div>
        <p className="sp-terms-text">
          I agree to the <a href="#terms" onClick={e => e.stopPropagation()}>Terms of Service</a> and{' '}
          <a href="#privacy" onClick={e => e.stopPropagation()}>Privacy Policy</a>.
          All data is processed locally on your device.
        </p>
      </div>

      {error && (
        <div className="sp-error">
          <Ic.Alert />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="sp-success">
          <Ic.Check />
          <span>Account created! Signing you in…</span>
        </div>
      )}

      <div className="sp-btn-row">
        <button type="button" className="sp-btn-back" onClick={onBack} disabled={loading}>
          <Ic.ChevronLeft /> Back
        </button>
        <button
          type="submit"
          className={`sp-btn-primary sp-btn-primary--grow${!agreed ? ' sp-btn-primary--dim' : ''}`}
          disabled={loading || success || !agreed}
        >
          {loading ? <span className="sp-spinner" /> : null}
          {loading ? 'Creating account…' : success ? 'Redirecting…' : 'Create Account'}
        </button>
      </div>
    </form>
  );
};

// ════════════════════════════════════════════════════════════════
// MAIN SIGNUP PAGE
// ════════════════════════════════════════════════════════════════
const SignUpPage = ({ onSignUp, onGoToLogin }) => {
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    role: '',
    department: '',
    password: '',
    confirmPassword: '',
  });

  const handleSubmit = useCallback(async () => {
    setError('');
    
    if (!form.password || form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (getPasswordStrength(form.password).score < 2) {
      setError('Please choose a stronger password.');
      return;
    }

    setLoading(true);
    
    try {
      await new Promise(resolve => setTimeout(resolve, 1100));
      
      const existing = JSON.parse(localStorage.getItem('mg_registered_users') || '[]');
      const emailKey = form.email.trim().toLowerCase();
      
      if (existing.find(u => u.email === emailKey)) {
        throw new Error('An account with this email already exists.');
      }

      const newUser = {
        name: `${form.firstName.trim()} ${form.lastName.trim()}`,
        email: emailKey,
        password: form.password,
        role: form.role,
        department: form.department || 'General',
        dept: form.department || 'General',
        createdAt: Date.now(),
      };
      
      localStorage.setItem('mg_registered_users', JSON.stringify([...existing, newUser]));
      setSuccess(true);
      
      await new Promise(resolve => setTimeout(resolve, 1400));
      
      const userObj = { ...newUser, loginAt: Date.now() };
      localStorage.setItem('mg_user', JSON.stringify(userObj));
      onSignUp(userObj);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, [form, onSignUp]);

  const progressPct = ((step - 1) / (STEPS.length - 1)) * 100;
  const previewName = [form.firstName, form.lastName].filter(Boolean).join(' ');

  const handleNextStep = useCallback(() => {
    setStep(prev => prev + 1);
    setError('');
  }, []);

  const handlePrevStep = useCallback(() => {
    setStep(prev => prev - 1);
    setError('');
  }, []);

  return (
    <div className="sp-root">
      <StaticBackground />

      <div className="sp-left">
        <div className="sp-brand">
          <div className="sp-brand-icon"><Ic.Brain /></div>
          <div className="sp-brand-text">
            <span className="sp-brand-name">MindGuard<span>AI</span></span>
            <span className="sp-brand-tagline">Cognitive Load Prevention</span>
          </div>
        </div>

        <div className="sp-progress-section">
          <div className="sp-progress-label">Account setup</div>
          <div className="sp-progress-track">
            <div className="sp-progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <div className="sp-steps-list">
            {STEPS.map(s => (
              <div key={s.num} className={`sp-step-item${step === s.num ? ' sp-step-item--active' : ''}${step > s.num ? ' sp-step-item--done' : ''}`}>
                <div className="sp-step-num">
                  {step > s.num ? <Ic.Check /> : s.num}
                </div>
                <div className="sp-step-meta">
                  <div className="sp-step-meta-title">{s.label}</div>
                  <div className="sp-step-meta-desc">{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={`sp-preview-card${previewName ? ' sp-preview-card--visible' : ''}`}>
          <div className="sp-preview-label">Your account preview</div>
          <div className="sp-preview-user">
            <div className="sp-preview-avatar">
              {previewName ? previewName.charAt(0).toUpperCase() : '?'}
            </div>
            <div className="sp-preview-info">
              <div className="sp-preview-name">{previewName || 'Your name'}</div>
              <div className="sp-preview-role">{form.role || 'Role not selected'}</div>
              <div className="sp-preview-email">{form.email || 'email@example.com'}</div>
            </div>
          </div>
        </div>

        <div className="sp-benefits">
          {[
            { icon: <Ic.Zap />, color: '#00e5ff', text: 'Real-time fatigue scores every 1.5 seconds' },
            { icon: <Ic.Shield />, color: '#00ff9d', text: '100% private — all processing stays local' },
            { icon: <Ic.Brain />, color: '#a78bfa', text: 'AI learns your personal cognitive baseline' },
          ].map((b, i) => (
            <div className="sp-benefit" key={i}>
              <div className="sp-benefit-icon" style={{ color: b.color, borderColor: `${b.color}30`, background: `${b.color}10` }}>
                {b.icon}
              </div>
              <span className="sp-benefit-text">{b.text}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="sp-right">
        <div className="sp-form-box">
          <div className="sp-form-header">
            <div className="sp-form-eyebrow">Step {step} of {STEPS.length}</div>
            <h2 className="sp-form-title">Create your account</h2>
            <p className="sp-form-sub">Join MindGuard and start protecting your cognitive performance.</p>
          </div>

          <div className="sp-tab-row">
            {STEPS.map(s => (
              <div
                key={s.num}
                className={`sp-tab${step === s.num ? ' sp-tab--active' : ''}${step > s.num ? ' sp-tab--done' : ''}`}
              >
                <div className="sp-tab-dot">
                  {step > s.num ? <Ic.Check /> : s.num}
                </div>
                <span className="sp-tab-label">{s.label}</span>
              </div>
            ))}
          </div>

          <div className="sp-step-content">
            {step === 1 && (
              <StepOne
                form={form}
                setForm={setForm}
                onNext={handleNextStep}
                error={error}
                setError={setError}
              />
            )}
            {step === 2 && (
              <StepTwo
                form={form}
                setForm={setForm}
                onNext={handleNextStep}
                onBack={handlePrevStep}
                error={error}
                setError={setError}
              />
            )}
            {step === 3 && (
              <StepThree
                form={form}
                setForm={setForm}
                onSubmit={handleSubmit}
                onBack={handlePrevStep}
                error={error}
                loading={loading}
                success={success}
              />
            )}
          </div>

          <p className="sp-switch">
            Already have an account?{' '}
            <button className="sp-switch-link" onClick={onGoToLogin}>Sign in</button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignUpPage;