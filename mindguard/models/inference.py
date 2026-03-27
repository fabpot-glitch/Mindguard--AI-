"""Inference engine for real-time predictions."""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import time
from collections import deque
import json

from models.fusion_model import CognitiveFusionModel, ModelOutput
from config.logging_config import model_logger


class InferenceEngine:
    """Real-time inference engine for cognitive state prediction."""
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        device: str = 'cpu',
        use_onnx: bool = False,
        onnx_path: Optional[Path] = None,
        window_size: int = 30,  # Number of frames to keep for context
        prediction_horizon: int = 10,  # Number of steps to predict ahead
        confidence_threshold: float = 0.7
    ):
        """
        Initialize inference engine.
        
        Args:
            model_path: Path to PyTorch model checkpoint
            device: Device to run inference on
            use_onnx: Whether to use ONNX runtime
            onnx_path: Path to ONNX model
            window_size: Size of sliding window for temporal context
            prediction_horizon: Number of steps to predict ahead
            confidence_threshold: Minimum confidence for predictions
        """
        self.device = device
        self.window_size = window_size
        self.prediction_horizon = prediction_horizon
        self.confidence_threshold = confidence_threshold
        self.use_onnx = use_onnx
        
        # Initialize model
        if use_onnx and onnx_path:
            self._load_onnx_model(onnx_path)
        elif model_path:
            self._load_pytorch_model(model_path)
        else:
            raise ValueError("Either model_path or onnx_path must be provided")
        
        # Buffers for temporal context
        self.feature_buffer: Dict[str, deque] = {}
        self.prediction_buffer = deque(maxlen=100)
        self.timestamps = deque(maxlen=1000)
        
        # Performance metrics
        self.inference_times = deque(maxlen=100)
        self.total_inferences = 0
        
        model_logger.info(f"Inference engine initialized on {device}")
    
    def _load_pytorch_model(self, model_path: Path):
        """Load PyTorch model."""
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # Create model
        self.model = CognitiveFusionModel(
            modality_dims=checkpoint.get('modality_dims'),
            embed_dim=checkpoint.get('config', {}).get('embed_dim', 64),
            hidden_dim=checkpoint.get('config', {}).get('hidden_dim', 128),
            num_heads=checkpoint.get('config', {}).get('num_heads', 4),
            num_encoder_layers=checkpoint.get('config', {}).get('num_encoder_layers', 2),
            num_attention_layers=checkpoint.get('config', {}).get('num_attention_layers', 2),
            dropout=checkpoint.get('config', {}).get('dropout', 0.1),
            use_attention=checkpoint.get('config', {}).get('use_attention', True)
        )
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()
        
        model_logger.info(f"PyTorch model loaded from {model_path}")
    
    def _load_onnx_model(self, onnx_path: Path):
        """Load ONNX model."""
        try:
            import onnxruntime as ort
            
            # Set up ONNX runtime session
            providers = ['CPUExecutionProvider']
            if self.device == 'cuda':
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
            self.ort_session = ort.InferenceSession(
                str(onnx_path),
                providers=providers
            )
            
            # Get input/output details
            self.ort_inputs = {
                inp.name: inp for inp in self.ort_session.get_inputs()
            }
            self.ort_outputs = {
                out.name: out for out in self.ort_session.get_outputs()
            }
            
            model_logger.info(f"ONNX model loaded from {onnx_path}")
            
        except ImportError:
            model_logger.error("ONNX Runtime not installed. Please install onnxruntime.")
            raise
    
    def initialize_buffer(self, modality_names: List[str]):
        """Initialize feature buffers for temporal context."""
        for name in modality_names:
            self.feature_buffer[name] = deque(maxlen=self.window_size)
    
    def update_buffer(self, features: Dict[str, np.ndarray]):
        """Update feature buffers with new data."""
        for name, feat in features.items():
            if name in self.feature_buffer:
                self.feature_buffer[name].append(feat)
    
    def get_window_features(self) -> Dict[str, np.ndarray]:
        """Get sliding window features for prediction."""
        window_features = {}
        
        for name, buffer in self.feature_buffer.items():
            if len(buffer) >= self.window_size:
                # Stack buffer into window
                window = np.stack(list(buffer)[-self.window_size:])
                window_features[name] = window
            else:
                # Not enough data yet
                window_features[name] = None
        
        return window_features
    
    def predict(
        self,
        features: Dict[str, np.ndarray],
        return_details: bool = False
    ) -> ModelOutput:
        """
        Make prediction from features.
        
        Args:
            features: Dictionary of feature arrays
            return_details: Whether to return detailed outputs
            
        Returns:
            ModelOutput with predictions
        """
        start_time = time.time()
        
        # Update buffer
        self.update_buffer(features)
        
        # Get window features
        window_features = self.get_window_features()
        
        # Check if we have enough data
        if any(v is None for v in window_features.values()):
            # Return default prediction with low confidence
            return ModelOutput(
                fatigue=0.5,
                stress=0.5,
                attention=0.5,
                cognitive_load=0.5,
                confidence=0.0
            )
        
        # Run inference
        if self.use_onnx:
            output = self._predict_onnx(window_features)
        else:
            output = self._predict_pytorch(window_features, return_details)
        
        # Update performance metrics
        inference_time = time.time() - start_time
        self.inference_times.append(inference_time)
        self.total_inferences += 1
        self.prediction_buffer.append(output)
        self.timestamps.append(time.time())
        
        return output
    
    def _predict_pytorch(
        self,
        features: Dict[str, np.ndarray],
        return_details: bool = False
    ) -> ModelOutput:
        """Run PyTorch inference."""
        with torch.no_grad():
            # Convert to tensors
            inputs = {}
            for name, feat in features.items():
                if feat is not None:
                    # Add batch dimension
                    if len(feat.shape) == 2:
                        feat = feat[np.newaxis, ...]
                    inputs[name] = torch.from_numpy(feat).float().to(self.device)
            
            # Forward pass
            outputs = self.model(inputs, return_embeddings=return_details)
        
        # Extract predictions
        fatigue = float(outputs['fatigue'].cpu().numpy()[0])
        stress = float(outputs['stress'].cpu().numpy()[0])
        attention = float(outputs['attention'].cpu().numpy()[0])
        cognitive_load = float(outputs['cognitive_load'].cpu().numpy()[0])
        confidence = float(outputs['confidence'].cpu().numpy()[0])
        
        # Get embeddings if requested
        embeddings = None
        if return_details and 'embeddings' in outputs:
            embeddings = {
                name: emb for name, emb in outputs['embeddings'].items()
            }
        
        return ModelOutput(
            fatigue=fatigue,
            stress=stress,
            attention=attention,
            cognitive_load=cognitive_load,
            confidence=confidence,
            features=features,
            embeddings=embeddings
        )
    
    def _predict_onnx(self, features: Dict[str, np.ndarray]) -> ModelOutput:
        """Run ONNX inference."""
        # Prepare inputs
        ort_inputs = {}
        for name, feat in features.items():
            if feat is not None and name in self.ort_inputs:
                # Ensure correct shape and type
                if len(feat.shape) == 2:
                    feat = feat[np.newaxis, ...]
                ort_inputs[self.ort_inputs[name].name] = feat.astype(np.float32)
        
        # Run inference
        ort_outputs = self.ort_session.run(None, ort_inputs)
        
        # Parse outputs
        output_dict = {}
        for i, out_name in enumerate(self.ort_outputs):
            output_dict[out_name] = ort_outputs[i]
        
        # Extract predictions
        fatigue = float(output_dict.get('fatigue', [[0.5]])[0][0])
        stress = float(output_dict.get('stress', [[0.5]])[0][0])
        attention = float(output_dict.get('attention', [[0.5]])[0][0])
        cognitive_load = float(output_dict.get('cognitive_load', [[0.5]])[0][0])
        confidence = float(output_dict.get('confidence', [[0.5]])[0][0])
        
        return ModelOutput(
            fatigue=fatigue,
            stress=stress,
            attention=attention,
            cognitive_load=cognitive_load,
            confidence=confidence,
            features=features
        )
    
    def predict_batch(
        self,
        features_list: List[Dict[str, np.ndarray]]
    ) -> List[ModelOutput]:
        """
        Make predictions for a batch of samples.
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of ModelOutput predictions
        """
        if self.use_onnx:
            # ONNX doesn't support variable batch size well, use loop
            return [self.predict(f) for f in features_list]
        
        # PyTorch batch processing
        with torch.no_grad():
            # Prepare batch
            batch_inputs = {}
            for name in features_list[0].keys():
                batch_feats = []
                for f in features_list:
                    if name in f and f[name] is not None:
                        feat = f[name]
                        if len(feat.shape) == 1:
                            feat = feat[np.newaxis, np.newaxis, ...]
                        elif len(feat.shape) == 2:
                            feat = feat[np.newaxis, ...]
                        batch_feats.append(feat)
                
                if batch_feats:
                    batch_inputs[name] = torch.from_numpy(
                        np.concatenate(batch_feats, axis=0)
                    ).float().to(self.device)
            
            # Forward pass
            outputs = self.model(batch_inputs)
        
        # Convert outputs
        results = []
        batch_size = len(features_list)
        for i in range(batch_size):
            results.append(ModelOutput(
                fatigue=float(outputs['fatigue'][i].cpu().numpy()),
                stress=float(outputs['stress'][i].cpu().numpy()),
                attention=float(outputs['attention'][i].cpu().numpy()),
                cognitive_load=float(outputs['cognitive_load'][i].cpu().numpy()),
                confidence=float(outputs['confidence'][i].cpu().numpy()),
                features=features_list[i]
            ))
        
        return results
    
    def get_trend(self, window: int = 10) -> Dict[str, float]:
        """Get trend of recent predictions."""
        if len(self.prediction_buffer) < window:
            return {}
        
        recent = list(self.prediction_buffer)[-window:]
        
        trends = {}
        for metric in ['fatigue', 'stress', 'attention', 'cognitive_load']:
            values = [getattr(p, metric) for p in recent]
            if len(values) >= 2:
                # Linear trend using first and last
                trends[metric] = (values[-1] - values[0]) / len(values)
            else:
                trends[metric] = 0.0
        
        return trends
    
    def get_average_inference_time(self) -> float:
        """Get average inference time in milliseconds."""
        if not self.inference_times:
            return 0.0
        return np.mean(self.inference_times) * 1000
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get inference statistics."""
        return {
            'total_inferences': self.total_inferences,
            'avg_inference_time_ms': self.get_average_inference_time(),
            'buffer_sizes': {
                name: len(buffer)
                for name, buffer in self.feature_buffer.items()
            },
            'window_size': self.window_size,
            'prediction_horizon': self.prediction_horizon,
            'using_onnx': self.use_onnx
        }
    
    def reset(self):
        """Reset inference engine state."""
        for buffer in self.feature_buffer.values():
            buffer.clear()
        self.prediction_buffer.clear()
        self.timestamps.clear()
        self.total_inferences = 0


class StreamingInferenceEngine(InferenceEngine):
    """Inference engine optimized for streaming data."""
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        device: str = 'cpu',
        use_onnx: bool = False,
        onnx_path: Optional[Path] = None,
        window_size: int = 30,
        prediction_horizon: int = 10,
        confidence_threshold: float = 0.7,
        update_frequency: float = 5.0  # Hz
    ):
        super().__init__(
            model_path=model_path,
            device=device,
            use_onnx=use_onnx,
            onnx_path=onnx_path,
            window_size=window_size,
            prediction_horizon=prediction_horizon,
            confidence_threshold=confidence_threshold
        )
        
        self.update_frequency = update_frequency
        self.update_interval = 1.0 / update_frequency
        self.last_update_time = 0.0
        self.current_prediction: Optional[ModelOutput] = None
    
    def process_stream(
        self,
        feature_stream,
        callback=None
    ):
        """
        Process streaming features.
        
        Args:
            feature_stream: Generator yielding feature dictionaries
            callback: Optional callback for predictions
        """
        import time
        
        for features in feature_stream:
            current_time = time.time()
            
            # Update buffer with new features
            self.update_buffer(features)
            
            # Run inference at specified frequency
            if current_time - self.last_update_time >= self.update_interval:
                prediction = self.predict(features)
                self.current_prediction = prediction
                self.last_update_time = current_time
                
                if callback:
                    callback(prediction)
            
            yield self.current_prediction