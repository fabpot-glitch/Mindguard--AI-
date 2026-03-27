"""Core cognitive engine for real-time state estimation."""

import asyncio
import time
import numpy as np
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from collections import deque
import threading

from models.fusion_model import CognitiveFusionModel, ModelOutput
from models.inference import InferenceEngine
from collectors.collector_manager import CollectorManager
from engine.feature_normalizer import FeatureNormalizer
from engine.state_tracker import StateTracker, StatePoint
from engine.calibration import Calibrator
from config.logging_config import get_logger, engine_logger
from config import settings, thresholds

logger = get_logger(__name__)


class CognitiveEngine:
    """Real-time cognitive state estimation engine."""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        inference_frequency: float = 5.0,  # Hz
        use_onnx: bool = False,
        onnx_path: Optional[str] = None,
        device: str = 'cpu'
    ):
        """
        Initialize cognitive engine.
        
        Args:
            model_path: Path to model weights
            inference_frequency: Inference frequency in Hz
            use_onnx: Whether to use ONNX runtime
            onnx_path: Path to ONNX model
            device: Device to run inference on
        """
        self.inference_frequency = inference_frequency
        self.inference_interval = 1.0 / inference_frequency
        self.device = device
        
        # Initialize components
        self.collector_manager = CollectorManager()
        self.normalizer = FeatureNormalizer()
        self.state_tracker = StateTracker()
        self.calibrator = Calibrator()
        
        # Initialize model
        if use_onnx and onnx_path:
            self.inference_engine = InferenceEngine(
                onnx_path=onnx_path,
                use_onnx=True,
                device=device
            )
        else:
            self.inference_engine = InferenceEngine(
                model_path=model_path,
                use_onnx=False,
                device=device
            )
        
        # State
        self.is_running = False
        self.is_paused = False
        self.engine_thread: Optional[threading.Thread] = None
        
        # Current state
        self.current_state: Optional[ModelOutput] = None
        
        # Performance metrics
        self.inference_times = deque(maxlen=100)
        self.total_inferences = 0
        self.errors = 0
        
        # Callbacks
        self.state_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        logger.info(f"CognitiveEngine initialized at {inference_frequency}Hz on {device}")
    
    def start(self) -> bool:
        """Start the cognitive engine."""
        if self.is_running:
            logger.warning("Engine already running")
            return False
        
        # Start collectors
        if not self.collector_manager.start_all():
            logger.error("Failed to start collectors")
            return False
        
        self.is_running = True
        self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
        self.engine_thread.start()
        
        logger.info("Cognitive engine started")
        return True
    
    def stop(self) -> None:
        """Stop the cognitive engine."""
        self.is_running = False
        
        if self.engine_thread:
            self.engine_thread.join(timeout=5.0)
        
        self.collector_manager.stop_all()
        logger.info("Cognitive engine stopped")
    
    def pause(self) -> None:
        """Pause inference."""
        self.is_paused = True
        logger.info("Engine paused")
    
    def resume(self) -> None:
        """Resume inference."""
        self.is_paused = False
        logger.info("Engine resumed")
    
    def _engine_loop(self) -> None:
        """Main engine loop."""
        logger.info("Engine loop started")
        
        while self.is_running:
            try:
                if not self.is_paused:
                    loop_start = time.time()
                    
                    # Run inference
                    state = self._run_inference()
                    
                    if state:
                        self.current_state = state
                        
                        # Create state point
                        state_point = StatePoint(
                            timestamp=datetime.now(),
                            fatigue=state.fatigue,
                            stress=state.stress,
                            attention=state.attention,
                            cognitive_load=state.cognitive_load,
                            confidence=state.confidence
                        )
                        
                        # Update tracker
                        self.state_tracker.update(state_point)
                        
                        # Trigger callbacks
                        self._trigger_state_callbacks(state_point.to_dict())
                        
                        # Check for alerts
                        self._check_alerts(state_point)
                    
                    # Maintain frequency
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, self.inference_interval - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                self.errors += 1
                logger.error(f"Error in engine loop: {e}")
                time.sleep(1.0)
        
        logger.info("Engine loop stopped")
    
    def _run_inference(self) -> Optional[ModelOutput]:
        """Run single inference."""
        inference_start = time.time()
        
        try:
            # Get fused features from collectors
            features = self.collector_manager.get_fused_features(window_seconds=1.0)
            
            if not features:
                logger.debug("No features available for inference")
                return None
            
            # Normalize features
            normalized = {}
            for modality, feat in features.items():
                self.normalizer.update(modality, feat)
                normalized[modality] = self.normalizer.normalize(modality, feat)
            
            # Run model inference
            output = self.inference_engine.predict(normalized)
            
            # Record inference time
            inference_time = time.time() - inference_start
            self.inference_times.append(inference_time)
            self.total_inferences += 1
            
            return output
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return None
    
    def _check_alerts(self, state_point: StatePoint):
        """Check if alerts need to be triggered."""
        alerts = []
        
        # Check thresholds
        if state_point.fatigue >= thresholds.fatigue_critical:
            alerts.append({
                'type': 'critical_fatigue',
                'level': 'critical',
                'value': state_point.fatigue,
                'threshold': thresholds.fatigue_critical,
                'timestamp': datetime.now().isoformat()
            })
        elif state_point.fatigue >= thresholds.fatigue_high:
            alerts.append({
                'type': 'high_fatigue',
                'level': 'warning',
                'value': state_point.fatigue,
                'threshold': thresholds.fatigue_high,
                'timestamp': datetime.now().isoformat()
            })
        
        if state_point.stress >= thresholds.stress_high:
            alerts.append({
                'type': 'high_stress',
                'level': 'warning',
                'value': state_point.stress,
                'threshold': thresholds.stress_high,
                'timestamp': datetime.now().isoformat()
            })
        
        if state_point.attention <= thresholds.attention_low:
            alerts.append({
                'type': 'low_attention',
                'level': 'warning',
                'value': state_point.attention,
                'threshold': thresholds.attention_low,
                'timestamp': datetime.now().isoformat()
            })
        
        # Check deviation from baseline
        deviation = self.state_tracker.get_deviation_from_baseline()
        if deviation and deviation.get('fatigue', 0) > 0.2:
            alerts.append({
                'type': 'fatigue_anomaly',
                'level': 'info',
                'value': deviation['fatigue'],
                'threshold': 0.2,
                'timestamp': datetime.now().isoformat()
            })
        
        if alerts:
            self._trigger_alert_callbacks(alerts)
    
    def register_state_callback(self, callback: Callable):
        """Register callback for state updates."""
        self.state_callbacks.append(callback)
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts."""
        self.alert_callbacks.append(callback)
    
    def _trigger_state_callbacks(self, state: Dict[str, Any]):
        """Trigger all state callbacks."""
        for callback in self.state_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"State callback failed: {e}")
    
    def _trigger_alert_callbacks(self, alerts: List[Dict[str, Any]]):
        """Trigger all alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                callback(alerts)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Get current cognitive state."""
        return self.state_tracker.get_current_state()
    
    def get_state_history(self, **kwargs) -> List[Dict[str, Any]]:
        """Get state history."""
        return self.state_tracker.get_history(**kwargs)
    
    def get_trends(self) -> Dict[str, float]:
        """Get current trends."""
        return self.state_tracker.get_trends()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'total_inferences': self.total_inferences,
            'avg_inference_time': np.mean(self.inference_times) if self.inference_times else 0,
            'errors': self.errors,
            'collectors': self.collector_manager.get_statistics(),
            'state': self.state_tracker.get_statistics(),
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'inference_frequency': self.inference_frequency
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'running': self.is_running and not self.is_paused,
            'paused': self.is_paused,
            'inferences': self.total_inferences,
            'collectors': self.collector_manager.get_status(),
            'last_state': self.get_current_state(),
            'trends': self.get_trends()
        }
    
    def reset_calibration(self):
        """Reset calibration data."""
        self.normalizer.reset()
        self.state_tracker.reset()
        logger.info("Calibration reset")