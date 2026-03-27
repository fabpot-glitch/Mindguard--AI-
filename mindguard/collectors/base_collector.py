"""Base collector abstract class for all data collectors."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import queue
import time
from dataclasses import dataclass, field

from config.logging_config import LoggerMixin


@dataclass
class DataPoint:
    """Single data point from a collector."""
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseCollector(ABC, LoggerMixin):
    """Abstract base class for all data collectors."""
    
    def __init__(
        self,
        name: str,
        sampling_rate: float = 30.0,
        buffer_size: int = 1000
    ):
        """
        Initialize base collector.
        
        Args:
            name: Collector name
            sampling_rate: Sampling rate in Hz
            buffer_size: Maximum buffer size
        """
        self.name = name
        self.sampling_rate = sampling_rate
        self.sampling_interval = 1.0 / sampling_rate
        self.buffer_size = buffer_size
        
        # Data buffer
        self.buffer = queue.Queue(maxsize=buffer_size)
        self.data_history: List[DataPoint] = []
        
        # Control flags
        self.is_running = False
        self.is_paused = False
        self.thread: Optional[threading.Thread] = None
        
        # Statistics
        self.samples_collected = 0
        self.errors = 0
        self.last_sample_time: Optional[datetime] = None
        self.start_time: Optional[datetime] = None
        
        self.logger.info(f"Initialized {name} collector at {sampling_rate}Hz")
    
    @abstractmethod
    def _collect_sample(self) -> Optional[DataPoint]:
        """Collect a single data sample. Must be implemented by subclass."""
        pass
    
    @abstractmethod
    def calibrate(self) -> bool:
        """Calibrate the collector. Returns True if calibration successful."""
        pass
    
    @abstractmethod
    def validate_sample(self, sample: DataPoint) -> bool:
        """Validate a collected sample. Returns True if sample is valid."""
        pass
    
    def start(self) -> None:
        """Start data collection."""
        if self.is_running:
            self.logger.warning(f"{self.name} collector already running")
            return
        
        self.is_running = True
        self.is_paused = False
        self.start_time = datetime.now()
        self.thread = threading.Thread(target=self._collection_loop, name=f"{self.name}_collector")
        self.thread.daemon = True
        self.thread.start()
        self.logger.info(f"Started {self.name} collector")
    
    def stop(self) -> None:
        """Stop data collection."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        self.logger.info(f"Stopped {self.name} collector, collected {self.samples_collected} samples")
    
    def pause(self) -> None:
        """Pause data collection."""
        self.is_paused = True
        self.logger.info(f"Paused {self.name} collector")
    
    def resume(self) -> None:
        """Resume data collection."""
        self.is_paused = False
        self.logger.info(f"Resumed {self.name} collector")
    
    def _collection_loop(self) -> None:
        """Main collection loop."""
        while self.is_running:
            try:
                if not self.is_paused:
                    loop_start = time.time()
                    
                    # Collect sample
                    sample = self._collect_sample()
                    
                    if sample and self.validate_sample(sample):
                        self._process_sample(sample)
                    
                    # Maintain sampling rate
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, self.sampling_interval - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                self.errors += 1
                self.logger.error(f"Error in {self.name} collection loop: {e}")
                time.sleep(1.0)
    
    def _process_sample(self, sample: DataPoint) -> None:
        """Process a collected sample."""
        self.samples_collected += 1
        self.last_sample_time = sample.timestamp
        
        # Add to buffer (non-blocking)
        try:
            self.buffer.put_nowait(sample)
        except queue.Full:
            # Remove oldest and add new
            try:
                self.buffer.get_nowait()
                self.buffer.put_nowait(sample)
            except queue.Empty:
                pass
        
        # Add to history (keep last 100)
        self.data_history.append(sample)
        if len(self.data_history) > 100:
            self.data_history = self.data_history[-100:]
    
    def get_latest_sample(self) -> Optional[DataPoint]:
        """Get the latest sample without removing it."""
        try:
            # Peek at the last item in queue
            samples: List[DataPoint] = []
            while not self.buffer.empty():
                samples.append(self.buffer.get_nowait())
            
            # Put them back
            for sample in samples:
                self.buffer.put_nowait(sample)
            
            return samples[-1] if samples else None
        except queue.Empty:
            return None
    
    def get_samples(self, count: int = 1) -> List[DataPoint]:
        """Get specified number of samples from buffer."""
        samples: List[DataPoint] = []
        for _ in range(min(count, self.buffer.qsize())):
            try:
                samples.append(self.buffer.get_nowait())
            except queue.Empty:
                break
        return samples
    
    def clear_buffer(self) -> None:
        """Clear the data buffer."""
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break
        self.logger.info(f"Cleared {self.name} buffer")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collector statistics."""
        runtime = 0
        if self.start_time:
            runtime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "name": self.name,
            "samples_collected": self.samples_collected,
            "errors": self.errors,
            "buffer_size": self.buffer.qsize(),
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "sampling_rate": self.sampling_rate,
            "runtime_seconds": runtime,
            "samples_per_second": self.samples_collected / max(runtime, 1)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get collector status for dashboard."""
        latest = self.get_latest_sample()
        return {
            "name": self.name,
            "active": self.is_running and not self.is_paused,
            "samples": self.samples_collected,
            "last_sample": latest.timestamp.isoformat() if latest else None,
            "error_rate": self.errors / max(self.samples_collected, 1)
        }