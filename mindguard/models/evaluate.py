"""Evaluation module for cognitive fusion model."""

import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    confusion_matrix,
    classification_report
)
import pandas as pd

from models.fusion_model import CognitiveFusionModel
from models.train import CognitiveDataset
from config.logging_config import model_logger


class Evaluator:
    """Evaluation module for cognitive models."""
    
    def __init__(
        self,
        model: nn.Module,
        test_loader: DataLoader,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    ):
        """
        Initialize evaluator.
        
        Args:
            model: Model to evaluate
            test_loader: Test data loader
            device: Device to run evaluation on
        """
        self.model = model.to(device)
        self.test_loader = test_loader
        self.device = device
        self.model.eval()
        
    def evaluate(self) -> Dict[str, float]:
        """Evaluate model on test set."""
        total_loss = 0.0
        all_predictions = defaultdict(list)
        all_targets = defaultdict(list)
        
        mse_loss = nn.MSELoss()
        mae_loss = nn.L1Loss()
        
        with torch.no_grad():
            for inputs, targets in self.test_loader:
                inputs = {
                    name: tensor.to(self.device)
                    for name, tensor in inputs.items()
                }
                targets = {
                    name: tensor.to(self.device)
                    for name, tensor in targets.items()
                }
                
                outputs = self.model(inputs)
                
                # Store predictions and targets
                for key in ['fatigue', 'stress', 'attention', 'cognitive_load']:
                    all_predictions[key].extend(outputs[key].cpu().numpy())
                    all_targets[key].extend(targets[key].cpu().numpy())
        
        # Calculate metrics
        metrics = {}
        for key in ['fatigue', 'stress', 'attention', 'cognitive_load']:
            y_true = np.array(all_targets[key])
            y_pred = np.array(all_predictions[key])
            
            metrics[f'{key}_mae'] = mean_absolute_error(y_true, y_pred)
            metrics[f'{key}_rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
            metrics[f'{key}_r2'] = r2_score(y_true, y_pred)
            
            # Mean Absolute Percentage Error
            mask = y_true > 0
            if mask.any():
                mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
                metrics[f'{key}_mape'] = mape
            
            # Accuracy within thresholds
            for threshold in [0.05, 0.1, 0.15]:
                acc = np.mean(np.abs(y_true - y_pred) <= threshold)
                metrics[f'{key}_acc_{int(threshold*100)}'] = acc
        
        # Overall metrics
        all_true = np.concatenate([all_targets[k] for k in ['fatigue', 'stress', 'attention', 'cognitive_load']])
        all_pred = np.concatenate([all_predictions[k] for k in ['fatigue', 'stress', 'attention', 'cognitive_load']])
        
        metrics['overall_mae'] = mean_absolute_error(all_true, all_pred)
        metrics['overall_rmse'] = np.sqrt(mean_squared_error(all_true, all_pred))
        metrics['overall_r2'] = r2_score(all_true, all_pred)
        
        return metrics, all_predictions, all_targets
    
    def evaluate_by_demographics(
        self,
        demographics: List[Dict]
    ) -> Dict[str, Dict[str, float]]:
        """
        Evaluate model performance by demographic groups.
        
        Args:
            demographics: List of demographic info for each sample
            
        Returns:
            Dictionary of metrics by group
        """
        # Group predictions by demographic categories
        groups = defaultdict(lambda: defaultdict(list))
        
        with torch.no_grad():
            for i, (inputs, targets) in enumerate(self.test_loader):
                inputs = {
                    name: tensor.to(self.device)
                    for name, tensor in inputs.items()
                }
                targets = {
                    name: tensor.to(self.device)
                    for name, tensor in targets.items()
                }
                
                outputs = self.model(inputs)
                
                # Get demographic for this batch
                batch_demo = demographics[i * len(inputs):(i + 1) * len(inputs)]
                
                for j, demo in enumerate(batch_demo):
                    for key in ['fatigue', 'stress', 'attention', 'cognitive_load']:
                        groups[demo.get('age_group', 'unknown')][f'{key}_pred'].append(
                            outputs[key][j].item()
                        )
                        groups[demo.get('age_group', 'unknown')][f'{key}_true'].append(
                            targets[key][j].item()
                        )
        
        # Calculate metrics per group
        group_metrics = {}
        for group, data in groups.items():
            metrics = {}
            for key in ['fatigue', 'stress', 'attention', 'cognitive_load']:
                y_true = np.array(data[f'{key}_true'])
                y_pred = np.array(data[f'{key}_pred'])
                
                if len(y_true) > 0:
                    metrics[f'{key}_mae'] = mean_absolute_error(y_true, y_pred)
                    metrics[f'{key}_rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
                    metrics[f'{key}_r2'] = r2_score(y_true, y_pred)
            
            group_metrics[group] = metrics
        
        return group_metrics
    
    def plot_predictions(
        self,
        all_predictions: Dict[str, List],
        all_targets: Dict[str, List],
        save_path: Optional[Path] = None
    ):
        """Plot prediction vs actual scatter plots."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        metrics = ['fatigue', 'stress', 'attention', 'cognitive_load']
        titles = ['Fatigue', 'Stress', 'Attention', 'Cognitive Load']
        
        for i, (metric, title) in enumerate(zip(metrics, titles)):
            ax = axes[i]
            
            y_true = np.array(all_targets[metric])
            y_pred = np.array(all_predictions[metric])
            
            # Scatter plot
            ax.scatter(y_true, y_pred, alpha=0.5, s=10)
            
            # Perfect prediction line
            min_val = min(y_true.min(), y_pred.min())
            max_val = max(y_true.max(), y_pred.max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='Perfect')
            
            # ±10% lines
            ax.plot([min_val, max_val], [min_val + 0.1, max_val + 0.1], 'g--', alpha=0.3)
            ax.plot([min_val, max_val], [min_val - 0.1, max_val - 0.1], 'g--', alpha=0.3)
            
            ax.set_xlabel('True')
            ax.set_ylabel('Predicted')
            ax.set_title(f'{title} Predictions')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path / 'predictions_scatter.png', dpi=150, bbox_inches='tight')
        plt.show()
    
    def plot_error_distribution(
        self,
        all_predictions: Dict[str, List],
        all_targets: Dict[str, List],
        save_path: Optional[Path] = None
    ):
        """Plot error distributions."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        metrics = ['fatigue', 'stress', 'attention', 'cognitive_load']
        titles = ['Fatigue', 'Stress', 'Attention', 'Cognitive Load']
        
        for i, (metric, title) in enumerate(zip(metrics, titles)):
            ax = axes[i]
            
            y_true = np.array(all_targets[metric])
            y_pred = np.array(all_predictions[metric])
            
            errors = y_pred - y_true
            
            ax.hist(errors, bins=50, alpha=0.7, edgecolor='black')
            ax.axvline(x=0, color='r', linestyle='--', label='Zero error')
            ax.axvline(x=errors.mean(), color='g', linestyle='--', label=f'Mean: {errors.mean():.3f}')
            
            ax.set_xlabel('Prediction Error')
            ax.set_ylabel('Frequency')
            ax.set_title(f'{title} Error Distribution')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path / 'error_distribution.png', dpi=150, bbox_inches='tight')
        plt.show()
    
    def plot_confusion_matrix(
        self,
        all_predictions: Dict[str, List],
        all_targets: Dict[str, List],
        thresholds: List[float] = [0.3, 0.6],
        save_path: Optional[Path] = None
    ):
        """Plot confusion matrices for binary classification."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        metrics = ['fatigue', 'stress', 'attention', 'cognitive_load']
        titles = ['Fatigue', 'Stress', 'Attention', 'Cognitive Load']
        
        for i, (metric, title) in enumerate(zip(metrics, titles)):
            ax = axes[i]
            
            y_true = np.array(all_targets[metric])
            y_pred = np.array(all_predictions[metric])
            
            # Convert to binary classes based on thresholds
            y_true_class = np.digitize(y_true, thresholds)
            y_pred_class = np.digitize(y_pred, thresholds)
            
            cm = confusion_matrix(y_true_class, y_pred_class)
            
            sns.heatmap(cm, annot=True, fmt='d', ax=ax, cmap='Blues')
            ax.set_xlabel('Predicted')
            ax.set_ylabel('True')
            ax.set_title(f'{title} Confusion Matrix')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path / 'confusion_matrices.png', dpi=150, bbox_inches='tight')
        plt.show()
    
    def generate_report(
        self,
        save_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive evaluation report."""
        model_logger.info("Generating evaluation report...")
        
        # Evaluate
        metrics, predictions, targets = self.evaluate()
        
        # Create report
        report = {
            'metrics': metrics,
            'summary': {
                'total_samples': len(self.test_loader.dataset),
                'device': self.device,
                'model_params': self.model.get_num_parameters()
            }
        }
        
        # Add classification metrics for threshold-based categories
        for threshold in [0.3, 0.5, 0.7]:
            for metric in ['fatigue', 'stress', 'attention', 'cognitive_load']:
                y_true = np.array(targets[metric])
                y_pred = np.array(predictions[metric])
                
                y_true_bin = (y_true >= threshold).astype(int)
                y_pred_bin = (y_pred >= threshold).astype(int)
                
                if len(np.unique(y_true_bin)) > 1:
                    report[f'{metric}_classification_{int(threshold*100)}'] = {
                        'accuracy': np.mean(y_true_bin == y_pred_bin),
                        'precision': self._precision(y_true_bin, y_pred_bin),
                        'recall': self._recall(y_true_bin, y_pred_bin),
                        'f1': self._f1(y_true_bin, y_pred_bin)
                    }
        
        # Save report
        if save_path:
            save_path.mkdir(parents=True, exist_ok=True)
            
            with open(save_path / 'evaluation_report.json', 'w') as f:
                json.dump(report, f, indent=2)
            
            # Generate plots
            self.plot_predictions(predictions, targets, save_path)
            self.plot_error_distribution(predictions, targets, save_path)
            self.plot_confusion_matrix(predictions, targets, save_path)
            
            model_logger.info(f"Report saved to {save_path}")
        
        # Print summary
        self._print_summary(metrics)
        
        return report
    
    def _precision(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate precision."""
        true_pos = np.sum((y_pred == 1) & (y_true == 1))
        false_pos = np.sum((y_pred == 1) & (y_true == 0))
        return true_pos / (true_pos + false_pos + 1e-8)
    
    def _recall(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate recall."""
        true_pos = np.sum((y_pred == 1) & (y_true == 1))
        false_neg = np.sum((y_pred == 0) & (y_true == 1))
        return true_pos / (true_pos + false_neg + 1e-8)
    
    def _f1(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate F1 score."""
        prec = self._precision(y_true, y_pred)
        rec = self._recall(y_true, y_pred)
        return 2 * (prec * rec) / (prec + rec + 1e-8)
    
    def _print_summary(self, metrics: Dict[str, float]):
        """Print evaluation summary."""
        print("\n" + "="*50)
        print("EVALUATION SUMMARY")
        print("="*50)
        
        for metric in ['fatigue', 'stress', 'attention', 'cognitive_load']:
            print(f"\n{metric.upper()}:")
            print(f"  MAE:  {metrics[f'{metric}_mae']:.4f}")
            print(f"  RMSE: {metrics[f'{metric}_rmse']:.4f}")
            print(f"  R²:   {metrics[f'{metric}_r2']:.4f}")
            if f'{metric}_mape' in metrics:
                print(f"  MAPE: {metrics[f'{metric}_mape']:.2f}%")
        
        print(f"\nOVERALL:")
        print(f"  MAE:  {metrics['overall_mae']:.4f}")
        print(f"  RMSE: {metrics['overall_rmse']:.4f}")
        print(f"  R²:   {metrics['overall_r2']:.4f}")
        print("="*50)


def main():
    """Main evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Evaluate MindGuard AI model')
    parser.add_argument('--model', type=str, required=True,
                        help='Path to model checkpoint')
    parser.add_argument('--data', type=str, required=True,
                        help='Path to test data')
    parser.add_argument('--output', type=str, default='evaluation_results',
                        help='Output directory for results')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size for evaluation')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu',
                        help='Device to use')
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    dataset = CognitiveDataset(
        data_path=Path(args.data),
        modality_names=['eye', 'keyboard', 'screen', 'voice'],
        sequence_length=30,
        stride=30,  # Non-overlapping for test
        normalize=True
    )
    
    # Create data loader
    test_loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=4
    )
    
    # Load model
    checkpoint = torch.load(args.model, map_location=args.device)
    
    model = CognitiveFusionModel(
        modality_dims=dataset.features_dims if hasattr(dataset, 'features_dims') else None,
        embed_dim=checkpoint.get('config', {}).get('embed_dim', 64),
        hidden_dim=checkpoint.get('config', {}).get('hidden_dim', 128),
        num_heads=checkpoint.get('config', {}).get('num_heads', 4),
        num_encoder_layers=checkpoint.get('config', {}).get('num_encoder_layers', 2),
        num_attention_layers=checkpoint.get('config', {}).get('num_attention_layers', 2),
        dropout=checkpoint.get('config', {}).get('dropout', 0.1),
        use_attention=checkpoint.get('config', {}).get('use_attention', True)
    )
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model_logger.info(f"Model loaded from {args.model}")
    
    # Evaluate
    evaluator = Evaluator(model, test_loader, device=args.device)
    report = evaluator.generate_report(save_path=output_dir)
    
    model_logger.info(f"Evaluation complete. Results saved to {output_dir}")


if __name__ == '__main__':
    from collections import defaultdict
    main()