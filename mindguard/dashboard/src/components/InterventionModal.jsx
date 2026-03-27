import React, { useState, useEffect } from 'react';
import './InterventionModal.css';

const InterventionModal = ({ intervention, onDismiss, onComplete }) => {
  const [timeLeft, setTimeLeft] = useState(intervention?.duration_seconds || 60);
  const [selectedAction, setSelectedAction] = useState(null);

  useEffect(() => {
    if (!intervention) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [intervention]);

  if (!intervention) return null;

  const getIcon = () => {
    switch (intervention.type) {
      case 'break_reminder':
        return '☕';
      case 'breathing_exercise':
        return '🧘';
      case 'hydration_reminder':
        return '💧';
      case 'task_switch_suggestion':
        return '🔄';
      case 'stretch_reminder':
        return '🤸';
      case 'focus_recovery':
        return '🎯';
      case 'energy_boost':
        return '⚡';
      default:
        return '🔔';
    }
  };

  const getColor = () => {
    switch (intervention.level) {
      case 'critical':
        return '#F44336';
      case 'warning':
        return '#FF9800';
      case 'suggestion':
        return '#4CAF50';
      default:
        return '#4A90E2';
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="intervention-modal-overlay">
      <div className="intervention-modal" style={{ borderColor: getColor() }}>
        <div className="modal-header" style={{ background: `linear-gradient(135deg, ${getColor()}20, transparent)` }}>
          <div className="modal-icon" style={{ backgroundColor: getColor() }}>
            {getIcon()}
          </div>
          <div className="modal-title">
            <h2>{intervention.type.replace(/_/g, ' ').toUpperCase()}</h2>
            <span className="modal-level" style={{ backgroundColor: getColor() }}>
              {intervention.level}
            </span>
          </div>
          <button className="modal-close" onClick={onDismiss}>×</button>
        </div>

        <div className="modal-content">
          <p className="modal-message">{intervention.message}</p>

          <div className="modal-timer">
            <div className="timer-circle">
              <svg width="80" height="80">
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  fill="none"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth="4"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  fill="none"
                  stroke={getColor()}
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 36}`}
                  strokeDashoffset={2 * Math.PI * 36 * (1 - timeLeft / intervention.duration_seconds)}
                  transform="rotate(-90 40 40)"
                />
                <text x="40" y="45" textAnchor="middle" fill="white" fontSize="16">
                  {formatTime(timeLeft)}
                </text>
              </svg>
            </div>
          </div>

          {intervention.actions && intervention.actions.length > 0 && (
            <div className="modal-actions">
              <h3>Choose action:</h3>
              <div className="action-buttons">
                {intervention.actions.map((action, idx) => (
                  <button
                    key={idx}
                    className={`action-btn ${selectedAction === idx ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedAction(idx);
                      if (action === 'Dismiss') {
                        onDismiss();
                      } else if (action.includes('Take') || action.includes('Start')) {
                        onComplete();
                      }
                    }}
                    style={selectedAction === idx ? { backgroundColor: getColor() } : {}}
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="modal-footer">
            <button className="dismiss-btn" onClick={onDismiss}>
              Dismiss
            </button>
            <button className="complete-btn" onClick={onComplete} style={{ backgroundColor: getColor() }}>
              Complete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterventionModal;