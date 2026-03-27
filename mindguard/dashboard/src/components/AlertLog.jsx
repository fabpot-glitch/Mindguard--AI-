import React, { useState } from 'react';
import './AlertLog.css';

const AlertLog = ({ alerts, onDismiss, maxAlerts = 10 }) => {
  const [filter, setFilter] = useState('all');

  const getAlertIcon = (type) => {
    switch (type) {
      case 'critical_fatigue':
        return '⚠️';
      case 'high_fatigue':
        return '😴';
      case 'high_stress':
        return '😰';
      case 'low_attention':
        return '🎯';
      case 'high_cognitive_load':
        return '🧠';
      default:
        return '🔔';
    }
  };

  const getAlertColor = (level) => {
    switch (level) {
      case 'critical':
        return '#F44336';
      case 'warning':
        return '#FF9800';
      case 'info':
        return '#4A90E2';
      default:
        return '#9E9E9E';
    }
  };

  const filteredAlerts = alerts
    .filter(alert => filter === 'all' || alert.level === filter)
    .slice(0, maxAlerts);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="alert-log">
      <div className="alert-header">
        <h3>Alert Log</h3>
        <select 
          value={filter} 
          onChange={(e) => setFilter(e.target.value)}
          className="filter-select"
        >
          <option value="all">All</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
      </div>

      <div className="alert-list">
        {filteredAlerts.length === 0 ? (
          <div className="no-alerts">
            <p>No alerts to display</p>
          </div>
        ) : (
          filteredAlerts.map((alert, idx) => (
            <div 
              key={idx} 
              className="alert-item"
              style={{ borderLeftColor: getAlertColor(alert.level) }}
            >
              <div className="alert-icon">
                {getAlertIcon(alert.type)}
              </div>
              
              <div className="alert-content">
                <div className="alert-header-row">
                  <span className="alert-type">
                    {alert.type.replace(/_/g, ' ')}
                  </span>
                  <span className="alert-time">
                    {formatTime(alert.timestamp)}
                  </span>
                </div>
                
                <div className="alert-details">
                  <span className="alert-value">
                    Value: {Math.round(alert.value * 100)}%
                  </span>
                  <span className="alert-threshold">
                    Threshold: {Math.round(alert.threshold * 100)}%
                  </span>
                </div>
                
                <div className="alert-actions">
                  <button 
                    className="dismiss-btn"
                    onClick={() => onDismiss(alert.id)}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {alerts.length > maxAlerts && (
        <div className="alert-footer">
          <button className="view-all-btn">
            View all {alerts.length} alerts
          </button>
        </div>
      )}
    </div>
  );
};

export default AlertLog;