"""Feature normalization module for real-time data."""

import numpy as np
from typing import Dict, List, Optional, Any
from collections import deque
import json
from pathlib import Path

from config.logging_config import get_logger

logger = get_logger(__name__)


class FeatureNormalizer:
    """Normalizes features in real-time using rolling statistics."""
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize normalizer.
        
        Args:
            window_size: Size of rolling window for statistics
        """
        self.window_size = window_size
        
        # Rolling statistics
        self.rolling_stats: Dict[str, Dict[str, deque]] = {}
        self.global_stats: Dict[str, Dict[str, float]] = {}
        
        # Normalization parameters
        self.norm_params: Dict[str, Dict[str, float]] = {}
        
        logger.info(f"FeatureNormalizer initialized with window size {window_size}")
    
    def update(self, modality: str, features: np.ndarray):
        """
        Update rolling statistics with new features.
        
        Args:
            modality: Modality name
            features: Feature array
        """
        if modality not in self.rolling_stats:
            self.rolling_stats[modality] = {
                'values': deque(maxlen=self.window_size),
                'means': deque(maxlen=self.window_size),
                'stds': deque(maxlen=self.window_size)
            }
        
        # Store raw values
        self.rolling_stats[modality]['values'].append(features)
        
        # Update statistics if we have enough data
        if len(self.rolling_stats[modality]['values']) >= 100:
            values = np.array(self.rolling_stats[modality]['values'])
            
            # Compute per-feature statistics
            means = np.mean(values, axis=0)
            stds = np.std(values, axis=0)
            
            self.rolling_stats[modality]['means'].append(means)
            self.rolling_stats[modality]['stds'].append(stds)
            
            # Update normalization parameters
            self.norm_params[modality] = {
                'mean': np.mean(self.rolling_stats[modality]['means'], axis=0).tolist(),
                'std': np.mean(self.rolling_stats[modality]['stds'], axis=0).tolist(),
                'min': np.min(values, axis=0).tolist(),
                'max': np.max(values, axis=0).tolist()
            }
    
    def normalize(self, modality: str, features: np.ndarray, method: str = 'zscore') -> np.ndarray:
        """
        Normalize features.
        
        Args:
            modality: Modality name
            features: Feature array
            method: Normalization method ('zscore', 'minmax', 'robust')
        
        Returns:
            Normalized features
        """
        if modality not in self.norm_params:
            return features  # No normalization parameters yet
        
        params = self.norm_params[modality]
        
        if method == 'zscore':
            # Z-score normalization
            mean = np.array(params['mean'])
            std = np.array(params['std'])
            std = np.where(std < 1e-6, 1.0, std)  # Avoid division by zero
            normalized = (features - mean) / std
            
        elif method == 'minmax':
            # Min-max normalization to [0, 1]
            min_val = np.array(params['min'])
            max_val = np.array(params['max'])
            range_val = max_val - min_val
            range_val = np.where(range_val < 1e-6, 1.0, range_val)
            normalized = (features - min_val) / range_val
            
        elif method == 'robust':
            # Robust normalization using percentiles
            # Simplified version using mean/std
            mean = np.array(params['mean'])
            std = np.array(params['std'])
            std = np.where(std < 1e-6, 1.0, std)
            normalized = (features - mean) / (2 * std)
            normalized = np.clip(normalized, -5, 5)  # Clip outliers
            
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        
        return normalized
    
    def normalize_batch(self, modality: str, features: np.ndarray) -> np.ndarray:
        """Normalize a batch of features."""
        if len(features.shape) == 1:
            return self.normalize(modality, features)
        
        normalized = np.zeros_like(features)
        for i in range(features.shape[0]):
            normalized[i] = self.normalize(modality, features[i])
        
        return normalized
    
    def denormalize(self, modality: str, normalized: np.ndarray) -> np.ndarray:
        """
        Denormalize features back to original scale.
        
        Args:
            modality: Modality name
            normalized: Normalized features
        
        Returns:
            Denormalized features
        """
        if modality not in self.norm_params:
            return normalized
        
        params = self.norm_params[modality]
        mean = np.array(params['mean'])
        std = np.array(params['std'])
        
        return normalized * std + mean
    
    def get_statistics(self, modality: str) -> Dict[str, Any]:
        """Get current statistics for a modality."""
        if modality not in self.rolling_stats:
            return {}
        
        stats = self.rolling_stats[modality]
        
        return {
            'n_samples': len(stats['values']),
            'n_updates': len(stats['means']),
            'current_mean': np.mean(stats['values'][-100:], axis=0).tolist() if stats['values'] else [],
            'current_std': np.std(stats['values'][-100:], axis=0).tolist() if stats['values'] else [],
            'norm_params': self.norm_params.get(modality, {})
        }
    
    def reset(self):
        """Reset all statistics."""
        self.rolling_stats.clear()
        self.norm_params.clear()
        logger.info("FeatureNormalizer reset")
    
    def save(self, path: Path):
        """Save normalization parameters to file."""
        save_path = path / 'norm_params.json'
        with open(save_path, 'w') as f:
            json.dump(self.norm_params, f, indent=2)
        logger.info(f"Saved normalization parameters to {save_path}")
    
    def load(self, path: Path):
        """Load normalization parameters from file."""
        load_path = path / 'norm_params.json'
        if load_path.exists():
            with open(load_path, 'r') as f:
                self.norm_params = json.load(f)
            logger.info(f"Loaded normalization parameters from {load_path}")