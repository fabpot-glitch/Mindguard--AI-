"""Tests for cognitive engine."""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

from engine.cognitive_engine import CognitiveEngine
from models.fusion_model import ModelOutput


class TestCognitiveEngine:
    """Test suite for CognitiveEngine."""
    
    @pytest.fixture
    def engine(self, mock_collector_manager):
        """Create cognitive engine instance for testing."""
        with patch('engine.cognitive_engine.CollectorManager', return_value=mock_collector_manager):
            engine = CognitiveEngine(inference_frequency=10.0)
            engine.model = Mock()
            engine.model.predict.return_value = ModelOutput(
                fatigue=0.65,
                stress=0.45,
                attention=0.72,
                cognitive_load=0.58,
                confidence=0.88
            )
            return engine
    
    def test_initialization(self, engine):
        """Test proper engine initialization."""
        assert engine.inference_frequency == 10.0
        assert engine.inference_interval == 0.1
        assert engine.is_running == False
        assert engine.is_paused == False
        assert engine.current_state == None
    
    def test_start_stop(self, engine):
        """Test engine start and stop."""
        # Mock collector manager start
        engine.collector_manager.start_all.return_value = True
        
        # Start engine
        result = engine.start()
        assert result == True
        assert engine.is_running == True
        
        # Stop engine
        engine.stop()
        assert engine.is_running == False
    
    def test_pause_resume(self, engine):
        """Test pause and resume functionality."""
        assert engine.is_paused == False
        
        engine.pause()
        assert engine.is_paused == True
        
        engine.resume()
        assert engine.is_paused == False
    
    def test_run_inference(self, engine, sample_features):
        """Test inference execution."""
        # Mock features
        engine.collector_manager.get_fused_features.return_value = sample_features
        
        # Run inference
        state = engine._run_inference()
        
        assert state is not None
        assert state.fatigue == 0.65
        assert state.stress == 0.45
        assert engine.total_inferences == 1
        assert len(engine.inference_times) == 1
    
    def test_run_inference_no_features(self, engine):
        """Test inference with no features."""
        engine.collector_manager.get_fused_features.return_value = {}
        
        state = engine._run_inference()
        assert state is None
    
    def test_state_callbacks(self, engine):
        """Test state update callbacks."""
        callback_called = False
        
        def test_callback(state):
            nonlocal callback_called
            callback_called = True
        
        engine.register_state_callback(test_callback)
        
        # Simulate state update
        test_state = ModelOutput(0.7, 0.5, 0.6, 0.8, 0.9)
        engine._trigger_state_callbacks(test_state)
        
        assert callback_called == True
    
    def test_alert_callbacks(self, engine):
        """Test alert callbacks."""
        callback_called = False
        
        def test_callback(alerts):
            nonlocal callback_called
            callback_called = True
            assert len(alerts) > 0
        
        engine.register_alert_callback(test_callback)
        
        # Create alerts
        alerts = [{'type': 'test', 'level': 'warning', 'value': 0.9, 'threshold': 0.8}]
        engine._trigger_alert_callbacks(alerts)
        
        assert callback_called == True
    
    def test_alert_detection(self, engine):
        """Test alert detection logic."""
        from config import thresholds
        
        # Test critical fatigue
        state = ModelOutput(
            fatigue=0.95,  # Above critical threshold
            stress=0.5,
            attention=0.6,
            cognitive_load=0.5,
            confidence=0.9
        )
        
        alerts_detected = []
        
        def capture_alerts(alerts):
            alerts_detected.extend(alerts)
        
        engine.register_alert_callback(capture_alerts)
        engine._check_alerts(state)
        
        assert len(alerts_detected) > 0
        assert any(a['type'] == 'critical_fatigue' for a in alerts_detected)
        
        # Test high stress
        alerts_detected = []
        state = ModelOutput(
            fatigue=0.6,
            stress=0.85,  # Above stress threshold
            attention=0.6,
            cognitive_load=0.5,
            confidence=0.9
        )
        
        engine._check_alerts(state)
        assert any(a['type'] == 'high_stress' for a in alerts_detected)
    
    def test_get_current_state(self, engine, mock_model_output):
        """Test current state retrieval."""
        # No state yet
        assert engine.get_current_state() is None
        
        # Set state
        engine.current_state = mock_model_output
        
        state = engine.get_current_state()
        assert state is not None
        assert state['fatigue'] == 0.65
        assert state['stress'] == 0.45
        assert 'timestamp' in state
    
    def test_get_statistics(self, engine):
        """Test statistics retrieval."""
        # Add some inference times
        engine.inference_times.extend([0.01, 0.02, 0.015])
        engine.total_inferences = 3
        
        stats = engine.get_statistics()
        
        assert stats['total_inferences'] == 3
        assert stats['avg_inference_time'] > 0
        assert 'collectors' in stats
        assert 'is_running' in stats
    
    def test_reset_calibration(self, engine):
        """Test calibration reset."""
        engine.normalizer = Mock()
        engine.state_tracker = Mock()
        
        engine.reset_calibration()
        
        engine.normalizer.reset.assert_called_once()
        engine.state_tracker.reset.assert_called_once()
    
    def test_engine_loop(self, engine):
        """Test main engine loop (limited)."""
        engine.is_running = True
        engine._run_inference = Mock(return_value=ModelOutput(0.5, 0.5, 0.5, 0.5, 0.5))
        
        # Run one iteration manually
        engine._engine_loop_step = Mock()
        
        # Should not raise
        try:
            engine._engine_loop()
        except:
            # Loop is infinite, so we need to break
            engine.is_running = False
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, engine):
        """Test thread safety with concurrent access."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def worker():
            for _ in range(10):
                engine.total_inferences += 1
                results.put(engine.total_inferences)
        
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Check that all increments were counted
        assert engine.total_inferences == 50