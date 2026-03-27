"""State tracker for maintaining cognitive state history and trends."""

import numpy as np
from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StatePoint:
    """Single cognitive state point."""
    timestamp: datetime
    fatigue: float
    stress: float
    attention: float
    cognitive_load: float
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'fatigue': self.fatigue,
            'stress': self.stress,
            'attention': self.attention,
            'cognitive_load': self.cognitive_load,
            'confidence': self.confidence
        }


class StateTracker:
    """Tracks cognitive state history and computes trends."""
    
    def __init__(self, max_history: int = 10000):
        """
        Initialize state tracker.
        
        Args:
            max_history: Maximum number of history points to keep
        """
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.baseline: Optional[Dict[str, float]] = None
        self.last_update: Optional[datetime] = None
        
        # Trend windows (in seconds)
        self.trend_windows = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour
        
        logger.info(f"StateTracker initialized with max history {max_history}")
    
    def update(self, state_point: StatePoint):
        """Add new state point to history."""
        self.history.append(state_point)
        self.last_update = datetime.now()
        
        # Update baseline if needed
        if len(self.history) == 100:  # After 100 points
            self._compute_baseline()
    
    def _compute_baseline(self):
        """Compute baseline from history."""
        if len(self.history) < 50:
            return
        
        # Use last 500 points or all if less
        n_points = min(500, len(self.history))
        recent = list(self.history)[-n_points:]
        
        self.baseline = {
            'fatigue': np.mean([s.fatigue for s in recent]),
            'stress': np.mean([s.stress for s in recent]),
            'attention': np.mean([s.attention for s in recent]),
            'cognitive_load': np.mean([s.cognitive_load for s in recent]),
            'confidence': np.mean([s.confidence for s in recent])
        }
        
        logger.debug("Baseline updated")
    
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Get most recent state."""
        if not self.history:
            return None
        
        latest = self.history[-1]
        return latest.to_dict()
    
    def get_history(self, start_time: Optional[datetime] = None, 
                    end_time: Optional[datetime] = None,
                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get filtered history."""
        states = list(self.history)
        
        if start_time:
            states = [s for s in states if s.timestamp >= start_time]
        if end_time:
            states = [s for s in states if s.timestamp <= end_time]
        if limit:
            states = states[-limit:]
        
        return [s.to_dict() for s in states]
    
    def get_trends(self, window_seconds: int = 300) -> Dict[str, float]:
        """
        Get trends over specified window.
        
        Args:
            window_seconds: Time window for trend calculation
        
        Returns:
            Dictionary of trend values (positive = increasing)
        """
        if len(self.history) < 10:
            return {}
        
        now = datetime.now()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Get points in window
        window_points = [s for s in self.history if s.timestamp >= window_start]
        
        if len(window_points) < 5:
            return {}
        
        # Calculate trends using linear regression
        trends = {}
        metrics = ['fatigue', 'stress', 'attention', 'cognitive_load']
        
        for metric in metrics:
            values = [getattr(s, metric) for s in window_points]
            x = np.arange(len(values))
            
            # Simple linear regression
            slope = np.polyfit(x, values, 1)[0]
            
            # Normalize by value range
            value_range = max(values) - min(values)
            if value_range > 0:
                trends[metric] = slope / value_range * len(values)
            else:
                trends[metric] = 0.0
        
        return trends
    
    def get_deviation_from_baseline(self) -> Dict[str, float]:
        """Get current deviation from baseline."""
        if not self.baseline or not self.history:
            return {}
        
        latest = self.history[-1]
        
        return {
            'fatigue': latest.fatigue - self.baseline['fatigue'],
            'stress': latest.stress - self.baseline['stress'],
            'attention': latest.attention - self.baseline['attention'],
            'cognitive_load': latest.cognitive_load - self.baseline['cognitive_load']
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get state statistics."""
        if len(self.history) < 10:
            return {}
        
        metrics = ['fatigue', 'stress', 'attention', 'cognitive_load', 'confidence']
        stats = {}
        
        for metric in metrics:
            values = [getattr(s, metric) for s in self.history]
            stats[metric] = {
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'current': values[-1]
            }
        
        return stats
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary."""
        return {
            'current': self.get_current_state(),
            'baseline': self.baseline,
            'trends_1min': self.get_trends(60),
            'trends_5min': self.get_trends(300),
            'trends_15min': self.get_trends(900),
            'deviation': self.get_deviation_from_baseline(),
            'statistics': self.get_statistics(),
            'history_length': len(self.history),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def reset(self):
        """Reset tracker."""
        self.history.clear()
        self.baseline = None
        self.last_update = None
        logger.info("StateTracker reset")