import React, { useState, useEffect } from 'react';
import './BreathingExercise.css';

const BreathingExercise = ({ onClose, duration = 60 }) => {
  const [phase, setPhase] = useState('inhale');
  const [count, setCount] = useState(4);
  const [cycles, setCycles] = useState(0);
  const [isActive, setIsActive] = useState(true);

  // Breathing pattern: 4-7-8 method
  const phases = {
    inhale: { duration: 4, next: 'hold', instruction: 'Inhale slowly...' },
    hold: { duration: 7, next: 'exhale', instruction: 'Hold your breath...' },
    exhale: { duration: 8, next: 'inhale', instruction: 'Exhale gently...' }
  };

  useEffect(() => {
    if (!isActive) return;

    const timer = setInterval(() => {
      setCount(prev => {
        const newCount = prev - 1;
        
        if (newCount === 0) {
          // Move to next phase
          setPhase(prevPhase => {
            const nextPhase = phases[prevPhase].next;
            setCount(phases[nextPhase].duration);
            
            if (nextPhase === 'inhale') {
              setCycles(c => c + 1);
            }
            
            return nextPhase;
          });
          return phases[phase].duration;
        }
        
        return newCount;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [phase, isActive]);

  // Auto-close after duration
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, duration * 1000);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const circleSize = 200;
  const progress = (count / phases[phase].duration) * 100;

  return (
    <div className="breathing-overlay">
      <div className="breathing-modal">
        <div className="breathing-header">
          <h2>Breathing Exercise</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="breathing-content">
          <div className="breathing-circle-container">
            <svg width={circleSize} height={circleSize} className="breathing-circle">
              {/* Background circle */}
              <circle
                cx={circleSize / 2}
                cy={circleSize / 2}
                r={circleSize * 0.4}
                fill="none"
                stroke="rgba(74, 144, 226, 0.2)"
                strokeWidth="8"
              />
              
              {/* Progress circle */}
              <circle
                cx={circleSize / 2}
                cy={circleSize / 2}
                r={circleSize * 0.4}
                fill="none"
                stroke="#4A90E2"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * circleSize * 0.4}`}
                strokeDashoffset={2 * Math.PI * circleSize * 0.4 * (1 - progress / 100)}
                transform={`rotate(-90 ${circleSize / 2} ${circleSize / 2})`}
                style={{ transition: 'stroke-dashoffset 0.3s ease' }}
              />
            </svg>
            
            <div className="breathing-center">
              <div className={`phase-indicator ${phase}`}>
                {phases[phase].instruction}
              </div>
              <div className="phase-count">
                {count}s
              </div>
            </div>
          </div>

          <div className="breathing-info">
            <div className="cycle-counter">
              <span className="counter-label">Cycles Completed:</span>
              <span className="counter-value">{cycles}</span>
            </div>
            
            <div className="phase-steps">
              <div className={`step ${phase === 'inhale' ? 'active' : ''}`}>
                <span className="step-number">1</span>
                <span className="step-name">Inhale (4s)</span>
              </div>
              <div className={`step ${phase === 'hold' ? 'active' : ''}`}>
                <span className="step-number">2</span>
                <span className="step-name">Hold (7s)</span>
              </div>
              <div className={`step ${phase === 'exhale' ? 'active' : ''}`}>
                <span className="step-number">3</span>
                <span className="step-name">Exhale (8s)</span>
              </div>
            </div>

            <div className="breathing-tips">
              <h4>Tips:</h4>
              <ul>
                <li>Breathe deeply from your diaphragm</li>
                <li>Keep your shoulders relaxed</li>
                <li>Focus on the sensation of breathing</li>
                <li>If you feel dizzy, return to normal breathing</li>
              </ul>
            </div>
          </div>

          <div className="breathing-controls">
            <button 
              className="pause-btn"
              onClick={() => setIsActive(!isActive)}
            >
              {isActive ? 'Pause' : 'Resume'}
            </button>
            <button className="done-btn" onClick={onClose}>
              I'm Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BreathingExercise;