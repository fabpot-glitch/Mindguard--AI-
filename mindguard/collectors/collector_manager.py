"""Manager class to coordinate all data collectors."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading
import time
import numpy as np

from collectors.base_collector import BaseCollector, DataPoint
from collectors.eye_tracker import EyeTracker
from collectors.keyboard_monitor import KeyboardMonitor
from collectors.screen_monitor import ScreenMonitor
from collectors.voice_analyzer import VoiceAnalyzer
from config.logging_config import LoggerMixin
from config import settings


class CollectorManager(LoggerMixin):
    """Manages all data collectors and synchronizes their output."""
    
    def __init__(self):
        """Initialize collector manager."""
        self.collectors: Dict[str, BaseCollector] = {}
        self.is_running = False
        self.manager_thread: Optional[threading.Thread] = None
        
        # Synchronization
        self.sync_window = 0.1  # 100ms synchronization window
        self.last_sync_time: Optional[datetime] = None
        
        # Data fusion buffer
        self.fusion_buffer: List[Dict] = []
        self.max_buffer_size = 1000
        
        self.logger.info("Initialized CollectorManager")
    
    def initialize_collectors(self) -> None:
        """Initialize all collectors with configuration."""
        try:
            self.collectors["eye"] = EyeTracker(
                camera_id=settings.collectors.camera_id,
                fps=settings.collectors.camera_fps
            )
            self.logger.info("Eye tracker initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize eye tracker: {e}")
        
        try:
            self.collectors["keyboard"] = KeyboardMonitor(
                sampling_rate=settings.collectors.keyboard_sampling_rate
            )
            self.logger.info("Keyboard monitor initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize keyboard monitor: {e}")
        
        try:
            self.collectors["screen"] = ScreenMonitor(
                capture_fps=settings.collectors.screen_capture_fps
            )
            self.logger.info("Screen monitor initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize screen monitor: {e}")
        
        if settings.features.enable_voice_analysis:
            try:
                self.collectors["voice"] = VoiceAnalyzer(
                    sample_rate=settings.collectors.audio_sample_rate
                )
                self.logger.info("Voice analyzer initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize voice analyzer: {e}")
    
    def start_all(self) -> bool:
        """Start all collectors."""
        if not self.collectors:
            self.initialize_collectors()
        
        for name, collector in self.collectors.items():
            try:
                collector.start()
                self.logger.info(f"Started {name} collector")
            except Exception as e:
                self.logger.error(f"Failed to start {name} collector: {e}")
                return False
        
        self.is_running = True
        self.manager_thread = threading.Thread(target=self._manager_loop)
        self.manager_thread.daemon = True
        self.manager_thread.start()
        
        self.logger.info("All collectors started")
        return True
    
    def stop_all(self) -> None:
        """Stop all collectors."""
        self.is_running = False
        
        if self.manager_thread:
            self.manager_thread.join(timeout=5.0)
        
        for name, collector in self.collectors.items():
            try:
                collector.stop()
                self.logger.info(f"Stopped {name} collector")
            except Exception as e:
                self.logger.error(f"Error stopping {name} collector: {e}")
        
        self.logger.info("All collectors stopped")
    
    def pause_all(self) -> None:
        """Pause all collectors."""
        for collector in self.collectors.values():
            collector.pause()
        self.logger.info("All collectors paused")
    
    def resume_all(self) -> None:
        """Resume all collectors."""
        for collector in self.collectors.values():
            collector.resume()
        self.logger.info("All collectors resumed")
    
    def _manager_loop(self) -> None:
        """Manager loop for synchronization."""
        while self.is_running:
            try:
                # Synchronize collectors
                synced_data = self._synchronize_collectors()
                
                if synced_data:
                    self._process_synced_data(synced_data)
                
                time.sleep(0.05)  # 20Hz manager loop
                
            except Exception as e:
                self.logger.error(f"Error in manager loop: {e}")
                time.sleep(1.0)
    
    def _synchronize_collectors(self) -> Optional[Dict[str, DataPoint]]:
        """Synchronize data from all collectors within time window."""
        current_time = datetime.now()
        
        # Get latest samples from all collectors
        latest_samples = {}
        for name, collector in self.collectors.items():
            sample = collector.get_latest_sample()
            if sample:
                latest_samples[name] = sample
        
        if not latest_samples:
            return None
        
        # Find reference time (latest of all samples)
        ref_time = max(s.timestamp for s in latest_samples.values())
        
        # Filter samples within sync window
        synced = {}
        for name, sample in latest_samples.items():
            time_diff = abs((ref_time - sample.timestamp).total_seconds())
            if time_diff <= self.sync_window:
                synced[name] = sample
        
        # Require at least 2 collectors for fusion
        if len(synced) >= 2:
            self.last_sync_time = current_time
            return synced
        
        return None
    
    def _process_synced_data(self, synced_data: Dict[str, DataPoint]) -> None:
        """Process synchronized data."""
        # Create fused data point
        fused = {
            "timestamp": self.last_sync_time or datetime.now(),
            "sources": list(synced_data.keys()),
            "data": {}
        }
        
        # Extract features from each collector
        for name, sample in synced_data.items():
            fused["data"][name] = sample.data
        
        # Add to fusion buffer
        self.fusion_buffer.append(fused)
        if len(self.fusion_buffer) > self.max_buffer_size:
            self.fusion_buffer = self.fusion_buffer[-self.max_buffer_size:]
    
    def get_fused_features(self, window_seconds: float = 1.0) -> Dict[str, np.ndarray]:
        """Get fused features for a time window."""
        if not self.fusion_buffer:
            return {}
        
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(seconds=window_seconds)
        
        # Get samples within window
        window_samples = [
            s for s in self.fusion_buffer
            if s["timestamp"] >= cutoff_time
        ]
        
        if not window_samples:
            return {}
        
        # Aggregate features by source
        features = {}
        sources = ["eye", "keyboard", "screen", "voice"]
        
        for source in sources:
            source_data = [
                s["data"].get(source, {})
                for s in window_samples
                if source in s["data"]
            ]
            
            if source_data:
                # Convert to numpy array
                features[source] = self._dicts_to_array(source_data)
        
        return features
    
    def _dicts_to_array(self, dicts: List[Dict]) -> np.ndarray:
        """Convert list of dictionaries to numpy array."""
        if not dicts:
            return np.array([])
        
        # Get all keys
        keys = set()
        for d in dicts:
            keys.update(d.keys())
        
        # Sort keys for consistent ordering
        sorted_keys = sorted(keys)
        
        # Create array
        array = []
        for d in dicts:
            row = [d.get(k, 0.0) for k in sorted_keys]
            array.append(row)
        
        return np.array(array)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all collectors."""
        return {
            name: collector.get_status()
            for name, collector in self.collectors.items()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all collectors."""
        return {
            name: collector.get_statistics()
            for name, collector in self.collectors.items()
        }