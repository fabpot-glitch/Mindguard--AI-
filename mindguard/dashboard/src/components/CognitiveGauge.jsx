import React, { useEffect, useState } from 'react';
import './CognitiveGauge.css';

const CognitiveGauge = ({ 
  title, 
  value, 
  thresholds, 
  trend, 
  unit = '%', 
  type = 'default',
  reverse = false,
  size = 'medium'
}) => {
  const [animatedValue, setAnimatedValue] = useState(0);
  const percentage = Math.min(100, Math.max(0, value * 100));
  
  // Determine color based on value and thresholds
  const getColor = () => {
    if (reverse) {
      if (percentage <= thresholds.low * 100) return '#4CAF50';
      if (percentage <= thresholds.medium * 100) return '#FFC107';
      if (percentage <= thresholds.high * 100) return '#FF9800';
      return '#F44336';
    } else {
      if (percentage <= thresholds.low * 100) return '#4CAF50';
      if (percentage <= thresholds.medium * 100) return '#FFC107';
      if (percentage <= thresholds.high * 100) return '#FF9800';
      return '#F44336';
    }
  };

  // Animate value changes
  useEffect(() => {
    const step = (percentage - animatedValue) / 10;
    const timer = setTimeout(() => {
      setAnimatedValue(prev => {
        const next = prev + step;
        return Math.abs(next - percentage) < 0.1 ? percentage : next;
      });
    }, 50);
    return () => clearTimeout(timer);
  }, [percentage, animatedValue]);

  // Calculate arc paths for SVG
  const radius = size === 'large' ? 80 : size === 'small' ? 40 : 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - animatedValue / 100);

  return (
    <div className={`cognitive-gauge ${type} ${size}`}>
      <h3 className="gauge-title">{title}</h3>
      
      <div className="gauge-container">
        <svg className="gauge-svg" viewBox="0 0 200 120">
          {/* Background arc */}
          <path
            d="M30,100 A70,70 0 0,1 170,100"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="12"
            strokeLinecap="round"
          />
          
          {/* Foreground arc */}
          <path
            d="M30,100 A70,70 0 0,1 170,100"
            fill="none"
            stroke={getColor()}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: 'stroke-dashoffset 0.3s ease' }}
          />
          
          {/* Value text */}
          <text
            x="100"
            y="85"
            textAnchor="middle"
            className="gauge-value"
          >
            {Math.round(animatedValue)}{unit}
          </text>
        </svg>

        {/* Trend indicator */}
        {trend !== undefined && (
          <div className={`trend-indicator ${trend > 0 ? 'up' : 'down'}`}>
            <i className={`fas fa-arrow-${trend > 0 ? 'up' : 'down'}`}></i>
            <span>{Math.abs(Math.round(trend * 100))}%</span>
          </div>
        )}
      </div>

      {/* Threshold markers */}
      <div className="threshold-markers">
        <div className="marker low" style={{ left: `${thresholds.low * 100}%` }}>
          <span className="marker-label">Low</span>
        </div>
        <div className="marker medium" style={{ left: `${thresholds.medium * 100}%` }}>
          <span className="marker-label">Med</span>
        </div>
        <div className="marker high" style={{ left: `${thresholds.high * 100}%` }}>
          <span className="marker-label">High</span>
        </div>
      </div>

      {/* Status message */}
      <div className="status-message" style={{ color: getColor() }}>
        {percentage <= thresholds.low * 100 && (reverse ? 'Excellent Focus' : 'Low - Good')}
        {percentage > thresholds.low * 100 && percentage <= thresholds.medium * 100 && 
          (reverse ? 'Moderate Focus' : 'Moderate - Normal')}
        {percentage > thresholds.medium * 100 && percentage <= thresholds.high * 100 && 
          (reverse ? 'Declining Focus' : 'High - Caution')}
        {percentage > thresholds.high * 100 && 
          (reverse ? 'Critical - Take Break' : 'Critical - Immediate Action')}
      </div>
    </div>
  );
};

export default CognitiveGauge;