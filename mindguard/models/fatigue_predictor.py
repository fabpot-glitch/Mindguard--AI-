"""Fatigue prediction head with temporal modeling."""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, List


class TemporalConvNet(nn.Module):
    """Temporal convolutional network for sequence modeling."""
    
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        dilation_growth: int = 2,
        num_layers: int = 4,
        dropout: float = 0.1
    ):
        super().__init__()
        
        layers = []
        for i in range(num_layers):
            dilation = dilation_growth ** i
            padding = (kernel_size - 1) * dilation // 2
            
            conv = nn.Conv1d(
                in_channels if i == 0 else out_channels,
                out_channels,
                kernel_size,
                padding=padding,
                dilation=dilation
            )
            layers.append(conv)
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass."""
        return self.network(x)


class FatiguePredictor(nn.Module):
    """Fatigue prediction with temporal modeling."""
    
    def __init__(
        self,
        input_dim: int = 64,
        hidden_dim: int = 128,
        num_temporal_layers: int = 3,
        prediction_horizon: int = 10,  # Predict 10 steps ahead
        dropout: float = 0.1
    ):
        """
        Initialize fatigue predictor.
        
        Args:
            input_dim: Input feature dimension
            hidden_dim: Hidden dimension
            num_temporal_layers: Number of temporal layers
            prediction_horizon: Number of steps to predict ahead
            dropout: Dropout rate
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.prediction_horizon = prediction_horizon
        
        # Temporal encoder
        self.temporal_encoder = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_temporal_layers,
            batch_first=True,
            dropout=dropout,
            bidirectional=True
        )
        
        # Temporal convolution for local patterns
        self.temporal_conv = TemporalConvNet(
            in_channels=hidden_dim * 2,  # Bidirectional
            out_channels=hidden_dim,
            num_layers=3,
            dropout=dropout
        )
        
        # Current state predictor
        self.current_predictor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        # Future trajectory predictor
        self.trajectory_predictor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, prediction_horizon)
        )
        
        # Uncertainty estimator
        self.uncertainty_estimator = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Softplus()  # Positive uncertainty
        )
        
        # Attention over history
        self.history_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )
        
    def forward(
        self,
        features: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            features: Input features [batch, seq_len, input_dim]
            mask: Optional mask for padding [batch, seq_len]
            
        Returns:
            current_prediction: Current fatigue [batch]
            trajectory: Future trajectory [batch, horizon]
            uncertainty: Prediction uncertainty [batch]
            attention_weights: Attention weights [batch, seq_len]
        """
        batch_size, seq_len, _ = features.shape
        
        # Encode temporal sequence
        lstm_out, (hidden, cell) = self.temporal_encoder(features)
        # lstm_out: [batch, seq_len, hidden*2]
        
        # Apply temporal convolution
        conv_out = self.temporal_conv(lstm_out.transpose(1, 2))
        conv_out = conv_out.transpose(1, 2)  # [batch, seq_len, hidden]
        
        # Apply attention over history
        if mask is not None:
            # Create attention mask (True = masked)
            attn_mask = ~mask.bool()
            attended, attention_weights = self.history_attention(
                conv_out, conv_out, conv_out,
                key_padding_mask=attn_mask
            )
        else:
            attended, attention_weights = self.history_attention(
                conv_out, conv_out, conv_out
            )
        
        # Use last timestep for prediction
        last_features = attended[:, -1, :]  # [batch, hidden]
        
        # Current state prediction
        current = self.current_predictor(last_features).squeeze(-1)
        
        # Future trajectory prediction
        trajectory = self.trajectory_predictor(last_features)  # [batch, horizon]
        trajectory = torch.sigmoid(trajectory)  # Bound to [0, 1]
        
        # Uncertainty estimation
        uncertainty = self.uncertainty_estimator(last_features).squeeze(-1)
        
        return current, trajectory, uncertainty, attention_weights
    
    def predict_future(
        self,
        features: torch.Tensor,
        steps: int,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict future fatigue values.
        
        Args:
            features: Input features [batch, seq_len, input_dim]
            steps: Number of steps to predict
            mask: Optional mask for padding
            
        Returns:
            predictions: Future predictions [batch, steps]
            uncertainties: Prediction uncertainties [batch, steps]
        """
        batch_size, seq_len, _ = features.shape
        
        # Get initial prediction
        current, trajectory, uncertainty, _ = self.forward(features, mask)
        
        if steps <= self.prediction_horizon:
            # Use precomputed trajectory
            predictions = trajectory[:, :steps]
            uncertainties = uncertainty.unsqueeze(1).expand(-1, steps)
        else:
            # Need to iterate
            predictions = []
            uncertainties = []
            
            # Use first prediction
            predictions.append(trajectory[:, 0].unsqueeze(1))
            uncertainties.append(uncertainty.unsqueeze(1))
            
            # Recursive prediction
            current_features = features
            for i in range(1, steps):
                # Update features with last prediction
                new_feature = torch.zeros(batch_size, 1, self.input_dim).to(features.device)
                new_feature[:, :, 0] = trajectory[:, i-1] if i-1 < self.prediction_horizon else predictions[-1].squeeze(-1)
                
                current_features = torch.cat([current_features[:, 1:, :], new_feature], dim=1)
                
                # Predict next step
                _, traj, unc, _ = self.forward(current_features, mask)
                
                predictions.append(traj[:, 0].unsqueeze(1))
                uncertainties.append(unc.unsqueeze(1))
            
            predictions = torch.cat(predictions, dim=1)
            uncertainties = torch.cat(uncertainties, dim=1)
        
        return predictions, uncertainties
    
    def get_time_to_threshold(
        self,
        features: torch.Tensor,
        threshold: float = 0.8,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Estimate time to reach threshold.
        
        Args:
            features: Input features [batch, seq_len, input_dim]
            threshold: Fatigue threshold
            mask: Optional mask for padding
            
        Returns:
            time_to_threshold: Steps to reach threshold [batch]
            confidence: Confidence in prediction [batch]
        """
        # Predict future trajectory
        predictions, uncertainties = self.predict_future(features, 30, mask)
        
        batch_size = predictions.shape[0]
        time_to_threshold = torch.full((batch_size,), 30, device=predictions.device)
        confidence = torch.ones(batch_size, device=predictions.device)
        
        for i in range(batch_size):
            # Find first time prediction exceeds threshold
            exceed_idx = torch.where(predictions[i] >= threshold)[0]
            if len(exceed_idx) > 0:
                time_to_threshold[i] = exceed_idx[0].float()
                # Confidence based on uncertainty at that step
                confidence[i] = 1.0 / (1.0 + uncertainties[i, exceed_idx[0]])
            else:
                # Never reaches threshold within horizon
                time_to_threshold[i] = -1.0  # Indicates never
                confidence[i] = 0.0
        
        return time_to_threshold, confidence


class FatiguePredictorConfig:
    """Configuration for fatigue predictor."""
    
    def __init__(
        self,
        input_dim: int = 64,
        hidden_dim: int = 128,
        num_temporal_layers: int = 3,
        prediction_horizon: int = 10,
        dropout: float = 0.1
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_temporal_layers = num_temporal_layers
        self.prediction_horizon = prediction_horizon
        self.dropout = dropout
    
    def build(self) -> FatiguePredictor:
        """Build predictor from config."""
        return FatiguePredictor(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            num_temporal_layers=self.num_temporal_layers,
            prediction_horizon=self.prediction_horizon,
            dropout=self.dropout
        )