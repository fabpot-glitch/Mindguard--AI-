"""Training pipeline for cognitive fusion model."""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import yaml
from tqdm import tqdm
from datetime import datetime
import wandb
from collections import defaultdict

from models.fusion_model import CognitiveFusionModel
from config.logging_config import model_logger


class CognitiveDataset(Dataset):
    """Dataset for cognitive state training."""
    
    def __init__(
        self,
        data_path: Path,
        modality_names: List[str],
        sequence_length: int = 30,
        stride: int = 5,
        normalize: bool = True
    ):
        """
        Initialize dataset.
        
        Args:
            data_path: Path to preprocessed data
            modality_names: List of modality names
            sequence_length: Length of sequences
            stride: Stride for sliding window
            normalize: Whether to normalize features
        """
        self.modality_names = modality_names
        self.sequence_length = sequence_length
        self.stride = stride
        
        # Load data
        data = np.load(data_path, allow_pickle=True).item()
        
        self.features = {}
        for name in modality_names:
            if name in data['features']:
                self.features[name] = data['features'][name].astype(np.float32)
        
        self.labels = data['labels']
        
        # Extract label values
        self.fatigue_labels = np.array([l.get('fatigue', 0.5) for l in self.labels], dtype=np.float32)
        self.stress_labels = np.array([l.get('stress', 0.5) for l in self.labels], dtype=np.float32)
        self.attention_labels = np.array([l.get('attention', 0.5) for l in self.labels], dtype=np.float32)
        self.load_labels = np.array([l.get('cognitive_load', 0.5) for l in self.labels], dtype=np.float32)
        
        # Calculate normalization statistics
        if normalize:
            self._calculate_normalization()
        
        # Create indices for sliding window
        self.indices = []
        n_samples = len(self.labels)
        for i in range(0, n_samples - sequence_length + 1, stride):
            self.indices.append(i)
        
        model_logger.info(f"Created dataset with {len(self.indices)} sequences")
    
    def _calculate_normalization(self):
        """Calculate feature normalization statistics."""
        self.norm_stats = {}
        
        for name, feat in self.features.items():
            if feat is not None:
                # Reshape to [n_samples, features]
                flat_feat = feat.reshape(-1, feat.shape[-1])
                self.norm_stats[name] = {
                    'mean': flat_feat.mean(axis=0),
                    'std': flat_feat.std(axis=0) + 1e-8,
                    'min': flat_feat.min(axis=0),
                    'max': flat_feat.max(axis=0)
                }
    
    def normalize_features(self, features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Normalize features using stored statistics."""
        normalized = {}
        for name, feat in features.items():
            if name in self.norm_stats and feat is not None:
                stats = self.norm_stats[name]
                feat_norm = (feat - stats['mean']) / stats['std']
                feat_norm = np.clip(feat_norm, -5, 5)
                normalized[name] = feat_norm
            else:
                normalized[name] = feat
        return normalized
    
    def __len__(self) -> int:
        return len(self.indices)
    
    def __getitem__(self, idx: int) -> Tuple[Dict[str, torch.Tensor], Dict[str, torch.Tensor]]:
        start_idx = self.indices[idx]
        end_idx = start_idx + self.sequence_length
        
        # Get sequence for each modality
        sequence = {}
        for name, feat in self.features.items():
            if feat is not None:
                seq = feat[start_idx:end_idx]
                sequence[name] = torch.from_numpy(seq).float()
        
        # Get labels (last value in sequence)
        labels = {
            'fatigue': torch.tensor(self.fatigue_labels[end_idx - 1], dtype=torch.float32),
            'stress': torch.tensor(self.stress_labels[end_idx - 1], dtype=torch.float32),
            'attention': torch.tensor(self.attention_labels[end_idx - 1], dtype=torch.float32),
            'cognitive_load': torch.tensor(self.load_labels[end_idx - 1], dtype=torch.float32)
        }
        
        return sequence, labels


class Trainer:
    """Trainer for cognitive fusion model."""
    
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        use_wandb: bool = False,
        config: Optional[Dict] = None
    ):
        """
        Initialize trainer.
        
        Args:
            model: Model to train
            train_loader: Training data loader
            val_loader: Validation data loader
            learning_rate: Learning rate
            weight_decay: Weight decay
            device: Device to train on
            use_wandb: Whether to use Weights & Biases logging
            config: Configuration dictionary
        """
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.use_wandb = use_wandb
        self.config = config or {}
        
        # Optimizer
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        # Scheduler
        self.scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer,
            T_0=10,
            T_mult=2,
            eta_min=1e-6
        )
        
        # Loss functions
        self.mse_loss = nn.MSELoss()
        self.bce_loss = nn.BCELoss()
        self.mae_loss = nn.L1Loss()
        
        # Training state
        self.current_epoch = 0
        self.best_val_loss = float('inf')
        self.best_val_metrics = {}
        self.patience = 15
        self.patience_counter = 0
        
        # History
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_metrics': defaultdict(list),
            'val_metrics': defaultdict(list),
            'learning_rates': []
        }
        
        # Initialize wandb
        if use_wandb:
            wandb.init(project='mindguard-ai', config=config)
            wandb.watch(model)
        
        model_logger.info(f"Trainer initialized on device: {device}")
        model_logger.info(f"Model has {model.get_num_parameters():,} parameters")
    
    def train_epoch(self) -> Dict[str, float]:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        metrics = defaultdict(float)
        
        pbar = tqdm(self.train_loader, desc=f"Epoch {self.current_epoch}")
        for batch_idx, (inputs, targets) in enumerate(pbar):
            # Move to device
            inputs = {
                name: tensor.to(self.device)
                for name, tensor in inputs.items()
            }
            targets = {
                name: tensor.to(self.device)
                for name, tensor in targets.items()
            }
            
            # Forward pass
            outputs = self.model(inputs)
            
            # Compute losses
            fatigue_loss = self.mse_loss(outputs['fatigue'], targets['fatigue'])
            stress_loss = self.mse_loss(outputs['stress'], targets['stress'])
            attention_loss = self.mse_loss(outputs['attention'], targets['attention'])
            load_loss = self.mse_loss(outputs['cognitive_load'], targets['cognitive_load'])
            
            # Multi-task loss with uncertainty weighting
            loss = (
                fatigue_loss * torch.exp(-self.model.log_vars['fatigue']) +
                stress_loss * torch.exp(-self.model.log_vars['stress']) +
                attention_loss * torch.exp(-self.model.log_vars['attention']) +
                load_loss * torch.exp(-self.model.log_vars['cognitive_load']) +
                self.model.log_vars['fatigue'] +
                self.model.log_vars['stress'] +
                self.model.log_vars['attention'] +
                self.model.log_vars['cognitive_load']
            ) / 4.0
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            # Update metrics
            total_loss += loss.item()
            metrics['fatigue_mae'] += self.mae_loss(outputs['fatigue'], targets['fatigue']).item()
            metrics['stress_mae'] += self.mae_loss(outputs['stress'], targets['stress']).item()
            metrics['attention_mae'] += self.mae_loss(outputs['attention'], targets['attention']).item()
            metrics['load_mae'] += self.mae_loss(outputs['cognitive_load'], targets['cognitive_load']).item()
            
            # Update progress bar
            pbar.set_postfix({
                'loss': f"{loss.item():.4f}",
                'fatigue': f"{outputs['fatigue'].mean().item():.2f}"
            })
        
        # Average metrics
        n_batches = len(self.train_loader)
        avg_loss = total_loss / n_batches
        for key in metrics:
            metrics[key] /= n_batches
        
        return {'loss': avg_loss, **metrics}
    
    def validate(self) -> Dict[str, float]:
        """Validate the model."""
        if not self.val_loader:
            return {}
        
        self.model.eval()
        total_loss = 0.0
        metrics = defaultdict(float)
        
        with torch.no_grad():
            for inputs, targets in self.val_loader:
                inputs = {
                    name: tensor.to(self.device)
                    for name, tensor in inputs.items()
                }
                targets = {
                    name: tensor.to(self.device)
                    for name, tensor in targets.items()
                }
                
                outputs = self.model(inputs)
                
                # Compute losses
                fatigue_loss = self.mse_loss(outputs['fatigue'], targets['fatigue'])
                stress_loss = self.mse_loss(outputs['stress'], targets['stress'])
                attention_loss = self.mse_loss(outputs['attention'], targets['attention'])
                load_loss = self.mse_loss(outputs['cognitive_load'], targets['cognitive_load'])
                
                loss = (fatigue_loss + stress_loss + attention_loss + load_loss) / 4.0
                
                total_loss += loss.item()
                metrics['fatigue_mae'] += self.mae_loss(outputs['fatigue'], targets['fatigue']).item()
                metrics['stress_mae'] += self.mae_loss(outputs['stress'], targets['stress']).item()
                metrics['attention_mae'] += self.mae_loss(outputs['attention'], targets['attention']).item()
                metrics['load_mae'] += self.mae_loss(outputs['cognitive_load'], targets['cognitive_load']).item()
        
        n_batches = len(self.val_loader)
        avg_loss = total_loss / n_batches
        for key in metrics:
            metrics[key] /= n_batches
        
        return {'loss': avg_loss, **metrics}
    
    def train(self, num_epochs: int) -> Dict[str, List[float]]:
        """Train the model."""
        model_logger.info(f"Starting training for {num_epochs} epochs")
        
        for epoch in range(num_epochs):
            self.current_epoch = epoch
            
            # Train
            train_metrics = self.train_epoch()
            self.history['train_loss'].append(train_metrics['loss'])
            for key, value in train_metrics.items():
                if key != 'loss':
                    self.history['train_metrics'][key].append(value)
            
            # Validate
            val_metrics = self.validate()
            if val_metrics:
                self.history['val_loss'].append(val_metrics['loss'])
                for key, value in val_metrics.items():
                    if key != 'loss':
                        self.history['val_metrics'][key].append(value)
            
            # Learning rate
            current_lr = self.optimizer.param_groups[0]['lr']
            self.history['learning_rates'].append(current_lr)
            self.scheduler.step()
            
            # Log metrics
            log_msg = f"Epoch {epoch}: train_loss={train_metrics['loss']:.4f}"
            if val_metrics:
                log_msg += f", val_loss={val_metrics['loss']:.4f}"
            log_msg += f", lr={current_lr:.6f}"
            model_logger.info(log_msg)
            
            # Wandb logging
            if self.use_wandb:
                wandb_log = {
                    'train/loss': train_metrics['loss'],
                    'train/fatigue_mae': train_metrics.get('fatigue_mae', 0),
                    'train/stress_mae': train_metrics.get('stress_mae', 0),
                    'train/attention_mae': train_metrics.get('attention_mae', 0),
                    'train/load_mae': train_metrics.get('load_mae', 0),
                    'learning_rate': current_lr
                }
                if val_metrics:
                    wandb_log.update({
                        'val/loss': val_metrics['loss'],
                        'val/fatigue_mae': val_metrics.get('fatigue_mae', 0),
                        'val/stress_mae': val_metrics.get('stress_mae', 0),
                        'val/attention_mae': val_metrics.get('attention_mae', 0),
                        'val/load_mae': val_metrics.get('load_mae', 0)
                    })
                wandb.log(wandb_log)
            
            # Early stopping
            if val_metrics and val_metrics['loss'] < self.best_val_loss:
                self.best_val_loss = val_metrics['loss']
                self.best_val_metrics = val_metrics
                self.patience_counter = 0
                self.save_checkpoint('best_model.pt')
                model_logger.info(f"New best model saved with val_loss={val_metrics['loss']:.4f}")
            else:
                self.patience_counter += 1
                if self.patience_counter >= self.patience:
                    model_logger.info(f"Early stopping after {epoch} epochs")
                    break
            
            # Save checkpoint every 10 epochs
            if epoch % 10 == 0 and epoch > 0:
                self.save_checkpoint(f'checkpoint_epoch_{epoch}.pt')
        
        return self.history
    
    def save_checkpoint(self, filename: str) -> None:
        """Save model checkpoint."""
        checkpoint = {
            'epoch': self.current_epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_loss': self.best_val_loss,
            'best_val_metrics': self.best_val_metrics,
            'history': self.history,
            'config': self.config
        }
        
        # Create weights directory if it doesn't exist
        weights_dir = Path('models/weights')
        weights_dir.mkdir(parents=True, exist_ok=True)
        
        path = weights_dir / filename
        torch.save(checkpoint, path)
        model_logger.info(f"Checkpoint saved to {path}")
    
    def load_checkpoint(self, path: Path) -> None:
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.current_epoch = checkpoint['epoch']
        self.best_val_loss = checkpoint['best_val_loss']
        self.best_val_metrics = checkpoint.get('best_val_metrics', {})
        self.history = checkpoint['history']
        model_logger.info(f"Checkpoint loaded from {path}")


def main():
    """Main training function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train MindGuard AI model')
    parser.add_argument('--config', type=str, default='configs/training_config.yaml',
                        help='Path to training configuration')
    parser.add_argument('--data', type=str, default='data/processed/deap_processed.npy',
                        help='Path to training data')
    parser.add_argument('--wandb', action='store_true', help='Use Weights & Biases')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu',
                        help='Device to use')
    args = parser.parse_args()
    
    # Load configuration
    if Path(args.config).exists():
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {
            'batch_size': 32,
            'num_epochs': 100,
            'learning_rate': 1e-3,
            'weight_decay': 1e-4,
            'sequence_length': 30,
            'embed_dim': 64,
            'hidden_dim': 128,
            'num_heads': 4,
            'num_encoder_layers': 2,
            'num_attention_layers': 2,
            'dropout': 0.1,
            'use_attention': True
        }
    
    # Create dataset
    dataset = CognitiveDataset(
        data_path=Path(args.data),
        modality_names=['eye', 'keyboard', 'screen', 'voice'],
        sequence_length=config['sequence_length'],
        stride=5
    )
    
    # Split into train/val
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(
        dataset, [train_size, val_size]
    )
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        drop_last=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )
    
    # Create model
    model = CognitiveFusionModel(
        modality_dims=dataset.features_dims if hasattr(dataset, 'features_dims') else None,
        embed_dim=config['embed_dim'],
        hidden_dim=config['hidden_dim'],
        num_heads=config['num_heads'],
        num_encoder_layers=config['num_encoder_layers'],
        num_attention_layers=config['num_attention_layers'],
        dropout=config['dropout'],
        use_attention=config['use_attention']
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        learning_rate=config['learning_rate'],
        weight_decay=config['weight_decay'],
        device=args.device,
        use_wandb=args.wandb,
        config=config
    )
    
    # Train
    history = trainer.train(config['num_epochs'])
    
    # Save final model
    trainer.save_checkpoint('mindguard_final.pt')
    
    # Save training history
    with open('models/weights/training_history.json', 'w') as f:
        json.dump(history, f, indent=2)
    
    model_logger.info("Training completed!")
    
    if args.wandb:
        wandb.finish()


if __name__ == '__main__':
    main()