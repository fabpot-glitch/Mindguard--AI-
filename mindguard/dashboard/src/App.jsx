import React, { useState, useEffect } from "react";
import "./App.css";

// ── AUTH PAGES ────────────────────────────────────────────────
import LoginPage  from "./pages/LoginPage";
import SignUpPage from "./pages/SignUpPage";

// ── HOOKS ────────────────────────────────────────────────────
import { useWebSocket }      from "./hooks/useWebSocket";
import { useCognitiveState } from "./hooks/useCognitiveState";
import { useIntervention }   from "./hooks/useIntervention";
import { useSessionTimer }   from "./hooks/useSessionTimer";

// ── COMPONENTS ───────────────────────────────────────────────
import Header             from "./components/Header";
import Dashboard          from "./components/Dashboard";
import CognitiveGauge     from "./components/CognitiveGauge";
import Timeline           from "./components/Timeline";
import RadarChart         from "./components/RadarChart";
import InterventionModal  from "./components/InterventionModal";
import AlertLog           from "./components/AlertLog";
import PredictionPanel    from "./components/PredictionPanel";
import SignalStatus       from "./components/SignalStatus";
import ModeSelector       from "./components/ModeSelector";
import BreathingExercise  from "./components/BreathingExercise";
import SessionTimer       from "./components/SessionTimer";
import WeeklyReport       from "./components/WeeklyReport";

// ── CONFIG ────────────────────────────────────────────────────
const WS_URL  = process.env.REACT_APP_WS_URL  || "ws://localhost:8000/ws";
const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// ══════════════════════════════════════════════════════════════
// APP ROOT  —  handles auth routing + dashboard
// ══════════════════════════════════════════════════════════════
export default function App() {

  // ── AUTH STATE ────────────────────────────────────────────
  // Always start on 'login'. Only move to 'dashboard' after
  // successful login / signup, or if a valid session exists.
  const [screen, setScreen] = useState("login");
  const [user,   setUser]   = useState(null);

  // On mount: restore session only if mg_user exists in localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("mg_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && parsed.email) {
          setUser(parsed);
          setScreen("dashboard");
        }
      }
    } catch {
      // corrupted storage — clear it and stay on login
      localStorage.removeItem("mg_user");
    }
  }, []);

  const handleLogin  = (account) => { setUser(account); setScreen("dashboard"); };
  const handleSignUp = (account) => { setUser(account); setScreen("dashboard"); };

  const handleLogout = () => {
    localStorage.removeItem("mg_user");
    localStorage.removeItem("mg_settings");
    setUser(null);
    setScreen("login");
  };

  // ── HOOKS (always called — React rules of hooks) ──────────
  const { state: rawState, connected }      = useWebSocket(WS_URL);
  const { cognitiveState, history, alerts } = useCognitiveState(rawState);
  const { intervention, dismiss }           = useIntervention(cognitiveState);
  const { sessionTime, resetTimer }         = useSessionTimer();

  // ── LOCAL STATE ───────────────────────────────────────────
  const [mode, setMode]                         = useState("FOCUS");
  const [showWeeklyReport, setShowWeeklyReport] = useState(false);

  // ── DERIVED RISK LEVEL ────────────────────────────────────
  const riskLevel = (() => {
    if (!cognitiveState) return "NOMINAL";
    const { fatigue, stress } = cognitiveState;
    if (fatigue > 70 || stress > 65) return "CRITICAL";
    if (fatigue > 50 || stress > 50) return "ELEVATED";
    return "NOMINAL";
  })();

  // ── SEND MODE CHANGE TO BACKEND ───────────────────────────
  useEffect(() => {
    if (screen !== "dashboard") return;
    fetch(`${API_URL}/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    }).catch(() => {});
  }, [mode, screen]);

  // ══════════════════════════════════════════════════════════
  // AUTH SCREENS — shown before dashboard
  // ══════════════════════════════════════════════════════════
  if (screen === "login") {
    return (
      <LoginPage
        onLogin={handleLogin}
        onGoToSignUp={() => setScreen("signup")}
      />
    );
  }

  if (screen === "signup") {
    return (
      <SignUpPage
        onSignUp={handleSignUp}
        onGoToLogin={() => setScreen("login")}
      />
    );
  }

  // ══════════════════════════════════════════════════════════
  // DASHBOARD (authenticated)
  // ══════════════════════════════════════════════════════════
  return (
    <div className="app-root">

      {/* ── TOP HEADER BAR ─────────────────────────────────── */}
      <Header
        user={user}
        connected={connected}
        riskLevel={riskLevel}
        mode={mode}
        alerts={alerts}
        onLogout={handleLogout}
      >
        <ModeSelector mode={mode} onChange={setMode} />
        <SessionTimer sessionTime={sessionTime} onReset={resetTimer} />
      </Header>

      {/* ── MAIN DASHBOARD GRID ────────────────────────────── */}
      <Dashboard>

        {/* ── ROW 1: 4 COGNITIVE SCORE GAUGES ─────────────── */}
        <CognitiveGauge
          label="COGNITIVE LOAD" icon="🧠"
          value={cognitiveState?.cognitive ?? 0}
          description="Processing capacity"
        />
        <CognitiveGauge
          label="ATTENTION SCORE" icon="🎯"
          value={cognitiveState?.attention ?? 0}
          description="Focus level"
        />
        <CognitiveGauge
          label="STRESS INDEX" icon="⚡"
          value={cognitiveState?.stress ?? 0}
          description="Cortisol proxy"
          invert
        />
        <CognitiveGauge
          label="FATIGUE LEVEL" icon="💤"
          value={cognitiveState?.fatigue ?? 0}
          description="Neural exhaustion"
          invert
        />

        {/* ── ROW 2: TIMELINE + RADAR ──────────────────────── */}
        <Timeline history={history} />
        <RadarChart
          cognitive={cognitiveState?.cognitive ?? 0}
          attention={cognitiveState?.attention  ?? 0}
          stress={cognitiveState?.stress    ?? 0}
          fatigue={cognitiveState?.fatigue  ?? 0}
        />

        {/* ── ROW 3: PREDICTION / SIGNAL / ALERTS ──────────── */}
        <PredictionPanel
          cognitiveState={cognitiveState}
          mode={mode}
          connected={connected}
        />
        <SignalStatus connected={connected} mode={mode} />
        <AlertLog alerts={alerts} />

        {/* ── ROW 4: WEEKLY REPORT (toggled) ───────────────── */}
        {showWeeklyReport && (
          <WeeklyReport onClose={() => setShowWeeklyReport(false)} />
        )}

      </Dashboard>

      {/* ── BREATHING EXERCISE (BREAK mode) ──────────────────── */}
      {mode === "BREAK" && (
        <BreathingExercise onComplete={() => setMode("FOCUS")} />
      )}

      {/* ── INTERVENTION MODAL ───────────────────────────────── */}
      {intervention && (
        <InterventionModal
          intervention={intervention}
          onDismiss={dismiss}
          onStartBreath={() => setMode("BREAK")}
        />
      )}

      {/* ── WEEKLY REPORT TOGGLE ─────────────────────────────── */}
      <button
        className="weekly-report-btn"
        onClick={() => setShowWeeklyReport(prev => !prev)}
        title="Toggle Weekly Report"
      >
        📊
      </button>

    </div>
  );
}