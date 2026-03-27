"""Modality encoder for processing individual data streams."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Optional, Tuple
import math


class PositionalEncoding(nn.Module):
    """Positional encoding for sequence data."""
    
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add positional encoding to input."""
        return x + self.pe[:x.size(0), :]


class ModalityEncoder(nn.Module):
    """Encode individual modalities into embeddings."""
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        output_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
        use_sequence: bool = True,
        max_seq_len: int = 100
    ):
        """
        Initialize modality encoder.
        
        Args:
            input_dim: Input feature dimension
            hidden_dim: Hidden layer dimension
            output_dim: Output embedding dimension
            num_layers: Number of encoder layers
            dropout: Dropout rate
            use_sequence: Whether to process as sequence
            max_seq_len: Maximum sequence length
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.use_sequence = use_sequence
        
        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        if use_sequence:
            # Sequence processing
            self.positional_encoding = PositionalEncoding(hidden_dim, max_seq_len)
            
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=hidden_dim,
                nhead=4,
                dim_feedforward=hidden_dim * 4,
                dropout=dropout,
                batch_first=True
            )
            self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            
            # Sequence pooling
            self.pooling = nn.Sequential(
                nn.AdaptiveAvgPool1d(1),
                nn.Flatten()
            )
        else:
            # Simple feedforward for non-sequence data
            self.feedforward = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            )
        
        # Output projection
        self.output_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )
        
        # Feature statistics
        self.register_buffer('feature_mean', torch.zeros(input_dim))
        self.register_buffer('feature_std', torch.ones(input_dim))
        self.register_buffer('feature_min', torch.zeros(input_dim))
        self.register_buffer('feature_max', torch.ones(input_dim))
        
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor [batch_size, seq_len, input_dim] or [batch_size, input_dim]
            mask: Optional mask for padding [batch_size, seq_len]
            
        Returns:
            Encoded embedding [batch_size, output_dim]
        """
        # Handle different input shapes
        if len(x.shape) == 2:
            # Non-sequence input [batch, features]
            x = x.unsqueeze(1)  # Add sequence dimension
            has_seq = False
        else:
            has_seq = True
        
        batch_size, seq_len, feat_dim = x.shape
        
        # Normalize features
        x = (x - self.feature_mean) / (self.feature_std + 1e-8)
        x = torch.clamp(x, -5, 5)  # Clip outliers
        
        # Input projection
        x = self.input_proj(x)  # [batch, seq_len, hidden]
        
        if self.use_sequence and has_seq:
            # Add positional encoding
            x = self.positional_encoding(x)
            
            # Apply transformer encoder
            if mask is not None:
                # Create attention mask (True = masked)
                attn_mask = ~mask.bool()
                x = self.transformer_encoder(x, src_key_padding_mask=attn_mask)
            else:
                x = self.transformer_encoder(x)
            
            # Pool sequence dimension
            if mask is not None:
                # Masked mean pooling
                mask = mask.unsqueeze(-1).float()
                x = (x * mask).sum(dim=1) / (mask.sum(dim=1) + 1e-8)
            else:
                # Mean pooling
                x = x.mean(dim=1)
        else:
            # Simple feedforward (use last timestep or mean)
            if has_seq:
                x = x.mean(dim=1)  # Average over sequence
            else:
                x = x.squeeze(1)  # Remove sequence dimension
            
            x = self.feedforward(x)
        
        # Output projection
        output = self.output_proj(x)
        
        return output
    
    def update_normalization(self, features: torch.Tensor):
        """Update feature normalization statistics."""
        if len(features.shape) == 3:
            features = features.view(-1, features.shape[-1])
        
        self.feature_mean = features.mean(dim=0)
        self.feature_std = features.std(dim=0)
        self.feature_min = features.min(dim=0)[0]
        self.feature_max = features.max(dim=0)[0]
    
    def get_output_dim(self) -> int:
        """Get output dimension."""
        return self.output_dim
    
    def get_input_dim(self) -> int:
        """Get input dimension."""
        return self.input_dim


class ModalityEncoderConfig:
    """Configuration for modality encoder."""
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        output_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
        use_sequence: bool = True
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.use_sequence = use_sequence
    
    def build(self) -> ModalityEncoder:
        """Build encoder from config."""
        return ModalityEncoder(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            output_dim=self.output_dim,
            num_layers=self.num_layers,
            dropout=self.dropout,
            use_sequence=self.use_sequence
        )