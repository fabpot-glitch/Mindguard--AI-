"""Keyboard monitoring collector (privacy-safe - only timing, no content)."""

import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import deque
import numpy as np
from pynput import keyboard

from collectors.base_collector import BaseCollector, DataPoint
from config.logging_config import collector_logger


class KeyboardMonitor(BaseCollector):
    """Privacy-safe keyboard monitor - only records timing, not content."""
    
    def __init__(self, sampling_rate: float = 100.0):
        """
        Initialize keyboard monitor.
        
        Args:
            sampling_rate: Sampling rate in Hz
        """
        super().__init__("keyboard_monitor", sampling_rate=sampling_rate)
        
        # Timing data (privacy-safe - no key content)
        self.key_times: List[float] = []
        self.key_intervals: deque = deque(maxlen=100)
        self.press_times: Dict[int, float] = {}  # key hash -> press time
        self.hold_times: List[float] = []  # key hold durations
        
        # Statistics
        self.key_count = 0
        self.error_count = 0
        self.typing_speed = 0.0  # keys per minute
        self.hesitation_count = 0
        self.rhythm_variance = 0.0
        self.avg_hold_time = 0.0
        
        # Thresholds
        self.hesitation_threshold = 0.5  # 500ms
        self.error_threshold = 0.3  # 30% error rate
        
        # Control
        self.listener: Optional[keyboard.Listener] = None
        self.statistics_lock = threading.Lock()
        
        self.logger.info("KeyboardMonitor initialized (privacy-safe mode)")
    
    def calibrate(self) -> bool:
        """
        Calibrate keyboard monitor.
        
        Returns:
            True if calibration successful
        """
        self.logger.info("Starting keyboard monitor calibration")
        
        # Collect baseline typing pattern
        self.logger.info("Please type normally for 10 seconds...")
        
        initial_count = self.key_count
        calibration_time = 10  # seconds
        
        # Wait for calibration period
        time.sleep(calibration_time)
        
        with self.statistics_lock:
            if (self.key_count - initial_count) > 10 and len(self.key_intervals) > 5:
                # Calculate baseline rhythm
                intervals = list(self.key_intervals)
                avg_interval = np.mean(intervals)
                self.hesitation_threshold = avg_interval * 2.0
                
                self.logger.info(f"Calibration complete - avg interval: {avg_interval*1000:.1f}ms")
                return True
        
        self.logger.warning("Calibration failed - insufficient data")
        return False
    
    def start(self) -> None:
        """Start keyboard monitoring."""
        if self.is_running:
            return
        
        # Start keyboard listener
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        
        super().start()
        
        self.logger.info("Keyboard monitoring started")
    
    def stop(self) -> None:
        """Stop keyboard monitoring."""
        super().stop()
        
        if self.listener:
            self.listener.stop()
            self.listener = None
    
    def _on_press(self, key: keyboard.Key) -> None:
        """Handle key press event."""
        current_time = time.time()
        
        # Store press time (use hash for privacy)
        key_id = hash(key)
        self.press_times[key_id] = current_time
        
        # Calculate interval from last key
        if self.key_times:
            interval = current_time - self.key_times[-1]
            if interval < 2.0:  # Ignore long pauses
                self.key_intervals.append(interval)
                
                # Detect hesitation
                if interval > self.hesitation_threshold:
                    self.hesitation_count += 1
        
        self.key_times.append(current_time)
        self.key_count += 1
        
        # Keep only last 1000 timings
        if len(self.key_times) > 1000:
            self.key_times = self.key_times[-1000:]
    
    def _on_release(self, key: keyboard.Key) -> None:
        """Handle key release event."""
        key_id = hash(key)
        
        if key_id in self.press_times:
            hold_time = time.time() - self.press_times[key_id]
            if 0.01 < hold_time < 2.0:  # Valid hold time
                self.hold_times.append(hold_time)
                if len(self.hold_times) > 100:
                    self.hold_times = self.hold_times[-100:]
            
            del self.press_times[key_id]
    
    def _collect_sample(self) -> Optional[DataPoint]:
        """Collect a keyboard monitoring sample."""
        with self.statistics_lock:
            # Calculate typing speed (keys per minute over last 10 seconds)
            if len(self.key_times) >= 2:
                recent_times = self.key_times[-20:]  # Last ~20 keys
                if len(recent_times) >= 2:
                    time_span = recent_times[-1] - recent_times[0]
                    if time_span > 0:
                        keys_per_second = len(recent_times) / time_span
                        self.typing_speed = keys_per_second * 60
                    else:
                        self.typing_speed = 0
            else:
                self.typing_speed = 0
            
            # Calculate rhythm variance
            if len(self.key_intervals) > 5:
                intervals = list(self.key_intervals)
                self.rhythm_variance = float(np.var(intervals))
            else:
                self.rhythm_variance = 0
            
            # Calculate average hold time
            if self.hold_times:
                self.avg_hold_time = float(np.mean(self.hold_times[-50:]))
            
            # Calculate error rate (based on hesitation)
            if self.key_count > 0:
                error_rate = self.hesitation_count / max(self.key_count, 1)
            else:
                error_rate = 0
            
            # Determine if typing is active
            is_typing = len(self.key_times) > 0 and (time.time() - self.key_times[-1]) < 2.0
        
        return DataPoint(
            timestamp=datetime.now(),
            source="keyboard",
            data={
                "typing_speed": float(self.typing_speed),
                "rhythm_variance": float(self.rhythm_variance),
                "hesitation_rate": float(self.hesitation_count / max(self.key_count, 1)),
                "avg_hold_time": float(self.avg_hold_time),
                "key_count": self.key_count,
                "is_typing": is_typing
            },
            metadata={
                "sample_interval": self.sampling_interval
            }
        )
    
    def validate_sample(self, sample: DataPoint) -> bool:
        """Validate keyboard monitoring sample."""
        required_fields = ["typing_speed", "rhythm_variance", "hesitation_rate", "is_typing"]
        
        # Check required fields
        for field in required_fields:
            if field not in sample.data:
                return False
        
        # Check value ranges
        if sample.data["typing_speed"] < 0 or sample.data["typing_speed"] > 600:
            return False
        if sample.data["hesitation_rate"] < 0 or sample.data["hesitation_rate"] > 1:
            return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get keyboard statistics."""
        stats = super().get_statistics()
        with self.statistics_lock:
            stats.update({
                "total_keys": self.key_count,
                "hesitations": self.hesitation_count,
                "avg_interval": float(np.mean(list(self.key_intervals))) if self.key_intervals else 0,
                "avg_hold_time": float(self.avg_hold_time)
            })
        return stats