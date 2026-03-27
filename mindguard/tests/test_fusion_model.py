"""Tests for cognitive fusion model."""

import torch
import numpy as np
import pytest

from models.fusion_model import CognitiveFusionModel, ModelOutput


class TestCognitiveFusionModel:
    """Test suite for CognitiveFusionModel."""
    
    @pytest.fixture
    def model(self):
        """Create model instance for testing."""
        return CognitiveFusionModel()
    
    def test_initialization(self, model):
        """Test proper model initialization."""
        assert model.num_modalities == 4
        assert hasattr(model, 'encoders')
        assert hasattr(model, 'fatigue_head')
        assert hasattr(model, 'stress_head')
        assert model.get_num_parameters() > 0
    
    def test_forward_pass(self, model, sample_batch_features):
        """Test forward pass with dummy data."""
        batch_size = 4
        
        # Convert to tensors
        inputs = {
            name: torch.from_numpy(feat)
            for name, feat in sample_batch_features.items()
        }
        
        # Forward pass
        outputs = model(inputs)
        
        # Check outputs
        expected_keys = ['fatigue', 'stress', 'attention', 'cognitive_load', 
                        'confidence', 'fatigue_raw', 'stress_raw', 'attention_raw',
                        'cognitive_load_raw', 'fatigue_uncertainty', 'stress_uncertainty',
                        'attention_uncertainty', 'load_uncertainty']
        
        for key in expected_keys:
            assert key in outputs, f"Missing output: {key}"
        
        # Check shapes
        assert outputs['fatigue'].shape == (batch_size,)
        assert outputs['stress'].shape == (batch_size,)
        assert outputs['attention'].shape == (batch_size,)
        assert outputs['cognitive_load'].shape == (batch_size,)
        assert outputs['confidence'].shape == (batch_size,)
        
        # Check value ranges (should be between 0 and 1 due to sigmoid)
        assert torch.all(outputs['fatigue'] >= 0) and torch.all(outputs['fatigue'] <= 1)
        assert torch.all(outputs['stress'] >= 0) and torch.all(outputs['stress'] <= 1)
        assert torch.all(outputs['attention'] >= 0) and torch.all(outputs['attention'] <= 1)
        assert torch.all(outputs['cognitive_load'] >= 0) and torch.all(outputs['cognitive_load'] <= 1)
    
    def test_forward_with_missing_modalities(self, model):
        """Test forward pass with missing modalities."""
        batch_size = 2
        
        # Create inputs with missing voice
        inputs = {
            'eye': torch.randn(batch_size, 5),
            'keyboard': torch.randn(batch_size, 5),
            'screen': torch.randn(batch_size, 5)
            # voice missing
        }
        
        # Forward pass should still work
        outputs = model(inputs)
        
        assert 'fatigue' in outputs
        assert outputs['fatigue'].shape == (batch_size,)
    
    def test_forward_with_different_shapes(self, model):
        """Test forward pass with different input shapes."""
        batch_size = 2
        
        # Test with 1D inputs (no sequence)
        inputs_1d = {
            'eye': torch.randn(batch_size, 5),
            'keyboard': torch.randn(batch_size, 5),
            'screen': torch.randn(batch_size, 5),
            'voice': torch.randn(batch_size, 8)
        }
        
        outputs_1d = model(inputs_1d)
        assert outputs_1d['fatigue'].shape == (batch_size,)
        
        # Test with 2D inputs (with sequence)
        seq_len = 10
        inputs_2d = {
            'eye': torch.randn(batch_size, seq_len, 5),
            'keyboard': torch.randn(batch_size, seq_len, 5),
            'screen': torch.randn(batch_size, seq_len, 5),
            'voice': torch.randn(batch_size, seq_len, 8)
        }
        
        outputs_2d = model(inputs_2d)
        assert outputs_2d['fatigue'].shape == (batch_size,)
    
    def test_predict_method(self, model, sample_features):
        """Test predict method with numpy inputs."""
        # Make prediction
        output = model.predict(sample_features, device='cpu')
        
        # Check output type
        assert isinstance(output, ModelOutput)
        
        # Check value ranges
        assert 0 <= output.fatigue <= 1
        assert 0 <= output.stress <= 1
        assert 0 <= output.attention <= 1
        assert 0 <= output.cognitive_load <= 1
        assert 0 <= output.confidence <= 1
        
        # Check features preserved
        assert output.features is not None
        for name in sample_features:
            assert name in output.features
    
    def test_gradient_flow(self, model):
        """Test that gradients flow through all parameters."""
        batch_size = 2
        
        inputs = {
            'eye': torch.randn(batch_size, 5, requires_grad=True),
            'keyboard': torch.randn(batch_size, 5, requires_grad=True),
            'screen': torch.randn(batch_size, 5, requires_grad=True),
            'voice': torch.randn(batch_size, 8, requires_grad=True)
        }
        
        outputs = model(inputs)
        loss = outputs['fatigue'].sum() + outputs['stress'].sum()
        loss.backward()
        
        # Check that all parameters have gradients
        for name, param in model.named_parameters():
            assert param.grad is not None, f"Parameter {name} has no gradient"
    
    def test_model_save_load(self, model, tmp_path):
        """Test model saving and loading."""
        # Save model
        save_path = tmp_path / "model.pt"
        torch.save(model.state_dict(), save_path)
        
        # Load model
        new_model = CognitiveFusionModel(
            modality_dims=model.modality_dims,
            embed_dim=64,
            hidden_dim=128,
            num_heads=4,
            num_encoder_layers=2,
            num_attention_layers=2,
            dropout=0.1,
            use_attention=True
        )
        new_model.load_state_dict(torch.load(save_path))
        
        # Compare predictions
        inputs = {
            'eye': torch.randn(1, 5),
            'keyboard': torch.randn(1, 5),
            'screen': torch.randn(1, 5),
            'voice': torch.randn(1, 8)
        }
        
        with torch.no_grad():
            output1 = model(inputs)
            output2 = new_model(inputs)
        
        for key in ['fatigue', 'stress', 'attention', 'cognitive_load']:
            assert torch.allclose(output1[key], output2[key], rtol=1e-4)
    
    def test_embedding_extraction(self, model):
        """Test embedding extraction."""
        batch_size = 2
        
        inputs = {
            'eye': torch.randn(batch_size, 5),
            'keyboard': torch.randn(batch_size, 5),
            'screen': torch.randn(batch_size, 5),
            'voice': torch.randn(batch_size, 8)
        }
        
        embedding = model.get_embedding(inputs)
        
        # Check embedding shape
        assert embedding.shape == (batch_size, 64)  # hidden_dim // 2
    
    @pytest.mark.parametrize("batch_size", [1, 4, 8])
    def test_different_batch_sizes(self, model, batch_size):
        """Test model with different batch sizes."""
        inputs = {
            'eye': torch.randn(batch_size, 5),
            'keyboard': torch.randn(batch_size, 5),
            'screen': torch.randn(batch_size, 5),
            'voice': torch.randn(batch_size, 8)
        }
        
        outputs = model(inputs)
        
        assert outputs['fatigue'].shape == (batch_size,)
    
    def test_uncertainty_outputs(self, model):
        """Test uncertainty estimation outputs."""
        batch_size = 2
        
        inputs = {
            'eye': torch.randn(batch_size, 5),
            'keyboard': torch.randn(batch_size, 5),
            'screen': torch.randn(batch_size, 5),
            'voice': torch.randn(batch_size, 8)
        }
        
        outputs = model(inputs)
        
        # Check uncertainty outputs
        assert 'fatigue_uncertainty' in outputs
        assert 'stress_uncertainty' in outputs
        assert 'attention_uncertainty' in outputs
        assert 'load_uncertainty' in outputs
        
        # Uncertainties should be positive
        assert torch.all(outputs['fatigue_uncertainty'] >= 0)
        assert torch.all(outputs['stress_uncertainty'] >= 0)
    
    def test_modality_names(self, model):
        """Test modality name retrieval."""
        names = model.get_modality_names()
        assert len(names) == 4
        assert 'eye' in names
        assert 'keyboard' in names
        assert 'screen' in names
        assert 'voice' in names


class TestModelOutput:
    """Test suite for ModelOutput dataclass."""
    
    def test_creation(self, mock_model_output):
        """Test ModelOutput creation."""
        output = mock_model_output
        assert output.fatigue == 0.65
        assert output.stress == 0.45
        assert output.attention == 0.72
        assert output.cognitive_load == 0.58
        assert output.confidence == 0.88
    
    def test_to_dict(self, mock_model_output):
        """Test conversion to dictionary."""
        output = mock_model_output
        d = output.to_dict()
        
        assert isinstance(d, dict)
        assert d['fatigue'] == 0.65
        assert d['stress'] == 0.45
        assert d['attention'] == 0.72
        assert d['cognitive_load'] == 0.58
        assert d['confidence'] == 0.88
    
    def test_to_array(self, mock_model_output):
        """Test conversion to numpy array."""
        output = mock_model_output
        arr = output.to_array()
        
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (5,)
        assert arr[0] == 0.65
        assert arr[1] == 0.45
        assert arr[2] == 0.72
        assert arr[3] == 0.58
        assert arr[4] == 0.88