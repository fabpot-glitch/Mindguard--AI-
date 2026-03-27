"""Tests for intervention engine."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from engine.intervention_engine import InterventionEngine, Intervention, InterventionType, InterventionLevel


class TestInterventionEngine:
    """Test suite for InterventionEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create intervention engine instance for testing."""
        return InterventionEngine()
    
    def test_initialization(self, engine):
        """Test proper engine initialization."""
        assert len(engine.intervention_history) == 0
        assert engine.active_intervention is None
        assert engine.intervention_count_today == 0
        assert len(engine.templates) > 0
    
    def test_evaluate_no_intervention(self, engine):
        """Test evaluation when no intervention needed."""
        state = {
            'fatigue': 0.5,
            'stress': 0.4,
            'attention': 0.8,
            'cognitive_load': 0.5
        }
        alerts = []
        
        intervention = engine.evaluate(state, alerts)
        assert intervention is None
    
    def test_evaluate_high_fatigue(self, engine):
        """Test evaluation with high fatigue."""
        state = {
            'fatigue': 0.85,
            'stress': 0.4,
            'attention': 0.8,
            'cognitive_load': 0.5
        }
        alerts = [{'type': 'high_fatigue', 'level': 'warning'}]
        
        with patch('random.choice', return_value=InterventionType.BREAK_REMINDER):
            intervention = engine.evaluate(state, alerts)
        
        assert intervention is not None
        assert intervention.type == InterventionType.BREAK_REMINDER
        assert engine.active_intervention is not None
    
    def test_evaluate_critical_fatigue(self, engine):
        """Test evaluation with critical fatigue."""
        state = {
            'fatigue': 0.95,
            'stress': 0.4,
            'attention': 0.8,
            'cognitive_load': 0.5
        }
        alerts = [{'type': 'critical_fatigue', 'level': 'critical'}]
        
        intervention = engine.evaluate(state, alerts)
        
        assert intervention is not None
        assert intervention.level == InterventionLevel.CRITICAL
    
    def test_evaluate_high_stress(self, engine):
        """Test evaluation with high stress."""
        state = {
            'fatigue': 0.5,
            'stress': 0.8,
            'attention': 0.8,
            'cognitive_load': 0.5
        }
        alerts = [{'type': 'high_stress', 'level': 'warning'}]
        
        intervention = engine.evaluate(state, alerts)
        
        assert intervention is not None
        assert intervention.type in [InterventionType.BREATHING_EXERCISE, InterventionType.MINDFULNESS_MOMENT]
    
    def test_evaluate_low_attention(self, engine):
        """Test evaluation with low attention."""
        state = {
            'fatigue': 0.5,
            'stress': 0.4,
            'attention': 0.25,
            'cognitive_load': 0.5
        }
        alerts = [{'type': 'low_attention', 'level': 'warning'}]
        
        intervention = engine.evaluate(state, alerts)
        
        assert intervention is not None
        assert intervention.type in [InterventionType.FOCUS_RECOVERY, InterventionType.TASK_SWITCH_SUGGESTION]
    
    def test_cooldown_period(self, engine):
        """Test cooldown between interventions."""
        engine.last_intervention_time = datetime.now() - timedelta(seconds=30)
        
        # Should not allow intervention (cooldown 120s)
        can_intervene = engine._check_cooldown()
        assert can_intervene == False
        
        # After cooldown
        engine.last_intervention_time = datetime.now() - timedelta(seconds=130)
        can_intervene = engine._check_cooldown()
        assert can_intervene == True
    
    def test_daily_limit(self, engine):
        """Test daily intervention limit."""
        engine.intervention_count_today = 50  # Above limit
        
        can_intervene = engine._check_daily_limit()
        assert can_intervene == False
        
        # New day
        engine.last_reset_date = datetime.now().date() - timedelta(days=1)
        engine.intervention_count_today = 50
        
        can_intervene = engine._check_daily_limit()
        assert can_intervene == True
    
    def test_complete_intervention(self, engine, mock_intervention):
        """Test completing an intervention."""
        # Create intervention
        intervention = Intervention(
            type=InterventionType.BREAK_REMINDER,
            level=InterventionLevel.WARNING,
            message='Test',
            duration_seconds=300,
            actions=['Test']
        )
        engine.active_intervention = intervention
        
        # Complete it
        result = engine.complete_intervention(intervention.id)
        
        assert result == True
        assert engine.active_intervention is None
    
    def test_dismiss_intervention(self, engine, mock_intervention):
        """Test dismissing an intervention."""
        # Create intervention
        intervention = Intervention(
            type=InterventionType.BREAK_REMINDER,
            level=InterventionLevel.WARNING,
            message='Test',
            duration_seconds=300,
            actions=['Test']
        )
        engine.active_intervention = intervention
        
        # Dismiss it
        result = engine.dismiss_intervention(intervention.id)
        
        assert result == True
        assert engine.active_intervention is None
    
    def test_get_active_intervention(self, engine):
        """Test getting active intervention."""
        assert engine.get_active_intervention() is None
        
        # Create and set intervention
        intervention = Intervention(
            type=InterventionType.BREAK_REMINDER,
            level=InterventionLevel.WARNING,
            message='Test',
            duration_seconds=300,
            actions=['Test']
        )
        engine.active_intervention = intervention
        
        active = engine.get_active_intervention()
        assert active is not None
        assert active['type'] == 'break_reminder'
    
    def test_intervention_history(self, engine):
        """Test intervention history tracking."""
        # Create multiple interventions
        for i in range(5):
            intervention = Intervention(
                type=InterventionType.BREAK_REMINDER,
                level=InterventionLevel.WARNING,
                message=f'Test {i}',
                duration_seconds=300,
                actions=['Test']
            )
            engine.intervention_history.append(intervention)
        
        history = engine.get_intervention_history(limit=3)
        assert len(history) == 3
    
    def test_get_statistics(self, engine):
        """Test statistics retrieval."""
        # Add some history
        for i in range(3):
            intervention = Intervention(
                type=InterventionType.BREAK_REMINDER if i % 2 == 0 else InterventionType.BREATHING_EXERCISE,
                level=InterventionLevel.WARNING,
                message=f'Test {i}',
                duration_seconds=300,
                actions=['Test']
            )
            engine.intervention_history.append(intervention)
        
        stats = engine.get_statistics()
        
        assert 'total_today' in stats
        assert 'last_intervention' in stats
        assert 'active' in stats
        assert 'by_type' in stats
    
    def test_create_intervention(self, engine):
        """Test intervention creation from template."""
        intervention = engine._create_intervention(
            InterventionType.BREAK_REMINDER,
            'warning'
        )
        
        assert intervention.type == InterventionType.BREAK_REMINDER
        assert intervention.level == InterventionLevel.WARNING
        assert intervention.duration_seconds > 0
        assert len(intervention.actions) > 0


class TestIntervention:
    """Test suite for Intervention class."""
    
    def test_creation(self):
        """Test intervention creation."""
        intervention = Intervention(
            type=InterventionType.BREAK_REMINDER,
            level=InterventionLevel.WARNING,
            message='Test intervention',
            duration_seconds=300,
            actions=['Action 1', 'Action 2']
        )
        
        assert intervention.type == InterventionType.BREAK_REMINDER
        assert intervention.level == InterventionLevel.WARNING
        assert intervention.message == 'Test intervention'
        assert intervention.duration_seconds == 300
        assert len(intervention.actions) == 2
        assert intervention.id is not None
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        intervention = Intervention(
            type=InterventionType.BREAK_REMINDER,
            level=InterventionLevel.WARNING,
            message='Test',
            duration_seconds=300,
            actions=['Action 1']
        )
        
        d = intervention.to_dict()
        
        assert d['type'] == 'break_reminder'
        assert d['level'] == 'warning'
        assert d['message'] == 'Test'
        assert d['duration_seconds'] == 300
        assert 'timestamp' in d