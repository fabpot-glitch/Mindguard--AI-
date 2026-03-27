import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Custom hook for managing session timer
 * @param {Object} options - Configuration options
 * @returns {Object} Timer state and methods
 */
export const useSessionTimer = (options = {}) => {
  const {
    autoStart = false,
    onTick,
    onStart,
    onPause,
    onReset,
    onComplete,
    targetDuration = null // in seconds
  } = options;

  const [time, setTime] = useState(0);
  const [isActive, setIsActive] = useState(autoStart);
  const [isPaused, setIsPaused] = useState(false);
  const [laps, setLaps] = useState([]);
  const [sessions, setSessions] = useState([]);
  
  const timerRef = useRef(null);
  const startTimeRef = useRef(null);
  const pausedTimeRef = useRef(0);

  // Start timer
  const startTimer = useCallback(() => {
    if (!isActive) {
      setIsActive(true);
      setIsPaused(false);
      startTimeRef.current = Date.now() - pausedTimeRef.current * 1000;
      
      if (onStart) onStart(time);
    }
  }, [isActive, time, onStart]);

  // Pause timer
  const pauseTimer = useCallback(() => {
    if (isActive && !isPaused) {
      setIsPaused(true);
      pausedTimeRef.current = time;
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      
      if (onPause) onPause(time);
    }
  }, [isActive, isPaused, time, onPause]);

  // Resume timer
  const resumeTimer = useCallback(() => {
    if (isActive && isPaused) {
      setIsPaused(false);
      startTimeRef.current = Date.now() - time * 1000;
      
      if (onStart) onStart(time);
    }
  }, [isActive, isPaused, time, onStart]);

  // Stop timer
  const stopTimer = useCallback(() => {
    if (isActive) {
      setIsActive(false);
      setIsPaused(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      
      // Save session
      if (time > 0) {
        const session = {
          id: Date.now(),
          startTime: new Date(Date.now() - time * 1000),
          endTime: new Date(),
          duration: time,
          laps: [...laps]
        };
        
        setSessions(prev => [session, ...prev].slice(0, 50));
      }
      
      if (onComplete) onComplete(time);
    }
  }, [isActive, time, laps, onComplete]);

  // Reset timer
  const resetTimer = useCallback(() => {
    setIsActive(false);
    setIsPaused(false);
    setTime(0);
    setLaps([]);
    pausedTimeRef.current = 0;
    
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    
    if (onReset) onReset();
  }, [onReset]);

  // Add lap
  const addLap = useCallback(() => {
    if (isActive && !isPaused) {
      const lastLapTime = laps.length > 0 ? laps[laps.length - 1].time : 0;
      const lapTime = time - lastLapTime;
      
      const lap = {
        number: laps.length + 1,
        time: time,
        lapTime: lapTime,
        timestamp: new Date().toISOString()
      };
      
      setLaps(prev => [...prev, lap]);
    }
  }, [isActive, isPaused, time, laps]);

  // Remove last lap
  const removeLastLap = useCallback(() => {
    setLaps(prev => prev.slice(0, -1));
  }, []);

  // Clear all laps
  const clearLaps = useCallback(() => {
    setLaps([]);
  }, []);

  // Format time
  const formatTime = useCallback((totalSeconds) => {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    return {
      hours: hours.toString().padStart(2, '0'),
      minutes: minutes.toString().padStart(2, '0'),
      seconds: seconds.toString().padStart(2, '0'),
      total: `${hours.toString().padStart(2, '0')}:${minutes
        .toString()
        .padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`,
      hoursValue: hours,
      minutesValue: minutes,
      secondsValue: seconds
    };
  }, []);

  // Get progress percentage (if target duration set)
  const getProgress = useCallback(() => {
    if (!targetDuration) return 0;
    return Math.min((time / targetDuration) * 100, 100);
  }, [time, targetDuration]);

  // Get session statistics
  const getStats = useCallback(() => {
    if (sessions.length === 0) return null;
    
    const totalTime = sessions.reduce((acc, s) => acc + s.duration, 0);
    const avgTime = totalTime / sessions.length;
    const maxTime = Math.max(...sessions.map(s => s.duration));
    const minTime = Math.min(...sessions.map(s => s.duration));
    
    // Group by date
    const byDate = {};
    sessions.forEach(s => {
      const date = new Date(s.startTime).toLocaleDateString();
      if (!byDate[date]) {
        byDate[date] = {
          count: 0,
          total: 0
        };
      }
      byDate[date].count++;
      byDate[date].total += s.duration;
    });
    
    return {
      totalSessions: sessions.length,
      totalTime,
      avgTime,
      maxTime,
      minTime,
      byDate
    };
  }, [sessions]);

  // Timer effect
  useEffect(() => {
    if (isActive && !isPaused) {
      timerRef.current = setInterval(() => {
        setTime(prevTime => {
          const newTime = prevTime + 1;
          if (onTick) onTick(newTime);
          
          // Check if target duration reached
          if (targetDuration && newTime >= targetDuration) {
            stopTimer();
          }
          
          return newTime;
        });
      }, 1000);
    }
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isActive, isPaused, targetDuration, onTick, stopTimer]);

  // Auto-start effect
  useEffect(() => {
    if (autoStart) {
      startTimer();
    }
    
    return () => {
      if (isActive) {
        stopTimer();
      }
    };
  }, [autoStart, startTimer, stopTimer, isActive]);

  const formattedTime = formatTime(time);
  const progress = getProgress();
  const stats = getStats();

  return {
    // State
    time,
    formattedTime,
    isActive,
    isPaused,
    laps,
    sessions,
    progress,
    stats,
    
    // Methods
    startTimer,
    pauseTimer,
    resumeTimer,
    stopTimer,
    resetTimer,
    addLap,
    removeLastLap,
    clearLaps,
    
    // Getters
    getProgress,
    getStats,
    formatTime
  };
};

export default useSessionTimer;