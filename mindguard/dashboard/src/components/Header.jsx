import React, { useState, useEffect, useRef, useCallback } from 'react';
import './Header.css';

// ── ICONS ─────────────────────────────────────────────────────────────────────
const I = {
  Brain: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2a2.5 2.5 0 0 1 5 0"/>
      <path d="M4 8a4 4 0 0 1 7-2.65"/><path d="M20 8a4 4 0 0 0-7-2.65"/>
      <path d="M3.5 13a4 4 0 0 0 7 2.65"/><path d="M20.5 13a4 4 0 0 1-7 2.65"/>
      <path d="M9 15.4V22"/><path d="M15 15.4V22"/><path d="M9 22h6"/>
      <circle cx="12" cy="13" r="2"/>
    </svg>
  ),
  Clock: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 15.5"/>
    </svg>
  ),
  Play:  () => <svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6,4 20,12 6,20"/></svg>,
  Pause: () => <svg viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="4" width="4" height="16" rx="1"/><rect x="15" y="4" width="4" height="16" rx="1"/></svg>,
  Reset: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>
    </svg>
  ),
  Bell: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>
  ),
  Settings: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  ),
  BarChart: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  ),
  Logout: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
      <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
    </svg>
  ),
  Eye: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
    </svg>
  ),
  EyeOff: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  ),
  User: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  ),
  Lock: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  ),
  X: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
  ChevronDown: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  ),
  Alert: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  ),
  Info: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>
  ),
  Trash: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
    </svg>
  ),
  Monitor: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
  ),
  Mic: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  ),
  Wifi: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/>
      <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>
    </svg>
  ),
  Sun: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  ),
  Download: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  ),
};

// ── HELPERS ───────────────────────────────────────────────────────────────────
const pad = (n) => String(Math.max(0, Math.floor(n))).padStart(2, '0');
const fmtClock   = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
const fmtDate    = (d) => d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
const fmtSession = (ms) => {
  if (!ms || ms < 0) return '00:00';
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
};
const timeAgo = (ts) => {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
};

const RISK_LEVELS = {
  fresh:    { cls: 'risk-fresh',    label: 'OPTIMAL'  },
  mild:     { cls: 'risk-mild',     label: 'MILD'     },
  moderate: { cls: 'risk-moderate', label: 'MODERATE' },
  critical: { cls: 'risk-critical', label: 'CRITICAL' },
};
const CONN_STATES = {
  live:         { cls: 'conn-live',         label: 'LIVE'      },
  simulated:    { cls: 'conn-simulated',    label: 'SIMULATED' },
  offline:      { cls: 'conn-offline',      label: 'OFFLINE'   },
  reconnecting: { cls: 'conn-reconnecting', label: 'RECONNECTING' },
};

// ── DEFAULT SETTINGS ──────────────────────────────────────────────────────────
const DEFAULT_SETTINGS = {
  notifications: { critical: true,  moderate: true,  mild: false, hydration: true,  sound: true,  breakReminder: true },
  sensors:       { eye: true,       keyboard: true,  voice: true, screen: true                                         },
  thresholds:    { mildAt: 35,      moderateAt: 55,  criticalAt: 75                                                     },
  appearance:    { theme: 'dark',   reducedMotion: false,         compactMode: false                                    },
  session:       { autoBreakAt: 90, breakDuration: 10,            showPredictions: true                                 },
  data:          { retainDays: 30,  exportFormat: 'csv',          anonymize: false                                      },
};

// ── NOTIFICATION SOUND ────────────────────────────────────────────────────────
const playNotificationSound = () => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.3);
  } catch (err) {
    console.warn('Could not play notification sound:', err);
  }
};

// ══════════════════════════════════════════════════════════════════════════════
// NOTIFICATIONS PANEL
// ══════════════════════════════════════════════════════════════════════════════
const NotificationsPanel = ({ alerts, settings, onDismiss, onDismissAll, onToggleSetting, onClose }) => {
  const [activeFilter, setActiveFilter] = useState('All');
  const unread = alerts.filter(a => !a.seen).length;
  
  const notifColor = (p) => p >= 5 ? '#ff3b5c' : p >= 3 ? '#ff9838' : p >= 2 ? '#ffe566' : '#00e5ff';
  const notifIcon  = (p) => p >= 5 ? '🔴' : p >= 3 ? '🟠' : p >= 2 ? '🟡' : '🔵';
  
  const getSeverity = (priority) => {
    if (priority >= 5) return 'Critical';
    if (priority >= 3) return 'Moderate';
    return 'Info';
  };

  const filteredAlerts = alerts.filter(a => {
    if (activeFilter === 'All') return true;
    return getSeverity(a.priority) === activeFilter;
  });

  const handleDismiss = (id) => {
    if (settings.notifications.sound) playNotificationSound();
    onDismiss(id);
  };

  return (
    <div className="panel notif-panel">
      <div className="panel-header">
        <div className="panel-title">
          <I.Bell />
          Notifications
          {unread > 0 && <span className="panel-badge">{unread} new</span>}
        </div>
        <div className="panel-header-actions">
          {alerts.length > 0 && (
            <button className="panel-text-btn" onClick={onDismissAll}>Clear all</button>
          )}
          <button className="panel-close-btn" onClick={onClose}><I.X /></button>
        </div>
      </div>

      <div className="notif-tabs">
        {['All','Critical','Moderate','Info'].map(t => (
          <button 
            key={t} 
            className={`notif-tab ${activeFilter === t ? 'notif-tab-active' : ''}`}
            onClick={() => setActiveFilter(t)}
          >
            {t}
            {t !== 'All' && (() => {
              const count = alerts.filter(a => getSeverity(a.priority) === t).length;
              return count > 0 ? ` (${count})` : '';
            })()}
          </button>
        ))}
      </div>

      <div className="panel-body">
        {filteredAlerts.length === 0 ? (
          <div className="panel-empty">
            <div className="panel-empty-icon">✓</div>
            <div className="panel-empty-title">All clear</div>
            <div className="panel-empty-sub">
              {activeFilter === 'All' 
                ? 'No notifications right now' 
                : `No ${activeFilter.toLowerCase()} notifications`}
            </div>
          </div>
        ) : (
          <div className="notif-list">
            {filteredAlerts.map(a => (
              <div key={a.id} className={`notif-item${!a.seen ? ' notif-unread' : ''}`}>
                <div className="notif-icon-col">
                  <span className="notif-type-icon">{notifIcon(a.priority)}</span>
                  {!a.seen && <div className="notif-unread-dot" />}
                </div>
                <div className="notif-content">
                  <div className="notif-item-title" style={{ color: notifColor(a.priority) }}>{a.title}</div>
                  <div className="notif-item-msg">{a.message}</div>
                  <div className="notif-item-time">{timeAgo(new Date(a.triggered_at).getTime())}</div>
                </div>
                <button className="notif-dismiss-btn" onClick={() => handleDismiss(a.id)}><I.X /></button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="panel-footer">
        <div className="notif-footer-row">
          {[
            { label: 'Critical alerts', key: 'critical', on: settings.notifications.critical },
            { label: 'Break reminders', key: 'breakReminder', on: settings.notifications.breakReminder },
            { label: 'Sound', key: 'sound', on: settings.notifications.sound },
          ].map(item => (
            <div key={item.key} className="notif-toggle-row">
              <span className="notif-toggle-label">{item.label}</span>
              <button 
                className={`toggle-pill${item.on ? ' on' : ''}`}
                onClick={() => onToggleSetting('notifications', item.key, !item.on)}
              >
                <div className="toggle-thumb" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// SETTINGS PANEL
// ══════════════════════════════════════════════════════════════════════════════
const SettingsPanel = ({ settings, onChange, user, onClose }) => {
  const [tab, setTab] = useState('notifications');
  const [hasChanges, setHasChanges] = useState(false);
  const [showSaveNotice, setShowSaveNotice] = useState(false);
  
  const tabs = [
    { id: 'notifications', label: 'Notifications', icon: '🔔' },
    { id: 'sensors',       label: 'Sensors',        icon: '📡' },
    { id: 'thresholds',    label: 'Thresholds',     icon: '📊' },
    { id: 'session',       label: 'Session',        icon: '⏱' },
    { id: 'appearance',    label: 'Appearance',     icon: '🎨' },
    { id: 'data',          label: 'Data & Privacy', icon: '🔒' },
  ];

  const Toggle = ({ checked, onChange: onCh }) => (
    <button className={`toggle-pill${checked ? ' on' : ''}`} onClick={() => { onCh(!checked); setHasChanges(true); }}>
      <div className="toggle-thumb" />
    </button>
  );

  const Slider = ({ value, min, max, step = 1, onChange: onCh, unit = '' }) => (
    <div className="settings-slider-wrap">
      <input 
        type="range" 
        className="settings-slider" 
        min={min} 
        max={max} 
        step={step} 
        value={value}
        onChange={e => { onCh(Number(e.target.value)); setHasChanges(true); }} 
      />
      <span className="settings-slider-val">{value}{unit}</span>
    </div>
  );

  const Row = ({ label, sub, children }) => (
    <div className="settings-row">
      <div className="settings-row-info">
        <div className="settings-row-label">{label}</div>
        {sub && <div className="settings-row-sub">{sub}</div>}
      </div>
      <div className="settings-row-control">{children}</div>
    </div>
  );

  const Section = ({ title, children }) => (
    <div className="settings-section">
      <div className="settings-section-title">{title}</div>
      {children}
    </div>
  );

  const set = (group, key, val) => {
    onChange({ ...settings, [group]: { ...settings[group], [key]: val } });
    setHasChanges(true);
  };

  const handleSave = () => {
    setShowSaveNotice(true);
    setHasChanges(false);
    setTimeout(() => setShowSaveNotice(false), 2000);
  };

  const handleExportData = () => {
    const dataToExport = {
      settings,
      exportedAt: new Date().toISOString(),
      user: settings.data.anonymize ? { id: user.id } : user,
    };
    
    const dataStr = settings.data.exportFormat === 'json' 
      ? JSON.stringify(dataToExport, null, 2)
      : convertToCSV(dataToExport);
    
    const blob = new Blob([dataStr], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mindguard-settings-${Date.now()}.${settings.data.exportFormat}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const convertToCSV = (data) => {
    let csv = 'Setting,Value\n';
    Object.entries(data.settings).forEach(([group, values]) => {
      Object.entries(values).forEach(([key, value]) => {
        csv += `${group}.${key},${value}\n`;
      });
    });
    return csv;
  };

  return (
    <div className="panel settings-panel">
      <div className="panel-header">
        <div className="panel-title">
          <I.Settings />Settings
          {hasChanges && <span className="panel-badge">Unsaved</span>}
        </div>
        <button className="panel-close-btn" onClick={onClose}><I.X /></button>
      </div>

      {showSaveNotice && (
        <div className="settings-save-notice">
          <I.Check /> Settings saved successfully
        </div>
      )}

      <div className="settings-layout">
        <div className="settings-sidebar">
          {tabs.map(t => (
            <button key={t.id} className={`settings-tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
              <span className="settings-tab-icon">{t.icon}</span>
              <span className="settings-tab-label">{t.label}</span>
            </button>
          ))}
          <div className="settings-user-card">
            <div className="settings-user-avatar">{user?.name?.charAt(0) || '?'}</div>
            <div className="settings-user-info">
              <div className="settings-user-name">{user?.name}</div>
              <div className="settings-user-role">{user?.role}</div>
            </div>
          </div>
        </div>

        <div className="settings-content">
          {tab === 'notifications' && (
            <>
              <Section title="Alert Triggers">
                <Row label="Critical fatigue alerts" sub={`Fire when score exceeds ${settings.thresholds.criticalAt}%`}>
                  <Toggle checked={settings.notifications.critical} onChange={v => set('notifications','critical',v)}/>
                </Row>
                <Row label="Moderate fatigue alerts" sub={`Fire when score exceeds ${settings.thresholds.moderateAt}%`}>
                  <Toggle checked={settings.notifications.moderate} onChange={v => set('notifications','moderate',v)}/>
                </Row>
                <Row label="Mild fatigue alerts" sub={`Fire when score exceeds ${settings.thresholds.mildAt}%`}>
                  <Toggle checked={settings.notifications.mild} onChange={v => set('notifications','mild',v)}/>
                </Row>
                <Row label="Hydration reminders" sub="Every 45 minutes during session">
                  <Toggle checked={settings.notifications.hydration} onChange={v => set('notifications','hydration',v)}/>
                </Row>
                <Row label="Break reminders" sub="Auto-suggest breaks based on predictions">
                  <Toggle checked={settings.notifications.breakReminder} onChange={v => set('notifications','breakReminder',v)}/>
                </Row>
              </Section>
              <Section title="Delivery">
                <Row label="Sound alerts" sub="Play audio when notifications arrive">
                  <Toggle checked={settings.notifications.sound} onChange={v => set('notifications','sound',v)}/>
                </Row>
              </Section>
            </>
          )}

          {tab === 'sensors' && (
            <Section title="Active Sensors">
              {[
                { key:'eye',      label:'Eye Tracking',   sub:'Blink rate, PERCLOS, EAR via webcam',   icon:'👁' },
                { key:'keyboard', label:'Keystroke',      sub:'WPM, IKI, error rate',       icon:'⌨' },
                { key:'voice',    label:'Voice Analysis', sub:'Pitch, energy, stress via microphone',   icon:'🎙' },
                { key:'screen',   label:'Screen Monitor', sub:'Mouse velocity, scroll, clicks', icon:'🖥' },
              ].map(s => (
                <Row key={s.key} label={<span>{s.icon} {s.label}</span>} sub={s.sub}>
                  <Toggle checked={settings.sensors[s.key]} onChange={v => set('sensors', s.key, v)}/>
                </Row>
              ))}
            </Section>
          )}

          {tab === 'thresholds' && (
            <Section title="Fatigue Level Thresholds">
              <Row label="Mild threshold" sub={`Score ≥ ${settings.thresholds.mildAt}% = MILD`}>
                <Slider value={settings.thresholds.mildAt} min={20} max={50} onChange={v => set('thresholds','mildAt',v)} unit="%"/>
              </Row>
              <Row label="Moderate threshold" sub={`Score ≥ ${settings.thresholds.moderateAt}% = MODERATE`}>
                <Slider value={settings.thresholds.moderateAt} min={40} max={70} onChange={v => set('thresholds','moderateAt',v)} unit="%"/>
              </Row>
              <Row label="Critical threshold" sub={`Score ≥ ${settings.thresholds.criticalAt}% = CRITICAL`}>
                <Slider value={settings.thresholds.criticalAt} min={60} max={90} onChange={v => set('thresholds','criticalAt',v)} unit="%"/>
              </Row>
            </Section>
          )}

          {tab === 'session' && (
            <Section title="Session Behaviour">
              <Row label="Auto-break at" sub="Trigger mandatory break after this many minutes">
                <Slider value={settings.session.autoBreakAt} min={30} max={180} step={5} onChange={v => set('session','autoBreakAt',v)} unit=" min"/>
              </Row>
              <Row label="Break duration" sub="Recommended break length">
                <Slider value={settings.session.breakDuration} min={5} max={30} step={5} onChange={v => set('session','breakDuration',v)} unit=" min"/>
              </Row>
              <Row label="Show predictions" sub="Display AI break and error risk predictions">
                <Toggle checked={settings.session.showPredictions} onChange={v => set('session','showPredictions',v)}/>
              </Row>
            </Section>
          )}

          {tab === 'appearance' && (
            <Section title="Display">
              <Row label="Theme" sub="Dashboard color scheme">
                <select 
                  className="settings-select" 
                  value={settings.appearance.theme} 
                  onChange={e => { set('appearance','theme',e.target.value); setHasChanges(true); }}
                >
                  <option value="dark">Dark (default)</option>
                  <option value="darker">Darker</option>
                  <option value="midnight">Midnight</option>
                </select>
              </Row>
              <Row label="Compact mode" sub="Reduce card padding and font sizes">
                <Toggle checked={settings.appearance.compactMode} onChange={v => set('appearance','compactMode',v)}/>
              </Row>
              <Row label="Reduced motion" sub="Disable animations and scanline effects">
                <Toggle checked={settings.appearance.reducedMotion} onChange={v => set('appearance','reducedMotion',v)}/>
              </Row>
            </Section>
          )}

          {tab === 'data' && (
            <>
              <Section title="Data Retention">
                <Row label="Retain session history" sub="How many days to store local history">
                  <Slider value={settings.data.retainDays} min={1} max={90} onChange={v => set('data','retainDays',v)} unit=" days"/>
                </Row>
                <Row label="Export format" sub="Default format when exporting session data">
                  <select 
                    className="settings-select" 
                    value={settings.data.exportFormat} 
                    onChange={e => { set('data','exportFormat',e.target.value); setHasChanges(true); }}
                  >
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                    <option value="xlsx">Excel</option>
                  </select>
                </Row>
              </Section>
              <Section title="Privacy">
                <Row label="Anonymize exports" sub="Strip name and email from exported files">
                  <Toggle checked={settings.data.anonymize} onChange={v => set('data','anonymize',v)}/>
                </Row>
              </Section>
              <Section title="Export Data">
                <button className="settings-export-btn" onClick={handleExportData}>
                  <I.Download /> Export Settings ({settings.data.exportFormat.toUpperCase()})
                </button>
              </Section>
            </>
          )}

          <div className="settings-save-row">
            <button 
              className={`settings-save-btn${hasChanges ? ' has-changes' : ''}`} 
              onClick={handleSave}
              disabled={!hasChanges}
            >
              <I.Check /> {hasChanges ? 'Save Changes' : 'All Saved'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// USER DROPDOWN with Real-Time Stats
// ══════════════════════════════════════════════════════════════════════════════
const UserDropdown = ({ user, realTimeStats, onLogout, onClose }) => (
  <div className="panel user-dropdown">
    <div className="user-drop-top">
      <div className="user-drop-avatar">{user.name.charAt(0)}</div>
      <div>
        <div className="user-drop-name">{user.name}</div>
        <div className="user-drop-role">{user.role} · {user.dept}</div>
        <div className="user-drop-email">{user.email}</div>
      </div>
    </div>
    <div className="user-drop-divider" />
    <div className="user-drop-stats">
      <div className="user-drop-stat">
        <div className="user-drop-stat-val">{realTimeStats.currentFatigue || '0'}%</div>
        <div className="user-drop-stat-label">Current Fatigue</div>
      </div>
      <div className="user-drop-stat">
        <div className="user-drop-stat-val">{realTimeStats.currentFocus || '0'}%</div>
        <div className="user-drop-stat-label">Focus Score</div>
      </div>
      <div className="user-drop-stat">
        <div className="user-drop-stat-val">{realTimeStats.currentStress || '0'}%</div>
        <div className="user-drop-stat-label">Stress Level</div>
      </div>
    </div>
    <div className="user-drop-stats" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
      <div className="user-drop-stat">
        <div className="user-drop-stat-val">{realTimeStats.blinkRate || '0'}/min</div>
        <div className="user-drop-stat-label">Blink Rate</div>
      </div>
      <div className="user-drop-stat">
        <div className="user-drop-stat-val">{realTimeStats.wpm || '0'} WPM</div>
        <div className="user-drop-stat-label">Typing Speed</div>
      </div>
    </div>
    <div className="user-drop-divider" />
    <div className="user-drop-stats" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
      <div className="user-drop-stat">
        <div className="user-drop-stat-val">{realTimeStats.sessionDuration || '00:00'}</div>
        <div className="user-drop-stat-label">Session Time</div>
      </div>
      <div className="user-drop-stat">
        <div className="user-drop-stat-val">{realTimeStats.breaksTaken || '0'}</div>
        <div className="user-drop-stat-label">Breaks Taken</div>
      </div>
    </div>
    <div className="user-drop-divider" />
    <button className="user-drop-logout" onClick={() => { onLogout(); onClose(); }}>
      <I.Logout /> Sign out
    </button>
  </div>
);

// ══════════════════════════════════════════════════════════════════════════════
// MAIN HEADER with Real-Time Data Integration
// ══════════════════════════════════════════════════════════════════════════════
const Header = ({
  user,
  realTimeData = {}, // Real-time data from dashboard
  onDismissAlert,
  onDismissAllAlerts,
  onLogout,
  onSettingsChange,
  onReportClick,
}) => {

  // Extract real-time metrics
  const fatigueScore = realTimeData.fatigue_score || 0;
  const focusScore = realTimeData.focus_score || 0.7;
  const stressLevel = realTimeData.stress_level || 0.3;
  const blinkRate = realTimeData.blink_rate || 14;
  const wpm = realTimeData.wpm || 45;
  const cameraActive = realTimeData.camera_active || false;
  const micActive = realTimeData.mic_active || false;
  const faceDetected = realTimeData.face_detected || false;
  
  // Determine fatigue level based on actual score
  let fatigueLevel = 'fresh';
  if (fatigueScore >= 75) fatigueLevel = 'critical';
  else if (fatigueScore >= 55) fatigueLevel = 'moderate';
  else if (fatigueScore >= 35) fatigueLevel = 'mild';
  
  // Determine connection status based on active sensors
  let wsStatus = 'offline';
  if (cameraActive || micActive) wsStatus = 'live';
  else if (cameraActive || micActive === false) wsStatus = 'simulated';
  
  // ── panels ──
  const [showNotif,    setShowNotif]    = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showUser,     setShowUser]     = useState(false);
  
  // ── settings ──
  const [settings, setSettings] = useState(() => {
    try { 
      const saved = localStorage.getItem('mg_settings');
      return saved ? JSON.parse(saved) : DEFAULT_SETTINGS; 
    } catch { 
      return DEFAULT_SETTINGS; 
    }
  });
  
  // ── timer ──
  const [now, setNow] = useState(new Date());
  const [sessionMs, setSessionMs] = useState(0);
  const [paused, setPaused] = useState(false);
  const startRef = useRef(Date.now());
  const pausedRef = useRef(null);
  const pausedTotalRef = useRef(0);
  const [breaksTaken, setBreaksTaken] = useState(0);
  
  // ── alerts ──
  const [alertHistory, setAlertHistory] = useState([]);
  const lastAlertTimeRef = useRef({});
  
  // ── hydration reminder ──
  const lastHydrationRef = useRef(Date.now());
  const HYDRATION_INTERVAL = 45 * 60 * 1000;
  
  // ── auto break ──
  const [autoBreakTriggered, setAutoBreakTriggered] = useState(false);
  
  // ── real-time stats for user dropdown ──
  const realTimeStats = {
    currentFatigue: Math.round(fatigueScore),
    currentFocus: Math.round(focusScore * 100),
    currentStress: Math.round(stressLevel * 100),
    blinkRate: Math.round(blinkRate),
    wpm: Math.round(wpm),
    sessionDuration: fmtSession(sessionMs),
    breaksTaken: breaksTaken,
  };
  
  // Clock update
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  
  // Session timer update
  useEffect(() => {
    const t = setInterval(() => {
      if (!paused) setSessionMs(Date.now() - startRef.current - pausedTotalRef.current);
    }, 1000);
    return () => clearInterval(t);
  }, [paused]);
  
  // Close panels when clicking outside
  const headerRef = useRef(null);
  useEffect(() => {
    const fn = (e) => {
      if (headerRef.current && !headerRef.current.contains(e.target)) {
        setShowNotif(false); setShowSettings(false); setShowUser(false);
      }
    };
    document.addEventListener('mousedown', fn);
    return () => document.removeEventListener('mousedown', fn);
  }, []);
  
  // Load alerts from localStorage
  useEffect(() => {
    try {
      const savedAlerts = localStorage.getItem('mg_alerts');
      if (savedAlerts) setAlertHistory(JSON.parse(savedAlerts));
    } catch (err) {
      console.warn('Could not load alerts:', err);
    }
  }, []);
  
  // Check fatigue and trigger alerts based on real-time data
  useEffect(() => {
    if (!settings.notifications) return;
    
    const now = Date.now();
    const cooldownPeriod = 5 * 60 * 1000; // 5 minutes
    
    const checkAndTrigger = (level, threshold, priority) => {
      if (fatigueScore >= threshold && settings.notifications[level]) {
        const lastAlert = lastAlertTimeRef.current[level] || 0;
        if (now - lastAlert > cooldownPeriod) {
          triggerAlert(level, fatigueScore, priority);
          lastAlertTimeRef.current[level] = now;
        }
      }
    };
    
    const triggerAlert = (level, score, priority) => {
      const alertData = {
        id: `alert_${Date.now()}_${Math.random()}`,
        title: `${level.toUpperCase()} Fatigue Detected`,
        message: `Fatigue score is at ${score}%. ${getRecommendation(level)}`,
        priority: priority,
        severity: level,
        triggered_at: new Date().toISOString(),
        seen: false,
        score: score
      };
      
      setAlertHistory(prev => [alertData, ...prev]);
      
      if (settings.notifications.sound) playNotificationSound();
      
      // Store in localStorage
      try {
        const savedAlerts = localStorage.getItem('mg_alerts');
        const existingAlerts = savedAlerts ? JSON.parse(savedAlerts) : [];
        localStorage.setItem('mg_alerts', JSON.stringify([alertData, ...existingAlerts]));
      } catch (err) {
        console.warn('Could not save alert:', err);
      }
      
      console.log(`Alert: ${level} fatigue at ${score}%`);
    };
    
    const getRecommendation = (level) => {
      switch(level) {
        case 'critical': return 'Take an immediate 15-minute break. Your cognitive performance is severely impaired.';
        case 'moderate': return 'Consider a 5-10 minute break to restore focus.';
        case 'mild': return 'A short break soon would help maintain productivity.';
        default: return 'Monitor your fatigue levels.';
      }
    };
    
    checkAndTrigger('critical', settings.thresholds.criticalAt, 5);
    checkAndTrigger('moderate', settings.thresholds.moderateAt, 3);
    checkAndTrigger('mild', settings.thresholds.mildAt, 2);
    
  }, [fatigueScore, settings.thresholds, settings.notifications]);
  
  // Hydration reminder
  useEffect(() => {
    if (!settings.notifications.hydration || paused) return;
    
    const checkHydration = setInterval(() => {
      const timeSinceLastReminder = Date.now() - lastHydrationRef.current;
      if (timeSinceLastReminder >= HYDRATION_INTERVAL) {
        if (settings.notifications.sound) playNotificationSound();
        
        const hydrationAlert = {
          id: `hydration_${Date.now()}`,
          title: "💧 Hydration Reminder",
          message: "Time to drink some water! Staying hydrated helps maintain focus and reduces fatigue.",
          priority: 2,
          severity: "info",
          triggered_at: new Date().toISOString(),
          seen: false
        };
        
        setAlertHistory(prev => [hydrationAlert, ...prev]);
        
        try {
          const savedAlerts = localStorage.getItem('mg_alerts');
          const existingAlerts = savedAlerts ? JSON.parse(savedAlerts) : [];
          localStorage.setItem('mg_alerts', JSON.stringify([hydrationAlert, ...existingAlerts]));
        } catch (err) {
          console.warn('Could not save hydration alert:', err);
        }
        
        console.log('💧 Hydration reminder triggered');
        lastHydrationRef.current = Date.now();
      }
    }, 60000);
    
    return () => clearInterval(checkHydration);
  }, [settings.notifications.hydration, settings.notifications.sound, paused]);
  
  // Auto-break check
  useEffect(() => {
    if (paused || autoBreakTriggered) return;
    
    const sessionMinutes = sessionMs / (60 * 1000);
    if (sessionMinutes >= settings.session.autoBreakAt && settings.notifications.breakReminder) {
      setAutoBreakTriggered(true);
      setBreaksTaken(prev => prev + 1);
      
      const breakAlert = {
        id: `break_${Date.now()}`,
        title: "⏰ Break Time!",
        message: `You've been working for ${Math.floor(sessionMinutes)} minutes. Take a ${settings.session.breakDuration} minute break to recharge.`,
        priority: 3,
        severity: "moderate",
        triggered_at: new Date().toISOString(),
        seen: false
      };
      
      setAlertHistory(prev => [breakAlert, ...prev]);
      
      if (settings.notifications.sound) playNotificationSound();
      
      try {
        const savedAlerts = localStorage.getItem('mg_alerts');
        const existingAlerts = savedAlerts ? JSON.parse(savedAlerts) : [];
        localStorage.setItem('mg_alerts', JSON.stringify([breakAlert, ...existingAlerts]));
      } catch (err) {
        console.warn('Could not save break alert:', err);
      }
      
      console.log('⏰ Auto-break triggered at', settings.session.autoBreakAt, 'minutes');
    }
  }, [sessionMs, settings.session.autoBreakAt, settings.notifications.breakReminder, settings.notifications.sound, paused, autoBreakTriggered]);
  
  const saveSettings = useCallback((s) => {
    setSettings(s);
    localStorage.setItem('mg_settings', JSON.stringify(s));
    if (onSettingsChange) onSettingsChange(s);
  }, [onSettingsChange]);
  
  const handleToggleSetting = useCallback((group, key, value) => {
    const newSettings = {
      ...settings,
      [group]: {
        ...settings[group],
        [key]: value
      }
    };
    saveSettings(newSettings);
  }, [settings, saveSettings]);
  
  const togglePause = () => {
    if (!paused) { 
      pausedRef.current = Date.now(); 
      setPaused(true); 
    } else { 
      if (pausedRef.current) { 
        pausedTotalRef.current += Date.now() - pausedRef.current; 
        pausedRef.current = null; 
      } 
      setPaused(false); 
      setAutoBreakTriggered(false);
    }
  };
  
  const resetTimer = () => {
    startRef.current = Date.now(); 
    pausedTotalRef.current = 0;
    pausedRef.current = null; 
    setSessionMs(0); 
    setPaused(false);
    lastHydrationRef.current = Date.now();
    setAutoBreakTriggered(false);
  };
  
  const handleDismissAlert = (id) => {
    setAlertHistory(prev => prev.map(alert => 
      alert.id === id ? { ...alert, seen: true } : alert
    ));
    
    try {
      const updatedAlerts = alertHistory.map(alert => 
        alert.id === id ? { ...alert, seen: true } : alert
      );
      localStorage.setItem('mg_alerts', JSON.stringify(updatedAlerts));
    } catch (err) {
      console.warn('Could not update alerts:', err);
    }
    
    if (onDismissAlert) onDismissAlert(id);
  };
  
  const handleDismissAllAlerts = () => {
    setAlertHistory(prev => prev.map(alert => ({ ...alert, seen: true })));
    
    try {
      const updatedAlerts = alertHistory.map(alert => ({ ...alert, seen: true }));
      localStorage.setItem('mg_alerts', JSON.stringify(updatedAlerts));
    } catch (err) {
      console.warn('Could not update alerts:', err);
    }
    
    if (onDismissAllAlerts) onDismissAllAlerts();
  };
  
  const unread = alertHistory.filter(a => !a.seen).length;
  const risk = RISK_LEVELS[fatigueLevel] || RISK_LEVELS.fresh;
  const conn = CONN_STATES[wsStatus] || CONN_STATES.simulated;
  const isReconnecting = wsStatus === 'reconnecting' || wsStatus === 'connecting';
  
  const openPanel = (which) => {
    setShowNotif(which === 'notif');
    setShowSettings(which === 'settings');
    setShowUser(which === 'user');
  };
  
  return (
    <div ref={headerRef} style={{ position: 'relative' }}>
      <header className="header">
        {/* LOGO */}
        <div className="header-logo">
          <div className="header-icon"><I.Brain /></div>
          <div className="header-title-wrap">
            <div className="header-title">Mind<span className="header-title-accent">Guard</span></div>
            <div className="header-subtitle">Cognitive Load Prevention System</div>
          </div>
        </div>
        
        {/* CENTER — clock + session */}
        <div className="header-center">
          <div className="header-clock">
            <span className="header-clock-icon"><I.Clock /></span>
            <span className="header-clock-time">{fmtClock(now)}</span>
            <span className="header-clock-sep" />
            <span className="header-clock-date">{fmtDate(now)}</span>
          </div>
          <div className="header-session">
            <span className="header-session-label">Session</span>
            <span className="header-session-time" style={{ color: paused ? '#ff9838' : '#7b2fff' }}>{fmtSession(sessionMs)}</span>
            <div className="header-session-controls">
              <button className="header-session-btn" onClick={togglePause} title={paused ? 'Resume' : 'Pause'}>
                {paused ? <I.Play /> : <I.Pause />}
              </button>
              <button className="header-session-btn" onClick={resetTimer} title="Reset"><I.Reset /></button>
            </div>
          </div>
        </div>
        
        {/* RIGHT */}
        <div className="header-right">
          <div className={`risk-badge ${risk.cls}`}><span className="risk-dot" />{risk.label}</div>
          <div className={`conn-badge ${conn.cls}`}><span className="conn-dot" />{conn.label}</div>
          <div className="header-divider" />
          
          {/* Report btn */}
          <button className="header-icon-btn" title="Report" onClick={onReportClick}>
            <I.BarChart />
          </button>
          
          {/* Notifications */}
          <button
            className={`header-icon-btn${unread > 0 ? ' has-alerts' : ''}${showNotif ? ' active-panel-btn' : ''}`}
            title="Notifications"
            onClick={() => openPanel(showNotif ? null : 'notif')}
          >
            <I.Bell />
            {unread > 0 && <span className="header-notif-badge">{unread > 9 ? '9+' : unread}</span>}
          </button>
          
          {/* Settings */}
          <button
            className={`header-icon-btn${showSettings ? ' active-panel-btn' : ''}`}
            title="Settings"
            onClick={() => openPanel(showSettings ? null : 'settings')}
          >
            <I.Settings />
          </button>
          
          <div className="header-divider" />
          
          {/* User chip with real-time fatigue indicator */}
          <div className={`header-user${showUser ? ' active-user' : ''}`} onClick={() => openPanel(showUser ? null : 'user')}>
            <div className="header-user-info">
              <div className="header-user-name">{user.name}</div>
              <div className="header-user-role">{user.role}</div>
            </div>
            <div className="header-avatar" style={{ position: 'relative' }}>
              {user.name.charAt(0)}
              <span className={`header-status-dot ${fatigueScore > 55 ? 'warning' : fatigueScore > 35 ? 'caution' : 'good'}`} />
            </div>
            <span className="header-chevron"><I.ChevronDown /></span>
          </div>
        </div>
        
        {isReconnecting && <div className="header-reconnect-bar" />}
      </header>
      
      {/* ── PANELS ────────────────────────────────────────────── */}
      {showNotif && (
        <NotificationsPanel
          alerts={alertHistory}
          settings={settings}
          onDismiss={handleDismissAlert}
          onDismissAll={handleDismissAllAlerts}
          onToggleSetting={handleToggleSetting}
          onClose={() => setShowNotif(false)}
        />
      )}
      
      {showSettings && (
        <SettingsPanel
          settings={settings}
          onChange={saveSettings}
          user={user}
          onClose={() => setShowSettings(false)}
        />
      )}
      
      {showUser && (
        <UserDropdown
          user={user}
          realTimeStats={realTimeStats}
          onLogout={onLogout}
          onClose={() => setShowUser(false)}
        />
      )}
    </div>
  );
};

export default Header;