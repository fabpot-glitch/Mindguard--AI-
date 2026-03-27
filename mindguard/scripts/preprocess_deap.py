#!/usr/bin/env python3
"""Preprocess DEAP dataset for cognitive state estimation."""

import numpy as np
import scipy.io
import scipy.signal
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
import json
from tqdm import tqdm
import pickle
from collections import defaultdict

from config.logging_config import setup_logging, get_logger

logger = get_logger(__name__)


class DEAPPreprocessor:
    """Preprocessor for DEAP dataset."""
    
    # EEG channel names
    EEG_CHANNELS = [
        'Fp1', 'AF3', 'F3', 'F7', 'FC5', 'FC1', 'C3', 'T7', 'CP5', 'CP1',
        'P3', 'P7', 'PO3', 'O1', 'Oz', 'Pz', 'Fp2', 'AF4', 'Fz', 'F4',
        'F8', 'FC6', 'FC2', 'Cz', 'C4', 'T8', 'CP6', 'CP2', 'P4', 'P8',
        'PO4', 'O2'
    ]
    
    # Physiological channels
    PHYSIO_CHANNELS = ['hEOG', 'vEOG', 'zEMG', 'tEMG', 'GSR', 'Respiration', 'Plethysmograph', 'Temperature']
    
    def __init__(
        self,
        data_dir: Path,
        output_dir: Path,
        sampling_rate: int = 128,
        target_rate: int = 128,
        sequence_length: int = 256,  # 2 seconds at 128Hz
        stride: int = 64,  # 0.5 second stride
        use_eeg: bool = True,
        use_physio: bool = True
    ):
        """
        Initialize DEAP preprocessor.
        
        Args:
            data_dir: Directory containing DEAP data
            output_dir: Output directory for processed data
            sampling_rate: Original sampling rate
            target_rate: Target sampling rate after resampling
            sequence_length: Length of sequences in samples
            stride: Stride for sliding window
            use_eeg: Whether to use EEG channels
            use_physio: Whether to use physiological channels
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.sampling_rate = sampling_rate
        self.target_rate = target_rate
        self.sequence_length = sequence_length
        self.stride = stride
        self.use_eeg = use_eeg
        self.use_physio = use_physio
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Resampling ratio
        self.resample_ratio = target_rate / sampling_rate
        
        logger.info(f"DEAP Preprocessor initialized")
        logger.info(f"Data dir: {data_dir}")
        logger.info(f"Output dir: {output_dir}")
    
    def load_participant_data(self, participant_id: int) -> Dict:
        """
        Load data for a single participant.
        
        Args:
            participant_id: Participant ID (1-32)
            
        Returns:
            Dictionary containing data and labels
        """
        file_path = self.data_dir / f's{participant_id:02d}.mat'
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        # Load mat file
        mat_data = scipy.io.loadmat(file_path)
        
        # Extract data and labels
        data = mat_data['data']  # Shape: (40, 40, 8064) - (trials, channels, samples)
        labels = mat_data['labels']  # Shape: (40, 4) - (trials, [valence, arousal, dominance, liking])
        
        return {
            'data': data,
            'labels': labels,
            'participant_id': participant_id
        }
    
    def preprocess_trial(
        self,
        trial_data: np.ndarray,
        trial_labels: np.ndarray
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, float]]:
        """
        Preprocess a single trial.
        
        Args:
            trial_data: Trial data array (channels, samples)
            trial_labels: Trial labels [valence, arousal, dominance, liking]
            
        Returns:
            Features dictionary and labels dictionary
        """
        # Apply bandpass filter (0.5-45 Hz)
        b, a = scipy.signal.butter(4, [0.5, 45], btype='band', fs=self.sampling_rate)
        filtered_data = scipy.signal.filtfilt(b, a, trial_data, axis=1)
        
        # Remove baseline (first 3 seconds)
        baseline_samples = 3 * self.sampling_rate
        filtered_data = filtered_data[:, baseline_samples:]
        
        # Resample if needed
        if self.sampling_rate != self.target_rate:
            new_length = int(filtered_data.shape[1] * self.resample_ratio)
            resampled = np.zeros((filtered_data.shape[0], new_length))
            for i in range(filtered_data.shape[0]):
                resampled[i] = scipy.signal.resample(
                    filtered_data[i], new_length
                )
            filtered_data = resampled
        
        # Extract features
        features = {}
        
        if self.use_eeg:
            # EEG channels (first 32)
            eeg_data = filtered_data[:32]
            features['eeg'] = self._extract_eeg_features(eeg_data)
        
        if self.use_physio:
            # Physiological channels (last 8)
            physio_data = filtered_data[32:]
            features['physio'] = self._extract_physio_features(physio_data)
        
        # Create labels
        labels = {
            'valence': float(trial_labels[0]),
            'arousal': float(trial_labels[1]),
            'dominance': float(trial_labels[2]),
            'liking': float(trial_labels[3])
        }
        
        # Normalize labels to [0, 1] (DEAP uses 1-9 scale)
        for key in labels:
            labels[key] = (labels[key] - 1) / 8.0
        
        # Map to cognitive states
        cognitive_labels = self._map_to_cognitive(labels)
        
        return features, cognitive_labels
    
    def _extract_eeg_features(self, eeg_data: np.ndarray) -> np.ndarray:
        """Extract EEG features."""
        n_channels, n_samples = eeg_data.shape
        
        # Compute features per channel
        features = []
        
        # Band powers
        frequencies = np.fft.rfftfreq(n_samples, 1/self.target_rate)
        bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 45)
        }
        
        for channel in eeg_data:
            channel_features = []
            
            # Time domain features
            channel_features.append(np.mean(channel))  # Mean
            channel_features.append(np.std(channel))   # Std
            channel_features.append(np.ptp(channel))   # Peak-to-peak
            channel_features.append(np.sqrt(np.mean(channel**2)))  # RMS
            
            # Frequency domain features
            fft_vals = np.fft.rfft(channel)
            fft_power = np.abs(fft_vals)**2
            
            for band, (low, high) in bands.items():
                idx = np.where((frequencies >= low) & (frequencies < high))[0]
                if len(idx) > 0:
                    band_power = np.mean(fft_power[idx])
                    channel_features.append(band_power)
                else:
                    channel_features.append(0)
            
            # Ratios
            alpha_power = channel_features[-3]  # Alpha is third band
            beta_power = channel_features[-2]    # Beta is fourth band
            if alpha_power > 0:
                channel_features.append(beta_power / alpha_power)  # Beta/Alpha ratio
            else:
                channel_features.append(0)
            
            features.extend(channel_features)
        
        return np.array(features)
    
    def _extract_physio_features(self, physio_data: np.ndarray) -> np.ndarray:
        """Extract physiological features."""
        features = []
        
        # Define which physiological channels we have
        # Order: hEOG, vEOG, zEMG, tEMG, GSR, Respiration, Pleth, Temperature
        for i, channel in enumerate(physio_data):
            channel_features = []
            
            # Basic statistics
            channel_features.append(np.mean(channel))
            channel_features.append(np.std(channel))
            channel_features.append(np.ptp(channel))
            
            # Specific features per channel type
            if i == 4:  # GSR
                # Skin conductance response features
                scr_peaks, _ = scipy.signal.find_peaks(channel, height=np.mean(channel) + np.std(channel))
                channel_features.append(len(scr_peaks))  # Number of SCRs
                if len(scr_peaks) > 0:
                    channel_features.append(np.mean(channel[scr_peaks]))  # Average peak height
                else:
                    channel_features.append(0)
            
            elif i == 5:  # Respiration
                # Breathing rate
                resp_fft = np.abs(np.fft.rfft(channel))
                resp_freqs = np.fft.rfftfreq(len(channel), 1/self.target_rate)
                # Find peak frequency (breathing rate)
                peak_idx = np.argmax(resp_fft[1:]) + 1
                channel_features.append(resp_freqs[peak_idx] * 60)  # Breaths per minute
            
            elif i == 6:  # Plethysmograph (blood volume pulse)
                # Heart rate
                bvp_fft = np.abs(np.fft.rfft(channel))
                bvp_freqs = np.fft.rfftfreq(len(channel), 1/self.target_rate)
                # Find peak frequency (heart rate)
                peak_idx = np.argmax(bvp_fft[1:20]) + 1  # Look in 0-10 Hz range
                channel_features.append(bvp_freqs[peak_idx] * 60)  # Beats per minute
            
            elif i == 7:  # Temperature
                # Temperature trend
                if len(channel) > 1:
                    channel_features.append(channel[-1] - channel[0])  # Overall change
                else:
                    channel_features.append(0)
            
            features.extend(channel_features)
        
        return np.array(features)
    
    def _map_to_cognitive(self, labels: Dict[str, float]) -> Dict[str, float]:
        """Map DEAP labels to cognitive states."""
        # Fatigue: low arousal + low valence
        fatigue = 1.0 - (labels['arousal'] * 0.6 + labels['valence'] * 0.4)
        
        # Stress: high arousal + low valence
        stress = labels['arousal'] * (1.0 - labels['valence'])
        
        # Attention: high arousal + high valence
        attention = labels['arousal'] * labels['valence']
        
        # Cognitive load: combination of arousal and dominance
        cognitive_load = (labels['arousal'] + labels['dominance']) / 2.0
        
        return {
            'fatigue': float(np.clip(fatigue, 0, 1)),
            'stress': float(np.clip(stress, 0, 1)),
            'attention': float(np.clip(attention, 0, 1)),
            'cognitive_load': float(np.clip(cognitive_load, 0, 1))
        }
    
    def process_all(self, num_participants: int = 32) -> Dict:
        """
        Process all participants.
        
        Args:
            num_participants: Number of participants to process
            
        Returns:
            Dictionary with processed data
        """
        all_features = defaultdict(list)
        all_labels = []
        
        for participant_id in tqdm(range(1, num_participants + 1), desc="Processing participants"):
            participant_data = self.load_participant_data(participant_id)
            if participant_data is None:
                continue
            
            data = participant_data['data']
            labels = participant_data['labels']
            
            # Process each trial
            for trial_idx in range(data.shape[0]):
                trial_data = data[trial_idx]
                trial_labels = labels[trial_idx]
                
                features, cognitive_labels = self.preprocess_trial(
                    trial_data, trial_labels
                )
                
                # Apply sliding window
                if self.use_eeg:
                    n_windows = (features['eeg'].shape[0] - self.sequence_length) // self.stride + 1
                    if n_windows > 0:
                        for window_start in range(0, n_windows * self.stride, self.stride):
                            window_end = window_start + self.sequence_length
                            all_features['eeg'].append(features['eeg'][window_start:window_end])
                            all_labels.append(cognitive_labels)
                
                if self.use_physio and 'physio' in features:
                    all_features['physio'].append(features['physio'])
        
        # Convert to numpy arrays
        processed_data = {
            'features': {},
            'labels': all_labels,
            'metadata': {
                'num_samples': len(all_labels),
                'sampling_rate': self.target_rate,
                'sequence_length': self.sequence_length,
                'stride': self.stride
            }
        }
        
        for modality, features in all_features.items():
            processed_data['features'][modality] = np.array(features)
            logger.info(f"{modality} features shape: {processed_data['features'][modality].shape}")
        
        return processed_data
    
    def save_processed_data(self, data: Dict, filename: str = 'deap_processed.npy'):
        """Save processed data."""
        output_path = self.output_dir / filename
        np.save(output_path, data)
        logger.info(f"Saved processed data to {output_path}")
        
        # Also save metadata as JSON
        metadata_path = self.output_dir / 'deap_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(data['metadata'], f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")


def main():
    """Main preprocessing function."""
    parser = argparse.ArgumentParser(description='Preprocess DEAP dataset')
    parser.add_argument('--data-dir', type=str, required=True,
                        help='Directory containing DEAP data')
    parser.add_argument('--output-dir', type=str, default='data/processed',
                        help='Output directory for processed data')
    parser.add_argument('--sampling-rate', type=int, default=128,
                        help='Original sampling rate')
    parser.add_argument('--target-rate', type=int, default=128,
                        help='Target sampling rate')
    parser.add_argument('--sequence-length', type=int, default=256,
                        help='Sequence length in samples')
    parser.add_argument('--stride', type=int, default=64,
                        help='Stride for sliding window')
    parser.add_argument('--no-eeg', action='store_true',
                        help='Disable EEG features')
    parser.add_argument('--no-physio', action='store_true',
                        help='Disable physiological features')
    parser.add_argument('--num-participants', type=int, default=32,
                        help='Number of participants to process')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level='INFO')
    
    # Create preprocessor
    preprocessor = DEAPPreprocessor(
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        sampling_rate=args.sampling_rate,
        target_rate=args.target_rate,
        sequence_length=args.sequence_length,
        stride=args.stride,
        use_eeg=not args.no_eeg,
        use_physio=not args.no_physio
    )
    
    # Process data
    processed_data = preprocessor.process_all(num_participants=args.num_participants)
    
    # Save
    preprocessor.save_processed_data(processed_data)
    
    logger.info("DEAP preprocessing complete!")


if __name__ == '__main__':
    main()