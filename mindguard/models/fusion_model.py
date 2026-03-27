"""Multimodal fusion model for cognitive state estimation."""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from models.modality_encoder import ModalityEncoder
from models.attention_encoder import AttentionEncoder


@dataclass
class ModelOutput:
    """Model output container."""
    fatigue: float
    stress: float
    attention: float
    cognitive_load: float
    confidence: float
    features: Optional[Dict[str, np.ndarray]] = None
    embeddings: Optional[Dict[str, np.ndarray]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'fatigue': self.fatigue,
            'stress': self.stress,
            'attention': self.attention,
            'cognitive_load': self.cognitive_load,
            'confidence': self.confidence
        }
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array([
            self.fatigue,
            self.stress,
            self.attention,
            self.cognitive_load,
            self.confidence
        ])


class CognitiveFusionModel(nn.Module):
    """Multimodal fusion model for cognitive state estimation."""
    
    def __init__(
        self,
        modality_dims: Optional[Dict[str, int]] = None,
        embed_dim: int = 64,
        hidden_dim: int = 128,
        num_heads: int = 4,
        num_encoder_layers: int = 2,
        num_attention_layers: int = 2,
        dropout: float = 0.1,
        use_attention: bool = True
    ):
        """
        Initialize fusion model.
        
        Args:
            modality_dims: Dictionary mapping modality names to input dimensions
            embed_dim: Embedding dimension
            hidden_dim: Hidden dimension
            num_heads: Number of attention heads
            num_encoder_layers: Number of modality encoder layers
            num_attention_layers: Number of cross-attention layers
            dropout: Dropout rate
            use_attention: Whether to use cross-modal attention
        """
        super().__init__()
        
        if modality_dims is None:
            modality_dims = {
                'eye': 5,        # EAR, blink_rate, perclos, pupil_dilation, face_detected
                'keyboard': 5,    # typing_speed, rhythm_variance, hesitation_rate, key_count, is_typing
                'screen': 5,      # app_switch_rate, idle_time, focus_score, scroll_activity, context_switches
                'voice': 8        # pitch_mean, pitch_std, energy, zcr, mfcc_1, mfcc_2, mfcc_3, is_speaking
            }
        
        self.modality_dims = modality_dims
        self.modality_names = list(modality_dims.keys())
        self.num_modalities = len(self.modality_names)
        self.embed_dim = embed_dim
        self.use_attention = use_attention
        
        # Modality encoders
        self.encoders = nn.ModuleDict({
            name: ModalityEncoder(
                input_dim=dim,
                hidden_dim=hidden_dim,
                output_dim=embed_dim,
                num_layers=num_encoder_layers,
                dropout=dropout,
                use_sequence=False  # Process as fixed vectors
            )
            for name, dim in modality_dims.items()
        })
        
        # Cross-modal attention
        if use_attention:
            self.attention = AttentionEncoder(
                embed_dim=embed_dim,
                num_heads=num_heads,
                num_layers=num_attention_layers,
                num_modalities=self.num_modalities,
                dropout=dropout
            )
        
        # Fusion layer
        fusion_input_dim = embed_dim * self.num_modalities
        self.fusion_layer = nn.Sequential(
            nn.Linear(fusion_input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU()
        )
        
        # Output heads
        self.fatigue_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, 32),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.stress_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, 32),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.attention_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, 32),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.cognitive_load_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, 32),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # Confidence estimation
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        
        # Uncertainty estimation (aleatoric)
        self.log_vars = nn.ParameterDict({
            name: nn.Parameter(torch.zeros(1))
            for name in ['fatigue', 'stress', 'attention', 'cognitive_load']
        })
        
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.LayerNorm):
                nn.init.constant_(module.weight, 1)
                nn.init.constant_(module.bias, 0)
    
    def forward(
        self,
        inputs: Dict[str, torch.Tensor],
        return_embeddings: bool = False,
        return_attention: bool = False
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            inputs: Dictionary mapping modality names to input tensors
            return_embeddings: Whether to return modality embeddings
            return_attention: Whether to return attention weights
            
        Returns:
            Dictionary with predictions
        """
        batch_size = next(iter(inputs.values())).shape[0]
        device = next(self.parameters()).device
        
        # Encode each modality
        embeddings = {}
        valid_modalities = []
        
        for name in self.modality_names:
            if name in inputs and inputs[name] is not None:
                x = inputs[name]
                
                # Ensure correct shape
                if len(x.shape) == 1:
                    x = x.unsqueeze(0)  # Add batch dimension
                if len(x.shape) == 2:
                    # Already [batch, features]
                    pass
                else:
                    x = x.view(batch_size, -1)
                
                # Ensure correct feature dimension
                expected_dim = self.modality_dims[name]
                if x.shape[1] != expected_dim:
                    if x.shape[1] < expected_dim:
                        # Pad with zeros
                        padding = torch.zeros(batch_size, expected_dim - x.shape[1]).to(device)
                        x = torch.cat([x, padding], dim=1)
                    else:
                        # Truncate
                        x = x[:, :expected_dim]
                
                # Encode
                embeddings[name] = self.encoders[name](x)
                valid_modalities.append(name)
            else:
                # Use zero embedding for missing modality
                embeddings[name] = torch.zeros(batch_size, self.embed_dim).to(device)
        
        # Stack embeddings
        embedding_list = [embeddings[name] for name in self.modality_names]
        stacked = torch.stack(embedding_list, dim=1)  # [batch, num_mod, embed_dim]
        
        # Apply cross-modal attention
        attention_weights = None
        if self.use_attention:
            # Convert to dictionary for attention
            attn_input = {
                name: embeddings[name] for name in self.modality_names
            }
            attended, attention_weights = self.attention(
                attn_input,
                return_all_attention=return_attention
            )
            
            # Stack attended embeddings
            attended_list = [attended[name] for name in self.modality_names]
            fused = torch.stack(attended_list, dim=1)  # [batch, num_mod, embed_dim]
        else:
            fused = stacked
        
        # Flatten modalities
        flat_fused = fused.reshape(batch_size, -1)  # [batch, num_mod * embed_dim]
        
        # Fusion
        fused_features = self.fusion_layer(flat_fused)
        
        # Predictions
        fatigue = self.fatigue_head(fused_features)
        stress = self.stress_head(fused_features)
        attention = self.attention_head(fused_features)
        cognitive_load = self.cognitive_load_head(fused_features)
        confidence = self.confidence_head(fused_features)
        
        # Apply uncertainty weighting (multi-task learning)
        fatigue_precision = torch.exp(-self.log_vars['fatigue'])
        stress_precision = torch.exp(-self.log_vars['stress'])
        attention_precision = torch.exp(-self.log_vars['attention'])
        load_precision = torch.exp(-self.log_vars['cognitive_load'])
        
        # Weighted outputs
        fatigue_weighted = fatigue * fatigue_precision
        stress_weighted = stress * stress_precision
        attention_weighted = attention * attention_precision
        load_weighted = cognitive_load * load_precision
        
        output = {
            'fatigue': fatigue_weighted.squeeze(-1),
            'stress': stress_weighted.squeeze(-1),
            'attention': attention_weighted.squeeze(-1),
            'cognitive_load': load_weighted.squeeze(-1),
            'confidence': confidence.squeeze(-1),
            'fatigue_raw': fatigue.squeeze(-1),
            'stress_raw': stress.squeeze(-1),
            'attention_raw': attention.squeeze(-1),
            'cognitive_load_raw': cognitive_load.squeeze(-1),
            'fatigue_uncertainty': torch.exp(self.log_vars['fatigue']).expand(batch_size),
            'stress_uncertainty': torch.exp(self.log_vars['stress']).expand(batch_size),
            'attention_uncertainty': torch.exp(self.log_vars['attention']).expand(batch_size),
            'load_uncertainty': torch.exp(self.log_vars['cognitive_load']).expand(batch_size)
        }
        
        if return_embeddings:
            output['embeddings'] = {
                name: embeddings[name].detach().cpu().numpy()
                for name in self.modality_names
            }
        
        if return_attention and attention_weights is not None:
            output['attention_weights'] = attention_weights
        
        return output
    
    def predict(
        self,
        features: Dict[str, np.ndarray],
        device: str = 'cpu'
    ) -> ModelOutput:
        """
        Make prediction from numpy features.
        
        Args:
            features: Dictionary of feature arrays
            device: Device to run inference on
            
        Returns:
            ModelOutput with predictions
        """
        self.eval()
        
        # Convert to tensors
        inputs = {}
        for name in self.modality_names:
            if name in features and features[name] is not None:
                feat = features[name]
                if isinstance(feat, np.ndarray):
                    if len(feat.shape) == 1:
                        feat = feat.reshape(1, -1)
                    inputs[name] = torch.from_numpy(feat).float().to(device)
        
        if not inputs:
            # No valid inputs
            return ModelOutput(
                fatigue=0.5,
                stress=0.5,
                attention=0.5,
                cognitive_load=0.5,
                confidence=0.0
            )
        
        with torch.no_grad():
            outputs = self.forward(inputs, return_embeddings=True)
        
        # Get embeddings if available
        embeddings = outputs.get('embeddings') if 'embeddings' in outputs else None
        
        return ModelOutput(
            fatigue=float(outputs['fatigue'].cpu().numpy()[0]),
            stress=float(outputs['stress'].cpu().numpy()[0]),
            attention=float(outputs['attention'].cpu().numpy()[0]),
            cognitive_load=float(outputs['cognitive_load'].cpu().numpy()[0]),
            confidence=float(outputs['confidence'].cpu().numpy()[0]),
            features=features,
            embeddings=embeddings
        )
    
    def get_embedding(self, inputs: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Get fused embedding without predictions."""
        batch_size = next(iter(inputs.values())).shape[0]
        device = next(self.parameters()).device
        
        # Encode each modality
        embeddings = []
        for name in self.modality_names:
            if name in inputs and inputs[name] is not None:
                x = inputs[name]
                if len(x.shape) == 1:
                    x = x.unsqueeze(0)
                embeddings.append(self.encoders[name](x))
            else:
                embeddings.append(torch.zeros(batch_size, self.embed_dim).to(device))
        
        # Stack and fuse
        stacked = torch.stack(embeddings, dim=1)
        flat = stacked.reshape(batch_size, -1)
        fused = self.fusion_layer(flat)
        
        return fused
    
    def get_num_parameters(self) -> int:
        """Get number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_modality_names(self) -> List[str]:
        """Get list of modality names."""
        return self.modality_names.copy()