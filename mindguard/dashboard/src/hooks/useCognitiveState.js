import { useState, useEffect, useCallback, useMemo } from 'react';

/**
 * Custom hook for managing cognitive state
 * @param {Object} lastMessage - Last WebSocket message
 * @returns {Object} Cognitive state and derived data
 */
export const useCognitiveState = (lastMessage) => {
  const [cognitiveState, setCognitiveState] = useState(null);
  const [history, setHistory] = useState([]);
  const [trends, setTrends] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [baseline, setBaseline] = useState(null);

  const MAX_HISTORY = 1000;
  const ALERT_THRESHOLDS = {
    fatigue: 0.8,
    stress: 0.75,
    attention: 0.3,
    cognitive_load: 0.85
  };

  // Process incoming state updates
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'state_update' && lastMessage.data) {
      updateCognitiveState(lastMessage.data);
    } else if (lastMessage.type === 'alert' && lastMessage.data) {
      addAlert(lastMessage.data);
    } else if (lastMessage.type === 'intervention' && lastMessage.data) {
      console.log('Intervention received:', lastMessage.data);
    }
  }, [lastMessage]);

  // Update cognitive state
  const updateCognitiveState = useCallback((newState) => {
    setCognitiveState(prevState => {
      const stateWithTime = {
        ...newState,
        timestamp: newState.timestamp || new Date().toISOString()
      };

      setHistory(prevHistory => {
        const newHistory = [...prevHistory, stateWithTime];
        return newHistory.slice(-MAX_HISTORY);
      });

      updateTrends(stateWithTime);
      checkAlerts(stateWithTime);

      return stateWithTime;
    });
  }, []);

  // Calculate trends based on historical data
  const updateTrends = useCallback((currentState) => {
    if (history.length < 10) return;

    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    const recentData = history.filter(h => new Date(h.timestamp) >= fiveMinutesAgo);

    if (recentData.length < 5) return;

    const calculateTrend = (metric) => {
      const values = recentData.map(d => d[metric]);
      const firstHalf = values.slice(0, Math.floor(values.length / 2));
      const secondHalf = values.slice(Math.floor(values.length / 2));

      const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
      const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;

      return secondAvg - firstAvg;
    };

    const calculateTimeToCritical = () => {
      if (recentData.length < 10) return null;

      const fatigueValues = recentData.map(d => d.fatigue);
      const x = Array.from({ length: fatigueValues.length }, (_, i) => i);

      const n = x.length;
      const sumX = x.reduce((a, b) => a + b, 0);
      const sumY = fatigueValues.reduce((a, b) => a + b, 0);
      const sumXY = x.reduce((a, _, i) => a + x[i] * fatigueValues[i], 0);
      const sumXX = x.reduce((a, _, i) => a + x[i] * x[i], 0);

      const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);

      if (slope <= 0) return null;

      const currentFatigue = fatigueValues[fatigueValues.length - 1];
      const stepsToCritical = (0.9 - currentFatigue) / slope;
      const minutesToCritical = stepsToCritical * 0.5;

      return minutesToCritical > 0 ? minutesToCritical : null;
    };

    const calculateOptimalBreak = () => {
      if (recentData.length < 20) return null;

      const fatigueTrend = calculateTrend('fatigue');
      const currentFatigue = currentState.fatigue;

      if (currentFatigue > 0.7 && fatigueTrend > 0.05) {
        return 'Now';
      } else if (currentFatigue > 0.6 || fatigueTrend > 0.1) {
        return 'Within 15 minutes';
      } else if (fatigueTrend > 0.05) {
        return 'Within 30 minutes';
      }

      return 'Not needed';
    };

    setTrends({
      fatigue: calculateTrend('fatigue'),
      stress: calculateTrend('stress'),
      attention: calculateTrend('attention'),
      cognitive_load: calculateTrend('cognitive_load'),
      timeToError: calculateTimeToCritical(),
      nextBreak: calculateOptimalBreak(),
      updatedAt: new Date().toISOString()
    });

  }, [history]); // ✅ FIXED: removed invalid `currentState` dependency

  // Check for alert conditions
  const checkAlerts = useCallback((state) => {
    const newAlerts = [];

    if (state.fatigue >= ALERT_THRESHOLDS.fatigue) {
      newAlerts.push({
        type: 'high_fatigue',
        level: state.fatigue >= 0.9 ? 'critical' : 'warning',
        value: state.fatigue,
        threshold: ALERT_THRESHOLDS.fatigue,
        timestamp: new Date().toISOString(),
        message: `Fatigue level is ${state.fatigue >= 0.9 ? 'critical' : 'high'}`
      });
    }

    if (state.stress >= ALERT_THRESHOLDS.stress) {
      newAlerts.push({
        type: 'high_stress',
        level: 'warning',
        value: state.stress,
        threshold: ALERT_THRESHOLDS.stress,
        timestamp: new Date().toISOString(),
        message: 'Stress level is high'
      });
    }

    if (state.attention <= ALERT_THRESHOLDS.attention) {
      newAlerts.push({
        type: 'low_attention',
        level: 'warning',
        value: state.attention,
        threshold: ALERT_THRESHOLDS.attention,
        timestamp: new Date().toISOString(),
        message: 'Attention level is low'
      });
    }

    if (state.cognitive_load >= ALERT_THRESHOLDS.cognitive_load) {
      newAlerts.push({
        type: 'high_cognitive_load',
        level: 'warning',
        value: state.cognitive_load,
        threshold: ALERT_THRESHOLDS.cognitive_load,
        timestamp: new Date().toISOString(),
        message: 'Cognitive load is high'
      });
    }

    if (newAlerts.length > 0) {
      setAlerts(prev => [...newAlerts, ...prev].slice(0, 50));
    }
  }, []);

  // Add manual alert
  const addAlert = useCallback((alert) => {
    setAlerts(prev => [alert, ...prev].slice(0, 50));
  }, []);

  // Dismiss alert
  const dismissAlert = useCallback((alertId) => {
    setAlerts(prev => prev.filter(a => a.id !== alertId));
  }, []);

  // Clear all alerts
  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  // Reset history
  const resetHistory = useCallback(() => {
    setHistory([]);
    setTrends({});
  }, []);

  // Calculate baseline from history
  const calculateBaseline = useCallback(() => {
    if (history.length < 100) return null;

    const recentHistory = history.slice(-500);

    const baselineData = {
      fatigue: recentHistory.reduce((acc, h) => acc + h.fatigue, 0) / recentHistory.length,
      stress: recentHistory.reduce((acc, h) => acc + h.stress, 0) / recentHistory.length,
      attention: recentHistory.reduce((acc, h) => acc + h.attention, 0) / recentHistory.length,
      cognitive_load: recentHistory.reduce((acc, h) => acc + h.cognitive_load, 0) / recentHistory.length,
      confidence: recentHistory.reduce((acc, h) => acc + h.confidence, 0) / recentHistory.length,
      sampleCount: recentHistory.length,
      calculatedAt: new Date().toISOString()
    };

    setBaseline(baselineData);
    return baselineData;
  }, [history]);

  // Calculate deviation from baseline
  const calculateDeviation = useCallback(() => {
    if (!baseline || !cognitiveState) return null;

    return {
      fatigue: cognitiveState.fatigue - baseline.fatigue,
      stress: cognitiveState.stress - baseline.stress,
      attention: cognitiveState.attention - baseline.attention,
      cognitive_load: cognitiveState.cognitive_load - baseline.cognitive_load,
      confidence: cognitiveState.confidence - baseline.confidence
    };
  }, [baseline, cognitiveState]);

  // Get summary statistics
  const getSummary = useCallback(() => {
    if (history.length === 0) return null;

    const stats = {};
    const metrics = ['fatigue', 'stress', 'attention', 'cognitive_load', 'confidence'];

    metrics.forEach(metric => {
      const values = history.map(h => h[metric]).filter(v => v !== undefined);
      if (values.length > 0) {
        stats[metric] = {
          min: Math.min(...values),
          max: Math.max(...values),
          avg: values.reduce((a, b) => a + b, 0) / values.length,
          current: values[values.length - 1]
        };
      }
    });

    return stats;
  }, [history]);

  // Memoized derived data
  const derivedData = useMemo(() => {
    if (!cognitiveState) return null;

    return {
      fatiguePercentage: Math.round(cognitiveState.fatigue * 100),
      stressPercentage: Math.round(cognitiveState.stress * 100),
      attentionPercentage: Math.round(cognitiveState.attention * 100),
      cognitiveLoadPercentage: Math.round(cognitiveState.cognitive_load * 100),
      confidencePercentage: Math.round(cognitiveState.confidence * 100),
      isHighFatigue: cognitiveState.fatigue >= 0.7,
      isHighStress: cognitiveState.stress >= 0.7,
      isLowAttention: cognitiveState.attention <= 0.3,
      isHighLoad: cognitiveState.cognitive_load >= 0.7,
      overallScore: Math.round(
        ((1 - cognitiveState.fatigue) +
          (1 - cognitiveState.stress) +
          cognitiveState.attention +
          (1 - cognitiveState.cognitive_load)) / 4 * 100
      )
    };
  }, [cognitiveState]);

  return {
    cognitiveState,
    history,
    trends,
    alerts,
    baseline,
    derivedData,
    updateCognitiveState,
    addAlert,
    dismissAlert,
    clearAlerts,
    resetHistory,
    calculateBaseline,
    calculateDeviation,
    getSummary
  };
};

export default useCognitiveState;