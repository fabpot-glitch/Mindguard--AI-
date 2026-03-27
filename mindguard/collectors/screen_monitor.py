"""Screen activity monitoring collector."""

import time
import psutil
import platform
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import deque
import numpy as np
import threading

from collectors.base_collector import BaseCollector, DataPoint
from config.logging_config import collector_logger


class ScreenMonitor(BaseCollector):
    """Monitor screen activity, app switching, and user behavior."""
    
    def __init__(self, capture_fps: float = 5.0):
        """
        Initialize screen monitor.
        
        Args:
            capture_fps: Screen capture frequency
        """
        super().__init__("screen_monitor", sampling_rate=capture_fps)
        
        # Activity tracking
        self.current_app: Optional[str] = None
        self.app_switch_count = 0
        self.app_history: deque = deque(maxlen=100)
        
        # Scroll and mouse activity (simplified)
        self.scroll_count = 0
        self.scroll_history: deque = deque(maxlen=100)
        self.mouse_movements: List[tuple] = []
        
        # Idle detection
        self.idle_time = 0.0
        self.last_activity_time = time.time()
        
        # Statistics
        self.idle_threshold = 30.0  # seconds
        self.focus_score = 1.0
        self.context_switches = 0
        
        # Platform-specific
        self.os_name = platform.system()
        self.start_time: Optional[float] = None
        
        self.logger.info(f"ScreenMonitor initialized for {self.os_name}")
    
    def calibrate(self) -> bool:
        """
        Calibrate screen monitor.
        
        Returns:
            True if calibration successful
        """
        self.logger.info("Starting screen monitor calibration")
        
        # Collect baseline activity patterns
        initial_switches = self.app_switch_count
        initial_scrolls = self.scroll_count
        
        self.logger.info("Monitoring activity for 30 seconds...")
        time.sleep(30)
        
        # Calculate baseline rates
        switch_rate = (self.app_switch_count - initial_switches) / 30.0
        scroll_rate = (self.scroll_count - initial_scrolls) / 30.0
        
        self.logger.info(f"Calibration complete - switch rate: {switch_rate:.2f}/s, scroll rate: {scroll_rate:.2f}/s")
        return True
    
    def start(self) -> None:
        """Start screen monitoring."""
        super().start()
        self.start_time = time.time()
    
    def _get_active_window(self) -> Optional[str]:
        """Get active window title (platform-specific)."""
        try:
            if self.os_name == "Windows":
                import win32gui
                window = win32gui.GetForegroundWindow()
                return win32gui.GetWindowText(window) or "Unknown"
            elif self.os_name == "Darwin":  # macOS
                from AppKit import NSWorkspace
                app = NSWorkspace.sharedWorkspace().activeApplication()
                return app['NSApplicationName'] if app else "Unknown"
            elif self.os_name == "Linux":
                # Simplified for Linux
                return "Linux App"
        except Exception as e:
            self.logger.debug(f"Could not get active window: {e}")
        
        return "Unknown"
    
    def _get_idle_time(self) -> float:
        """Get system idle time."""
        try:
            if self.os_name == "Windows":
                import ctypes
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
                
                lii = LASTINPUTINFO()
                lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return millis / 1000.0
            else:
                # Fallback for non-Windows
                return time.time() - self.last_activity_time
        except Exception as e:
            self.logger.debug(f"Could not get idle time: {e}")
            return 0.0
    
    def _collect_sample(self) -> Optional[DataPoint]:
        """Collect screen monitoring sample."""
        # Get current active window
        new_app = self._get_active_window()
        
        # Check for app switch
        if new_app and new_app != self.current_app:
            if self.current_app is not None:  # Skip first detection
                self.app_switch_count += 1
                self.context_switches += 1
                self.app_history.append({
                    "from": self.current_app,
                    "to": new_app,
                    "time": datetime.now().isoformat()
                })
            self.current_app = new_app
        
        # Get idle time
        self.idle_time = self._get_idle_time()
        
        # Update last activity if not idle
        if self.idle_time < 1.0:
            self.last_activity_time = time.time()
        
        # Calculate focus score (0-1)
        if self.idle_time > self.idle_threshold:
            focus_score = 0.0
        else:
            # Higher score for: low app switching, active engagement
            switch_penalty = min(self.context_switches / 20.0, 0.5)  # Max 50% penalty
            idle_factor = max(0, 1.0 - (self.idle_time / self.idle_threshold))
            focus_score = idle_factor * (1.0 - switch_penalty)
        
        self.focus_score = max(0, min(1, focus_score))
        
        # Calculate scroll activity (per minute)
        runtime = max(1, (time.time() - (self.start_time or time.time())) / 60)
        scroll_activity = self.scroll_count / runtime
        
        return DataPoint(
            timestamp=datetime.now(),
            source="screen",
            data={
                "current_app": self.current_app or "Unknown",
                "app_switch_rate": self.app_switch_count / max(1, runtime),
                "idle_time": float(self.idle_time),
                "focus_score": float(self.focus_score),
                "scroll_activity": float(scroll_activity),
                "context_switches": self.context_switches
            },
            metadata={
                "os": self.os_name
            }
        )
    
    def validate_sample(self, sample: DataPoint) -> bool:
        """Validate screen monitoring sample."""
        required_fields = ["idle_time", "focus_score", "app_switch_rate"]
        
        # Check required fields
        for field in required_fields:
            if field not in sample.data:
                return False
        
        # Check value ranges
        if sample.data["focus_score"] < 0 or sample.data["focus_score"] > 1:
            return False
        if sample.data["idle_time"] < 0:
            return False
        
        return True
    
    def record_scroll(self, direction: str, amount: int) -> None:
        """Record scroll event."""
        self.scroll_count += 1
        self.scroll_history.append({
            "direction": direction,
            "amount": amount,
            "time": datetime.now().isoformat()
        })
    
    def record_mouse_movement(self, x: int, y: int) -> None:
        """Record mouse movement."""
        self.mouse_movements.append((x, y, time.time()))
        if len(self.mouse_movements) > 1000:
            self.mouse_movements = self.mouse_movements[-1000:]
    
    def get_activity_summary(self) -> Dict[str, Any]:
        """Get summary of screen activity."""
        runtime = max(1, (time.time() - (self.start_time or time.time())) / 60)
        return {
            "current_app": self.current_app,
            "total_app_switches": self.app_switch_count,
            "total_scrolls": self.scroll_count,
            "current_idle_time": self.idle_time,
            "focus_score": self.focus_score,
            "switches_per_minute": self.app_switch_count / runtime,
            "scrolls_per_minute": self.scroll_count / runtime
        }