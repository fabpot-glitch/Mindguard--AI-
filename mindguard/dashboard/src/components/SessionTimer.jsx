import React, { useState, useEffect } from 'react';
import './SessionTimer.css';

const SessionTimer = ({ isActive, onTimeUpdate }) => {
  const [time, setTime] = useState(0);
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    let interval = null;
    
    if (isActive) {
      interval = setInterval(() => {
        setTime(prevTime => {
          const newTime = prevTime + 1;
          if (onTimeUpdate) onTimeUpdate(newTime);
          return newTime;
        });
      }, 1000);
    } else if (!isActive && time !== 0) {
      clearInterval(interval);
    }
    
    return () => clearInterval(interval);
  }, [isActive, time, onTimeUpdate]);

  const formatTime = (totalSeconds) => {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    return {
      hours: hours.toString().padStart(2, '0'),
      minutes: minutes.toString().padStart(2, '0'),
      seconds: seconds.toString().padStart(2, '0'),
      total: `${hours.toString().padStart(2, '0')}:${minutes
        .toString()
        .padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
    };
  };

  const saveSession = () => {
    if (time < 60) return; // Don't save sessions shorter than 1 minute
    
    const newSession = {
      id: Date.now(),
      startTime: new Date(Date.now() - time * 1000),
      endTime: new Date(),
      duration: time,
      date: new Date().toLocaleDateString()
    };
    
    setSessions(prev => [newSession, ...prev].slice(0, 10));
    setTime(0);
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatted = formatTime(time);

  return (
    <div className="session-timer">
      <div className="timer-display">
        <div className="time-units">
          <div className="time-unit">
            <span className="unit-value">{formatted.hours}</span>
            <span className="unit-label">hours</span>
          </div>
          <span className="unit-separator">:</span>
          <div className="time-unit">
            <span className="unit-value">{formatted.minutes}</span>
            <span className="unit-label">minutes</span>
          </div>
          <span className="unit-separator">:</span>
          <div className="time-unit">
            <span className="unit-value">{formatted.seconds}</span>
            <span className="unit-label">seconds</span>
          </div>
        </div>
        
        <div className="timer-controls">
          {!isActive ? (
            <button className="start-btn" onClick={() => onTimeUpdate && onTimeUpdate('start')}>
              <i className="fas fa-play"></i> Start Session
            </button>
          ) : (
            <button className="pause-btn" onClick={() => onTimeUpdate && onTimeUpdate('pause')}>
              <i className="fas fa-pause"></i> Pause
            </button>
          )}
          
          {time > 0 && !isActive && (
            <button className="save-btn" onClick={saveSession}>
              <i className="fas fa-save"></i> Save Session
            </button>
          )}
          
          <button className="reset-btn" onClick={() => setTime(0)}>
            <i className="fas fa-redo"></i> Reset
          </button>
        </div>
      </div>

      {sessions.length > 0 && (
        <div className="recent-sessions">
          <h4>Recent Sessions</h4>
          <div className="session-list">
            {sessions.map(session => (
              <div key={session.id} className="session-item">
                <div className="session-time">
                  <i className="far fa-clock"></i>
                  {session.startTime.toLocaleTimeString()} - {session.endTime.toLocaleTimeString()}
                </div>
                <div className="session-duration">
                  {formatDuration(session.duration)}
                </div>
                <div className="session-date">
                  {session.date}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="timer-stats">
        <div className="stat">
          <span className="stat-label">Today's Total</span>
          <span className="stat-value">
            {formatDuration(sessions.reduce((acc, s) => acc + s.duration, 0))}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Sessions Today</span>
          <span className="stat-value">{sessions.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Avg Duration</span>
          <span className="stat-value">
            {sessions.length > 0 
              ? formatDuration(sessions.reduce((acc, s) => acc + s.duration, 0) / sessions.length)
              : '0m'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SessionTimer;