import React, { useEffect, useRef } from 'react';
import './RadarChart.css';

const RadarChart = ({ data }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width = 300;
    const height = canvas.height = 300;
    const center = { x: width / 2, y: height / 2 };
    const radius = Math.min(width, height) * 0.35;

    // Define axes
    const axes = [
      { key: 'fatigue', label: 'Fatigue', color: '#F44336' },
      { key: 'stress', label: 'Stress', color: '#FF9800' },
      { key: 'attention', label: 'Attention', color: '#4CAF50' },
      { key: 'cognitive_load', label: 'Cognitive Load', color: '#9C27B0' },
      { key: 'confidence', label: 'Confidence', color: '#4A90E2' }
    ];

    const angleStep = (Math.PI * 2) / axes.length;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw background circles
    for (let i = 1; i <= 4; i++) {
      const r = radius * (i / 4);
      ctx.beginPath();
      ctx.arc(center.x, center.y, r, 0, 2 * Math.PI);
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.stroke();

      // Percentage labels
      ctx.fillStyle = 'rgba(255,255,255,0.3)';
      ctx.font = '10px Inter';
      ctx.fillText(`${i * 25}%`, center.x + r + 5, center.y - 5);
    }

    // Draw axis lines
    axes.forEach((_, i) => {
      const angle = i * angleStep - Math.PI / 2;
      const x = center.x + radius * Math.cos(angle);
      const y = center.y + radius * Math.sin(angle);

      ctx.beginPath();
      ctx.moveTo(center.x, center.y);
      ctx.lineTo(x, y);
      ctx.strokeStyle = 'rgba(255,255,255,0.2)';
      ctx.stroke();

      // Axis labels
      const labelX = center.x + (radius + 20) * Math.cos(angle);
      const labelY = center.y + (radius + 20) * Math.sin(angle);
      ctx.fillStyle = 'rgba(255,255,255,0.7)';
      ctx.font = '12px Inter';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(axes[i].label, labelX, labelY);
    });

    // Draw data polygon
    ctx.beginPath();
    axes.forEach((axis, i) => {
      const value = data[axis.key] || 0.5;
      const angle = i * angleStep - Math.PI / 2;
      const x = center.x + radius * value * Math.cos(angle);
      const y = center.y + radius * value * Math.sin(angle);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.closePath();

    // Fill polygon
    ctx.fillStyle = 'rgba(74, 144, 226, 0.2)';
    ctx.fill();
    
    // Stroke polygon
    ctx.strokeStyle = '#4A90E2';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw data points
    axes.forEach((axis, i) => {
      const value = data[axis.key] || 0.5;
      const angle = i * angleStep - Math.PI / 2;
      const x = center.x + radius * value * Math.cos(angle);
      const y = center.y + radius * value * Math.sin(angle);

      ctx.beginPath();
      ctx.arc(x, y, 5, 0, 2 * Math.PI);
      ctx.fillStyle = axis.color;
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

  }, [data]);

  return (
    <div className="radar-chart">
      <canvas ref={canvasRef} className="radar-canvas"></canvas>
      
      {/* Value summary */}
      <div className="radar-summary">
        {data && (
          <>
            <div className="summary-item">
              <span className="label">Fatigue:</span>
              <span className="value" style={{ color: '#F44336' }}>
                {Math.round(data.fatigue * 100)}%
              </span>
            </div>
            <div className="summary-item">
              <span className="label">Stress:</span>
              <span className="value" style={{ color: '#FF9800' }}>
                {Math.round(data.stress * 100)}%
              </span>
            </div>
            <div className="summary-item">
              <span className="label">Attention:</span>
              <span className="value" style={{ color: '#4CAF50' }}>
                {Math.round(data.attention * 100)}%
              </span>
            </div>
            <div className="summary-item">
              <span className="label">Cognitive Load:</span>
              <span className="value" style={{ color: '#9C27B0' }}>
                {Math.round(data.cognitive_load * 100)}%
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default RadarChart;