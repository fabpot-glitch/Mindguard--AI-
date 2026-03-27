/**
 * Score calculation utilities for MindGuard AI dashboard
 */

/**
 * Calculate overall cognitive score
 * @param {Object} state - Cognitive state
 * @returns {number} Overall score 0-100
 */
export const calculateOverallScore = (state) => {
  if (!state) return 0;
  
  const weights = {
    fatigue: 0.3,
    stress: 0.3,
    attention: 0.2,
    cognitive_load: 0.2
  };
  
  const normalizedFatigue = 1 - state.fatigue;
  const normalizedStress = 1 - state.stress;
  const normalizedLoad = 1 - state.cognitive_load;
  
  const score = (
    normalizedFatigue * weights.fatigue +
    normalizedStress * weights.stress +
    state.attention * weights.attention +
    normalizedLoad * weights.cognitive_load
  ) * 100;
  
  return Math.round(score);
};

/**
 * Calculate fatigue risk level
 * @param {number} fatigue - Fatigue value 0-1
 * @returns {Object} Risk level and color
 */
export const calculateFatigueRisk = (fatigue) => {
  if (fatigue >= 0.9) return { level: 'Critical', color: '#F44336', action: 'Immediate break required' };
  if (fatigue >= 0.8) return { level: 'High', color: '#FF9800', action: 'Take a break soon' };
  if (fatigue >= 0.6) return { level: 'Moderate', color: '#FFC107', action: 'Monitor fatigue' };
  if (fatigue >= 0.4) return { level: 'Mild', color: '#4CAF50', action: 'Normal range' };
  return { level: 'Low', color: '#2196F3', action: 'Optimal' };
};

/**
 * Calculate stress risk level
 * @param {number} stress - Stress value 0-1
 * @returns {Object} Risk level and color
 */
export const calculateStressRisk = (stress) => {
  if (stress >= 0.8) return { level: 'Critical', color: '#F44336', action: 'Immediate stress relief needed' };
  if (stress >= 0.7) return { level: 'High', color: '#FF9800', action: 'Practice relaxation' };
  if (stress >= 0.5) return { level: 'Moderate', color: '#FFC107', action: 'Monitor stress levels' };
  if (stress >= 0.3) return { level: 'Mild', color: '#4CAF50', action: 'Normal range' };
  return { level: 'Low', color: '#2196F3', action: 'Optimal' };
};

/**
 * Calculate attention quality
 * @param {number} attention - Attention value 0-1
 * @returns {Object} Quality level and color
 */
export const calculateAttentionQuality = (attention) => {
  if (attention >= 0.8) return { level: 'Excellent', color: '#4CAF50', action: 'Peak focus' };
  if (attention >= 0.6) return { level: 'Good', color: '#2196F3', action: 'Good focus' };
  if (attention >= 0.4) return { level: 'Moderate', color: '#FFC107', action: 'Normal focus' };
  if (attention >= 0.2) return { level: 'Low', color: '#FF9800', action: 'Declining focus' };
  return { level: 'Very Low', color: '#F44336', action: 'Difficulty focusing' };
};

/**
 * Calculate cognitive load level
 * @param {number} load - Cognitive load value 0-1
 * @returns {Object} Load level and color
 */
export const calculateLoadLevel = (load) => {
  if (load >= 0.9) return { level: 'Overwhelming', color: '#F44336', action: 'Reduce task complexity' };
  if (load >= 0.8) return { level: 'Very High', color: '#FF9800', action: 'Consider delegation' };
  if (load >= 0.6) return { level: 'High', color: '#FFC107', action: 'Monitor workload' };
  if (load >= 0.4) return { level: 'Moderate', color: '#4CAF50', action: 'Manageable' };
  return { level: 'Low', color: '#2196F3', action: 'Underutilized' };
};

/**
 * Calculate time to fatigue threshold
 * @param {Array} history - Historical data
 * @returns {Object} Time prediction
 */
export const calculateTimeToThreshold = (history) => {
  if (!history || history.length < 10) return null;
  
  const recent = history.slice(-20);
  const fatigueValues = recent.map(h => h.fatigue);
  
  // Linear regression
  const x = Array.from({ length: fatigueValues.length }, (_, i) => i);
  const n = x.length;
  
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = fatigueValues.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((a, _, i) => a + x[i] * fatigueValues[i], 0);
  const sumXX = x.reduce((a, _, i) => a + x[i] * x[i], 0);
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  
  if (slope <= 0) return null;
  
  const currentFatigue = fatigueValues[fatigueValues.length - 1];
  const stepsToThreshold = (0.8 - currentFatigue) / slope;
  const minutesToThreshold = stepsToThreshold * 0.5; // Assuming 30s between samples
  
  if (minutesToThreshold <= 0) return null;
  
  return {
    minutes: Math.round(minutesToThreshold * 10) / 10,
    threshold: 0.8,
    confidence: Math.min(1, Math.max(0, 1 - Math.abs(slope) * 10))
  };
};

/**
 * Calculate optimal break time
 * @param {Object} state - Current state
 * @param {Array} history - Historical data
 * @returns {Object} Break recommendation
 */
export const calculateOptimalBreak = (state, history) => {
  if (!state) return null;
  
  const fatigueRisk = calculateFatigueRisk(state.fatigue);
  const loadLevel = calculateLoadLevel(state.cognitive_load);
  const attentionQuality = calculateAttentionQuality(state.attention);
  
  // Calculate time since last break (simulated)
  const lastBreakTime = history && history.length > 0 
    ? history[history.length - 1].timestamp 
    : null;
  
  const minutesSinceBreak = lastBreakTime 
    ? (Date.now() - new Date(lastBreakTime)) / 60000 
    : 60;
  
  let recommendation = 'No break needed';
  let urgency = 'low';
  let suggestedDuration = 5;
  
  if (state.fatigue >= 0.8 || state.cognitive_load >= 0.8) {
    recommendation = 'Take a break now';
    urgency = 'high';
    suggestedDuration = 15;
  } else if (state.fatigue >= 0.6 || state.cognitive_load >= 0.7) {
    recommendation = 'Consider taking a break soon';
    urgency = 'medium';
    suggestedDuration = 10;
  } else if (minutesSinceBreak > 90) {
    recommendation = 'Time for a regular break';
    urgency = 'medium';
    suggestedDuration = 5;
  } else if (state.attention < 0.4) {
    recommendation = 'Short break to refresh focus';
    urgency = 'low';
    suggestedDuration = 5;
  }
  
  return {
    recommendation,
    urgency,
    suggestedDuration,
    minutesSinceBreak: Math.round(minutesSinceBreak),
    reasons: [
      fatigueRisk.level === 'Critical' ? 'Critical fatigue' : null,
      loadLevel.level === 'Overwhelming' ? 'Overwhelming load' : null,
      attentionQuality.level === 'Very Low' ? 'Very low attention' : null,
      minutesSinceBreak > 90 ? 'Long work session' : null
    ].filter(Boolean)
  };
};

/**
 * Calculate performance trend
 * @param {Array} history - Historical data
 * @returns {Object} Trend analysis
 */
export const calculateTrend = (history) => {
  if (!history || history.length < 10) return null;
  
  const metrics = ['fatigue', 'stress', 'attention', 'cognitive_load'];
  const trends = {};
  
  metrics.forEach(metric => {
    const values = history.slice(-20).map(h => h[metric]);
    const firstHalf = values.slice(0, 10);
    const secondHalf = values.slice(10);
    
    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
    
    trends[metric] = {
      direction: secondAvg > firstAvg ? 'up' : 'down',
      magnitude: Math.abs(secondAvg - firstAvg),
      percentage: ((secondAvg - firstAvg) / firstAvg) * 100
    };
  });
  
  return trends;
};

/**
 * Calculate focus score based on multiple factors
 * @param {Object} state - Current state
 * @returns {number} Focus score 0-100
 */
export const calculateFocusScore = (state) => {
  if (!state) return 0;
  
  const attentionWeight = 0.5;
  const fatigueWeight = 0.3;
  const stressWeight = 0.2;
  
  const attentionScore = state.attention * 100;
  const fatiguePenalty = (1 - state.fatigue) * 100;
  const stressPenalty = (1 - state.stress) * 100;
  
  const score = (
    attentionScore * attentionWeight +
    fatiguePenalty * fatigueWeight +
    stressPenalty * stressWeight
  );
  
  return Math.round(score);
};

/**
 * Calculate recovery needed
 * @param {Object} state - Current state
 * @returns {Object} Recovery recommendation
 */
export const calculateRecoveryNeeded = (state) => {
  if (!state) return null;
  
  const fatigueImpact = state.fatigue * 10;
  const stressImpact = state.stress * 8;
  const loadImpact = state.cognitive_load * 7;
  
  const totalImpact = fatigueImpact + stressImpact + loadImpact;
  
  if (totalImpact > 20) {
    return {
      level: 'High',
      minutes: Math.min(60, Math.round(totalImpact * 2)),
      activities: ['Deep breathing', 'Short walk', 'Hydration']
    };
  } else if (totalImpact > 15) {
    return {
      level: 'Moderate',
      minutes: Math.min(30, Math.round(totalImpact * 1.5)),
      activities: ['Stretch break', 'Eye rest', 'Quick meditation']
    };
  } else if (totalImpact > 10) {
    return {
      level: 'Low',
      minutes: Math.min(15, Math.round(totalImpact)),
      activities: ['Stand up', 'Look away from screen', 'Deep breath']
    };
  }
  
  return null;
};

/**
 * Calculate daily summary
 * @param {Array} history - Historical data
 * @returns {Object} Daily summary
 */
export const calculateDailySummary = (history) => {
  if (!history || history.length === 0) return null;
  
  const today = new Date().toDateString();
  const todayData = history.filter(h => new Date(h.timestamp).toDateString() === today);
  
  if (todayData.length === 0) return null;
  
  const avgState = {
    fatigue: todayData.reduce((acc, h) => acc + h.fatigue, 0) / todayData.length,
    stress: todayData.reduce((acc, h) => acc + h.stress, 0) / todayData.length,
    attention: todayData.reduce((acc, h) => acc + h.attention, 0) / todayData.length,
    cognitive_load: todayData.reduce((acc, h) => acc + h.cognitive_load, 0) / todayData.length,
    confidence: todayData.reduce((acc, h) => acc + h.confidence, 0) / todayData.length
  };
  
  const peakFocus = Math.max(...todayData.map(h => h.attention));
  const peakFatigue = Math.max(...todayData.map(h => h.fatigue));
  const peakStress = Math.max(...todayData.map(h => h.stress));
  
  return {
    averageState: avgState,
    overallScore: calculateOverallScore(avgState),
    peakFocus: Math.round(peakFocus * 100),
    peakFatigue: Math.round(peakFatigue * 100),
    peakStress: Math.round(peakStress * 100),
    dataPoints: todayData.length,
    duration: todayData.length * 0.5 // minutes (assuming 30s intervals)
  };
};

export default {
  calculateOverallScore,
  calculateFatigueRisk,
  calculateStressRisk,
  calculateAttentionQuality,
  calculateLoadLevel,
  calculateTimeToThreshold,
  calculateOptimalBreak,
  calculateTrend,
  calculateFocusScore,
  calculateRecoveryNeeded,
  calculateDailySummary
};