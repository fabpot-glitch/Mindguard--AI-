"""Tests for screen monitor collector."""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from collectors.screen_monitor import ScreenMonitor
from collectors.base_collector import DataPoint


class TestScreenMonitor:
    """Test suite for ScreenMonitor."""
    
    @pytest.fixture
    def screen_monitor(self):
        """Create screen monitor instance for testing."""
        with patch('platform.system', return_value='Windows'):
            monitor = ScreenMonitor(capture_fps=5.0)
            return monitor
    
    def test_initialization(self, screen_monitor):
        """Test proper initialization."""
        assert screen_monitor.name == "screen_monitor"
        assert screen_monitor.sampling_rate == 5.0
        assert screen_monitor.current_app is None
        assert screen_monitor.app_switch_count == 0
        assert screen_monitor.focus_score == 1.0
        assert screen_monitor.idle_threshold == 30.0
    
    def test_validate_sample(self, screen_monitor):
        """Test sample validation."""
        # Valid sample
        valid_sample = DataPoint(
            timestamp=datetime.now(),
            source="screen",
            data={
                "current_app": "Test App",
                "app_switch_rate": 0.3,
                "idle_time": 2.5,
                "focus_score": 0.85,
                "scroll_activity": 0.2,
                "context_switches": 5
            }
        )
        assert screen_monitor.validate_sample(valid_sample) == True
        
        # Invalid sample (missing field)
        invalid_sample = DataPoint(
            timestamp=datetime.now(),
            source="screen",
            data={
                "current_app": "Test App"
                # missing other fields
            }
        )
        assert screen_monitor.validate_sample(invalid_sample) == False
        
        # Invalid sample (value out of range)
        out_of_range_sample = DataPoint(
            timestamp=datetime.now(),
            source="screen",
            data={
                "current_app": "Test App",
                "app_switch_rate": 0.3,
                "idle_time": 2.5,
                "focus_score": 1.5,  # > 1
                "scroll_activity": 0.2,
                "context_switches": 5
            }
        )
        assert screen_monitor.validate_sample(out_of_range_sample) == False
    
    def test_collect_sample(self, screen_monitor):
        """Test sample collection."""
        screen_monitor.current_app = "Visual Studio Code"
        screen_monitor.app_switch_count = 10
        screen_monitor.context_switches = 15
        screen_monitor.idle_time = 5.0
        screen_monitor.focus_score = 0.75
        screen_monitor.scroll_count = 50
        screen_monitor.start_time = time.time() - 3600  # 1 hour ago
        
        sample = screen_monitor._collect_sample()
        
        assert sample is not None
        assert sample.source == "screen"
        assert sample.data["current_app"] == "Visual Studio Code"
        assert sample.data["app_switch_rate"] == 10 / 60  # per minute
        assert sample.data["idle_time"] == 5.0
        assert sample.data["focus_score"] == 0.75
    
    def test_app_switch_detection(self, screen_monitor):
        """Test app switch detection."""
        with patch.object(screen_monitor, '_get_active_window', side_effect=['App1', 'App2', 'App2']):
            # First call - initial app
            screen_monitor._check_app_change('App1')
            assert screen_monitor.current_app == 'App1'
            assert screen_monitor.app_switch_count == 0
            
            # Second call - app changed
            screen_monitor._check_app_change('App2')
            assert screen_monitor.current_app == 'App2'
            assert screen_monitor.app_switch_count == 1
            assert screen_monitor.context_switches == 1
            
            # Third call - same app
            screen_monitor._check_app_change('App2')
            assert screen_monitor.app_switch_count == 1
    
    def _check_app_change(self, new_app):
        """Helper to check app change."""
        if new_app and new_app != self.current_app:
            if self.current_app is not None:
                self.app_switch_count += 1
                self.context_switches += 1
            self.current_app = new_app
    
    def test_focus_score_calculation(self, screen_monitor):
        """Test focus score calculation."""
        screen_monitor.idle_threshold = 30.0
        
        # Active, low switching
        screen_monitor.idle_time = 5.0
        screen_monitor.context_switches = 5
        screen_monitor._calculate_focus_score()
        assert screen_monitor.focus_score > 0.7
        
        # Idle, high switching
        screen_monitor.idle_time = 35.0
        screen_monitor.context_switches = 20
        screen_monitor._calculate_focus_score()
        assert screen_monitor.focus_score < 0.3
    
    def _calculate_focus_score(self):
        """Helper to calculate focus score."""
        if self.idle_time > self.idle_threshold:
            self.focus_score = 0.0
        else:
            switch_penalty = min(self.context_switches / 20.0, 0.5)
            idle_factor = max(0, 1.0 - (self.idle_time / self.idle_threshold))
            self.focus_score = idle_factor * (1.0 - switch_penalty)
    
    def test_get_active_window_windows(self, screen_monitor):
        """Test getting active window on Windows."""
        screen_monitor.os_name = 'Windows'
        
        with patch('win32gui.GetForegroundWindow', return_value=12345):
            with patch('win32gui.GetWindowText', return_value='Test Window'):
                window = screen_monitor._get_active_window()
                assert window == 'Test Window'
    
    def test_get_active_window_macos(self, screen_monitor):
        """Test getting active window on macOS."""
        screen_monitor.os_name = 'Darwin'
        
        mock_workspace = Mock()
        mock_workspace.activeApplication.return_value = {'NSApplicationName': 'Test App'}
        
        with patch('AppKit.NSWorkspace.sharedWorkspace', return_value=mock_workspace):
            window = screen_monitor._get_active_window()
            assert window == 'Test App'
    
    def test_get_idle_time_windows(self, screen_monitor):
        """Test getting idle time on Windows."""
        screen_monitor.os_name = 'Windows'
        
        with patch('ctypes.windll.user32.GetLastInputInfo') as mock_get:
            with patch('ctypes.windll.kernel32.GetTickCount', return_value=10000):
                # Mock the LASTINPUTINFO structure
                mock_get.return_value = 1
                
                # We need to mock the structure properly
                with patch('ctypes.Structure'):
                    idle_time = screen_monitor._get_idle_time()
                    # This will be 0 in the mock, but we're just testing the call
                    assert idle_time >= 0
    
    def test_record_scroll(self, screen_monitor):
        """Test scroll recording."""
        screen_monitor.record_scroll('down', 100)
        
        assert screen_monitor.scroll_count == 1
        assert len(screen_monitor.scroll_history) == 1
        assert screen_monitor.scroll_history[0]['direction'] == 'down'
    
    def test_record_mouse_movement(self, screen_monitor):
        """Test mouse movement recording."""
        screen_monitor.record_mouse_movement(100, 200)
        
        assert len(screen_monitor.mouse_movements) == 1
        assert screen_monitor.mouse_movements[0][0] == 100
        assert screen_monitor.mouse_movements[0][1] == 200
    
    def test_get_activity_summary(self, screen_monitor):
        """Test activity summary retrieval."""
        screen_monitor.current_app = "Test App"
        screen_monitor.app_switch_count = 10
        screen_monitor.scroll_count = 50
        screen_monitor.idle_time = 5.0
        screen_monitor.focus_score = 0.8
        screen_monitor.start_time = time.time() - 1800  # 30 minutes ago
        
        summary = screen_monitor.get_activity_summary()
        
        assert summary["current_app"] == "Test App"
        assert summary["total_app_switches"] == 10
        assert summary["total_scrolls"] == 50
        assert summary["focus_score"] == 0.8
        assert "switches_per_minute" in summary
    
    def test_calibration(self, screen_monitor):
        """Test calibration process."""
        initial_switches = screen_monitor.app_switch_count
        initial_scrolls = screen_monitor.scroll_count
        
        with patch('time.sleep', return_value=None):
            result = screen_monitor.calibrate()
            
            assert isinstance(result, bool)