"""Export PyTorch model to ONNX format."""

import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Any
import argparse

from models.fusion_model import CognitiveFusionModel
from config.logging_config import model_logger


def export_to_onnx(
    model: nn.Module,
    output_path: Path,
    modality_dims: Dict[str, int],
    batch_size: int = 1,
    sequence_length: int = 30,
    device: str = 'cpu',
    dynamic_axes: bool = True,
    opset_version: int = 14,
    verbose: bool = False
):
    """
    Export PyTorch model to ONNX format.
    
    Args:
        model: PyTorch model to export
        output_path: Path to save ONNX model
        modality_dims: Dictionary of modality input dimensions
        batch_size: Batch size for dummy input
        sequence_length: Sequence length for dummy input
        device: Device to run export on
        dynamic_axes: Whether to use dynamic axes for variable batch/sequence
        opset_version: ONNX opset version
        verbose: Whether to print verbose output
    """
    model.eval()
    model.to(device)
    
    # Create dummy inputs
    dummy_inputs = {}
    input_names = []
    
    for name, dim in modality_dims.items():
        # Create dummy input [batch, seq_len, features]
        dummy = torch.randn(batch_size, sequence_length, dim).to(device)
        dummy_inputs[name] = dummy
        input_names.append(name)
    
    # Define output names
    output_names = [
        'fatigue',
        'stress',
        'attention',
        'cognitive_load',
        'confidence',
        'fatigue_raw',
        'stress_raw',
        'attention_raw',
        'cognitive_load_raw'
    ]
    
    # Define dynamic axes
    dynamic_axes_dict = {}
    if dynamic_axes:
        for name in input_names:
            dynamic_axes_dict[name] = {
                0: 'batch_size',
                1: 'sequence_length'
            }
        for name in output_names:
            dynamic_axes_dict[name] = {0: 'batch_size'}
    
    # Export to ONNX
    try:
        torch.onnx.export(
            model,
            tuple(dummy_inputs.values()),
            output_path,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes=dynamic_axes_dict if dynamic_axes else None,
            opset_version=opset_version,
            do_constant_folding=True,
            verbose=verbose,
            export_params=True,
            keep_initializers_as_inputs=False
        )
        
        model_logger.info(f"Model exported to ONNX: {output_path}")
        
        # Verify the exported model
        import onnx
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)
        model_logger.info("ONNX model verification passed")
        
        # Print model info
        if verbose:
            print("\nONNX Model Info:")
            print(f"  Inputs: {[inp.name for inp in onnx_model.graph.input]}")
            print(f"  Outputs: {[out.name for out in onnx_model.graph.output]}")
            print(f"  Parameters: {sum(p.dims.num_elements() for p in onnx_model.graph.initializer)}")
        
    except Exception as e:
        model_logger.error(f"ONNX export failed: {e}")
        raise


def optimize_onnx_model(
    input_path: Path,
    output_path: Optional[Path] = None
):
    """
    Optimize ONNX model for inference.
    
    Args:
        input_path: Path to input ONNX model
        output_path: Path to save optimized model
    """
    try:
        import onnx
        from onnxruntime.transformers import optimizer
        
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_optimized.onnx"
        
        # Load model
        model = onnx.load(input_path)
        
        # Optimize for transformer
        opt_options = optimizer.OptimizationOptions()
        opt_options.enable_gelu = True
        opt_options.enable_layer_norm = True
        opt_options.enable_attention = True
        opt_options.enable_skip_layer_norm = True
        opt_options.enable_embed_layer_norm = True
        opt_options.enable_bias_skip_layer_norm = True
        opt_options.enable_bias_gelu = True
        
        # Run optimization
        opt_model = optimizer.optimize_model(
            str(input_path),
            'cpu',
            num_heads=4,
            hidden_size=64,
            optimization_options=opt_options
        )
        
        # Save optimized model
        opt_model.save_model_to_file(str(output_path))
        
        model_logger.info(f"Optimized model saved to: {output_path}")
        
        # Compare sizes
        orig_size = input_path.stat().st_size / 1024 / 1024
        opt_size = output_path.stat().st_size / 1024 / 1024
        print(f"Original size: {orig_size:.2f} MB")
        print(f"Optimized size: {opt_size:.2f} MB")
        print(f"Size reduction: {(1 - opt_size/orig_size)*100:.1f}%")
        
    except ImportError:
        model_logger.warning("ONNX Runtime Transformers not available for optimization")
    except Exception as e:
        model_logger.error(f"ONNX optimization failed: {e}")


def test_onnx_model(
    onnx_path: Path,
    pytorch_model: Optional[nn.Module] = None,
    modality_dims: Optional[Dict[str, int]] = None,
    num_tests: int = 10
):
    """
    Test ONNX model against PyTorch model.
    
    Args:
        onnx_path: Path to ONNX model
        pytorch_model: Original PyTorch model for comparison
        modality_dims: Modality dimensions
        num_tests: Number of test runs
    """
    try:
        import onnxruntime as ort
        
        # Create ONNX session
        session = ort.InferenceSession(str(onnx_path))
        
        # Get input details
        input_details = {inp.name: inp for inp in session.get_inputs()}
        
        # Run tests
        all_close = True
        max_diff = 0.0
        
        for i in range(num_tests):
            # Create random input
            ort_inputs = {}
            pytorch_inputs = {}
            
            for name, inp in input_details.items():
                # Get shape from input details
                shape = inp.shape
                if any(d == 'batch_size' for d in shape):
                    batch_size = np.random.randint(1, 4)
                    shape = [batch_size if d == 'batch_size' else d for d in shape]
                if any(d == 'sequence_length' for d in shape):
                    seq_len = np.random.randint(10, 31)
                    shape = [seq_len if d == 'sequence_length' else d for d in shape]
                
                # Convert to ints
                shape = [int(d) if isinstance(d, (int, str)) else d for d in shape]
                
                # Create random data
                data = np.random.randn(*shape).astype(np.float32)
                ort_inputs[name] = data
                
                if pytorch_model:
                    pytorch_inputs[name] = torch.from_numpy(data)
            
            # Run ONNX inference
            ort_outputs = session.run(None, ort_inputs)
            
            if pytorch_model:
                # Run PyTorch inference
                with torch.no_grad():
                    pytorch_outputs = pytorch_model(pytorch_inputs)
                
                # Compare outputs
                for j, out_name in enumerate(['fatigue', 'stress', 'attention', 'cognitive_load', 'confidence']):
                    onnx_out = ort_outputs[j]
                    torch_out = pytorch_outputs[out_name].cpu().numpy()
                    
                    diff = np.abs(onnx_out - torch_out).max()
                    max_diff = max(max_diff, diff)
                    
                    if not np.allclose(onnx_out, torch_out, rtol=1e-3, atol=1e-3):
                        all_close = False
                        print(f"Output mismatch for {out_name}: max diff={diff:.6f}")
        
        if all_close:
            model_logger.info(f"ONNX model test passed! Max difference: {max_diff:.6f}")
        else:
            model_logger.warning(f"ONNX model test failed! Max difference: {max_diff:.6f}")
        
    except Exception as e:
        model_logger.error(f"ONNX test failed: {e}")


def main():
    """Main export function."""
    parser = argparse.ArgumentParser(description='Export MindGuard AI model to ONNX')
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to PyTorch checkpoint')
    parser.add_argument('--output', type=str, default='models/weights/mindguard.onnx',
                        help='Output path for ONNX model')
    parser.add_argument('--batch_size', type=int, default=1,
                        help='Batch size for dummy input')
    parser.add_argument('--sequence_length', type=int, default=30,
                        help='Sequence length for dummy input')
    parser.add_argument('--opset', type=int, default=14,
                        help='ONNX opset version')
    parser.add_argument('--optimize', action='store_true',
                        help='Optimize ONNX model after export')
    parser.add_argument('--test', action='store_true',
                        help='Test ONNX model against PyTorch')
    parser.add_argument('--device', type=str, default='cpu',
                        help='Device to use')
    parser.add_argument('--verbose', action='store_true',
                        help='Print verbose output')
    
    args = parser.parse_args()
    
    # Define modality dimensions
    modality_dims = {
        'eye': 5,
        'keyboard': 5,
        'screen': 5,
        'voice': 8
    }
    
    # Load PyTorch model
    checkpoint = torch.load(args.checkpoint, map_location=args.device)
    
    model = CognitiveFusionModel(
        modality_dims=modality_dims,
        embed_dim=checkpoint.get('config', {}).get('embed_dim', 64),
        hidden_dim=checkpoint.get('config', {}).get('hidden_dim', 128),
        num_heads=checkpoint.get('config', {}).get('num_heads', 4),
        num_encoder_layers=checkpoint.get('config', {}).get('num_encoder_layers', 2),
        num_attention_layers=checkpoint.get('config', {}).get('num_attention_layers', 2),
        dropout=checkpoint.get('config', {}).get('dropout', 0.1),
        use_attention=checkpoint.get('config', {}).get('use_attention', True)
    )
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model_logger.info(f"Model loaded from {args.checkpoint}")
    
    # Export to ONNX
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    export_to_onnx(
        model=model,
        output_path=output_path,
        modality_dims=modality_dims,
        batch_size=args.batch_size,
        sequence_length=args.sequence_length,
        device=args.device,
        opset_version=args.opset,
        verbose=args.verbose
    )
    
    # Optimize if requested
    if args.optimize:
        optimize_onnx_model(output_path)
    
    # Test if requested
    if args.test:
        test_onnx_model(
            output_path,
            pytorch_model=model if args.test else None,
            modality_dims=modality_dims
        )


if __name__ == '__main__':
    main()