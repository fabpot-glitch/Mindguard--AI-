"""Voice analysis collector for stress detection."""

import time
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading
import queue

try:
    import sounddevice as sd
    import librosa
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Warning: Audio libraries not available. Voice analyzer will be disabled.")

from collectors.base_collector import BaseCollector, DataPoint
from config.logging_config import collector_logger


class VoiceAnalyzer(BaseCollector):
    """Voice analysis collector for stress and emotion detection."""
    
    def __init__(self, sample_rate: int = 16000, chunk_duration: float = 2.0):
        """
        Initialize voice analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz
            chunk_duration: Duration of audio chunks to analyze (seconds)
        """
        super().__init__("voice_analyzer", sampling_rate=1.0 / chunk_duration)
        
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_samples = int(sample_rate * chunk_duration)
        
        # Audio buffer
        self.audio_buffer: queue.Queue = queue.Queue()
        self.recording = False
        self.audio_thread: Optional[threading.Thread] = None
        
        # Features
        self.pitch_mean: float = 0.0
        self.pitch_std: float = 0.0
        self.energy: float = 0.0
        self.zero_crossing_rate: float = 0.0
        self.mfccs: List[float] = [0.0] * 13
        self.speech_rate: float = 0.0
        self.is_speaking: bool = False
        
        # History
        self.pitch_history: List[float] = []
        self.energy_history: List[float] = []
        self.speech_segments: List[float] = []
        
        # Thresholds
        self.speech_threshold = 0.01  # Energy threshold for speech detection
        self.silence_duration = 0.5  # Seconds of silence to consider end of speech
        
        self.logger.info(f"VoiceAnalyzer initialized at {sample_rate}Hz")
    
    def calibrate(self) -> bool:
        """
        Calibrate voice analyzer.
        
        Returns:
            True if calibration successful
        """
        if not AUDIO_AVAILABLE:
            self.logger.warning("Audio libraries not available, skipping calibration")
            return False
        
        self.logger.info("Starting voice analyzer calibration")
        self.logger.info("Please remain silent for 5 seconds to measure background noise...")
        
        # Measure background noise
        noise_energies = []
        for _ in range(5):
            try:
                recording = sd.rec(int(self.sample_rate), samplerate=self.sample_rate,
                                  channels=1, dtype='float32')
                sd.wait()
                energy = np.mean(recording ** 2)
                noise_energies.append(energy)
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Calibration error: {e}")
        
        if noise_energies:
            background_noise = np.mean(noise_energies)
            self.speech_threshold = background_noise * 10  # Speech threshold 10x background
            self.logger.info(f"Calibration complete - speech threshold: {self.speech_threshold:.6f}")
            return True
        
        self.logger.warning("Calibration failed")
        return False
    
    def start(self) -> None:
        """Start voice analysis."""
        if not AUDIO_AVAILABLE:
            self.logger.error("Cannot start voice analyzer: audio libraries not available")
            return
        
        if self.is_running:
            return
        
        self.recording = True
        self.audio_thread = threading.Thread(target=self._audio_capture_loop)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        
        super().start()
        self.logger.info("Voice analyzer started")
    
    def stop(self) -> None:
        """Stop voice analysis."""
        self.recording = False
        if self.audio_thread:
            self.audio_thread.join(timeout=2.0)
        
        super().stop()
    
    def _audio_capture_loop(self) -> None:
        """Continuous audio capture loop."""
        while self.recording:
            try:
                # Record audio chunk
                recording = sd.rec(int(self.sample_rate * self.chunk_duration),
                                  samplerate=self.sample_rate,
                                  channels=1, dtype='float32')
                sd.wait()
                
                # Add to buffer
                self.audio_buffer.put(recording.flatten())
                
            except Exception as e:
                self.logger.error(f"Audio capture error: {e}")
                time.sleep(0.1)
    
    def _collect_sample(self) -> Optional[DataPoint]:
        """Collect a voice analysis sample."""
        if not AUDIO_AVAILABLE or self.audio_buffer.empty():
            return None
        
        try:
            # Get audio chunk
            audio = self.audio_buffer.get_nowait()
            
            # Extract features
            features = self._extract_features(audio)
            
            return DataPoint(
                timestamp=datetime.now(),
                source="voice",
                data=features,
                metadata={
                    "sample_rate": self.sample_rate,
                    "chunk_duration": self.chunk_duration
                }
            )
        except queue.Empty:
            return None
        except Exception as e:
            self.logger.error(f"Error collecting voice sample: {e}")
            return None
    
    def _extract_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract voice features from audio chunk."""
        try:
            # Energy (volume)
            energy = np.mean(audio ** 2)
            self.energy_history.append(energy)
            if len(self.energy_history) > 100:
                self.energy_history.pop(0)
            
            # Detect if speaking
            is_speaking = energy > self.speech_threshold
            if is_speaking and not self.is_speaking:
                # Start of speech segment
                self.speech_segments.append(time.time())
            self.is_speaking = is_speaking
            
            # Pitch (fundamental frequency)
            pitches, magnitudes = librosa.piptrack(y=audio, sr=self.sample_rate)
            pitches = pitches[pitches > 0]
            if len(pitches) > 0:
                self.pitch_mean = float(np.mean(pitches))
                self.pitch_std = float(np.std(pitches))
                self.pitch_history.append(self.pitch_mean)
                if len(self.pitch_history) > 100:
                    self.pitch_history.pop(0)
            
            # Zero crossing rate (measure of noisiness)
            zcr = librosa.feature.zero_crossing_rate(audio)[0, 0]
            
            # MFCCs (Mel-frequency cepstral coefficients)
            mfccs = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=13)
            self.mfccs = [float(np.mean(mfccs[i])) for i in range(min(13, mfccs.shape[0]))]
            
            # Speech rate (syllables per second - simplified)
            if len(self.speech_segments) > 1:
                recent_segments = self.speech_segments[-10:]
                if len(recent_segments) > 1:
                    time_span = recent_segments[-1] - recent_segments[0]
                    if time_span > 0:
                        self.speech_rate = len(recent_segments) / time_span
            
            # Spectral centroid (brightness of sound)
            spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]
            spectral_centroid = float(np.mean(spectral_centroids))
            
            return {
                "pitch_mean": self.pitch_mean,
                "pitch_std": self.pitch_std,
                "energy": float(energy),
                "zero_crossing_rate": float(zcr),
                "mfcc_1": self.mfccs[0] if self.mfccs else 0,
                "mfcc_2": self.mfccs[1] if len(self.mfccs) > 1 else 0,
                "mfcc_3": self.mfccs[2] if len(self.mfccs) > 2 else 0,
                "speech_rate": self.speech_rate,
                "is_speaking": is_speaking,
                "spectral_centroid": spectral_centroid
            }
            
        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
            return {
                "pitch_mean": 0.0,
                "pitch_std": 0.0,
                "energy": 0.0,
                "zero_crossing_rate": 0.0,
                "mfcc_1": 0.0,
                "mfcc_2": 0.0,
                "mfcc_3": 0.0,
                "speech_rate": 0.0,
                "is_speaking": False,
                "spectral_centroid": 0.0
            }
    
    def validate_sample(self, sample: DataPoint) -> bool:
        """Validate voice analysis sample."""
        required_fields = ["energy", "is_speaking"]
        
        # Check required fields
        for field in required_fields:
            if field not in sample.data:
                return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get voice analyzer statistics."""
        stats = super().get_statistics()
        stats.update({
            "avg_pitch": float(np.mean(self.pitch_history)) if self.pitch_history else 0,
            "avg_energy": float(np.mean(self.energy_history)) if self.energy_history else 0,
            "speaking_percentage": len([e for e in self.energy_history if e > self.speech_threshold]) / max(len(self.energy_history), 1) * 100
        })
        return stats