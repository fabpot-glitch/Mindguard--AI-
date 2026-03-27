import React, { useEffect, useRef, useState } from 'react';
import './Timeline.css';

const Timeline = ({ data, height = 200, selectedMetric = 'all', timeRange = '1h' }) => {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height });
  const [hoveredPoint, setHoveredPoint] = useState(null);

  // Metrics to display
  const metrics = [
    { key: 'fatigue', color: '#F44336', name: 'Fatigue' },
    { key: 'stress', color: '#FF9800', name: 'Stress' },
    { key: 'attention', color: '#4CAF50', name: 'Attention' },
    { key: 'cognitive_load', color: '#9C27B0', name: 'Cognitive Load' }
  ].filter(m => selectedMetric === 'all' || m.key === selectedMetric);

  // Filter data based on time range
  const getFilteredData = () => {
    if (!data || data.length === 0) return [];
    
    const now = new Date().getTime();
    const rangeMap = {
      '15m': 15 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '4h': 4 * 60 * 60 * 1000,
      '1d': 24 * 60 * 60 * 1000
    };
    
    const cutoff = now - rangeMap[timeRange];
    return data.filter(d => new Date(d.timestamp).getTime() > cutoff);
  };

  const filteredData = getFilteredData();

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height
        });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [height]);

  // Draw chart
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || filteredData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const { width, height } = dimensions;
    
    canvas.width = width;
    canvas.height = height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw background grid
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    
    // Horizontal grid lines
    for (let i = 0; i <= 4; i++) {
      const y = height - (height * i / 4);
      ctx.beginPath();
      ctx.moveTo(40, y);
      ctx.lineTo(width - 20, y);
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.stroke();
      
      // Labels
      ctx.fillStyle = 'rgba(255,255,255,0.5)';
      ctx.font = '10px Inter';
      ctx.fillText(`${i * 25}%`, 10, y - 5);
    }

    // Draw lines for each metric
    metrics.forEach((metric, idx) => {
      const points = [];
      
      // Calculate points
      filteredData.forEach((point, i) => {
        const x = 40 + (i / (filteredData.length - 1)) * (width - 60);
        const y = height - (point[metric.key] || 0) * height;
        points.push({ x, y, value: point[metric.key], timestamp: point.timestamp });
      });

      // Draw line
      ctx.beginPath();
      ctx.strokeStyle = metric.color;
      ctx.lineWidth = 2;
      
      points.forEach((point, i) => {
        if (i === 0) {
          ctx.moveTo(point.x, point.y);
        } else {
          ctx.lineTo(point.x, point.y);
        }
      });
      
      ctx.stroke();

      // Draw points
      points.forEach(point => {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 3, 0, 2 * Math.PI);
        ctx.fillStyle = metric.color;
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 1;
        ctx.stroke();
      });
    });

    // Draw time labels
    if (filteredData.length > 0) {
      const labelIndices = [0, Math.floor(filteredData.length / 2), filteredData.length - 1];
      labelIndices.forEach(idx => {
        const point = filteredData[idx];
        const x = 40 + (idx / (filteredData.length - 1)) * (width - 60);
        
        ctx.fillStyle = 'rgba(255,255,255,0.5)';
        ctx.font = '10px Inter';
        
        const date = new Date(point.timestamp);
        const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        ctx.fillText(timeStr, x - 20, height - 5);
      });
    }

  }, [filteredData, dimensions, metrics]);

  // Handle mouse move for tooltips
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Find closest point
    let closestPoint = null;
    let minDist = Infinity;

    filteredData.forEach((point, i) => {
      const pointX = 40 + (i / (filteredData.length - 1)) * (dimensions.width - 60);
      const dist = Math.abs(x - pointX);
      
      if (dist < minDist && dist < 20) {
        minDist = dist;
        closestPoint = { ...point, x: pointX, index: i };
      }
    });

    setHoveredPoint(closestPoint);
  };

  return (
    <div className="timeline" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className="timeline-canvas"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredPoint(null)}
      />

      {hoveredPoint && (
        <div 
          className="tooltip"
          style={{ left: hoveredPoint.x + 10, top: hoveredPoint.y - 40 }}
        >
          <div className="tooltip-time">
            {new Date(hoveredPoint.timestamp).toLocaleString()}
          </div>
          {metrics.map(metric => (
            <div key={metric.key} className="tooltip-value">
              <span style={{ color: metric.color }}>●</span>
              {metric.name}: {Math.round(hoveredPoint[metric.key] * 100)}%
            </div>
          ))}
        </div>
      )}

      {filteredData.length === 0 && (
        <div className="no-data">
          No data available for selected time range
        </div>
      )}
    </div>
  );
};

export default Timeline;