"""Attention-based encoders for multimodal fusion."""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple, Dict, List


class MultiHeadAttention(nn.Module):
    """Multi-head attention mechanism."""
    
    def __init__(
        self,
        embed_dim: int,
        num_heads: int = 8,
        dropout: float = 0.1
    ):
        super().__init__()
        
        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"
        
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.scale = self.head_dim ** -0.5
        
        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        return_attention: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass.
        
        Args:
            query: Query tensor [batch, tgt_len, embed_dim]
            key: Key tensor [batch, src_len, embed_dim]
            value: Value tensor [batch, src_len, embed_dim]
            mask: Attention mask [batch, tgt_len, src_len]
            return_attention: Whether to return attention weights
            
        Returns:
            Output tensor and optional attention weights
        """
        batch_size, tgt_len, _ = query.shape
        src_len = key.shape[1]
        
        # Project and reshape
        Q = self.q_proj(query).view(batch_size, tgt_len, self.num_heads, self.head_dim)
        K = self.k_proj(key).view(batch_size, src_len, self.num_heads, self.head_dim)
        V = self.v_proj(value).view(batch_size, src_len, self.num_heads, self.head_dim)
        
        # Transpose for batch*heads
        Q = Q.transpose(1, 2)  # [batch, heads, tgt_len, head_dim]
        K = K.transpose(1, 2)  # [batch, heads, src_len, head_dim]
        V = V.transpose(1, 2)  # [batch, heads, src_len, head_dim]
        
        # Compute attention scores
        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale  # [batch, heads, tgt_len, src_len]
        
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1) == 0, float('-inf'))
        
        attention_weights = F.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        # Apply attention to values
        context = torch.matmul(attention_weights, V)  # [batch, heads, tgt_len, head_dim]
        
        # Reshape back
        context = context.transpose(1, 2).contiguous().view(
            batch_size, tgt_len, self.embed_dim
        )
        
        # Output projection
        output = self.out_proj(context)
        
        if return_attention:
            return output, attention_weights
        return output, None


class CrossModalAttention(nn.Module):
    """Cross-modal attention for fusing multiple modalities."""
    
    def __init__(
        self,
        embed_dim: int = 64,
        num_heads: int = 4,
        num_modalities: int = 4,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.embed_dim = embed_dim
        self.num_modalities = num_modalities
        
        # Cross-attention layers
        self.cross_attentions = nn.ModuleList([
            MultiHeadAttention(embed_dim, num_heads, dropout)
            for _ in range(num_modalities)
        ])
        
        # Feed-forward networks
        self.ffns = nn.ModuleList([
            nn.Sequential(
                nn.Linear(embed_dim, embed_dim * 4),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(embed_dim * 4, embed_dim)
            )
            for _ in range(num_modalities)
        ])
        
        # Layer normalization
        self.norm1 = nn.ModuleList([nn.LayerNorm(embed_dim) for _ in range(num_modalities)])
        self.norm2 = nn.ModuleList([nn.LayerNorm(embed_dim) for _ in range(num_modalities)])
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(
        self,
        modalities: Dict[str, torch.Tensor],
        return_attention: bool = False
    ) -> Tuple[Dict[str, torch.Tensor], Optional[Dict[str, torch.Tensor]]]:
        """
        Forward pass.
        
        Args:
            modalities: Dictionary mapping modality names to embeddings
            return_attention: Whether to return attention weights
            
        Returns:
            Updated modalities and optional attention weights
        """
        modality_names = list(modalities.keys())
        embeddings = list(modalities.values())
        batch_size = embeddings[0].shape[0]
        
        # Stack embeddings for cross-attention
        stacked = torch.stack(embeddings, dim=1)  # [batch, num_mod, embed_dim]
        
        attention_weights = {} if return_attention else None
        
        # Apply cross-attention for each modality
        outputs = []
        for i, (name, attn, ffn, norm1, norm2) in enumerate(zip(
            modality_names,
            self.cross_attentions,
            self.ffns,
            self.norm1,
            self.norm2
        )):
            # Self-attention would be query = self, key/value = all modalities
            # For cross-modal, query is current modality, key/value are all modalities
            query = stacked[:, i:i+1, :]  # [batch, 1, embed_dim]
            key = stacked  # [batch, num_mod, embed_dim]
            value = stacked  # [batch, num_mod, embed_dim]
            
            # Cross-attention
            attended, attn_weights = attn(query, key, value, return_attention=return_attention)
            
            if return_attention:
                attention_weights[name] = attn_weights
            
            # Residual connection and layer norm
            attended = norm1(query.squeeze(1) + self.dropout(attended.squeeze(1)))
            
            # Feed-forward
            ff_output = ffn(attended)
            output = norm2(attended + self.dropout(ff_output))
            
            outputs.append(output)
        
        # Stack outputs back into dictionary
        updated_modalities = {
            name: output
            for name, output in zip(modality_names, outputs)
        }
        
        return updated_modalities, attention_weights


class AttentionEncoder(nn.Module):
    """Complete attention encoder with multiple layers."""
    
    def __init__(
        self,
        embed_dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        num_modalities: int = 4,
        dropout: float = 0.1
    ):
        super().__init__()
        
        self.embed_dim = embed_dim
        self.num_layers = num_layers
        
        # Cross-modal attention layers
        self.layers = nn.ModuleList([
            CrossModalAttention(embed_dim, num_heads, num_modalities, dropout)
            for _ in range(num_layers)
        ])
        
    def forward(
        self,
        modalities: Dict[str, torch.Tensor],
        return_all_attention: bool = False
    ) -> Tuple[Dict[str, torch.Tensor], Optional[List[Dict[str, torch.Tensor]]]]:
        """
        Forward pass through all attention layers.
        
        Args:
            modalities: Dictionary of modality embeddings
            return_all_attention: Whether to return attention from all layers
            
        Returns:
            Fused modalities and optional attention weights
        """
        all_attention_weights = [] if return_all_attention else None
        
        x = modalities
        for layer in self.layers:
            x, attn_weights = layer(x, return_attention=return_all_attention)
            
            if return_all_attention:
                all_attention_weights.append(attn_weights)
        
        return x, all_attention_weights
    
    def get_output_dim(self) -> int:
        """Get output dimension."""
        return self.embed_dim