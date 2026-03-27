"""Pytest configuration and fixtures."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from engine.cognitive_engine import CognitiveEngine
from engine.intervention_engine import InterventionEngine
from collectors.collector_manager import CollectorManager
from models.fusion_model import CognitiveFusionModel, ModelOutput


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_cognitive_state():
    """Create mock cognitive state."""
    return {
        'fatigue': 0.65,
        'stress': 0.45,
        'attention': 0.72,
        'cognitive_load': 0.58,
        'confidence': 0.88,
        'timestamp': datetime.now().isoformat()
    }


@pytest.fixture
def mock_model_output():
    """Create mock model output."""
    return ModelOutput(
        fatigue=0.65,
        stress=0.45,
        attention=0.72,
        cognitive_load=0.58,
        confidence=0.88
    )


@pytest.fixture
def mock_intervention():
    """Create mock intervention."""
    return {
        'id': 'test_intervention_123',
        'type': 'break_reminder',
        'level': 'warning',
        'message': 'Test intervention message',
        'duration_seconds': 300,
        'actions': ['Take break', 'Dismiss'],
        'timestamp': datetime.now().isoformat()
    }


@pytest.fixture
def sample_features():
    """Create sample features for testing."""
    return {
        'eye': np.random.randn(5).astype(np.float32),
        'keyboard': np.random.randn(5).astype(np.float32),
        'screen': np.random.randn(5).astype(np.float32),
        'voice': np.random.randn(8).astype(np.float32)
    }


@pytest.fixture
def sample_batch_features():
    """Create sample batch features for testing."""
    batch_size = 4
    return {
        'eye': np.random.randn(batch_size, 5).astype(np.float32),
        'keyboard': np.random.randn(batch_size, 5).astype(np.float32),
        'screen': np.random.randn(batch_size, 5).astype(np.float32),
        'voice': np.random.randn(batch_size, 8).astype(np.float32)
    }


@pytest.fixture
def mock_collector_manager():
    """Create mock collector manager."""
    manager = Mock(spec=CollectorManager)
    manager.get_fused_features.return_value = {
        'eye': np.random.randn(5),
        'keyboard': np.random.randn(5),
        'screen': np.random.randn(5)
    }
    manager.get_status.return_value = {
        'eye': {'active': True, 'samples': 1000, 'error_rate': 0.01},
        'keyboard': {'active': True, 'samples': 5000, 'error_rate': 0.02},
        'screen': {'active': True, 'samples': 200, 'error_rate': 0.005}
    }
    return manager


@pytest.fixture
def mock_cognitive_engine(mock_model_output):
    """Create mock cognitive engine."""
    engine = Mock(spec=CognitiveEngine)
    engine.get_current_state.return_value = {
        'fatigue': 0.65,
        'stress': 0.45,
        'attention': 0.72,
        'cognitive_load': 0.58,
        'confidence': 0.88,
        'timestamp': datetime.now().isoformat()
    }
    engine.state_history = [
        {'timestamp': (datetime.now() - timedelta(seconds=i*30)).isoformat(),
         'state': mock_model_output}
        for i in range(10)
    ]
    return engine


@pytest.fixture
def mock_intervention_engine(mock_intervention):
    """Create mock intervention engine."""
    engine = Mock(spec=InterventionEngine)
    engine.get_active_intervention.return_value = mock_intervention
    engine.get_intervention_history.return_value = [mock_intervention]
    return engine


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket."""
    websocket = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.client = Mock()
    websocket.client.host = '127.0.0.1'
    return websocket


@pytest.fixture
def sample_eye_data():
    """Create sample eye tracking data."""
    return {
        'ear': 0.25,
        'blink_rate': 15.0,
        'perclos': 0.08,
        'pupil_dilation': 1.2,
        'face_detected': True
    }


@pytest.fixture
def sample_keyboard_data():
    """Create sample keyboard data."""
    return {
        'typing_speed': 45.0,
        'rhythm_variance': 0.12,
        'hesitation_rate': 0.05,
        'key_count': 150,
        'is_typing': True
    }


@pytest.fixture
def sample_screen_data():
    """Create sample screen data."""
    return {
        'current_app': 'Visual Studio Code',
        'app_switch_rate': 0.3,
        'idle_time': 2.5,
        'focus_score': 0.85,
        'scroll_activity': 0.2,
        'context_switches': 5
    }


@pytest.fixture
def sample_voice_data():
    """Create sample voice data."""
    return {
        'pitch_mean': 120.0,
        'pitch_std': 15.0,
        'energy': 0.05,
        'zero_crossing_rate': 0.15,
        'mfcc_1': -0.5,
        'mfcc_2': 0.3,
        'mfcc_3': -0.2,
        'speech_rate': 3.5,
        'is_speaking': True
    }


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    with patch('config.settings') as mock_settings:
        mock_settings.api.host = '0.0.0.0'
        mock_settings.api.port = 8000
        mock_settings.api.debug = False
        mock_settings.model.device = 'cpu'
        mock_settings.model.path = 'models/weights/mindguard_best.pt'
        mock_settings.thresholds.fatigue_high = 0.8
        mock_settings.thresholds.fatigue_critical = 0.9
        mock_settings.thresholds.stress_high = 0.75
        mock_settings.thresholds.attention_low = 0.3
        yield mock_settings


@pytest.fixture
def mock_data_point():
    """Create mock data point."""
    from collectors.base_collector import DataPoint
    return DataPoint(
        timestamp=datetime.now(),
        source='test',
        data={'value': 42},
        metadata={'test': True}
    )