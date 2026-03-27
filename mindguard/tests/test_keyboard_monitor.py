"""Tests for keyboard monitor collector."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pynput import keyboard

from collectors.keyboard_monitor import KeyboardMonitor
from collectors.base_collector import DataPoint


class TestKeyboardMonitor:
    """Test suite for KeyboardMonitor."""
    
    @pytest.fixture
    def keyboard_monitor(self):
        """Create keyboard monitor instance for testing."""
        return KeyboardMonitor(sampling_rate=100.0)
    
    def test_initialization(self, keyboard_monitor):
        """Test proper initialization."""
        assert keyboard_monitor.name == "keyboard_monitor"
        assert keyboard_monitor.sampling_rate == 100.0
        assert keyboard_monitor.key_count == 0
        assert keyboard_monitor.hesitation_count == 0
        assert keyboard_monitor.hesitation_threshold == 0.5
    
    def test_validate_sample(self, keyboard_monitor):
        """Test sample validation."""
        # Valid sample
        valid_sample = DataPoint(
            timestamp=datetime.now(),
            source="keyboard",
            data={
                "typing_speed": 45.0,
                "rhythm_variance": 0.12,
                "hesitation_rate": 0.05,
                "avg_hold_time": 0.08,
                "key_count": 150,
                "is_typing": True
            }
        )
        assert keyboard_monitor.validate_sample(valid_sample) == True
        
        # Invalid sample (missing field)
        invalid_sample = DataPoint(
            timestamp=datetime.now(),
            source="keyboard",
            data={
                "typing_speed": 45.0
                # missing other fields
            }
        )
        assert keyboard_monitor.validate_sample(invalid_sample) == False
        
        # Invalid sample (value out of range)
        out_of_range_sample = DataPoint(
            timestamp=datetime.now(),
            source="keyboard",
            data={
                "typing_speed": 1000.0,  # Too high
                "rhythm_variance": 0.12,
                "hesitation_rate": 0.05,
                "avg_hold_time": 0.08,
                "key_count": 150,
                "is_typing": True
            }
        )
        assert keyboard_monitor.validate_sample(out_of_range_sample) == False
    
    def test_on_press(self, keyboard_monitor):
        """Test key press event handling."""
        # Mock a key press
        mock_key = Mock(spec=keyboard.Key)
        mock_key.__hash__ = Mock(return_value=12345)
        
        current_time = time.time()
        
        with patch('time.time', return_value=current_time):
            keyboard_monitor._on_press(mock_key)
        
        assert len(keyboard_monitor.key_times) == 1
        assert keyboard_monitor.key_times[0] == current_time
        assert keyboard_monitor.key_count == 1
        assert 12345 in keyboard_monitor.press_times
    
    def test_on_release(self, keyboard_monitor):
        """Test key release event handling."""
        # Setup a press
        mock_key = Mock(spec=keyboard.Key)
        mock_key.__hash__ = Mock(return_value=12345)
        
        press_time = time.time() - 0.1  # 100ms hold
        keyboard_monitor.press_times[12345] = press_time
        
        release_time = press_time + 0.1
        with patch('time.time', return_value=release_time):
            keyboard_monitor._on_release(mock_key)
        
        assert 12345 not in keyboard_monitor.press_times
        assert len(keyboard_monitor.hold_times) == 1
        assert keyboard_monitor.hold_times[0] == 0.1
    
    def test_collect_sample(self, keyboard_monitor):
        """Test sample collection."""
        # Add some typing data
        current_time = time.time()
        keyboard_monitor.key_times = [
            current_time - 2.0,
            current_time - 1.5,
            current_time - 1.0,
            current_time - 0.5
        ]
        keyboard_monitor.key_intervals.extend([0.5, 0.5, 0.5])
        keyboard_monitor.key_count = 4
        keyboard_monitor.hesitation_count = 1
        keyboard_monitor.hold_times = [0.08, 0.09, 0.07]
        
        sample = keyboard_monitor._collect_sample()
        
        assert sample is not None
        assert sample.source == "keyboard"
        assert sample.data["typing_speed"] > 0
        assert sample.data["key_count"] == 4
        assert sample.data["hesitation_rate"] == 0.25
    
    def test_typing_speed_calculation(self, keyboard_monitor):
        """Test typing speed calculation."""
        # Simulate typing at 60 WPM equivalent
        current_time = time.time()
        intervals = [0.2] * 20  # 300ms between keys = 200 keys/min ≈ 40 WPM
        keyboard_monitor.key_times = [current_time - i * 0.2 for i in range(20, 0, -1)]
        
        keyboard_monitor._calculate_typing_speed()
        
        assert keyboard_monitor.typing_speed > 0
    
    def _calculate_typing_speed(self):
        """Helper to calculate typing speed."""
        if len(self.key_times) >= 2:
            recent_times = self.key_times[-20:]
            if len(recent_times) >= 2:
                time_span = recent_times[-1] - recent_times[0]
                if time_span > 0:
                    keys_per_second = len(recent_times) / time_span
                    self.typing_speed = keys_per_second * 60
    
    def test_rhythm_variance_calculation(self, keyboard_monitor):
        """Test rhythm variance calculation."""
        keyboard_monitor.key_intervals.extend([0.2, 0.21, 0.19, 0.22, 0.2])
        
        keyboard_monitor._calculate_rhythm_variance()
        
        assert keyboard_monitor.rhythm_variance > 0
    
    def _calculate_rhythm_variance(self):
        """Helper to calculate rhythm variance."""
        if len(self.key_intervals) > 5:
            intervals = list(self.key_intervals)
            self.rhythm_variance = float(np.var(intervals))
    
    def test_hesitation_detection(self, keyboard_monitor):
        """Test hesitation detection."""
        keyboard_monitor.hesitation_threshold = 0.5
        
        # Fast typing (no hesitation)
        with patch('time.time', return_value=100.0):
            keyboard_monitor._on_press(Mock())
        
        with patch('time.time', return_value=100.3):  # 300ms interval
            keyboard_monitor._on_press(Mock())
        
        assert keyboard_monitor.hesitation_count == 0
        
        # Slow typing (hesitation)
        with patch('time.time', return_value=101.0):  # 700ms interval
            keyboard_monitor._on_press(Mock())
        
        assert keyboard_monitor.hesitation_count == 1
    
    def test_calibration(self, keyboard_monitor):
        """Test calibration process."""
        # Simulate typing during calibration
        with patch.object(keyboard_monitor, 'key_count', 50):
            with patch.object(keyboard_monitor, 'key_intervals', [0.2] * 20):
                with patch('time.sleep', return_value=None):
                    result = keyboard_monitor.calibrate()
                    
                    assert isinstance(result, bool)
    
    def test_get_statistics(self, keyboard_monitor):
        """Test statistics retrieval."""
        keyboard_monitor.key_count = 1000
        keyboard_monitor.hesitation_count = 50
        keyboard_monitor.key_intervals.extend([0.2] * 50)
        keyboard_monitor.hold_times = [0.08] * 50
        
        stats = keyboard_monitor.get_statistics()
        
        assert stats["name"] == "keyboard_monitor"
        assert stats["total_keys"] == 1000
        assert stats["hesitations"] == 50
        assert "avg_interval" in stats
        assert "avg_hold_time" in stats
    
    def test_privacy_safe(self, keyboard_monitor):
        """Test that keyboard monitor is privacy-safe (no key content)."""
        # Press a key
        mock_key = Mock(spec=keyboard.Key)
        mock_key.__hash__ = Mock(return_value=12345)
        
        keyboard_monitor._on_press(mock_key)
        
        # Check that we store hash, not the key itself
        assert 12345 in keyboard_monitor.press_times
        assert not hasattr(keyboard_monitor, 'key_history') or not keyboard_monitor.key_history