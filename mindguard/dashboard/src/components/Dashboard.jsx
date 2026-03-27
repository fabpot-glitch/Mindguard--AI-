import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, LineChart, Line, ComposedChart
} from 'recharts';

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const LEVELS = {
  fresh:    { color: '#00ff9d', glow: 'rgba(0,255,157,0.35)',   label: 'OPTIMAL',  bg: 'rgba(0,255,157,0.12)',   border: 'rgba(0,255,157,0.4)', recommendation: 'Great! Maintain your current workflow. Take breaks every 60 minutes.', action: 'Keep going!' },
  mild:     { color: '#ffe566', glow: 'rgba(255,229,102,0.35)', label: 'MILD',     bg: 'rgba(255,229,102,0.12)', border: 'rgba(255,229,102,0.4)', recommendation: 'Mild fatigue detected. Consider a short break in the next 30 minutes.', action: 'Take a short break soon' },
  moderate: { color: '#ff9838', glow: 'rgba(255,152,56,0.35)',  label: 'MODERATE', bg: 'rgba(255,152,56,0.12)',  border: 'rgba(255,152,56,0.4)', recommendation: 'Moderate fatigue. Take a 5-10 minute break to recharge.', action: 'Take a break now' },
  critical: { color: '#ff3b5c', glow: 'rgba(255,59,92,0.35)',   label: 'CRITICAL', bg: 'rgba(255,59,92,0.12)',   border: 'rgba(255,59,92,0.4)', recommendation: 'CRITICAL! Stop work immediately. Take a 15-minute break.', action: 'URGENT BREAK NEEDED' },
};

const ACTIVITY_STATUS = {
  focused: { icon: '🎯', label: 'Highly Focused', color: '#00ff9d', message: 'Excellent concentration detected!', advice: 'You\'re in a flow state. Keep going!' },
  productive: { icon: '⚡', label: 'Productive', color: '#00e5ff', message: 'Good workflow detected', advice: 'Stay consistent and take breaks when needed.' },
  distracted: { icon: '👀', label: 'Distracted', color: '#ffe566', message: 'Focus seems to be wandering', advice: 'Try the Pomodoro technique: 25 min work, 5 min break.' },
  fatigued: { icon: '😴', label: 'Fatigued', color: '#ff9838', message: 'Mental fatigue detected', advice: 'Take a 5-10 minute break to recharge.' },
  stressed: { icon: '😰', label: 'Stressed', color: '#ff3b5c', message: 'Stress levels elevated', advice: 'Practice 4-7-8 breathing: inhale 4s, hold 7s, exhale 8s.' },
  idle: { icon: '💤', label: 'Idle', color: '#6c8a9e', message: 'No activity detected', advice: 'Time to get back to work!' },
  excellent: { icon: '🌟', label: 'Peak Performance', color: '#a78bfa', message: 'You\'re in the zone!', advice: 'Exceptional cognitive state - optimal performance!' }
};

function ema(prev, next, alpha = 0.15) {
  if (prev === null || prev === undefined) return next;
  return prev * (1 - alpha) + next * alpha;
}

function clamp01(v) { return Math.min(1, Math.max(0, isNaN(v) ? 0 : v)); }

// ─── SENSOR MANAGER ──────────────────────────────────────────────────────────
class SensorManager {
  constructor() {
    this.smoothed = {
      blink_rate: 14,
      wpm: 45,
      perclos: 0.04,
      error_rate: 0.02,
      pitch_var: 20,
      mouse_vel: 150,
      mic_energy: 0,
      idle_time: 0,
      click_freq: 0,
      face_present: false,
      stress_level: 0.3,
      focus_score: 0.7,
      energy_level: 0.6,
      concentration: 0.7,
      eye_strain: 0.2,
      productivity_score: 0.65,
    };

    this._raw = {
      keyIntervals: [],
      errorCount: 0,
      keyCount: 0,
      mouseVelSamples: [],
      lastKeyTime: Date.now(),
      lastMousePos: { x: 0, y: 0 },
      lastMouseTime: Date.now(),
      lastActivity: Date.now(),
      clickTimes: [],
      audioLevels: [],
    };

    this.webcamStream = null;
    this.micStream = null;
    this.audioCtx = null;
    this.analyserNode = null;
    this.webcamVideo = null;
    this.webcamCanvas = null;
    this._prevLuma = null;
    this._blinkCooldown = 0;
    this._blinkTimes = [];

    this.webcamGranted = false;
    this.micGranted = false;
    this._cleanups = [];
    this._alive = true;
    this._smoothInterval = null;
    this._camActive = false;
    this._micActive = false;

    this._setupKeyboard();
    this._setupMouse();
    this._startSmoothLoop();
  }

  _setupKeyboard() {
    const onKeyDown = (e) => {
      if (!this._alive) return;
      const now = Date.now();
      const dt = now - this._raw.lastKeyTime;
      this._raw.keyCount++;
      this._raw.lastKeyTime = now;
      this._raw.lastActivity = now;

      if (e.key === 'Backspace' || e.key === 'Delete') this._raw.errorCount++;

      if (dt > 50 && dt < 2000) this._raw.keyIntervals.push(dt);
      if (this._raw.keyIntervals.length > 60) this._raw.keyIntervals.shift();
    };
    window.addEventListener('keydown', onKeyDown);
    this._cleanups.push(() => window.removeEventListener('keydown', onKeyDown));
  }

  _setupMouse() {
    const onMove = (e) => {
      if (!this._alive) return;
      const now = Date.now();
      const dx = e.clientX - this._raw.lastMousePos.x;
      const dy = e.clientY - this._raw.lastMousePos.y;
      const dt = now - this._raw.lastMouseTime;
      if (dt > 0) {
        const vel = Math.sqrt(dx * dx + dy * dy) / dt * 1000;
        if (vel > 5) {
          this._raw.mouseVelSamples.push(Math.min(500, vel));
          if (this._raw.mouseVelSamples.length > 30) this._raw.mouseVelSamples.shift();
        }
      }
      this._raw.lastMousePos = { x: e.clientX, y: e.clientY };
      this._raw.lastMouseTime = now;
      this._raw.lastActivity = now;
    };
    const onClick = () => {
      if (!this._alive) return;
      this._raw.clickTimes.push(Date.now());
      this._raw.lastActivity = Date.now();
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    window.addEventListener('click', onClick, { passive: true });
    this._cleanups.push(() => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('click', onClick);
    });
  }

  async startWebcam() {
    if (this._camActive || !this._alive) return false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
      });
      
      this.webcamStream = stream;
      this._camActive = true;
      this.webcamGranted = true;

      const video = document.createElement('video');
      const canvas = document.createElement('canvas');
      canvas.width = 320;
      canvas.height = 240;
      video.srcObject = stream;
      video.playsInline = true;
      video.muted = true;
      video.autoplay = true;
      
      await video.play();
      this.webcamVideo = video;
      this.webcamCanvas = canvas;
      
      this._startFaceDetection();
      return true;
    } catch (error) {
      this._camActive = false;
      return false;
    }
  }

  stopWebcam() {
    if (this.webcamStream) {
      this.webcamStream.getTracks().forEach(track => track.stop());
      this.webcamStream = null;
      this.webcamVideo = null;
      this._camActive = false;
      this.webcamGranted = false;
    }
  }

  _startFaceDetection() {
    const ctx = this.webcamCanvas.getContext('2d');
    
    const detect = () => {
      if (!this._alive || !this._camActive || !this.webcamVideo || this.webcamVideo.readyState < 2) {
        if (this._alive) setTimeout(detect, 200);
        return;
      }
      
      try {
        ctx.drawImage(this.webcamVideo, 0, 0, this.webcamCanvas.width, this.webcamCanvas.height);
        const imageData = ctx.getImageData(0, 0, this.webcamCanvas.width, this.webcamCanvas.height);
        const data = imageData.data;
        
        let skinPixelCount = 0;
        let totalPixels = 0;
        const startY = Math.round(this.webcamCanvas.height * 0.15);
        const endY = Math.round(this.webcamCanvas.height * 0.7);
        const startX = Math.round(this.webcamCanvas.width * 0.2);
        const endX = Math.round(this.webcamCanvas.width * 0.8);
        
        for (let y = startY; y < endY; y++) {
          for (let x = startX; x < endX; x++) {
            const idx = (y * this.webcamCanvas.width + x) * 4;
            const r = data[idx];
            const g = data[idx + 1];
            const b = data[idx + 2];
            if (r > 60 && g > 35 && b > 25 && r > g && r > b && Math.abs(r - g) > 15) {
              skinPixelCount++;
            }
            totalPixels++;
          }
        }
        
        const faceRatio = skinPixelCount / totalPixels;
        this.smoothed.face_present = faceRatio > 0.05 && faceRatio < 0.5;
        
        const eyeY = Math.round(this.webcamCanvas.height * 0.3);
        const eyeH = Math.round(this.webcamCanvas.height * 0.15);
        const eyeData = ctx.getImageData(startX, eyeY, endX - startX, eyeH);
        const eyePixels = eyeData.data;
        
        if (eyePixels.length > 0) {
          let luma = 0;
          for (let i = 0; i < eyePixels.length; i += 4) {
            luma += 0.299 * eyePixels[i] + 0.587 * eyePixels[i + 1] + 0.114 * eyePixels[i + 2];
          }
          luma /= (eyePixels.length / 4);
          
          if (this._prevLuma !== null && this._blinkCooldown === 0 && this.smoothed.face_present) {
            const diff = this._prevLuma - luma;
            if (diff > 8) {
              this._blinkTimes.push(Date.now());
              this._blinkCooldown = 12;
              this._blinkTimes = this._blinkTimes.filter(t => Date.now() - t < 60000);
            }
          }
          
          if (this._blinkCooldown > 0) this._blinkCooldown--;
          this._prevLuma = luma;
        }
        
        if (this.smoothed.face_present && this.smoothed.blink_rate < 12) {
          this.smoothed.eye_strain = ema(this.smoothed.eye_strain, 0.5 + (12 - this.smoothed.blink_rate) / 20, 0.1);
        } else {
          this.smoothed.eye_strain = ema(this.smoothed.eye_strain, 0.2, 0.1);
        }
        
      } catch (e) {}
      
      if (this._alive && this._camActive) setTimeout(detect, 100);
    };
    
    detect();
  }

  async startMic() {
    if (this._micActive || !this._alive) return false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { echoCancellation: true, noiseSuppression: true }
      });
      
      this.micStream = stream;
      this._micActive = true;
      this.micGranted = true;
      
      this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      await this.audioCtx.resume();
      
      const source = this.audioCtx.createMediaStreamSource(stream);
      const analyser = this.audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      this.analyserNode = analyser;
      this._startAudioAnalysis();
      return true;
    } catch (error) {
      this._micActive = false;
      return false;
    }
  }

  stopMic() {
    if (this.micStream) {
      this.micStream.getTracks().forEach(track => track.stop());
      this.micStream = null;
      if (this.audioCtx) this.audioCtx.close();
      this._micActive = false;
      this.micGranted = false;
    }
  }

  _startAudioAnalysis() {
    const dataArray = new Float32Array(this.analyserNode.fftSize);
    
    const analyze = () => {
      if (!this._alive || !this._micActive || !this.analyserNode) return;
      
      try {
        this.analyserNode.getFloatTimeDomainData(dataArray);
        let rms = 0;
        for (let i = 0; i < dataArray.length; i++) {
          rms += dataArray[i] * dataArray[i];
        }
        rms = Math.sqrt(rms / dataArray.length);
        const energy = Math.min(1, rms * 12);
        this.smoothed.mic_energy = ema(this.smoothed.mic_energy, energy, 0.15);
        
        if (energy > 0.08) {
          this.smoothed.pitch_var = ema(this.smoothed.pitch_var, 20 + Math.random() * 20, 0.12);
          this.smoothed.stress_level = ema(this.smoothed.stress_level, 0.3 + energy * 0.5, 0.1);
        }
      } catch (e) {}
      
      if (this._alive && this._micActive) requestAnimationFrame(analyze);
    };
    
    analyze();
  }

  _startSmoothLoop() {
    this._smoothInterval = setInterval(() => {
      if (!this._alive) return;
      const now = Date.now();

      if (this._raw.keyIntervals.length > 3) {
        const avgInterval = this._raw.keyIntervals.reduce((a, b) => a + b, 0) / this._raw.keyIntervals.length;
        const rawWpm = (60000 / avgInterval) / 5;
        this.smoothed.wpm = ema(this.smoothed.wpm, Math.min(120, Math.max(5, rawWpm)), 0.12);
      } else if (now - this._raw.lastKeyTime > 8000) {
        this.smoothed.wpm = ema(this.smoothed.wpm, 0, 0.04);
      }

      if (this._raw.keyCount > 5) {
        const rawErr = Math.min(0.3, this._raw.errorCount / this._raw.keyCount);
        this.smoothed.error_rate = ema(this.smoothed.error_rate, rawErr, 0.08);
      }

      if (this._raw.mouseVelSamples.length > 0) {
        const rawVel = this._raw.mouseVelSamples.reduce((a, b) => a + b, 0) / this._raw.mouseVelSamples.length;
        this.smoothed.mouse_vel = ema(this.smoothed.mouse_vel, rawVel, 0.15);
      } else {
        this.smoothed.mouse_vel = ema(this.smoothed.mouse_vel, 30, 0.05);
      }

      if (this._camActive && this._blinkTimes.length > 0) {
        const recentBlinks = this._blinkTimes.filter(t => now - t < 60000).length;
        const elapsed = Math.min(60, (now - (this._blinkTimes[0] || now)) / 1000 + 1);
        const rawBlink = (recentBlinks / elapsed) * 60;
        this.smoothed.blink_rate = ema(this.smoothed.blink_rate, Math.min(40, Math.max(2, rawBlink)), 0.12);
      } else {
        const idleFactor = Math.min(1, this.smoothed.idle_time / 120);
        this.smoothed.blink_rate = ema(this.smoothed.blink_rate, 14 - idleFactor * 4, 0.02);
      }

      this.smoothed.idle_time = Math.min(300, (now - this._raw.lastActivity) / 1000);
      this._raw.clickTimes = this._raw.clickTimes.filter(t => now - t < 60000);
      this.smoothed.click_freq = this._raw.clickTimes.length;

      this.smoothed.focus_score = ema(
        this.smoothed.focus_score,
        1 - (this.smoothed.stress_level * 0.4 + this.smoothed.error_rate * 0.3 + this.smoothed.idle_time / 300),
        0.1
      );
      
      this.smoothed.energy_level = ema(
        this.smoothed.energy_level,
        1 - (this.smoothed.stress_level * 0.5 + (1 - this.smoothed.wpm / 120) * 0.3),
        0.1
      );
      
      this.smoothed.concentration = ema(
        this.smoothed.concentration,
        (this.smoothed.focus_score + (1 - this.smoothed.error_rate) + (this.smoothed.wpm / 120)) / 3,
        0.1
      );
      
      this.smoothed.productivity_score = ema(
        this.smoothed.productivity_score,
        (this.smoothed.focus_score * 0.5 + this.smoothed.wpm / 120 * 0.3 + (1 - this.smoothed.error_rate) * 0.2),
        0.1
      );

      this.smoothed.wpm = Math.max(0, Math.min(120, this.smoothed.wpm));
      this.smoothed.error_rate = Math.max(0, Math.min(0.3, this.smoothed.error_rate));
      this.smoothed.mouse_vel = Math.max(0, Math.min(500, this.smoothed.mouse_vel));
      this.smoothed.blink_rate = Math.max(0, Math.min(40, this.smoothed.blink_rate));
      this.smoothed.stress_level = Math.max(0, Math.min(1, this.smoothed.stress_level));
      this.smoothed.focus_score = Math.max(0, Math.min(1, this.smoothed.focus_score));
      this.smoothed.energy_level = Math.max(0, Math.min(1, this.smoothed.energy_level));
      this.smoothed.concentration = Math.max(0, Math.min(1, this.smoothed.concentration));
      this.smoothed.eye_strain = Math.max(0, Math.min(1, this.smoothed.eye_strain));
      this.smoothed.productivity_score = Math.max(0, Math.min(1, this.smoothed.productivity_score));
    }, 500);
  }

  getMetrics() { return { ...this.smoothed }; }
  isActive() { return (Date.now() - this._raw.lastActivity) < 5000; }
  isCamActive() { return this._camActive; }
  isMicActive() { return this._micActive; }

  destroy() {
    this._alive = false;
    clearInterval(this._smoothInterval);
    this._cleanups.forEach(fn => fn());
    this.stopWebcam();
    this.stopMic();
  }
}

function calcFatigue(metrics, sessionMin, prevScore) {
  const signals = {
    blink: clamp01(1 - (metrics.blink_rate - 5) / 30),
    wpm: clamp01(1 - (metrics.wpm - 5) / 115),
    error: clamp01(metrics.error_rate / 0.15),
    mouse: clamp01(1 - (metrics.mouse_vel - 20) / 280),
    stress: metrics.stress_level,
    idle: clamp01(metrics.idle_time / 120),
  };

  const weights = { blink: 0.22, wpm: 0.20, error: 0.18, mouse: 0.15, stress: 0.15, idle: 0.10 };
  let raw = 0;
  for (const [k, w] of Object.entries(weights)) raw += signals[k] * w;
  raw += Math.min(0.25, sessionMin / 480);
  raw = clamp01(raw);

  return prevScore === null ? raw : ema(prevScore, raw, 0.08);
}

function getActivityStatus(metrics, fatigueScore, faceDetected, camActive, micActive) {
  const activityLevel = metrics.wpm > 30 || metrics.mouse_vel > 50 || metrics.mic_energy > 0.08;
  
  if (!activityLevel && metrics.idle_time > 60) return ACTIVITY_STATUS.idle;
  if (fatigueScore > 0.75) return ACTIVITY_STATUS.fatigued;
  if (metrics.stress_level > 0.7 && micActive) return ACTIVITY_STATUS.stressed;
  if (metrics.focus_score > 0.85 && metrics.concentration > 0.8 && metrics.wpm > 50) return ACTIVITY_STATUS.excellent;
  if (metrics.focus_score > 0.7 && metrics.wpm > 40 && metrics.error_rate < 0.05) return ACTIVITY_STATUS.focused;
  if (metrics.wpm > 30 && metrics.error_rate < 0.08) return ACTIVITY_STATUS.productive;
  if (metrics.focus_score < 0.4 || metrics.error_rate > 0.1) return ACTIVITY_STATUS.distracted;
  return ACTIVITY_STATUS.productive;
}

function getPersonalizedSuggestions(metrics, fatigueScore, faceDetected, camActive, micActive, activityStatus) {
  const suggestions = [];
  
  // Eye strain suggestions (only when camera is active)
  if (camActive && faceDetected) {
    if (metrics.blink_rate < 10) {
      suggestions.push({
        id: 'eye_strain',
        title: '👁️ Eye Strain Detected',
        description: `Your blink rate is only ${metrics.blink_rate.toFixed(0)} blinks/min (normal: 12-20).`,
        recommendation: 'Follow the 20-20-20 rule: Every 20 minutes, look at something 20 feet away for 20 seconds.',
        action: 'Blink slowly 10 times',
        icon: '👁️',
        priority: fatigueScore > 0.6 ? 'high' : 'medium'
      });
    }
    
    if (metrics.eye_strain > 0.6) {
      suggestions.push({
        id: 'eye_fatigue',
        title: '👁️ Eye Fatigue Increasing',
        description: `Eye strain level at ${(metrics.eye_strain * 100).toFixed(0)}%. Your eyes need rest.`,
        recommendation: 'Close your eyes for 20 seconds, then look at a distant object for 20 seconds.',
        action: 'Rest eyes now',
        icon: '👁️',
        priority: 'high'
      });
    }
  }
  
  // High error rate suggestions
  if (metrics.error_rate > 0.08) {
    suggestions.push({
      id: 'high_errors',
      title: '⌨️ High Typing Errors',
      description: `Error rate at ${(metrics.error_rate * 100).toFixed(0)}% (normal: <5%).`,
      recommendation: 'Take a 2-minute break to reset your focus. Mental fatigue may be affecting accuracy.',
      action: 'Take a short break',
      icon: '⌨️',
      priority: fatigueScore > 0.6 ? 'high' : 'medium'
    });
  }
  
  // Stress detection (only when mic is active)
  if (metrics.stress_level > 0.6 && micActive) {
    suggestions.push({
      id: 'high_stress',
      title: '😰 High Stress Detected',
      description: `Stress level at ${(metrics.stress_level * 100).toFixed(0)}% based on voice analysis.`,
      recommendation: 'Try the 4-7-8 breathing technique: Inhale 4s, hold 7s, exhale 8s. Repeat 4 times.',
      action: 'Start breathing exercise',
      icon: '😰',
      priority: 'high'
    });
  }
  
  // Fatigue suggestions
  if (fatigueScore > 0.65) {
    suggestions.push({
      id: 'high_fatigue',
      title: '⚠️ Critical Fatigue Alert',
      description: `Fatigue score at ${(fatigueScore * 100).toFixed(0)}% - cognitive performance impaired.`,
      recommendation: 'IMMEDIATE ACTION: Step away from your desk. Take a 10-15 minute break. Hydrate and stretch.',
      action: 'Take urgent break',
      icon: '⚠️',
      priority: 'high'
    });
  } else if (fatigueScore > 0.45) {
    suggestions.push({
      id: 'moderate_fatigue',
      title: '🌿 Moderate Fatigue',
      description: `Fatigue score at ${(fatigueScore * 100).toFixed(0)}% - performance may be declining.`,
      recommendation: 'Take a 5-minute break. Stand up, stretch, and look away from screen.',
      action: 'Take a short break',
      icon: '🌿',
      priority: 'medium'
    });
  }
  
  // Low WPM suggestion
  if (metrics.wpm < 30 && metrics.wpm > 0) {
    suggestions.push({
      id: 'low_wpm',
      title: '🐢 Reduced Typing Speed',
      description: `Your typing speed is ${metrics.wpm.toFixed(0)} WPM (normal: 40-80).`,
      recommendation: 'Mental fatigue may be affecting your processing speed. Try a 5-minute mindfulness break.',
      action: 'Mindfulness break',
      icon: '🐢',
      priority: 'medium'
    });
  }
  
  // Low focus suggestion
  if (metrics.focus_score < 0.4 && metrics.idle_time < 120) {
    suggestions.push({
      id: 'low_focus',
      title: '🎯 Focus Declining',
      description: `Focus score at ${(metrics.focus_score * 100).toFixed(0)}% - distractions detected.`,
      recommendation: 'Try the Pomodoro Technique: 25 minutes focused work, then 5 minutes break.',
      action: 'Start focus session',
      icon: '🎯',
      priority: 'medium'
    });
  }
  
  // Inactivity suggestion
  if (metrics.idle_time > 300) {
    suggestions.push({
      id: 'inactive',
      title: '💪 Extended Inactivity',
      description: `You've been idle for ${Math.floor(metrics.idle_time / 60)} minutes.`,
      recommendation: 'Stand up, stretch your arms and back, and walk around for 2 minutes to improve circulation.',
      action: 'Stand and stretch',
      icon: '💪',
      priority: 'medium'
    });
  }
  
  // Positive reinforcement (only when sensors are active and metrics are good)
  if (camActive && fatigueScore < 0.35 && metrics.focus_score > 0.7 && metrics.error_rate < 0.03) {
    suggestions.push({
      id: 'great_performance',
      title: '🎉 Excellent Performance!',
      description: 'Your cognitive metrics are optimal. Great focus and energy levels!',
      recommendation: 'Keep up the good work! Remember to take regular breaks to maintain this performance.',
      action: 'Keep going!',
      icon: '🎉',
      priority: 'low'
    });
  }
  
  return suggestions.sort((a, b) => {
    const priorityOrder = { high: 3, medium: 2, low: 1 };
    return priorityOrder[b.priority] - priorityOrder[a.priority];
  });
}

// ─── LIVE DATA HOOK ──────────────────────────────────────────────────────────
function useLiveData() {
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [camActive, setCamActive] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [active, setActive] = useState(false);
  const [faceDetected, setFaceDetected] = useState(false);
  const [isEnabling, setIsEnabling] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showPermissionHelp, setShowPermissionHelp] = useState(false);
  const [fatigueScore, setFatigueScore] = useState(0.18);
  const [activityStatus, setActivityStatus] = useState(ACTIVITY_STATUS.idle);
  const [realtimeAdvice, setRealtimeAdvice] = useState('');

  const sensorRef = useRef(null);
  const fatigueRef = useRef(null);
  const sessStart = useRef(Date.now());
  const alertCooldown = useRef({});

  useEffect(() => {
    sensorRef.current = new SensorManager();
    fatigueRef.current = 0.18;
    return () => { if (sensorRef.current) sensorRef.current.destroy(); };
  }, []);

  const enableSensors = useCallback(async () => {
    if (!sensorRef.current || isEnabling) return;
    setIsEnabling(true);
    setShowPermissionHelp(false);
    try {
      const camResult = await sensorRef.current.startWebcam();
      const micResult = await sensorRef.current.startMic();
      setCamActive(camResult);
      setMicActive(micResult);
      if (!camResult || !micResult) setShowPermissionHelp(true);
    } catch (error) {
      setShowPermissionHelp(true);
    } finally {
      setIsEnabling(false);
    }
  }, [isEnabling]);

  const stopCamera = useCallback(() => { if (sensorRef.current) { sensorRef.current.stopWebcam(); setCamActive(false); } }, []);
  const stopMicrophone = useCallback(() => { if (sensorRef.current) { sensorRef.current.stopMic(); setMicActive(false); } }, []);
  const startCamera = useCallback(async () => { if (!sensorRef.current) return; const result = await sensorRef.current.startWebcam(); setCamActive(result); if (!result) setShowPermissionHelp(true); }, []);
  const startMicrophone = useCallback(async () => { if (!sensorRef.current) return; const result = await sensorRef.current.startMic(); setMicActive(result); if (!result) setShowPermissionHelp(true); }, []);

  useEffect(() => {
    if (!sensorRef.current) return;
    
    const interval = setInterval(() => {
      const sensor = sensorRef.current;
      if (!sensor) return;
      
      const m = sensor.getMetrics();
      const sessionMin = (Date.now() - sessStart.current) / 60000;
      const newFatigue = calcFatigue(m, sessionMin, fatigueRef.current);
      fatigueRef.current = newFatigue;
      setFatigueScore(newFatigue);
      
      const status = getActivityStatus(m, newFatigue, m.face_present, sensor.isCamActive(), sensor.isMicActive());
      setActivityStatus(status);
      
      let advice = '';
      if (status === ACTIVITY_STATUS.excellent) advice = '🔥 Peak performance! Maintain this momentum.';
      else if (status === ACTIVITY_STATUS.focused) advice = '🎯 Great focus! Keep up the concentration.';
      else if (status === ACTIVITY_STATUS.productive) advice = '⚡ Productive workflow detected. Stay consistent.';
      else if (status === ACTIVITY_STATUS.distracted) advice = '👀 Focus seems to be wandering. Minimize distractions.';
      else if (status === ACTIVITY_STATUS.fatigued) advice = '😴 Fatigue detected. A short break would help.';
      else if (status === ACTIVITY_STATUS.stressed) advice = '😰 Stress elevated. Try deep breathing exercises.';
      else if (status === ACTIVITY_STATUS.idle) advice = '💤 No activity detected. Time to get back to work!';
      setRealtimeAdvice(advice);
      
      const level = newFatigue < 0.35 ? 'fresh' : newFatigue < 0.55 ? 'mild' : newFatigue < 0.75 ? 'moderate' : 'critical';
      const now = new Date();
      
      const snap = {
        fatigue_score: parseFloat(newFatigue.toFixed(3)),
        fatigue_level: level,
        confidence: parseFloat((0.55 + (sensor.isCamActive() ? 0.2 : 0) + (sensor.isMicActive() ? 0.15 : 0) + Math.min(0.1, sessionMin / 60)).toFixed(2)),
        trend: 0,
        session_average: 0,
        modality_weights: {
          eye: sensor.isCamActive() ? 0.30 : 0.10,
          keyboard: 0.28,
          voice: sensor.isMicActive() ? 0.22 : 0.08,
          screen: 0.20,
        },
        active_modalities: ['keyboard', 'screen', ...(sensor.isCamActive() ? ['eye'] : []), ...(sensor.isMicActive() ? ['voice'] : [])],
        metrics: {
          blink_rate: parseFloat(m.blink_rate.toFixed(1)),
          wpm: parseFloat(m.wpm.toFixed(1)),
          perclos: parseFloat(m.perclos.toFixed(3)),
          error_rate: parseFloat(m.error_rate.toFixed(3)),
          pitch_var: parseFloat(m.pitch_var.toFixed(1)),
          mouse_vel: parseFloat(m.mouse_vel.toFixed(0)),
          idle_time: parseFloat(m.idle_time.toFixed(1)),
          click_freq: m.click_freq,
          mic_energy: parseFloat(m.mic_energy.toFixed(3)),
          face_present: m.face_present,
          stress_level: parseFloat(m.stress_level.toFixed(2)),
          focus_score: parseFloat(m.focus_score.toFixed(2)),
          energy_level: parseFloat(m.energy_level.toFixed(2)),
          concentration: parseFloat(m.concentration.toFixed(2)),
          eye_strain: parseFloat(m.eye_strain.toFixed(2)),
          productivity_score: parseFloat(m.productivity_score.toFixed(2)),
        },
        timestamp: now.toISOString(),
        time: now.toLocaleTimeString('en', { hour12: false }),
        activity_status: status.label,
      };
      
      setMetrics(m);
      setActive(sensor.isActive());
      setFaceDetected(m.face_present);
      
      // Generate suggestions only when sensors are active
      const newSuggestions = getPersonalizedSuggestions(m, newFatigue, m.face_present, sensor.isCamActive(), sensor.isMicActive(), status);
      setSuggestions(newSuggestions.slice(0, 5));
      
      setHistory(prev => {
        const next = [...prev, snap].slice(-120);
        if (next.length > 1) {
          snap.trend = snap.fatigue_score - next[next.length - 2].fatigue_score;
          snap.session_average = next.reduce((s, h) => s + h.fatigue_score, 0) / next.length;
        }
        return next;
      });
      
      // Generate alerts only when sensors are active
      const now2 = Date.now();
      const triggerAlert = (key, ms, obj) => {
        if (!alertCooldown.current[key] || now2 - alertCooldown.current[key] > ms) {
          alertCooldown.current[key] = now2;
          setAlerts(prev => [{ ...obj, id: now2, timestamp: new Date().toLocaleTimeString() }, ...prev].slice(0, 12));
        }
      };
      
      // Only trigger alerts if at least one sensor is active
      if (sensor.isCamActive() || sensor.isMicActive()) {
        // Fatigue-based alerts
        if (level === 'critical') {
          triggerAlert('critical', 180000, { 
            priority: 5, 
            title: '⚠️ CRITICAL FATIGUE ALERT', 
            message: 'Cognitive performance severely impaired. Take a 15-minute break immediately!',
            recommendation: 'Step away from screen, hydrate, stretch'
          });
        } else if (level === 'moderate') {
          triggerAlert('moderate', 300000, { 
            priority: 3, 
            title: '🧘 Fatigue Building', 
            message: 'Fatigue levels elevated. A short break will help restore focus.',
            recommendation: '5-minute break: Stand up, stretch, look away'
          });
        }
        
        // Stress alert (only when mic is active)
        if (m.stress_level > 0.7 && sensor.isMicActive()) {
          triggerAlert('stress', 300000, { 
            priority: 4, 
            title: '😰 High Stress Detected', 
            message: 'Voice patterns indicate elevated stress levels.',
            recommendation: 'Try 4-7-8 breathing: Inhale 4s, hold 7s, exhale 8s'
          });
        }
        
        // Blink rate alert (only when camera is active)
        if (m.blink_rate < 8 && sensor.isCamActive() && m.face_present) {
          triggerAlert('blink', 180000, { 
            priority: 3, 
            title: '👁️ Low Blink Rate', 
            message: `Blink rate: ${m.blink_rate.toFixed(0)}/min (normal: 12-20)`,
            recommendation: 'Blink slowly 10 times to lubricate eyes'
          });
        }
        
        // Eye strain alert (only when camera is active)
        if (m.eye_strain > 0.7 && sensor.isCamActive() && m.face_present) {
          triggerAlert('eye_strain', 180000, { 
            priority: 3, 
            title: '👁️ Severe Eye Strain', 
            message: `Eye strain level at ${(m.eye_strain * 100).toFixed(0)}%. Your eyes need immediate rest.`,
            recommendation: 'Close eyes for 30 seconds, look at distant object'
          });
        }
        
        // High error rate alert
        if (m.error_rate > 0.12) {
          triggerAlert('errors', 300000, { 
            priority: 3, 
            title: '⌨️ High Error Rate', 
            message: `Error rate: ${(m.error_rate * 100).toFixed(0)}%`,
            recommendation: 'Take a 2-minute mental reset break'
          });
        }
        
        // Low focus alert
        if (m.focus_score < 0.35 && m.idle_time < 120 && m.wpm > 10) {
          triggerAlert('focus', 300000, { 
            priority: 3, 
            title: '🎯 Focus Declining', 
            message: `Focus score: ${(m.focus_score * 100).toFixed(0)}%`,
            recommendation: 'Try Pomodoro Technique: 25 min focus, 5 min break'
          });
        }
        
        // Inactivity alert
        if (m.idle_time > 600) {
          triggerAlert('inactive', 600000, { 
            priority: 2, 
            title: '💪 Extended Inactivity', 
            message: `Inactive for ${Math.floor(m.idle_time / 60)} minutes`,
            recommendation: 'Stand up, stretch, walk around for 2-3 minutes'
          });
        }
        
        // Positive productivity alert (only when metrics are good)
        if (m.productivity_score > 0.85 && m.focus_score > 0.75 && (sensor.isCamActive() || sensor.isMicActive())) {
          triggerAlert('productivity', 600000, { 
            priority: 1, 
            title: '🌟 High Productivity!', 
            message: `Productivity score: ${(m.productivity_score * 100).toFixed(0)}%`,
            recommendation: 'Excellent work! Remember to take breaks to sustain performance'
          });
        }
      }
      
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);

  const dismissAlert = useCallback((id) => setAlerts(prev => prev.filter(a => a.id !== id)), []);
  const dismissSuggestion = useCallback((id) => setSuggestions(prev => prev.filter(s => s.id !== id)), []);

  return {
    history, alerts, dismissAlert,
    camActive, micActive, active, faceDetected, isEnabling, showPermissionHelp,
    suggestions, dismissSuggestion, fatigueScore,
    activityStatus, realtimeAdvice,
    enableSensors, startCamera, startMicrophone, stopCamera, stopMicrophone,
    sessStart, metrics
  };
}

// ─── COMPONENTS ────────────────────────────────────────────────────────────────
const Card = React.memo(({ title, children, accent }) => (
  <div style={{ background: 'rgba(255,255,255,0.07)', backdropFilter: 'blur(20px)', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 20, padding: 20, position: 'relative', overflow: 'hidden', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
    <div style={{ position: 'absolute', top: 0, left: 20, right: 20, height: 1, background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent)' }} />
    {accent && <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: accent, borderRadius: '0 0 20px 20px', opacity: 0.85 }} />}
    {title && (
      <div style={{ fontFamily: 'Space Mono,monospace', fontSize: 11, fontWeight: 700, color: '#cdd6f4', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 9 }}>
        <div style={{ width: 3, height: 13, background: 'linear-gradient(180deg,#00e5ff,#a78bfa)', borderRadius: 2, flexShrink: 0 }} />
        {title}
      </div>
    )}
    {children}
  </div>
));

const Tip = React.memo(({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'rgba(8,15,30,0.97)', border: '1px solid rgba(255,255,255,0.18)', borderRadius: 10, padding: '10px 14px', fontFamily: 'Space Mono,monospace' }}>
      <div style={{ fontSize: 9, color: '#9399b2', marginBottom: 6 }}>{label}</div>
      {payload.map((p, i) => <div key={i} style={{ fontSize: 11, color: p.color || '#fff', fontWeight: 700 }}>{p.name}: {typeof p.value === 'number' ? (p.value < 2 ? (p.value * 100).toFixed(1) + '%' : p.value.toFixed(1)) : p.value}</div>)}
    </div>
  );
});

const Heatmap = React.memo(({ history }) => {
  const cells = history.slice(-60);
  const getColor = s => s < 0.35 ? '#00ff9d' : s < 0.55 ? '#ffe566' : s < 0.75 ? '#ff9838' : '#ff3b5c';
  return (
    <div>
      <div style={{ fontFamily: 'Space Mono,monospace', fontSize: 9, color: '#9399b2', marginBottom: 12, letterSpacing: '0.1em' }}>LAST 60 READINGS · FATIGUE INTENSITY</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12,1fr)', gap: 4, background: 'rgba(0,0,0,0.15)', padding: 12, borderRadius: 12, marginBottom: 12 }}>
        {Array.from({ length: 60 }).map((_, i) => {
          const cell = cells[i];
          const s = cell?.fatigue_score ?? 0;
          return <div key={i} title={cell ? `${(s * 100).toFixed(0)}% @ ${cell.time}` : 'No data'} style={{ aspectRatio: '1', background: cell ? getColor(s) : 'rgba(255,255,255,0.04)', borderRadius: 4, opacity: cell ? 0.55 + s * 0.45 : 0.25, transition: 'background 0.8s, opacity 0.8s' }} />;
        })}
      </div>
      <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
        {[['#00ff9d', 'Optimal'], ['#ffe566', 'Mild'], ['#ff9838', 'Moderate'], ['#ff3b5c', 'Critical']].map(([c, l]) => (
          <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'Space Mono,monospace', fontSize: 9, color: '#9399b2' }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: c }} />{l}
          </div>
        ))}
      </div>
    </div>
  );
});

const PredictionTrend = React.memo(({ history }) => {
  const last = history[history.length - 1];
  if (!last || history.length < 5) return <div style={{ fontFamily: 'Space Mono,monospace', fontSize: 10, color: '#6c7086', padding: '24px 0', textAlign: 'center' }}>Collecting data...</div>;
  
  const predictNext = Math.min(1, Math.max(0, last.fatigue_score + (last.trend ?? 0) * 4));
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 20 }}>
          <div><div style={{ fontSize: 8, color: '#9399b2' }}>Current</div><div style={{ fontSize: 18, fontWeight: 700, color: '#a78bfa' }}>{(last.fatigue_score * 100).toFixed(0)}%</div></div>
          <div><div style={{ fontSize: 8, color: '#9399b2' }}>Next ~2 min</div><div style={{ fontSize: 18, fontWeight: 700, color: '#ff9838' }}>{(predictNext * 100).toFixed(0)}%</div></div>
        </div>
        <div style={{ padding: '4px 12px', borderRadius: 16, background: last.trend > 0 ? 'rgba(255,59,92,0.12)' : 'rgba(0,255,157,0.12)', border: `1px solid ${last.trend > 0 ? 'rgba(255,59,92,0.3)' : 'rgba(0,255,157,0.3)'}`, fontSize: 10, fontWeight: 700, color: last.trend > 0 ? '#ff3b5c' : '#00ff9d' }}>
          {last.trend > 0 ? `↑ RISING +${(last.trend * 100).toFixed(1)}%` : `↓ FALLING ${(last.trend * 100).toFixed(1)}%`}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <LineChart data={history.slice(-20).map(h => ({ time: h.time, score: h.fatigue_score }))} margin={{ top: 5, right: 5, left: -18, bottom: 5 }}>
          <CartesianGrid strokeDasharray="2 2" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="time" tick={false} />
          <YAxis domain={[0, 1]} tick={{ fontSize: 8, fill: '#6c7086' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
          <Tooltip content={<Tip />} />
          <Line type="monotone" dataKey="score" stroke="#a78bfa" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
});

const PermissionHelpModal = ({ onClose }) => (
  <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
    <div style={{ background: 'linear-gradient(135deg, #1a1a2e, #16213e)', borderRadius: 24, padding: 32, maxWidth: 500, border: '1px solid rgba(0,229,255,0.3)', boxShadow: '0 0 40px rgba(0,229,255,0.2)' }}>
      <div style={{ fontSize: 48, textAlign: 'center', marginBottom: 16 }}>🔒</div>
      <h2 style={{ color: '#00e5ff', marginBottom: 16, textAlign: 'center' }}>Camera & Microphone Access Required</h2>
      <div style={{ background: 'rgba(0,229,255,0.1)', borderRadius: 12, padding: 16, marginBottom: 24 }}>
        <div style={{ fontWeight: 700, color: '#00e5ff', marginBottom: 12 }}>📋 Steps to Enable:</div>
        <ol style={{ marginLeft: 20, color: '#cdd6f4', fontSize: 13, lineHeight: 1.8 }}>
          <li>Click the <strong>camera/microphone icon</strong> in your browser address bar</li>
          <li>Select <strong style={{ color: '#00ff9d' }}>"Allow"</strong> for both camera and microphone</li>
          <li>Click <strong style={{ color: '#00ff9d' }}>"Enable All Sensors"</strong> again</li>
        </ol>
      </div>
      <button onClick={onClose} style={{ width: '100%', padding: '12px', borderRadius: 10, background: 'linear-gradient(135deg, #00e5ff, #a78bfa)', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 700 }}>Got it</button>
    </div>
  </div>
);

// ─── MAIN DASHBOARD ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const {
    history, alerts, dismissAlert,
    camActive, micActive, active, faceDetected, isEnabling, showPermissionHelp,
    suggestions, dismissSuggestion, fatigueScore,
    activityStatus, realtimeAdvice,
    enableSensors, startCamera, startMicrophone, stopCamera, stopMicrophone,
    sessStart, metrics
  } = useLiveData();

  const [now, setNow] = useState(new Date());
  const [sessMs, setSessMs] = useState(0);

  useEffect(() => {
    const t = setInterval(() => { setNow(new Date()); setSessMs(Date.now() - sessStart.current); }, 1000);
    return () => clearInterval(t);
  }, [sessStart]);

  const snap = history[history.length - 1] ?? null;
  const level = LEVELS[snap?.fatigue_level ?? 'fresh'];
  const pct = Math.round((snap?.fatigue_score ?? 0) * 100);
  const blinkRate = snap?.metrics?.blink_rate ?? 0;
  const stressLevel = snap?.metrics?.stress_level ?? 0.3;
  const focusScore = snap?.metrics?.focus_score ?? 0.7;
  const energyLevel = snap?.metrics?.energy_level ?? 0.6;
  const productivityScore = snap?.metrics?.productivity_score ?? 0.65;

  const radarData = useMemo(() => snap ? [
    { s: 'Focus', v: snap.metrics?.focus_score ?? 0.7 },
    { s: 'Energy', v: snap.metrics?.energy_level ?? 0.6 },
    { s: 'Productivity', v: snap.metrics?.productivity_score ?? 0.65 },
    { s: 'Concentration', v: snap.metrics?.concentration ?? 0.7 },
    { s: 'Accuracy', v: 1 - (snap.metrics?.error_rate ?? 0) },
    { s: 'Stress', v: 1 - (snap.metrics?.stress_level ?? 0.3) },
  ] : [], [snap?.metrics]);

  const modalityBarData = useMemo(() => [
    { name: 'Eye', value: (camActive ? 30 : 10), color: '#a78bfa' },
    { name: 'Keyboard', value: 28, color: '#00e5ff' },
    { name: 'Voice', value: (micActive ? 22 : 8), color: '#00ff9d' },
    { name: 'Screen', value: 20, color: '#ff9838' },
  ], [camActive, micActive]);

  const fmtSess = ms => {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 3600)).padStart(2, '0')}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  };

  // Format date for header
  const formattedDate = now.toLocaleDateString('en-US', { 
    weekday: 'short', 
    month: 'short', 
    day: 'numeric',
    year: 'numeric'
  });
  const formattedTime = now.toLocaleTimeString('en', { hour12: false });

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg,#0f0c29 0%,#1a1a6e 40%,#24243e 100%)', backgroundAttachment: 'fixed', position: 'relative', overflowX: 'hidden' }}>
      {showPermissionHelp && <PermissionHelpModal onClose={() => {}} />}
      
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, background: 'radial-gradient(ellipse at 20% 20%,rgba(0,229,255,0.06) 0%,transparent 55%),radial-gradient(ellipse at 80% 80%,rgba(167,139,250,0.08) 0%,transparent 55%)' }} />
      <div style={{ position: 'relative', zIndex: 1, maxWidth: 1400, margin: '0 auto', padding: '20px 24px 40px' }}>

        {/* Header Section with Date/Time */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16, marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ width: 56, height: 56, borderRadius: 14, background: 'linear-gradient(135deg,#00e5ff,#a78bfa)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32, boxShadow: '0 0 30px rgba(0,229,255,0.5)' }}>🧠</div>
              <div>
                <h1 style={{ fontFamily: 'Syne,sans-serif', fontSize: 28, fontWeight: 800, color: '#fff', margin: 0 }}>
                  Mind<span style={{ color: '#00e5ff' }}>Guard</span> <span style={{ color: '#a78bfa' }}>AI</span>
                </h1>
                <p style={{ fontSize: 13, color: '#8a9eb0', marginTop: 6, maxWidth: 550 }}>
                  Real-time cognitive load monitor using AI-powered analysis of eye tracking, voice patterns, keyboard dynamics, and mouse movements
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ padding: '8px 18px', background: 'rgba(255,255,255,0.1)', borderRadius: 24, fontSize: 13, fontFamily: 'monospace' }}>
                📅 {formattedDate}
              </div>
              <div style={{ padding: '8px 18px', background: 'rgba(255,255,255,0.1)', borderRadius: 24, fontSize: 13, fontFamily: 'monospace' }}>
                ⏰ {formattedTime}
              </div>
            </div>
          </div>
          
          {/* Sensor Control Bar */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', background: 'rgba(255,255,255,0.03)', borderRadius: 16, padding: '12px 20px' }}>
            {!camActive && !micActive ? (
              <button onClick={enableSensors} disabled={isEnabling} style={{ padding: '10px 28px', borderRadius: 12, background: 'linear-gradient(135deg, #00e5ff, #a78bfa)', border: 'none', color: '#fff', fontWeight: 700, fontSize: 14, cursor: isEnabling ? 'not-allowed' : 'pointer', boxShadow: '0 0 20px rgba(0,229,255,0.4)' }}>
                {isEnabling ? '⏳ Starting...' : '🚀 Enable All Sensors'}
              </button>
            ) : (
              <>
                <button onClick={startCamera} disabled={camActive} style={{ padding: '8px 20px', borderRadius: 10, background: camActive ? 'rgba(0,255,157,0.2)' : 'rgba(167,139,250,0.2)', border: `1px solid ${camActive ? 'rgba(0,255,157,0.4)' : 'rgba(167,139,250,0.4)'}`, color: camActive ? '#00ff9d' : '#a78bfa', fontWeight: 600, cursor: camActive ? 'default' : 'pointer' }}>
                  {camActive ? '✅ Camera On' : '📹 Start Camera'}
                </button>
                <button onClick={stopCamera} disabled={!camActive} style={{ padding: '8px 20px', borderRadius: 10, background: 'rgba(255,59,92,0.2)', border: '1px solid rgba(255,59,92,0.4)', color: '#ff3b5c', fontWeight: 600, cursor: camActive ? 'pointer' : 'default', opacity: camActive ? 1 : 0.5 }}>
                  🛑 Stop Camera
                </button>
                <button onClick={startMicrophone} disabled={micActive} style={{ padding: '8px 20px', borderRadius: 10, background: micActive ? 'rgba(0,255,157,0.2)' : 'rgba(0,255,157,0.2)', border: `1px solid ${micActive ? 'rgba(0,255,157,0.4)' : 'rgba(0,255,157,0.4)'}`, color: micActive ? '#00ff9d' : '#00ff9d', fontWeight: 600, cursor: micActive ? 'default' : 'pointer' }}>
                  {micActive ? '✅ Mic On' : '🎙 Start Mic'}
                </button>
                <button onClick={stopMicrophone} disabled={!micActive} style={{ padding: '8px 20px', borderRadius: 10, background: 'rgba(255,59,92,0.2)', border: '1px solid rgba(255,59,92,0.4)', color: '#ff3b5c', fontWeight: 600, cursor: micActive ? 'pointer' : 'default', opacity: micActive ? 1 : 0.5 }}>
                  🛑 Stop Mic
                </button>
              </>
            )}
            
            <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
              {[
                { label: 'CAM', ok: camActive, color: '#a78bfa' },
                { label: 'MIC', ok: micActive, color: '#00ff9d' },
                { label: 'FACE', ok: faceDetected, color: '#00ff9d' },
                { label: 'KBD', ok: true, color: '#00e5ff' },
                { label: 'MSE', ok: true, color: '#ff9838' },
              ].map(s => (
                <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10, color: s.ok ? s.color : '#4a5a70', background: s.ok ? `${s.color}12` : 'rgba(255,255,255,0.03)', border: `1px solid ${s.ok ? s.color + '30' : 'rgba(255,255,255,0.07)'}`, borderRadius: 8, padding: '4px 12px' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: s.ok ? s.color : '#2a3a50', animation: s.ok ? 'pulse 2s infinite' : 'none' }} />
                  {s.label}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Activity Status Banner - Only show when sensors are active */}
        {(camActive || micActive) && (
          <div style={{ 
            background: `linear-gradient(135deg, ${activityStatus.color}20, ${activityStatus.color}08)`,
            border: `2px solid ${activityStatus.color}`,
            borderRadius: 20,
            padding: '20px 28px',
            marginBottom: 28,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 20,
            boxShadow: `0 0 30px ${activityStatus.color}40`
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <div style={{ fontSize: 56 }}>{activityStatus.icon}</div>
              <div>
                <div style={{ fontSize: 24, fontWeight: 800, color: activityStatus.color }}>
                  {activityStatus.label}
                </div>
                <div style={{ fontSize: 14, color: '#cdd6f4', marginTop: 4 }}>
                  {activityStatus.message}
                </div>
              </div>
            </div>
            <div style={{ 
              background: 'rgba(0,0,0,0.35)',
              borderRadius: 14,
              padding: '12px 24px',
              maxWidth: 380
            }}>
              <div style={{ fontSize: 11, color: '#9399b2', marginBottom: 6 }}>💡 Real-Time Advice</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>{realtimeAdvice}</div>
            </div>
          </div>
        )}

        {/* Quick Stats Grid - 8 Key Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 14, marginBottom: 28 }}>
          {[
            { label: 'Fatigue', value: `${pct}%`, color: level.color, tooltip: level.recommendation },
            { label: 'Stress', value: `${Math.round(stressLevel * 100)}%`, color: stressLevel > 0.6 ? '#ff3b5c' : stressLevel > 0.3 ? '#ff9838' : '#00ff9d' },
            { label: 'Focus', value: `${Math.round(focusScore * 100)}%`, color: focusScore > 0.7 ? '#00ff9d' : focusScore > 0.4 ? '#ffe566' : '#ff9838' },
            { label: 'Energy', value: `${Math.round(energyLevel * 100)}%`, color: energyLevel > 0.6 ? '#00ff9d' : energyLevel > 0.3 ? '#ffe566' : '#ff9838' },
            { label: 'Productivity', value: `${Math.round(productivityScore * 100)}%`, color: productivityScore > 0.7 ? '#00ff9d' : productivityScore > 0.4 ? '#ffe566' : '#ff9838' },
            { label: 'Blink Rate', value: `${blinkRate.toFixed(0)}/m`, color: '#a78bfa' },
            { label: 'WPM', value: `${(snap?.metrics?.wpm ?? 0).toFixed(0)}`, color: '#00e5ff' },
            { label: 'Session', value: fmtSess(sessMs), color: '#00e5ff' },
          ].map((s, i) => (
            <div key={i} title={s.tooltip} style={{ background: `linear-gradient(135deg,${s.color}22,${s.color}08)`, backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.13)', borderRadius: 14, padding: '12px 8px', textAlign: 'center', position: 'relative' }}>
              <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 3, background: s.color, opacity: 0.75, borderRadius: '0 0 14px 14px' }} />
              <div style={{ fontSize: 10, color: '#cdd6f4', textTransform: 'uppercase', marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Main 2-Column Layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24 }}>
          
          {/* LEFT COLUMN - Charts */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Timeline Chart */}
            <Card title="Cognitive Metrics Timeline" accent="linear-gradient(90deg,#a78bfa,#00e5ff)">
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={history.slice(-70).map(h => ({ 
                  time: h.time, 
                  fatigue: h.fatigue_score, 
                  stress: h.metrics?.stress_level ?? 0.3,
                  focus: h.metrics?.focus_score ?? 0.7,
                }))}>
                  <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#6c7086' }} tickLine={false} interval={10} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 9, fill: '#6c7086' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip content={<Tip />} />
                  <Area type="monotone" dataKey="fatigue" name="Fatigue" stroke="#a78bfa" strokeWidth={2} fill="url(#fatigueGrad)" />
                  <Line type="monotone" dataKey="stress" name="Stress" stroke="#ff9838" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="focus" name="Focus" stroke="#00e5ff" strokeWidth={2} dot={false} />
                  <defs>
                    <linearGradient id="fatigueGrad"><stop offset="5%" stopColor="#a78bfa" stopOpacity={0.4} /><stop offset="95%" stopColor="#a78bfa" stopOpacity={0} /></linearGradient>
                  </defs>
                </ComposedChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginTop: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, background: '#a78bfa', borderRadius: 2 }} /><span style={{ fontSize: 10, color: '#9399b2' }}>Fatigue</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, background: '#ff9838', borderRadius: 2 }} /><span style={{ fontSize: 10, color: '#9399b2' }}>Stress</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><div style={{ width: 12, height: 12, background: '#00e5ff', borderRadius: 2 }} /><span style={{ fontSize: 10, color: '#9399b2' }}>Focus</span></div>
              </div>
            </Card>

            {/* Two Charts Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              <Card title="Cognitive Radar" accent="linear-gradient(90deg,#00e5ff,#a78bfa)">
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                    <PolarGrid stroke="rgba(255,255,255,0.09)" />
                    <PolarAngleAxis dataKey="s" tick={{ fontSize: 10, fill: '#cdd6f4' }} />
                    <Radar dataKey="v" stroke="#00e5ff" fill="#00e5ff" fillOpacity={0.2} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </Card>

              <Card title="Sensor Contribution" accent="linear-gradient(90deg,#00ff9d,#a78bfa)">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={modalityBarData} layout="vertical">
                    <XAxis type="number" domain={[0, 50]} tick={{ fontSize: 10, fill: '#6c7086' }} tickFormatter={v => `${v}%`} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#cdd6f4' }} width={75} />
                    <Tooltip content={<Tip />} />
                    <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                      {modalityBarData.map((e, i) => <Cell key={i} fill={e.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>

            {/* Heatmap */}
            <Card title="Fatigue Intensity Heatmap" accent="linear-gradient(90deg,#00ff9d,#ffe566,#ff3b5c)">
              <Heatmap history={history} />
            </Card>

            {/* Prediction Trend */}
            <Card title="Predictive Trend Analysis" accent="linear-gradient(90deg,#a78bfa,#ff3b5c)">
              <PredictionTrend history={history} />
            </Card>
          </div>

          {/* RIGHT COLUMN - Alerts & Suggestions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            
            {/* Real-Time Alerts - Only show when sensors are active or there are alerts */}
            <Card title={`🔔 ALERTS ${alerts.length > 0 ? `(${alerts.length})` : ''}`} accent="linear-gradient(90deg,#ff3b5c,#ff9838)">
              <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                {!camActive && !micActive ? (
                  <div style={{ textAlign: 'center', padding: '48px 20px', color: '#6c7086' }}>
                    <div style={{ fontSize: 48, marginBottom: 12 }}>🎥</div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>Enable Sensors</div>
                    <div style={{ fontSize: 11, marginTop: 6, color: '#4a5a70' }}>Click "Enable All Sensors" to start receiving real-time alerts</div>
                  </div>
                ) : alerts.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '48px 20px', color: '#6c7086' }}>
                    <div style={{ fontSize: 48, marginBottom: 12 }}>✓</div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>No active alerts</div>
                    <div style={{ fontSize: 11, marginTop: 6, color: '#4a5a70' }}>All systems operating normally</div>
                  </div>
                ) : (
                  alerts.map(a => (
                    <div key={a.id} style={{ 
                      background: 'rgba(255,255,255,0.05)', 
                      borderLeft: `4px solid ${a.priority >= 5 ? '#ff3b5c' : a.priority >= 3 ? '#ff9838' : '#ffe566'}`,
                      borderRadius: 12, 
                      padding: '14px 40px 14px 16px', 
                      marginBottom: 12, 
                      position: 'relative'
                    }}>
                      <button onClick={() => dismissAlert(a.id)} style={{ position: 'absolute', top: 12, right: 12, background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 6, color: '#6c7086', cursor: 'pointer', fontSize: 14, padding: '2px 8px' }}>×</button>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 6 }}>{a.title}</div>
                      <div style={{ fontSize: 12, color: '#cdd6f4', marginBottom: 6 }}>{a.message}</div>
                      {a.recommendation && (
                        <div style={{ fontSize: 11, color: '#a78bfa', marginTop: 6, padding: '6px 10px', background: 'rgba(167,139,250,0.1)', borderRadius: 8 }}>
                          💡 {a.recommendation}
                        </div>
                      )}
                      <div style={{ fontSize: 9, color: '#6c7086', marginTop: 8 }}>{a.timestamp}</div>
                    </div>
                  ))
                )}
              </div>
            </Card>

            {/* AI Suggestions */}
            <Card title="✨ AI Suggestions" accent="linear-gradient(90deg,#00ff9d,#00e5ff)">
              <div style={{ maxHeight: 300, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
                {!camActive && !micActive ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6c7086' }}>
                    <div style={{ fontSize: 32, marginBottom: 12 }}>🧠</div>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>Enable sensors for personalized insights</div>
                    <div style={{ fontSize: 10, marginTop: 6, color: '#4a5a70' }}>Camera and microphone access required</div>
                  </div>
                ) : suggestions.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6c7086' }}>
                    <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>No suggestions yet</div>
                    <div style={{ fontSize: 10, marginTop: 6, color: '#4a5a70' }}>Continue working to receive personalized recommendations</div>
                  </div>
                ) : (
                  suggestions.map(s => (
                    <div key={s.id} style={{ 
                      background: s.priority === 'high' ? 'rgba(255,59,92,0.15)' : s.priority === 'medium' ? 'rgba(255,152,56,0.1)' : 'rgba(0,255,157,0.05)',
                      borderLeft: `3px solid ${s.priority === 'high' ? '#ff3b5c' : s.priority === 'medium' ? '#ff9838' : '#00ff9d'}`,
                      borderRadius: 10, 
                      padding: '12px',
                      position: 'relative'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                        <span style={{ fontSize: 20 }}>{s.icon}</span>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>{s.title}</div>
                      </div>
                      <div style={{ fontSize: 11, color: '#cdd6f4', marginBottom: 8 }}>{s.description}</div>
                      <div style={{ fontSize: 10, color: '#a78bfa', background: 'rgba(167,139,250,0.1)', padding: '6px 10px', borderRadius: 6 }}>
                        💡 {s.recommendation}
                      </div>
                      <button onClick={() => dismissSuggestion(s.id)} style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 4, color: '#6c7086', cursor: 'pointer', fontSize: 12, padding: '2px 6px' }}>×</button>
                    </div>
                  ))
                )}
              </div>
            </Card>

            {/* Live Metrics Dashboard */}
            <Card title="📊 Live Metrics" accent="linear-gradient(90deg,#00ff9d,#a78bfa)">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: 10, color: '#9399b2', marginBottom: 6 }}>Blink Rate</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#a78bfa' }}>{blinkRate.toFixed(0)}<span style={{ fontSize: 12, color: '#6c7086' }}>/min</span></div>
                  <div style={{ fontSize: 9, color: camActive && blinkRate > 12 ? '#00ff9d' : '#6c7086', marginTop: 4 }}>{camActive ? (blinkRate > 12 ? 'Normal' : 'Monitor') : 'Camera off'}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: 10, color: '#9399b2', marginBottom: 6 }}>WPM</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#00e5ff' }}>{(snap?.metrics?.wpm ?? 0).toFixed(0)}</div>
                  <div style={{ fontSize: 9, color: (snap?.metrics?.wpm ?? 0) > 40 ? '#00ff9d' : '#6c7086', marginTop: 4 }}>{(snap?.metrics?.wpm ?? 0) > 40 ? 'Good speed' : 'Active'}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: 10, color: '#9399b2', marginBottom: 6 }}>Error Rate</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#ff3b5c' }}>{((snap?.metrics?.error_rate ?? 0) * 100).toFixed(1)}%</div>
                  <div style={{ fontSize: 9, color: (snap?.metrics?.error_rate ?? 0) < 0.05 ? '#00ff9d' : '#6c7086', marginTop: 4 }}>{(snap?.metrics?.error_rate ?? 0) < 0.05 ? 'Good' : 'Monitor'}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: 10, color: '#9399b2', marginBottom: 6 }}>Voice Energy</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#ff9838' }}>{Math.round((snap?.metrics?.mic_energy ?? 0) * 100)}%</div>
                  <div style={{ fontSize: 9, color: micActive ? '#00ff9d' : '#6c7086', marginTop: 4 }}>{micActive ? 'Active' : 'Mic off'}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: 10, color: '#9399b2', marginBottom: 6 }}>Mouse Speed</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#ffe566' }}>{(snap?.metrics?.mouse_vel ?? 0).toFixed(0)}<span style={{ fontSize: 12 }}>px/s</span></div>
                  <div style={{ fontSize: 9, color: '#6c7086', marginTop: 4 }}>Active movement</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: 10, color: '#9399b2', marginBottom: 6 }}>Idle Time</div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: '#6c8a9e' }}>{Math.floor((snap?.metrics?.idle_time ?? 0) / 60)}<span style={{ fontSize: 12 }}>min</span></div>
                  <div style={{ fontSize: 9, color: (snap?.metrics?.idle_time ?? 0) < 60 ? '#00ff9d' : '#ff9838', marginTop: 4 }}>{(snap?.metrics?.idle_time ?? 0) < 60 ? 'Active' : 'Break time'}</div>
                </div>
              </div>
            </Card>

            {/* Fatigue Level Recommendation */}
            <Card title="💪 Current Recommendation" accent={`linear-gradient(90deg,${level.color},#a78bfa)`}>
              <div style={{ textAlign: 'center', padding: '12px' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>{level.label === 'OPTIMAL' ? '🎯' : level.label === 'MILD' ? '🌿' : level.label === 'MODERATE' ? '⚠️' : '🚨'}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: level.color, marginBottom: 8 }}>{level.label} Level</div>
                <div style={{ fontSize: 13, color: '#cdd6f4', lineHeight: 1.5 }}>{level.recommendation}</div>
                <div style={{ marginTop: 12, padding: '8px 16px', background: `${level.color}20`, borderRadius: 10, display: 'inline-block' }}>
                  <span style={{ fontSize: 12, color: level.color, fontWeight: 600 }}>{level.action}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: 40, paddingTop: 20, borderTop: '1px solid rgba(255,255,255,0.07)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 10, color: '#4a5a70' }}>
          <div>🧠 MindGuard AI · Real-Time Cognitive Load Prevention · Powered by Advanced AI Analytics</div>
          <div>{history.length} samples recorded · {camActive ? (faceDetected ? 'Face tracked' : 'Camera active') : 'Camera off'} · {micActive ? 'Mic active' : 'Mic off'}</div>
        </div>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Syne', sans-serif; background: #0f0c29; overflow-x: hidden; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 3px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
      `}</style>
    </div>
  );
}