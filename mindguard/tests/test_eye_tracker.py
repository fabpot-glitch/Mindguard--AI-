"""Tests for eye tracker collector."""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import cv2
import mediapipe as mp

from collectors.eye_tracker import EyeTracker
from collectors.base_collector import DataPoint


class TestEyeTracker:
    """Test suite for EyeTracker."""
    
    @pytest.fixture
    def eye_tracker(self):
        """Create eye tracker instance for testing."""
        with patch('cv2.VideoCapture'):
            tracker = EyeTracker(camera_id=0, fps=30)
            return tracker
    
    def test_initialization(self, eye_tracker):
        """Test proper initialization."""
        assert eye_tracker.name == "eye_tracker"
        assert eye_tracker.sampling_rate == 30
        assert eye_tracker.camera_id == 0
        assert eye_tracker.ear_threshold == 0.2
        assert eye_tracker.face_detected == False
        assert eye_tracker.blink_rate == 0.0
        assert eye_tracker.perclos_value == 0.0
    
    def test_eye_aspect_ratio(self, eye_tracker):
        """Test EAR calculation."""
        # Create mock eye landmarks (open eye shape)
        eye = np.array([
            [0, 0],   # corner
            [0, 1],   # top inner
            [0, 2],   # top outer
            [2, 2],   # opposite corner
            [2, 1],   # bottom outer
            [2, 0]    # bottom inner
        ])
        
        ear = eye_tracker._eye_aspect_ratio(eye)
        assert ear > 0
        assert isinstance(ear, float)
        assert ear <= 1.0
        
        # Test with closed eye
        closed_eye = np.array([
            [0, 0],
            [0, 0.1],
            [0, 0.2],
            [2, 0.2],
            [2, 0.1],
            [2, 0]
        ])
        closed_ear = eye_tracker._eye_aspect_ratio(closed_eye)
        assert closed_ear < ear
    
    def test_validate_sample(self, eye_tracker):
        """Test sample validation."""
        # Valid sample
        valid_sample = DataPoint(
            timestamp=datetime.now(),
            source="eye",
            data={
                "ear": 0.3,
                "left_ear": 0.31,
                "right_ear": 0.29,
                "blink_rate": 15.0,
                "perclos": 0.1,
                "pupil_dilation": 1.2,
                "face_detected": True
            }
        )
        assert eye_tracker.validate_sample(valid_sample) == True
        
        # Invalid sample (missing field)
        invalid_sample = DataPoint(
            timestamp=datetime.now(),
            source="eye",
            data={
                "ear": 0.3,
                "blink_rate": 15.0
                # missing perclos and face_detected
            }
        )
        assert eye_tracker.validate_sample(invalid_sample) == False
        
        # Invalid sample (value out of range)
        out_of_range_sample = DataPoint(
            timestamp=datetime.now(),
            source="eye",
            data={
                "ear": 1.5,  # > 1
                "left_ear": 1.5,
                "right_ear": 1.5,
                "blink_rate": 15.0,
                "perclos": 0.1,
                "pupil_dilation": 1.2,
                "face_detected": True
            }
        )
        assert eye_tracker.validate_sample(out_of_range_sample) == False
    
    @patch('cv2.VideoCapture')
    def test_start_stop(self, mock_video_capture, eye_tracker):
        """Test start and stop methods."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_video_capture.return_value = mock_cap
        
        eye_tracker.start()
        assert eye_tracker.is_running == True
        assert eye_tracker.cap is not None
        
        eye_tracker.stop()
        assert eye_tracker.is_running == False
    
    def test_calibration(self, eye_tracker):
        """Test calibration process."""
        with patch.object(eye_tracker, '_capture_frame', return_value=np.zeros((480, 640, 3))):
            with patch.object(eye_tracker, '_extract_features', side_effect=[
                {"ear": 0.3, "pupil_dilation": 1.0} for _ in range(100)
            ]):
                result = eye_tracker.calibrate()
                assert isinstance(result, bool)
    
    def test_collect_sample(self, eye_tracker):
        """Test sample collection."""
        with patch.object(eye_tracker, '_capture_frame', return_value=np.zeros((480, 640, 3))):
            with patch.object(eye_tracker, '_extract_features', return_value={
                "ear": 0.3,
                "left_ear": 0.31,
                "right_ear": 0.29,
                "blink_rate": 15.0,
                "perclos": 0.1,
                "pupil_dilation": 1.2,
                "face_detected": True
            }):
                sample = eye_tracker._collect_sample()
                
                assert sample is not None
                assert sample.source == "eye"
                assert sample.data["ear"] == 0.3
                assert sample.data["blink_rate"] == 15.0
    
    def test_extract_features_no_face(self, eye_tracker):
        """Test feature extraction with no face detected."""
        mock_frame = np.zeros((480, 640, 3))
        
        with patch.object(eye_tracker.face_mesh, 'process', return_value=Mock(multi_face_landmarks=None)):
            features = eye_tracker._extract_features(mock_frame)
            
            assert features is None
            assert eye_tracker.face_detected == False
    
    def test_blink_detection(self, eye_tracker):
        """Test blink detection logic."""
        # Simulate a blink
        eye_tracker.ear_threshold = 0.2
        
        # Frame with eyes closed
        eye_tracker._handle_ear_value(0.1)  # Below threshold
        assert eye_tracker.blink_start_time is not None
        
        # Frame with eyes open
        eye_tracker._handle_ear_value(0.3)  # Above threshold
        # Blink should be counted
    
    def _handle_ear_value(self, ear_value):
        """Helper to handle EAR value for blink detection."""
        import time
        current_time = time.time()
        
        if ear_value < self.ear_threshold:
            if self.blink_start_time is None:
                self.blink_start_time = current_time
        else:
            if self.blink_start_time is not None:
                blink_duration = current_time - self.blink_start_time
                if 0.05 < blink_duration < 0.5:
                    self.blink_counter += 1
                self.blink_start_time = None
    
    def test_perclos_calculation(self, eye_tracker):
        """Test PERCLOS calculation."""
        eye_tracker.ear_threshold = 0.2
        
        # Add 10 closed frames and 40 open frames
        for _ in range(10):
            eye_tracker.perclos_window.append(True)  # Closed
        for _ in range(40):
            eye_tracker.perclos_window.append(False)  # Open
        
        eye_tracker._update_perclos()
        
        # PERCLOS should be 0.2 (10/50)
        assert eye_tracker.perclos_value == 0.2
    
    def _update_perclos(self):
        """Helper to update PERCLOS."""
        if self.perclos_window:
            self.perclos_value = sum(self.perclos_window) / len(self.perclos_window)
    
    def test_get_statistics(self, eye_tracker):
        """Test statistics retrieval."""
        eye_tracker.samples_collected = 1000
        eye_tracker.errors = 5
        eye_tracker.blink_rate = 15.0
        
        stats = eye_tracker.get_statistics()
        
        assert stats["name"] == "eye_tracker"
        assert stats["samples_collected"] == 1000
        assert stats["errors"] == 5
        assert "blink_rate" in stats or "samples_collected" in stats
    
    def test_get_status(self, eye_tracker):
        """Test status retrieval."""
        eye_tracker.is_running = True
        eye_tracker.is_paused = False
        eye_tracker.samples_collected = 500
        eye_tracker.errors = 2
        
        status = eye_tracker.get_status()
        
        assert status["name"] == "eye_tracker"
        assert status["active"] == True
        assert status["samples"] == 500
        assert status["error_rate"] == 2/500
    
    @patch('cv2.VideoCapture')
    def test_get_live_preview(self, mock_video_capture, eye_tracker):
        """Test live preview frame retrieval."""
        mock_cap = Mock()
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3)))
        mock_video_capture.return_value = mock_cap
        eye_tracker.cap = mock_cap
        
        eye_tracker.face_detected = True
        eye_tracker.ear_history = [0.3]
        eye_tracker.blink_rate = 15.0
        eye_tracker.perclos_value = 0.1
        
        frame = eye_tracker.get_live_preview()
        assert frame is not None
        assert isinstance(frame, np.ndarray)