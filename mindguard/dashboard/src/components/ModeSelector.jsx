import React from 'react';
import './ModeSelector.css';

const ModeSelector = ({ currentMode, onModeChange }) => {
  const modes = [
    {
      id: 'focus',
      name: 'Focus Mode',
      icon: '🎯',
      description: 'Optimized for deep work',
      color: '#4A90E2'
    },
    {
      id: 'meeting',
      name: 'Meeting Mode',
      icon: '👥',
      description: 'Enhanced for collaboration',
      color: '#9C27B0'
    },
    {
      id: 'break',
      name: 'Break Mode',
      icon: '☕',
      description: 'Relaxation and recovery',
      color: '#4CAF50'
    },
    {
      id: 'learning',
      name: 'Learning Mode',
      icon: '📚',
      description: 'Optimized for studying',
      color: '#FF9800'
    }
  ];

  return (
    <div className="mode-selector">
      <div className="mode-selector-header">
        <h3>Activity Mode</h3>
        <p>Select the mode that matches your current activity</p>
      </div>

      <div className="mode-grid">
        {modes.map(mode => (
          <button
            key={mode.id}
            className={`mode-card ${currentMode === mode.id ? 'active' : ''}`}
            onClick={() => onModeChange(mode.id)}
            style={{
              borderColor: currentMode === mode.id ? mode.color : 'transparent',
              background: currentMode === mode.id ? `${mode.color}20` : 'rgba(255,255,255,0.05)'
            }}
          >
            <div className="mode-icon" style={{ backgroundColor: mode.color }}>
              {mode.icon}
            </div>
            <div className="mode-info">
              <h4 className="mode-name">{mode.name}</h4>
              <p className="mode-description">{mode.description}</p>
            </div>
            {currentMode === mode.id && (
              <div className="mode-check">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="8" fill={mode.color} />
                  <path d="M6 10L9 13L14 7" stroke="white" strokeWidth="2" />
                </svg>
              </div>
            )}
          </button>
        ))}
      </div>

      <div className="mode-settings">
        <h4>Mode Settings</h4>
        <div className="setting-item">
          <label>
            <input type="checkbox" defaultChecked />
            Enable auto-detection
          </label>
          <span className="setting-description">
            Automatically switch modes based on activity
          </span>
        </div>
        
        <div className="setting-item">
          <label>
            <input type="checkbox" defaultChecked />
            Adjust thresholds per mode
          </label>
          <span className="setting-description">
            Use different alert thresholds for each mode
          </span>
        </div>
      </div>
    </div>
  );
};

export default ModeSelector;