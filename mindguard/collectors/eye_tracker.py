"""Eye tracking collector using MediaPipe."""

import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import time

from collectors.base_collector import BaseCollector, DataPoint
from config.logging_config import collector_logger


class EyeTracker(BaseCollector):
    """Eye tracking collector using webcam."""
    
    def __init__(self, camera_id: int = 0, fps: int = 30):
        """
        Initialize eye tracker.
        
        Args:
            camera_id: Camera device ID
            fps: Frames per second
        """
        super().__init__("eye_tracker", sampling_rate=fps)
        self.camera_id = camera_id
        self.cap: Optional[cv2.VideoCapture] = None
        
        # MediaPipe initialization
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Eye landmark indices (MediaPipe)
        self.LEFT_EYE_INDICES = [33, 133, 157, 158, 159, 160, 161, 173]
        self.RIGHT_EYE_INDICES = [362, 263, 387, 386, 385, 384, 398, 466]
        
        # Blink detection
        self.blink_counter = 0
        self.blink_rate = 0.0
        self.ear_threshold = 0.2
        self.ear_history: List[float] = []
        self.ear_history_size = 30
        self.blink_start_time: Optional[float] = None
        
        # PERCLOS (percentage of eye closure)
        self.perclos_window: List[bool] = []
        self.perclos_window_size = 300  # 10 seconds at 30fps
        self.perclos_value = 0.0
        
        # Pupil detection (simplified)
        self.pupil_dilation = 1.0
        self.pupil_baseline: Optional[float] = None
        
        # Statistics
        self.frame_count = 0
        self.face_detected = False
        self.last_face_time: Optional[datetime] = None
        
        self.logger.info(f"EyeTracker initialized with camera {camera_id}")
    
    def calibrate(self) -> bool:
        """
        Calibrate eye tracker.
        
        Returns:
            True if calibration successful
        """
        self.logger.info("Starting eye tracker calibration")
        
        # Collect baseline data
        ear_values: List[float] = []
        pupil_values: List[float] = []
        
        self.logger.info("Look at the camera normally for 5 seconds...")
        
        for i in range(150):  # Collect 150 frames (5 seconds at 30fps)
            frame = self._capture_frame()
            if frame is not None:
                features = self._extract_features(frame)
                if features:
                    ear_values.append(features.get("ear", 0))
                    pupil_values.append(features.get("pupil_dilation", 1.0))
            time.sleep(0.03)
            
            if i % 30 == 0:
                self.logger.info(f"Calibration: {i//30 + 1}/5 seconds")
        
        if len(ear_values) > 50:
            # Set EAR threshold based on baseline (70% of normal)
            avg_ear = np.mean(ear_values)
            self.ear_threshold = avg_ear * 0.7
            
            # Set pupil baseline
            self.pupil_baseline = np.mean(pupil_values) if pupil_values else 1.0
            
            self.logger.info(f"Calibration complete - EAR threshold: {self.ear_threshold:.3f}")
            return True
        
        self.logger.warning("Calibration failed - insufficient data")
        return False
    
    def start(self) -> None:
        """Start eye tracking."""
        if self.is_running:
            return
        
        # Initialize camera
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {self.camera_id}")
        
        self.cap.set(cv2.CAP_PROP_FPS, self.sampling_rate)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        super().start()
    
    def stop(self) -> None:
        """Stop eye tracking."""
        super().stop()
        
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def _capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame from camera."""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None
        
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    def _collect_sample(self) -> Optional[DataPoint]:
        """Collect a single eye tracking sample."""
        frame = self._capture_frame()
        if frame is None:
            return None
        
        features = self._extract_features(frame)
        if not features:
            return None
        
        return DataPoint(
            timestamp=datetime.now(),
            source="eye",
            data=features,
            metadata={
                "frame": self.frame_count,
                "face_detected": self.face_detected
            }
        )
    
    def _extract_features(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """Extract eye features from frame."""
        self.frame_count += 1
        
        # Process frame with MediaPipe
        results = self.face_mesh.process(frame)
        
        if not results or not results.multi_face_landmarks:
            self.face_detected = False
            return None
        
        self.face_detected = True
        self.last_face_time = datetime.now()
        
        landmarks = results.multi_face_landmarks[0]
        h, w = frame.shape[:2]
        
        # Extract eye landmarks
        left_eye = np.array([[landmarks.landmark[i].x * w,
                              landmarks.landmark[i].y * h]
                             for i in self.LEFT_EYE_INDICES if i < len(landmarks.landmark)])
        
        right_eye = np.array([[landmarks.landmark[i].x * w,
                               landmarks.landmark[i].y * h]
                              for i in self.RIGHT_EYE_INDICES if i < len(landmarks.landmark)])
        
        # Calculate eye aspect ratio (EAR)
        left_ear = self._eye_aspect_ratio(left_eye)
        right_ear = self._eye_aspect_ratio(right_eye)
        ear = (left_ear + right_ear) / 2.0
        
        # Update EAR history
        self.ear_history.append(ear)
        if len(self.ear_history) > self.ear_history_size:
            self.ear_history.pop(0)
        
        # Detect blinks
        current_time = time.time()
        if ear < self.ear_threshold:
            if self.blink_start_time is None:
                self.blink_start_time = current_time
        else:
            if self.blink_start_time is not None:
                # Blink ended
                blink_duration = current_time - self.blink_start_time
                if 0.05 < blink_duration < 0.5:  # Valid blink duration
                    self.blink_counter += 1
                self.blink_start_time = None
        
        # Calculate blink rate (blinks per minute over last 60 seconds)
        if self.frame_count % (self.sampling_rate * 60) == 0:  # Every minute
            self.blink_rate = self.blink_counter
            self.blink_counter = 0
        
        # Update PERCLOS (percentage of time eyes are closed)
        is_closed = ear < self.ear_threshold
        self.perclos_window.append(is_closed)
        if len(self.perclos_window) > self.perclos_window_size:
            self.perclos_window.pop(0)
        self.perclos_value = sum(self.perclos_window) / len(self.perclos_window) if self.perclos_window else 0
        
        # Estimate pupil dilation (simplified - based on eye openness)
        if self.pupil_baseline:
            dilation = ear / self.pupil_baseline
            self.pupil_dilation = float(np.clip(dilation, 0.5, 2.0))
        
        return {
            "ear": float(ear),
            "left_ear": float(left_ear),
            "right_ear": float(right_ear),
            "blink_rate": self.blink_rate,
            "perclos": self.perclos_value,
            "pupil_dilation": self.pupil_dilation,
            "face_detected": True
        }
    
    def _eye_aspect_ratio(self, eye: np.ndarray) -> float:
        """Calculate eye aspect ratio."""
        if len(eye) < 6:
            return 0.0
        
        # Vertical distances
        v1 = np.linalg.norm(eye[1] - eye[5])
        v2 = np.linalg.norm(eye[2] - eye[4])
        
        # Horizontal distance
        h = np.linalg.norm(eye[0] - eye[3])
        
        # EAR formula
        ear = (v1 + v2) / (2.0 * h + 1e-6)
        
        return float(ear)
    
    def validate_sample(self, sample: DataPoint) -> bool:
        """Validate eye tracking sample."""
        required_fields = ["ear", "blink_rate", "perclos", "face_detected"]
        
        # Check required fields
        for field in required_fields:
            if field not in sample.data:
                return False
        
        # Check value ranges
        if sample.data["ear"] < 0 or sample.data["ear"] > 1:
            return False
        if sample.data["perclos"] < 0 or sample.data["perclos"] > 1:
            return False
        
        return True
    
    def get_live_preview(self) -> Optional[np.ndarray]:
        """Get live preview frame with annotations."""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None
        
        # Add annotations
        if self.face_detected:
            cv2.putText(frame, f"EAR: {self.ear_history[-1]:.2f}" if self.ear_history else "EAR: N/A",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Blink rate: {self.blink_rate:.1f} bpm",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"PERCLOS: {self.perclos_value:.2f}",
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "No face detected",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return frame