"""Tests for voice analyzer collector."""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from collectors.voice_analyzer import VoiceAnalyzer
from collectors.base_collector import DataPoint


class TestVoiceAnalyzer:
    """Test suite for VoiceAnalyzer."""
    
    @pytest.fixture
    def voice_analyzer(self):
        """Create voice analyzer instance for testing."""
        with patch('collectors.voice_analyzer.AUDIO_AVAILABLE', True):
            with patch('sounddevice.rec'), patch('sounddevice.wait'):
                analyzer = VoiceAnalyzer(sample_rate=16000, chunk_duration=2.0)
                return analyzer
    
    def test_initialization(self, voice_analyzer):
        """Test proper initialization."""
        assert voice_analyzer.name == "voice_analyzer"
        assert voice_analyzer.sample_rate == 16000
        assert voice_analyzer.chunk_duration == 2.0
        assert voice_analyzer.pitch_mean == 0.0
        assert voice_analyzer.energy == 0.0
        assert voice_analyzer.is_speaking == False
    
    def test_validate_sample(self, voice_analyzer):
        """Test sample validation."""
        # Valid sample
        valid_sample = DataPoint(
            timestamp=datetime.now(),
            source="voice",
            data={
                "pitch_mean": 120.0,
                "pitch_std": 15.0,
                "energy": 0.05,
                "zero_crossing_rate": 0.15,
                "mfcc_1": -0.5,
                "mfcc_2": 0.3,
                "mfcc_3": -0.2,
                "speech_rate": 3.5,
                "is_speaking": True,
                "spectral_centroid": 850.0
            }
        )
        assert voice_analyzer.validate_sample(valid_sample) == True
        
        # Invalid sample (missing required field)
        invalid_sample = DataPoint(
            timestamp=datetime.now(),
            source="voice",
            data={
                "pitch_mean": 120.0,
                "energy": 0.05
                # missing is_speaking
            }
        )
        assert voice_analyzer.validate_sample(invalid_sample) == False
    
    def test_extract_features_speech(self, voice_analyzer):
        """Test feature extraction with speech."""
        # Create mock audio with speech-like characteristics
        duration = 2.0
        sample_rate = 16000
        t = np.linspace(0, duration, int(duration * sample_rate))
        
        # Create a signal with varying pitch (simulated speech)
        audio = np.sin(2 * np.pi * 120 * t) * 0.1  # 120 Hz tone
        audio += np.random.normal(0, 0.01, len(t))  # Add noise
        
        with patch('librosa.piptrack') as mock_piptrack:
            mock_piptrack.return_value = (
                np.array([[120.0]]),  # pitches
                np.array([[1.0]])      # magnitudes
            )
            
            with patch('librosa.feature.zero_crossing_rate', return_value=np.array([[0.15]])):
                with patch('librosa.feature.mfcc', return_value=np.random.randn(13, 100)):
                    with patch('librosa.feature.spectral_centroid', return_value=np.array([[850.0]])):
                        features = voice_analyzer._extract_features(audio)
                        
                        assert features is not None
                        assert features["pitch_mean"] > 0
                        assert features["energy"] > 0
                        assert "is_speaking" in features
    
    def test_extract_features_silence(self, voice_analyzer):
        """Test feature extraction with silence."""
        # Create silence
        audio = np.zeros(voice_analyzer.chunk_samples)
        
        features = voice_analyzer._extract_features(audio)
        
        assert features is not None
        assert features["energy"] < 0.001
        assert features["is_speaking"] == False
    
    def test_speech_detection(self, voice_analyzer):
        """Test speech detection."""
        voice_analyzer.speech_threshold = 0.01
        
        # Above threshold - speaking
        energy_high = 0.05
        is_speaking = voice_analyzer._detect_speech(energy_high)
        assert is_speaking == True
        
        # Below threshold - not speaking
        energy_low = 0.001
        is_speaking = voice_analyzer._detect_speech(energy_low)
        assert is_speaking == False
    
    def _detect_speech(self, energy):
        """Helper for speech detection."""
        return energy > self.speech_threshold
    
    def test_calibration(self, voice_analyzer):
        """Test calibration process."""
        with patch('sounddevice.rec') as mock_rec:
            with patch('sounddevice.wait'):
                # Mock recording returns
                mock_rec.return_value = np.random.randn(voice_analyzer.sample_rate)
                
                with patch('time.sleep', return_value=None):
                    result = voice_analyzer.calibrate()
                    
                    assert isinstance(result, bool)
    
    def test_start_stop(self, voice_analyzer):
        """Test start and stop methods."""
        voice_analyzer.start()
        assert voice_analyzer.is_running == True
        assert voice_analyzer.recording == True
        assert voice_analyzer.audio_thread is not None
        
        voice_analyzer.stop()
        assert voice_analyzer.is_running == False
        assert voice_analyzer.recording == False
    
    def test_collect_sample(self, voice_analyzer):
        """Test sample collection."""
        # Add audio to buffer
        test_audio = np.random.randn(voice_analyzer.chunk_samples)
        voice_analyzer.audio_buffer.put(test_audio)
        
        with patch.object(voice_analyzer, '_extract_features') as mock_extract:
            mock_extract.return_value = {
                "pitch_mean": 120.0,
                "pitch_std": 15.0,
                "energy": 0.05,
                "zero_crossing_rate": 0.15,
                "mfcc_1": -0.5,
                "mfcc_2": 0.3,
                "mfcc_3": -0.2,
                "speech_rate": 3.5,
                "is_speaking": True,
                "spectral_centroid": 850.0
            }
            
            sample = voice_analyzer._collect_sample()
            
            assert sample is not None
            assert sample.source == "voice"
            assert sample.data["pitch_mean"] == 120.0
    
    def test_audio_capture_loop(self, voice_analyzer):
        """Test audio capture loop."""
        voice_analyzer.recording = True
        
        with patch('sounddevice.rec') as mock_rec:
            mock_rec.return_value = np.random.randn(voice_analyzer.chunk_samples)
            
            with patch('sounddevice.wait'):
                # Run one iteration
                voice_analyzer._audio_capture_iteration()
                
                assert voice_analyzer.audio_buffer.qsize() == 1
    
    def _audio_capture_iteration(self):
        """Helper for single audio capture iteration."""
        try:
            recording = np.random.randn(self.chunk_samples)
            self.audio_buffer.put(recording)
        except Exception as e:
            pass
    
    def test_pitch_tracking(self, voice_analyzer):
        """Test pitch tracking."""
        # Simulate pitch tracking over time
        pitches = [110, 120, 130, 125, 115]
        
        for pitch in pitches:
            voice_analyzer.pitch_history.append(pitch)
        
        assert len(voice_analyzer.pitch_history) == 5
        assert np.mean(voice_analyzer.pitch_history) == 120.0
    
    def test_speech_rate_calculation(self, voice_analyzer):
        """Test speech rate calculation."""
        current_time = time.time()
        
        # Simulate speech segments
        voice_analyzer.speech_segments = [
            current_time - 10,
            current_time - 8,
            current_time - 6,
            current_time - 4,
            current_time - 2
        ]
        
        voice_analyzer._calculate_speech_rate()
        
        # Should be about 0.5 segments per second (5 segments over 10 seconds)
        assert voice_analyzer.speech_rate == 0.5
    
    def _calculate_speech_rate(self):
        """Helper to calculate speech rate."""
        if len(self.speech_segments) > 1:
            recent_segments = self.speech_segments[-10:]
            if len(recent_segments) > 1:
                time_span = recent_segments[-1] - recent_segments[0]
                if time_span > 0:
                    self.speech_rate = len(recent_segments) / time_span
    
    def test_get_statistics(self, voice_analyzer):
        """Test statistics retrieval."""
        voice_analyzer.samples_collected = 100
        voice_analyzer.errors = 2
        voice_analyzer.pitch_history = [110, 120, 130]
        voice_analyzer.energy_history = [0.01, 0.02, 0.03]
        
        stats = voice_analyzer.get_statistics()
        
        assert stats["name"] == "voice_analyzer"
        assert stats["samples_collected"] == 100
        assert "avg_pitch" in stats
        assert "avg_energy" in stats
        assert "speaking_percentage" in stats
    
    def test_error_handling(self, voice_analyzer):
        """Test error handling in feature extraction."""
        # Cause an error in feature extraction
        with patch('librosa.piptrack', side_effect=Exception("Test error")):
            features = voice_analyzer._extract_features(np.random.randn(100))
            
            # Should return default values
            assert features is not None
            assert features["pitch_mean"] == 0.0
            assert features["energy"] == 0.0