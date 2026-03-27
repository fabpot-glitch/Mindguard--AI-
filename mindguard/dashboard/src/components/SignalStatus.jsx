import React from 'react';
import './SignalStatus.css';

const SignalStatus = ({ collectors }) => {
  const getSignalIcon = (status) => {
    if (status >= 0.8) return '📶';
    if (status >= 0.5) return '📡';
    return '⚠️';
  };

  const getSignalColor = (status) => {
    if (status >= 0.8) return '#4CAF50';
    if (status >= 0.5) return '#FF9800';
    return '#F44336';
  };

  const getSignalText = (status) => {
    if (status >= 0.8) return 'Excellent';
    if (status >= 0.5) return 'Good';
    if (status >= 0.2) return 'Weak';
    return 'No Signal';
  };

  const defaultCollectors = {
    eye: { active: true, samples: 0, error_rate: 0 },
    keyboard: { active: true, samples: 0, error_rate: 0 },
    screen: { active: true, samples: 0, error_rate: 0 },
    voice: { active: false, samples: 0, error_rate: 0 }
  };

  const collectorData = collectors || defaultCollectors;

  return (
    <div className="signal-status">
      <h3>Signal Quality</h3>
      
      <div className="signal-grid">
        {/* Eye Tracker */}
        <div className="signal-card">
          <div className="signal-header">
            <span className="signal-name">👁️ Eye Tracker</span>
            {collectorData.eye?.active ? (
              <span className="signal-badge active">Active</span>
            ) : (
              <span className="signal-badge inactive">Inactive</span>
            )}
          </div>
          
          <div className="signal-metrics">
            <div className="metric">
              <span className="metric-label">Samples</span>
              <span className="metric-value">{collectorData.eye?.samples || 0}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Error Rate</span>
              <span className="metric-value">
                {((collectorData.eye?.error_rate || 0) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          
          <div className="signal-strength">
            <div className="strength-label">
              <span>Signal</span>
              <span style={{ color: getSignalColor(1 - (collectorData.eye?.error_rate || 0)) }}>
                {getSignalText(1 - (collectorData.eye?.error_rate || 0))}
              </span>
            </div>
            <div className="strength-bar">
              <div 
                className="strength-fill"
                style={{
                  width: `${(1 - (collectorData.eye?.error_rate || 0)) * 100}%`,
                  backgroundColor: getSignalColor(1 - (collectorData.eye?.error_rate || 0))
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* Keyboard Monitor */}
        <div className="signal-card">
          <div className="signal-header">
            <span className="signal-name">⌨️ Keyboard</span>
            {collectorData.keyboard?.active ? (
              <span className="signal-badge active">Active</span>
            ) : (
              <span className="signal-badge inactive">Inactive</span>
            )}
          </div>
          
          <div className="signal-metrics">
            <div className="metric">
              <span className="metric-label">Keys</span>
              <span className="metric-value">{collectorData.keyboard?.samples || 0}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Error Rate</span>
              <span className="metric-value">
                {((collectorData.keyboard?.error_rate || 0) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          
          <div className="signal-strength">
            <div className="strength-label">
              <span>Signal</span>
              <span style={{ color: getSignalColor(1 - (collectorData.keyboard?.error_rate || 0)) }}>
                {getSignalText(1 - (collectorData.keyboard?.error_rate || 0))}
              </span>
            </div>
            <div className="strength-bar">
              <div 
                className="strength-fill"
                style={{
                  width: `${(1 - (collectorData.keyboard?.error_rate || 0)) * 100}%`,
                  backgroundColor: getSignalColor(1 - (collectorData.keyboard?.error_rate || 0))
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* Screen Monitor */}
        <div className="signal-card">
          <div className="signal-header">
            <span className="signal-name">🖥️ Screen</span>
            {collectorData.screen?.active ? (
              <span className="signal-badge active">Active</span>
            ) : (
              <span className="signal-badge inactive">Inactive</span>
            )}
          </div>
          
          <div className="signal-metrics">
            <div className="metric">
              <span className="metric-label">Samples</span>
              <span className="metric-value">{collectorData.screen?.samples || 0}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Error Rate</span>
              <span className="metric-value">
                {((collectorData.screen?.error_rate || 0) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          
          <div className="signal-strength">
            <div className="strength-label">
              <span>Signal</span>
              <span style={{ color: getSignalColor(1 - (collectorData.screen?.error_rate || 0)) }}>
                {getSignalText(1 - (collectorData.screen?.error_rate || 0))}
              </span>
            </div>
            <div className="strength-bar">
              <div 
                className="strength-fill"
                style={{
                  width: `${(1 - (collectorData.screen?.error_rate || 0)) * 100}%`,
                  backgroundColor: getSignalColor(1 - (collectorData.screen?.error_rate || 0))
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* Voice Analyzer */}
        <div className="signal-card">
          <div className="signal-header">
            <span className="signal-name">🎤 Voice</span>
            {collectorData.voice?.active ? (
              <span className="signal-badge active">Active</span>
            ) : (
              <span className="signal-badge inactive">Inactive</span>
            )}
          </div>
          
          <div className="signal-metrics">
            <div className="metric">
              <span className="metric-label">Samples</span>
              <span className="metric-value">{collectorData.voice?.samples || 0}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Error Rate</span>
              <span className="metric-value">
                {((collectorData.voice?.error_rate || 0) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          
          <div className="signal-strength">
            <div className="strength-label">
              <span>Signal</span>
              <span style={{ color: getSignalColor(1 - (collectorData.voice?.error_rate || 0)) }}>
                {getSignalText(1 - (collectorData.voice?.error_rate || 0))}
              </span>
            </div>
            <div className="strength-bar">
              <div 
                className="strength-fill"
                style={{
                  width: `${(1 - (collectorData.voice?.error_rate || 0)) * 100}%`,
                  backgroundColor: getSignalColor(1 - (collectorData.voice?.error_rate || 0))
                }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="system-status">
        <h4>System Health</h4>
        <div className="status-item">
          <span>Data Collection</span>
          <span className="status-good">✓ Operational</span>
        </div>
        <div className="status-item">
          <span>Model Inference</span>
          <span className="status-good">✓ Running</span>
        </div>
        <div className="status-item">
          <span>WebSocket Connection</span>
          <span className="status-good">✓ Connected</span>
        </div>
      </div>
    </div>
  );
};

export default SignalStatus;