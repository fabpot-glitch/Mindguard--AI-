"""Intervention engine for proactive fatigue prevention."""

import random
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

from config.logging_config import get_logger, intervention_logger
from config import thresholds

logger = get_logger(__name__)


class InterventionType(Enum):
    """Types of interventions."""
    BREAK_REMINDER = 'break_reminder'
    BREATHING_EXERCISE = 'breathing_exercise'
    HYDRATION_REMINDER = 'hydration_reminder'
    TASK_SWITCH_SUGGESTION = 'task_switch_suggestion'
    STRETCH_REMINDER = 'stretch_reminder'
    FOCUS_RECOVERY = 'focus_recovery'
    ENERGY_BOOST = 'energy_boost'
    MINDFULNESS_MOMENT = 'mindfulness_moment'


class InterventionLevel(Enum):
    """Intervention severity levels."""
    INFO = 'info'
    SUGGESTION = 'suggestion'
    WARNING = 'warning'
    CRITICAL = 'critical'


class Intervention:
    """Single intervention instance."""
    
    def __init__(
        self,
        type: InterventionType,
        level: InterventionLevel,
        message: str,
        duration_seconds: int = 60,
        actions: Optional[List[str]] = None
    ):
        self.type = type
        self.level = level
        self.message = message
        self.duration_seconds = duration_seconds
        self.actions = actions or []
        self.timestamp = datetime.now()
        self.id = f"{type.value}_{int(self.timestamp.timestamp())}"
        self.status = 'pending'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'type': self.type.value,
            'level': self.level.value,
            'message': self.message,
            'duration_seconds': self.duration_seconds,
            'actions': self.actions,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status
        }


class InterventionEngine:
    """Engine for managing cognitive interventions."""
    
    def __init__(self):
        """Initialize intervention engine."""
        self.intervention_history: deque = deque(maxlen=100)
        self.active_intervention: Optional[Intervention] = None
        self.last_intervention_time: Optional[datetime] = None
        self.intervention_count_today = 0
        self.last_reset_date = datetime.now().date()
        
        # Callbacks
        self.intervention_callbacks: List[Callable] = []
        
        # Intervention templates
        self.templates = self._init_templates()
        
        # Trigger rules
        self.trigger_rules = {
            'critical_fatigue': [InterventionType.BREAK_REMINDER, InterventionType.MINDFULNESS_MOMENT],
            'high_fatigue': [InterventionType.BREAK_REMINDER, InterventionType.STRETCH_REMINDER],
            'high_stress': [InterventionType.BREATHING_EXERCISE, InterventionType.MINDFULNESS_MOMENT],
            'low_attention': [InterventionType.FOCUS_RECOVERY, InterventionType.TASK_SWITCH_SUGGESTION],
            'high_cognitive_load': [InterventionType.BREAK_REMINDER, InterventionType.ENERGY_BOOST],
            'fatigue_anomaly': [InterventionType.BREAK_REMINDER, InterventionType.HYDRATION_REMINDER]
        }
        
        logger.info("InterventionEngine initialized")
    
    def _init_templates(self) -> Dict[InterventionType, Dict]:
        """Initialize intervention templates."""
        return {
            InterventionType.BREAK_REMINDER: {
                'messages': [
                    "Time for a short break. Your fatigue level is elevated.",
                    "Consider taking a 5-minute break to recharge.",
                    "Your cognitive load is high. A brief pause would help.",
                    "Stand up and stretch for a few minutes."
                ],
                'actions': ['Take 5 min break', 'Postpone 15 min', 'Dismiss'],
                'duration': 300
            },
            InterventionType.BREATHING_EXERCISE: {
                'messages': [
                    "Try a quick breathing exercise: 4-7-8 breathing.",
                    "Let's do 1 minute of deep breathing together.",
                    "Stress detected. Follow along with a breathing exercise.",
                    "Take 5 deep breaths to reset."
                ],
                'actions': ['Start exercise', 'Later', 'Dismiss'],
                'duration': 60
            },
            InterventionType.HYDRATION_REMINDER: {
                'messages': [
                    "Time to hydrate! Your focus may improve with water.",
                    "Grab a glass of water - dehydration affects cognition.",
                    "Hydration break recommended. Your brain needs water.",
                    "Drink some water and see how you feel."
                ],
                'actions': ['Mark as done', 'Remind in 15 min', 'Dismiss'],
                'duration': 120
            },
            InterventionType.TASK_SWITCH_SUGGESTION: {
                'messages': [
                    "Consider switching to a different task type.",
                    "Your attention is drifting. A task change might help.",
                    "Time for a context switch? Try something different.",
                    "Switch to a simpler task for a while."
                ],
                'actions': ['Switch task', 'Stay focused', 'Dismiss'],
                'duration': 60
            },
            InterventionType.STRETCH_REMINDER: {
                'messages': [
                    "Quick stretch break? Your body will thank you.",
                    "Stand up and stretch for 2 minutes.",
                    "Physical movement can boost mental energy.",
                    "Roll your shoulders, stretch your neck."
                ],
                'actions': ['Start stretch', 'Later', 'Dismiss'],
                'duration': 120
            },
            InterventionType.FOCUS_RECOVERY: {
                'messages': [
                    "Let's refocus. Clear one small task now.",
                    "Pick one thing to complete in the next 5 minutes.",
                    "Focus recovery mode: eliminate distractions.",
                    "Close unnecessary tabs and focus on one thing."
                ],
                'actions': ['Start focus', 'Dismiss'],
                'duration': 300
            },
            InterventionType.ENERGY_BOOST: {
                'messages': [
                    "Energy dip detected. Quick boost suggestions:",
                    "• Stand up and walk briefly",
                    "• Splash cold water on face",
                    "• Have a healthy snack"
                ],
                'actions': ['Try something', 'Dismiss'],
                'duration': 180
            },
            InterventionType.MINDFULNESS_MOMENT: {
                'messages': [
                    "Take 2 minutes for mindfulness.",
                    "Close your eyes and focus on your breath.",
                    "Be present in this moment.",
                    "Notice your thoughts without judgment."
                ],
                'actions': ['Start mindfulness', 'Dismiss'],
                'duration': 120
            }
        }
    
    def evaluate(self, state: Dict[str, Any], alerts: List[Dict]) -> Optional[Intervention]:
        """
        Evaluate if intervention is needed.
        
        Args:
            state: Current cognitive state
            alerts: Current alerts
            
        Returns:
            Intervention if needed, None otherwise
        """
        # Check cooldown
        if not self._check_cooldown():
            return None
        
        # Check daily limit
        if not self._check_daily_limit():
            return None
        
        # Check if already active
        if self.active_intervention:
            return None
        
        # Evaluate alerts
        for alert in alerts:
            alert_type = alert.get('type')
            if alert_type in self.trigger_rules:
                # Select appropriate intervention type
                intervention_types = self.trigger_rules[alert_type]
                selected_type = random.choice(intervention_types)
                
                # Create intervention
                intervention = self._create_intervention(
                    selected_type,
                    alert.get('level', 'warning')
                )
                
                if intervention:
                    self.active_intervention = intervention
                    self.intervention_history.append(intervention)
                    self.last_intervention_time = datetime.now()
                    self.intervention_count_today += 1
                    
                    logger.info(f"Intervention triggered: {intervention.type.value} due to {alert_type}")
                    
                    # Trigger callbacks
                    self._trigger_intervention_callbacks(intervention)
                    
                    return intervention
        
        return None
    
    def _check_cooldown(self) -> bool:
        """Check if enough time has passed since last intervention."""
        if not self.last_intervention_time:
            return True
        
        cooldown_seconds = thresholds.intervention_cooldown
        elapsed = (datetime.now() - self.last_intervention_time).seconds
        return elapsed >= cooldown_seconds
    
    def _check_daily_limit(self) -> bool:
        """Check if daily intervention limit not exceeded."""
        # Reset counter if new day
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.intervention_count_today = 0
            self.last_reset_date = today
        
        max_daily = thresholds.max_interventions_per_hour * 8
        return self.intervention_count_today < max_daily
    
    def _create_intervention(self, type: InterventionType, level: str) -> Intervention:
        """Create intervention instance from template."""
        template = self.templates[type]
        
        # Map alert level to intervention level
        level_map = {
            'critical': InterventionLevel.CRITICAL,
            'warning': InterventionLevel.WARNING,
            'info': InterventionLevel.INFO,
            'suggestion': InterventionLevel.SUGGESTION
        }
        intervention_level = level_map.get(level, InterventionLevel.SUGGESTION)
        
        # Select random message
        message = random.choice(template['messages'])
        
        return Intervention(
            type=type,
            level=intervention_level,
            message=message,
            duration_seconds=template['duration'],
            actions=template['actions']
        )
    
    def complete_intervention(self, intervention_id: str) -> bool:
        """Mark intervention as completed."""
        if self.active_intervention and self.active_intervention.id == intervention_id:
            self.active_intervention.status = 'completed'
            self.active_intervention = None
            logger.info(f"Intervention {intervention_id} completed")
            return True
        
        # Check history
        for intervention in self.intervention_history:
            if intervention.id == intervention_id:
                intervention.status = 'completed'
                return True
        
        return False
    
    def dismiss_intervention(self, intervention_id: str) -> bool:
        """Dismiss active intervention."""
        if self.active_intervention and self.active_intervention.id == intervention_id:
            self.active_intervention.status = 'dismissed'
            self.active_intervention = None
            logger.info(f"Intervention {intervention_id} dismissed")
            return True
        return False
    
    def register_intervention_callback(self, callback: Callable):
        """Register callback for interventions."""
        self.intervention_callbacks.append(callback)
    
    def _trigger_intervention_callbacks(self, intervention: Intervention):
        """Trigger intervention callbacks."""
        for callback in self.intervention_callbacks:
            try:
                callback(intervention.to_dict())
            except Exception as e:
                logger.error(f"Intervention callback failed: {e}")
    
    def get_active_intervention(self) -> Optional[Dict[str, Any]]:
        """Get currently active intervention."""
        if self.active_intervention:
            return self.active_intervention.to_dict()
        return None
    
    def get_intervention_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent intervention history."""
        history = list(self.intervention_history)[-limit:]
        return [i.to_dict() for i in history]
    
    def get_interventions_by_type(self, type: str) -> List[Dict[str, Any]]:
        """Get interventions by type."""
        return [
            i.to_dict() for i in self.intervention_history
            if i.type.value == type
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get intervention statistics."""
        return {
            'total_today': self.intervention_count_today,
            'last_intervention': self.last_intervention_time.isoformat() if self.last_intervention_time else None,
            'active': self.active_intervention is not None,
            'by_type': {
                type.value: sum(1 for i in self.intervention_history if i.type == type)
                for type in InterventionType
            },
            'by_level': {
                level.value: sum(1 for i in self.intervention_history if i.level == level)
                for level in InterventionLevel
            }
        }
    
    def reset(self):
        """Reset intervention engine."""
        self.active_intervention = None
        self.last_intervention_time = None
        self.intervention_count_today = 0
        self.last_reset_date = datetime.now().date()
        logger.info("InterventionEngine reset")