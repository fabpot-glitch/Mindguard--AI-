import React from 'react';
import './PredictionPanel.css';

const PredictionPanel = ({ 
  fatigue, 
  confidence, 
  timeToError, 
  nextBreak,
  historicalData 
}) => {
  
  // Calculate time to critical fatigue
  const calculateTimeToCritical = () => {
    if (!historicalData || historicalData.length < 10) return null;
    
    const recent = historicalData.slice(-10);
    const slope = (recent[recent.length - 1].fatigue - recent[0].fatigue) / recent.length;
    
    if (slope <= 0) return null;
    
    const currentFatigue = fatigue;
    const stepsToCritical = (0.9 - currentFatigue) / slope;
    const minutesToCritical = stepsToCritical * 0.5; // Assuming 30s between samples
    
    return minutesToCritical > 0 ? minutesToCritical : null;
  };

  // Calculate optimal break time
  const calculateOptimalBreak = () => {
    if (!historicalData || historicalData.length < 30) return null;
    
    const recent = historicalData.slice(-30);
    const avgFatigue = recent.reduce((sum, d) => sum + d.fatigue, 0) / recent.length;
    const trend = recent[recent.length - 1].fatigue - recent[0].fatigue;
    
    if (avgFatigue > 0.7 && trend > 0.05) {
      return 'Now';
    } else if (avgFatigue > 0.6) {
      return 'Within 15 min';
    } else if (trend > 0.1) {
      return 'Within 30 min';
    }
    
    return 'Not needed';
  };

  const timeToCritical = calculateTimeToCritical();
  const optimalBreak = calculateOptimalBreak();

  // Recommendations based on current state
  const getRecommendations = () => {
    const recs = [];
    
    if (fatigue > 0.8) {
      recs.push({
        text: 'Critical fatigue detected. Take an immediate break.',
        icon: '⚠️',
        priority: 'high'
      });
    } else if (fatigue > 0.6) {
      recs.push({
        text: 'Fatigue building. Consider a short break soon.',
        icon: '😴',
        priority: 'medium'
      });
    }
    
    if (confidence < 0.7) {
      recs.push({
        text: 'Low confidence in predictions. Check sensor connections.',
        icon: '📡',
        priority: 'medium'
      });
    }
    
    if (timeToCritical && timeToCritical < 30) {
      recs.push({
        text: `Predicted to reach critical fatigue in ${Math.round(timeToCritical)} minutes.`,
        icon: '⏰',
        priority: 'high'
      });
    }
    
    if (recs.length === 0) {
      recs.push({
        text: 'All systems normal. Keep up the good work!',
        icon: '✅',
        priority: 'low'
      });
    }
    
    return recs;
  };

  const recommendations = getRecommendations();

  return (
    <div className="prediction-panel">
      <h3>AI Predictions & Recommendations</h3>
      
      <div className="prediction-grid">
        <div className="prediction-card">
          <div className="prediction-icon">⏱️</div>
          <div className="prediction-content">
            <span className="prediction-label">Time to Critical</span>
            <span className="prediction-value">
              {timeToCritical ? `${Math.round(timeToCritical)} min` : 'Not projected'}
            </span>
          </div>
        </div>

        <div className="prediction-card">
          <div className="prediction-icon">☕</div>
          <div className="prediction-content">
            <span className="prediction-label">Optimal Break</span>
            <span className="prediction-value">{optimalBreak}</span>
          </div>
        </div>

        <div className="prediction-card">
          <div className="prediction-icon">📊</div>
          <div className="prediction-content">
            <span className="prediction-label">Confidence</span>
            <span className="prediction-value">{(confidence * 100).toFixed(0)}%</span>
          </div>
        </div>

        <div className="prediction-card">
          <div className="prediction-icon">🔄</div>
          <div className="prediction-content">
            <span className="prediction-label">Trend</span>
            <span className="prediction-value">
              {fatigue > 0.7 ? 'Declining' : fatigue > 0.5 ? 'Stable' : 'Optimal'}
            </span>
          </div>
        </div>
      </div>

      <div className="recommendations">
        <h4>Active Recommendations</h4>
        <div className="recommendation-list">
          {recommendations.map((rec, idx) => (
            <div 
              key={idx} 
              className={`recommendation-item priority-${rec.priority}`}
            >
              <span className="rec-icon">{rec.icon}</span>
              <span className="rec-text">{rec.text}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="insight-footer">
        <p>
          Based on analysis of your last {historicalData?.length || 0} data points.
          Updates every 30 seconds.
        </p>
      </div>
    </div>
  );
};

export default PredictionPanel;