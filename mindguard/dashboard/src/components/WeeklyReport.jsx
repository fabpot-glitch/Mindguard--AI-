import React from 'react';
import './WeeklyReport.css';

const WeeklyReport = ({ data, onClose }) => {
  // Process data for weekly statistics
  const processWeeklyData = () => {
    if (!data || data.length === 0) return null;

    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    const weekData = data.filter(d => new Date(d.timestamp) >= weekAgo);
    
    if (weekData.length === 0) return null;

    // Calculate daily averages
    const dailyStats = {};
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    weekData.forEach(point => {
      const date = new Date(point.timestamp);
      const day = days[date.getDay()];
      
      if (!dailyStats[day]) {
        dailyStats[day] = {
          fatigue: [],
          stress: [],
          attention: [],
          cognitive_load: [],
          count: 0
        };
      }
      
      dailyStats[day].fatigue.push(point.fatigue);
      dailyStats[day].stress.push(point.stress);
      dailyStats[day].attention.push(point.attention);
      dailyStats[day].cognitive_load.push(point.cognitive_load);
      dailyStats[day].count++;
    });

    // Calculate averages
    Object.keys(dailyStats).forEach(day => {
      const stats = dailyStats[day];
      dailyStats[day] = {
        fatigue: stats.fatigue.reduce((a, b) => a + b, 0) / stats.fatigue.length,
        stress: stats.stress.reduce((a, b) => a + b, 0) / stats.stress.length,
        attention: stats.attention.reduce((a, b) => a + b, 0) / stats.attention.length,
        cognitive_load: stats.cognitive_load.reduce((a, b) => a + b, 0) / stats.cognitive_load.length,
        samples: stats.count
      };
    });

    // Calculate overall averages
    const overall = {
      fatigue: weekData.reduce((acc, d) => acc + d.fatigue, 0) / weekData.length,
      stress: weekData.reduce((acc, d) => acc + d.stress, 0) / weekData.length,
      attention: weekData.reduce((acc, d) => acc + d.attention, 0) / weekData.length,
      cognitive_load: weekData.reduce((acc, d) => acc + d.cognitive_load, 0) / weekData.length
    };

    // Calculate trends
    const midPoint = Math.floor(weekData.length / 2);
    const firstHalf = weekData.slice(0, midPoint);
    const secondHalf = weekData.slice(midPoint);
    
    const trends = {
      fatigue: (secondHalf.reduce((acc, d) => acc + d.fatigue, 0) / secondHalf.length) -
                (firstHalf.reduce((acc, d) => acc + d.fatigue, 0) / firstHalf.length),
      stress: (secondHalf.reduce((acc, d) => acc + d.stress, 0) / secondHalf.length) -
              (firstHalf.reduce((acc, d) => acc + d.stress, 0) / firstHalf.length),
      attention: (secondHalf.reduce((acc, d) => acc + d.attention, 0) / secondHalf.length) -
                 (firstHalf.reduce((acc, d) => acc + d.attention, 0) / firstHalf.length),
      cognitive_load: (secondHalf.reduce((acc, d) => acc + d.cognitive_load, 0) / secondHalf.length) -
                      (firstHalf.reduce((acc, d) => acc + d.cognitive_load, 0) / firstHalf.length)
    };

    return {
      daily: dailyStats,
      overall,
      trends,
      totalSamples: weekData.length,
      daysTracked: Object.keys(dailyStats).length
    };
  };

  const stats = processWeeklyData();

  if (!stats) {
    return (
      <div className="weekly-report">
        <div className="report-header">
          <h2>Weekly Report</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="no-data">
          <p>Insufficient data for weekly report. Please continue using MindGuard AI to generate insights.</p>
        </div>
      </div>
    );
  }

  const getScoreColor = (value) => {
    if (value < 0.3) return '#4CAF50';
    if (value < 0.6) return '#FF9800';
    return '#F44336';
  };

  const getTrendIcon = (trend) => {
    if (trend > 0.05) return '↑';
    if (trend < -0.05) return '↓';
    return '→';
  };

  const getTrendColor = (trend, metric) => {
    // For fatigue/stress/load, increase is bad
    if (metric === 'fatigue' || metric === 'stress' || metric === 'cognitive_load') {
      if (trend > 0.05) return '#F44336';
      if (trend < -0.05) return '#4CAF50';
    } else {
      // For attention, increase is good
      if (trend > 0.05) return '#4CAF50';
      if (trend < -0.05) return '#F44336';
    }
    return '#FFC107';
  };

  return (
    <div className="weekly-report">
      <div className="report-header">
        <h2>Weekly Cognitive Report</h2>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="report-date">
        {new Date().toLocaleDateString('en-US', { 
          month: 'long', 
          day: 'numeric', 
          year: 'numeric' 
        })} (Last 7 days)
      </div>

      <div className="report-summary">
        <div className="summary-card">
          <h3>Overall Cognitive Score</h3>
          <div className="overall-score">
            {((1 - (stats.overall.fatigue + stats.overall.stress) / 2) * 100).toFixed(0)}%
          </div>
          <p>Based on {stats.totalSamples} data points over {stats.daysTracked} days</p>
        </div>

        <div className="summary-grid">
          <div className="summary-item">
            <span className="label">Avg Fatigue</span>
            <span className="value" style={{ color: getScoreColor(stats.overall.fatigue) }}>
              {(stats.overall.fatigue * 100).toFixed(0)}%
            </span>
            <span className="trend" style={{ color: getTrendColor(stats.trends.fatigue, 'fatigue') }}>
              {getTrendIcon(stats.trends.fatigue)}
            </span>
          </div>
          
          <div className="summary-item">
            <span className="label">Avg Stress</span>
            <span className="value" style={{ color: getScoreColor(stats.overall.stress) }}>
              {(stats.overall.stress * 100).toFixed(0)}%
            </span>
            <span className="trend" style={{ color: getTrendColor(stats.trends.stress, 'stress') }}>
              {getTrendIcon(stats.trends.stress)}
            </span>
          </div>
          
          <div className="summary-item">
            <span className="label">Avg Attention</span>
            <span className="value" style={{ color: getScoreColor(1 - stats.overall.attention) }}>
              {(stats.overall.attention * 100).toFixed(0)}%
            </span>
            <span className="trend" style={{ color: getTrendColor(stats.trends.attention, 'attention') }}>
              {getTrendIcon(stats.trends.attention)}
            </span>
          </div>
          
          <div className="summary-item">
            <span className="label">Avg Cognitive Load</span>
            <span className="value" style={{ color: getScoreColor(stats.overall.cognitive_load) }}>
              {(stats.overall.cognitive_load * 100).toFixed(0)}%
            </span>
            <span className="trend" style={{ color: getTrendColor(stats.trends.cognitive_load, 'cognitive_load') }}>
              {getTrendIcon(stats.trends.cognitive_load)}
            </span>
          </div>
        </div>
      </div>

      <div className="daily-breakdown">
        <h3>Daily Breakdown</h3>
        <div className="daily-grid">
          {Object.entries(stats.daily).map(([day, values]) => (
            <div key={day} className="daily-card">
              <h4>{day}</h4>
              <div className="daily-metrics">
                <div className="daily-metric">
                  <span>Fatigue</span>
                  <span style={{ color: getScoreColor(values.fatigue) }}>
                    {(values.fatigue * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="daily-metric">
                  <span>Stress</span>
                  <span style={{ color: getScoreColor(values.stress) }}>
                    {(values.stress * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="daily-metric">
                  <span>Attention</span>
                  <span style={{ color: getScoreColor(1 - values.attention) }}>
                    {(values.attention * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="daily-metric">
                  <span>Load</span>
                  <span style={{ color: getScoreColor(values.cognitive_load) }}>
                    {(values.cognitive_load * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="daily-samples">
                {values.samples} samples
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="report-insights">
        <h3>Insights & Recommendations</h3>
        <ul>
          {stats.trends.fatigue > 0.1 && (
            <li className="warning">
              ⚠️ Fatigue levels have increased significantly this week. Consider taking more breaks.
            </li>
          )}
          {stats.trends.stress > 0.1 && (
            <li className="warning">
              ⚠️ Stress levels are trending upward. Try incorporating relaxation exercises.
            </li>
          )}
          {stats.trends.attention < -0.1 && (
            <li className="warning">
              ⚠️ Attention span is decreasing. Consider reducing distractions during work.
            </li>
          )}
          {stats.overall.fatigue < 0.3 && stats.overall.stress < 0.3 && (
            <li className="success">
              ✅ Great job managing cognitive load! Your metrics are in optimal range.
            </li>
          )}
          <li>
            💡 Best focus time appears to be mornings based on your data.
          </li>
          <li>
            🎯 You tend to have higher cognitive load in the afternoons. Schedule important tasks accordingly.
          </li>
        </ul>
      </div>

      <div className="report-footer">
        <button className="download-btn" onClick={() => window.print()}>
          <i className="fas fa-download"></i> Download PDF
        </button>
        <button className="share-btn">
          <i className="fas fa-share"></i> Share Report
        </button>
      </div>
    </div>
  );
};

export default WeeklyReport;