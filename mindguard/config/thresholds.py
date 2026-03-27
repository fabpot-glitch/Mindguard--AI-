"""Dynamic threshold management for cognitive states."""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
import json
from pathlib import Path


@dataclass
class AdaptiveThresholds:
    """Adaptive thresholds that adjust to user baseline."""
    
    # Base thresholds
    fatigue_base: float = 0.7
    stress_base: float = 0.65
    attention_base: float = 0.6
    cognitive_load_base: float = 0.7
    
    # Personalization factors
    user_baseline: Dict[str, float] = field(default_factory=dict)
    historical_data: List[Dict] = field(default_factory=list)
    adaptation_rate: float = 0.1
    max_history_size: int = 1000
    
    def __post_init__(self):
        """Initialize user baseline."""
        self.user_baseline = {
            "fatigue": self.fatigue_base,
            "stress": self.stress_base,
            "attention": self.attention_base,
            "cognitive_load": self.cognitive_load_base
        }
    
    def update_baseline(self, measurements: Dict[str, float]) -> None:
        """Update user baseline with new measurements."""
        for key, value in measurements.items():
            if key in self.user_baseline:
                # Exponential moving average
                self.user_baseline[key] = (
                    (1 - self.adaptation_rate) * self.user_baseline[key] +
                    self.adaptation_rate * value
                )
        
        # Store historical data point
        self.historical_data.append({
            "timestamp": datetime.now().isoformat(),
            **measurements
        })
        
        # Keep only last N points
        if len(self.historical_data) > self.max_history_size:
            self.historical_data = self.historical_data[-self.max_history_size:]
    
    def get_adaptive_threshold(self, metric: str, base_multiplier: float = 1.2) -> float:
        """Get adaptive threshold based on user baseline."""
        baseline = self.user_baseline.get(metric, 0.5)
        return min(baseline * base_multiplier, 0.95)
    
    def detect_anomaly(self, value: float, metric: str, std_multiplier: float = 2.0) -> bool:
        """Detect if current value is anomalous."""
        if len(self.historical_data) < 10:
            return False
        
        values = [d.get(metric, 0) for d in self.historical_data[-50:] if metric in d]
        if not values:
            return False
        
        mean = np.mean(values)
        std = np.std(values)
        
        return abs(value - mean) > std_multiplier * std
    
    def save(self, path: Path) -> None:
        """Save thresholds to file."""
        data = {
            "user_baseline": self.user_baseline,
            "historical_data": self.historical_data[-100:],  # Save last 100 points
            "adaptation_rate": self.adaptation_rate
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path: Path) -> None:
        """Load thresholds from file."""
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
            self.user_baseline = data.get("user_baseline", self.user_baseline)
            self.historical_data = data.get("historical_data", [])
            self.adaptation_rate = data.get("adaptation_rate", self.adaptation_rate)


@dataclass
class Thresholds:
    """Main thresholds configuration."""
    
    # Static thresholds
    fatigue_high: float = 0.8
    fatigue_critical: float = 0.9
    stress_high: float = 0.75
    attention_low: float = 0.3
    cognitive_load_high: float = 0.85
    
    # Intervention settings
    intervention_cooldown: int = 120  # seconds
    max_interventions_per_hour: int = 5
    min_intervention_interval: int = 30  # seconds
    
    # Adaptive thresholds
    adaptive: AdaptiveThresholds = field(default_factory=AdaptiveThresholds)
    
    # State tracking
    last_intervention_time: Optional[datetime] = None
    intervention_count: int = 0
    last_reset_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize tracking."""
        self.last_reset_date = datetime.now()
    
    def should_intervene(self, state: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        """Determine if intervention is needed."""
        current_time = datetime.now()
        
        # Reset daily counter if new day
        if current_time.date() != self.last_reset_date.date():
            self.intervention_count = 0
            self.last_reset_date = current_time
        
        # Check daily limit
        if self.intervention_count >= self.max_interventions_per_hour * 8:
            return False, None
        
        # Check cooldown
        if self.last_intervention_time:
            cooldown_remaining = (current_time - self.last_intervention_time).seconds
            if cooldown_remaining < self.min_intervention_interval:
                return False, None
        
        # Check thresholds
        fatigue = state.get("fatigue", 0)
        stress = state.get("stress", 0)
        attention = state.get("attention", 1)
        cognitive_load = state.get("cognitive_load", 0)
        
        if fatigue >= self.fatigue_critical:
            return True, "critical_fatigue"
        elif fatigue >= self.fatigue_high:
            return True, "high_fatigue"
        elif stress >= self.stress_high:
            return True, "high_stress"
        elif attention <= self.attention_low:
            return True, "low_attention"
        elif cognitive_load >= self.cognitive_load_high:
            return True, "high_cognitive_load"
        
        # Check adaptive thresholds
        if self.adaptive.detect_anomaly(fatigue, "fatigue"):
            return True, "fatigue_anomaly"
        
        return False, None
    
    def record_intervention(self) -> None:
        """Record that an intervention was triggered."""
        self.last_intervention_time = datetime.now()
        self.intervention_count += 1
    
    def update_baseline(self, measurements: Dict[str, float]) -> None:
        """Update adaptive baseline with new measurements."""
        self.adaptive.update_baseline(measurements)
    
    def get_current_thresholds(self) -> Dict[str, float]:
        """Get current threshold values."""
        return {
            "fatigue_high": self.fatigue_high,
            "fatigue_critical": self.fatigue_critical,
            "stress_high": self.stress_high,
            "attention_low": self.attention_low,
            "cognitive_load_high": self.cognitive_load_high,
            "adaptive_fatigue": self.adaptive.get_adaptive_threshold("fatigue"),
            "adaptive_stress": self.adaptive.get_adaptive_threshold("stress"),
            "adaptive_attention": self.adaptive.get_adaptive_threshold("attention", 0.8),
            "adaptive_cognitive_load": self.adaptive.get_adaptive_threshold("cognitive_load")
        }
    
    def save(self, path: Path) -> None:
        """Save thresholds to file."""
        data = {
            "fatigue_high": self.fatigue_high,
            "fatigue_critical": self.fatigue_critical,
            "stress_high": self.stress_high,
            "attention_low": self.attention_low,
            "cognitive_load_high": self.cognitive_load_high,
            "intervention_cooldown": self.intervention_cooldown,
            "max_interventions_per_hour": self.max_interventions_per_hour,
            "adaptive": {
                "user_baseline": self.adaptive.user_baseline,
                "adaptation_rate": self.adaptive.adaptation_rate
            }
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path: Path) -> None:
        """Load thresholds from file."""
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.fatigue_high = data.get("fatigue_high", self.fatigue_high)
            self.fatigue_critical = data.get("fatigue_critical", self.fatigue_critical)
            self.stress_high = data.get("stress_high", self.stress_high)
            self.attention_low = data.get("attention_low", self.attention_low)
            self.cognitive_load_high = data.get("cognitive_load_high", self.cognitive_load_high)
            self.intervention_cooldown = data.get("intervention_cooldown", self.intervention_cooldown)
            
            # Load adaptive data
            adaptive_data = data.get("adaptive", {})
            self.adaptive.user_baseline = adaptive_data.get("user_baseline", self.adaptive.user_baseline)
            self.adaptive.adaptation_rate = adaptive_data.get("adaptation_rate", self.adaptive.adaptation_rate)


# Global thresholds instance
thresholds = Thresholds()