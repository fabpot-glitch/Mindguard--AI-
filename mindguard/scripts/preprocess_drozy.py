#!/usr/bin/env python3
"""Preprocess DROZY dataset for fatigue estimation."""

import numpy as np
import scipy.io
import scipy.signal
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
import json
from tqdm import tqdm
import pandas as pd
import cv2
from collections import defaultdict

from config.logging_config import setup_logging, get_logger

logger = get_logger(__name__)


class DROZYPreprocessor:
    """Preprocessor for DROZY dataset."""
    
    # Fatigue levels in DROZY
    FATIGUE_LEVELS = ['alert', 'low_fatigue', 'medium_fatigue', 'high_fatigue']
    
    def __init__(
        self,
        data_dir: Path,
        output_dir: Path,
        use_eeg: bool = True,
        use_eye: bool = True,
        use_video: bool = True,
        sequence_length: int = 30,
        stride: int = 5,
        target_fps: int = 30
    ):
        """
        Initialize DROZY preprocessor.
        
        Args:
            data_dir: Directory containing DROZY data
            output_dir: Output directory for processed data
            use_eeg: Whether to use EEG data
            use_eye: Whether to use eye tracking data
            use_video: Whether to use video data
            sequence_length: Length of sequences in frames
            stride: Stride for sliding window
            target_fps: Target frames per second
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.use_eeg = use_eeg
        self.use_eye = use_eye
        self.use_video = use_video
        self.sequence_length = sequence_length
        self.stride = stride
        self.target_fps = target_fps
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DROZY Preprocessor initialized")
        logger.info(f"Data dir: {data_dir}")
        logger.info(f"Output dir: {output_dir}")
    
    def load_subject_info(self) -> pd.DataFrame:
        """Load subject information."""
        info_file = self.data_dir / 'subject_info.csv'
        if info_file.exists():
            return pd.read_csv(info_file)
        return None
    
    def load_eeg_data(self, subject_id: str) -> Optional[np.ndarray]:
        """Load EEG data for a subject."""
        eeg_file = self.data_dir / f'subject_{subject_id}' / 'eeg.mat'
        if eeg_file.exists():
            mat_data = scipy.io.loadmat(eeg_file)
            return mat_data['eeg']
        return None
    
    def load_eye_data(self, subject_id: str) -> Optional[pd.DataFrame]:
        """Load eye tracking data for a subject."""
        eye_file = self.data_dir / f'subject_{subject_id}' / 'eye_tracking.csv'
        if eye_file.exists():
            return pd.read_csv(eye_file)
        return None
    
    def load_video_data(self, subject_id: str) -> Optional[List[np.ndarray]]:
        """Load video frames for a subject."""
        video_dir = self.data_dir / f'subject_{subject_id}' / 'video'
        if video_dir.exists():
            frames = []
            for frame_file in sorted(video_dir.glob('frame_*.jpg')):
                frame = cv2.imread(str(frame_file))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame)
            return frames
        return None
    
    def load_fatigue_labels(self, subject_id: str) -> Optional[List[int]]:
        """Load fatigue labels for a subject."""
        label_file = self.data_dir / f'subject_{subject_id}' / 'fatigue_labels.csv'
        if label_file.exists():
            df = pd.read_csv(label_file)
            return df['fatigue_level'].values
        return None
    
    def extract_eeg_features(self, eeg_data: np.ndarray) -> np.ndarray:
        """Extract features from EEG data."""
        if eeg_data is None:
            return None
        
        n_channels, n_samples = eeg_data.shape
        
        # Apply bandpass filter
        b, a = scipy.signal.butter(4, [0.5, 45], btype='band', fs=self.target_fps)
        filtered = scipy.signal.filtfilt(b, a, eeg_data, axis=1)
        
        # Extract features per window
        window_size = self.target_fps * 2  # 2-second windows
        stride = self.target_fps // 2  # 0.5-second stride
        
        n_windows = (n_samples - window_size) // stride + 1
        features = []
        
        for i in range(n_windows):
            start = i * stride
            end = start + window_size
            window = filtered[:, start:end]
            
            window_features = []
            for channel in window:
                # Time domain features
                window_features.append(np.mean(channel))
                window_features.append(np.std(channel))
                window_features.append(np.ptp(channel))
                window_features.append(np.sqrt(np.mean(channel**2)))
                
                # Frequency domain features
                fft_vals = np.fft.rfft(channel)
                fft_power = np.abs(fft_vals)**2
                freqs = np.fft.rfftfreq(len(channel), 1/self.target_fps)
                
                # Band powers
                bands = {
                    'delta': (0.5, 4),
                    'theta': (4, 8),
                    'alpha': (8, 13),
                    'beta': (13, 30)
                }
                
                for band, (low, high) in bands.items():
                    idx = np.where((freqs >= low) & (freqs < high))[0]
                    if len(idx) > 0:
                        window_features.append(np.mean(fft_power[idx]))
                    else:
                        window_features.append(0)
            
            features.append(window_features)
        
        return np.array(features)
    
    def extract_eye_features(self, eye_data: pd.DataFrame) -> np.ndarray:
        """Extract features from eye tracking data."""
        if eye_data is None:
            return None
        
        features = []
        
        # Group by time windows
        window_size = self.target_fps * 2  # 2-second windows
        n_samples = len(eye_data)
        n_windows = n_samples // window_size
        
        for i in range(n_windows):
            start = i * window_size
            end = start + window_size
            window = eye_data.iloc[start:end]
            
            window_features = []
            
            # Pupil diameter
            if 'pupil_diameter' in window.columns:
                pupil = window['pupil_diameter'].values
                window_features.append(np.mean(pupil))
                window_features.append(np.std(pupil))
                window_features.append(np.ptp(pupil))
            
            # Gaze position
            if 'gaze_x' in window.columns and 'gaze_y' in window.columns:
                gaze_x = window['gaze_x'].values
                gaze_y = window['gaze_y'].values
                window_features.append(np.mean(gaze_x))
                window_features.append(np.std(gaze_x))
                window_features.append(np.mean(gaze_y))
                window_features.append(np.std(gaze_y))
                
                # Gaze velocity
                if len(gaze_x) > 1:
                    dt = 1.0 / self.target_fps
                    vx = np.diff(gaze_x) / dt
                    vy = np.diff(gaze_y) / dt
                    speed = np.sqrt(vx**2 + vy**2)
                    window_features.append(np.mean(speed))
                    window_features.append(np.std(speed))
            
            # Blink rate
            if 'blink' in window.columns:
                blinks = window['blink'].values
                window_features.append(np.sum(blinks))  # Number of blinks
                window_features.append(np.mean(blinks))  # Blink rate
            
            # Fixation duration
            if 'fixation' in window.columns:
                fixations = window['fixation'].values
                # Find fixation periods
                changes = np.diff(np.concatenate(([0], fixations)))
                fixation_starts = np.where(changes == 1)[0]
                fixation_ends = np.where(changes == -1)[0]
                
                if len(fixation_starts) > 0 and len(fixation_ends) > 0:
                    durations = fixation_ends - fixation_starts
                    window_features.append(np.mean(durations) / self.target_fps)  # Avg fixation duration
                    window_features.append(len(fixation_starts))  # Number of fixations
                else:
                    window_features.append(0)
                    window_features.append(0)
            
            features.append(window_features)
        
        return np.array(features)
    
    def extract_video_features(self, video_frames: List[np.ndarray]) -> np.ndarray:
        """Extract features from video frames."""
        if video_frames is None:
            return None
        
        features = []
        
        # Process frames in windows
        window_size = self.target_fps * 2  # 2-second windows
        n_frames = len(video_frames)
        n_windows = n_frames // window_size
        
        for i in range(n_windows):
            start = i * window_size
            end = start + window_size
            window_frames = video_frames[start:end]
            
            window_features = []
            
            for frame in window_frames:
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                
                # Face detection (simplified - would use face detector in production)
                # For now, use image statistics
                window_features.append(np.mean(gray))
                window_features.append(np.std(gray))
                
                # Edge density
                edges = cv2.Canny(gray, 50, 150)
                window_features.append(np.sum(edges > 0) / edges.size)
                
                # Motion between consecutive frames (if not first frame)
                if i > 0 or start > 0:
                    prev_frame = video_frames[start - 1] if start > 0 else video_frames[0]
                    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_RGB2GRAY)
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                    )
                    mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    window_features.append(np.mean(mag))
                    window_features.append(np.std(mag))
                else:
                    window_features.append(0)
                    window_features.append(0)
            
            # Average over window
            window_features = np.array(window_features).reshape(-1, len(window_frames))
            avg_features = np.mean(window_features, axis=1)
            features.append(avg_features)
        
        return np.array(features)
    
    def process_subject(self, subject_id: str) -> Optional[Dict]:
        """Process a single subject."""
        # Load data
        eeg_data = self.load_eeg_data(subject_id) if self.use_eeg else None
        eye_data = self.load_eye_data(subject_id) if self.use_eye else None
        video_frames = self.load_video_data(subject_id) if self.use_video else None
        fatigue_labels = self.load_fatigue_labels(subject_id)
        
        if fatigue_labels is None:
            logger.warning(f"No fatigue labels for subject {subject_id}")
            return None
        
        # Extract features
        features = {}
        
        if self.use_eeg and eeg_data is not None:
            eeg_features = self.extract_eeg_features(eeg_data)
            if eeg_features is not None:
                features['eeg'] = eeg_features
        
        if self.use_eye and eye_data is not None:
            eye_features = self.extract_eye_features(eye_data)
            if eye_features is not None:
                features['eye'] = eye_features
        
        if self.use_video and video_frames is not None:
            video_features = self.extract_video_features(video_frames)
            if video_features is not None:
                features['video'] = video_features
        
        if not features:
            logger.warning(f"No features extracted for subject {subject_id}")
            return None
        
        # Align features and labels
        min_length = min(
            [len(f) for f in features.values()] + [len(fatigue_labels)]
        )
        
        aligned_features = {}
        for modality, feat in features.items():
            aligned_features[modality] = feat[:min_length]
        
        aligned_labels = fatigue_labels[:min_length]
        
        # Convert fatigue levels to continuous scores
        label_map = {level: i/3.0 for i, level in enumerate(self.FATIGUE_LEVELS)}
        continuous_labels = [label_map.get(l, 0.5) for l in aligned_labels]
        
        return {
            'features': aligned_features,
            'labels': continuous_labels,
            'subject_id': subject_id
        }
    
    def process_all(self) -> Dict:
        """Process all subjects."""
        # Get list of subject directories
        subject_dirs = [d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith('subject_')]
        
        all_features = defaultdict(list)
        all_labels = []
        all_subject_ids = []
        
        for subject_dir in tqdm(subject_dirs, desc="Processing subjects"):
            subject_id = subject_dir.name.replace('subject_', '')
            
            subject_data = self.process_subject(subject_id)
            if subject_data is None:
                continue
            
            # Apply sliding window
            n_samples = len(subject_data['labels'])
            n_windows = (n_samples - self.sequence_length) // self.stride + 1
            
            for i in range(n_windows):
                start = i * self.stride
                end = start + self.sequence_length
                
                for modality, feat in subject_data['features'].items():
                    if feat.shape[0] > end:
                        window_feat = feat[start:end]
                        all_features[modality].append(window_feat)
                
                all_labels.append({
                    'fatigue': subject_data['labels'][end - 1],
                    'subject_id': subject_data['subject_id']
                })
                all_subject_ids.append(subject_data['subject_id'])
        
        # Convert to numpy arrays
        processed_data = {
            'features': {},
            'labels': all_labels,
            'metadata': {
                'num_samples': len(all_labels),
                'num_subjects': len(set(all_subject_ids)),
                'sequence_length': self.sequence_length,
                'stride': self.stride,
                'fatigue_levels': self.FATIGUE_LEVELS
            }
        }
        
        for modality, features in all_features.items():
            processed_data['features'][modality] = np.array(features)
            logger.info(f"{modality} features shape: {processed_data['features'][modality].shape}")
        
        return processed_data
    
    def save_processed_data(self, data: Dict, filename: str = 'drozy_processed.npy'):
        """Save processed data."""
        output_path = self.output_dir / filename
        np.save(output_path, data)
        logger.info(f"Saved processed data to {output_path}")
        
        # Also save metadata as JSON
        metadata_path = self.output_dir / 'drozy_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(data['metadata'], f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")


def main():
    """Main preprocessing function."""
    parser = argparse.ArgumentParser(description='Preprocess DROZY dataset')
    parser.add_argument('--data-dir', type=str, required=True,
                        help='Directory containing DROZY data')
    parser.add_argument('--output-dir', type=str, default='data/processed',
                        help='Output directory for processed data')
    parser.add_argument('--sequence-length', type=int, default=30,
                        help='Sequence length in frames')
    parser.add_argument('--stride', type=int, default=5,
                        help='Stride for sliding window')
    parser.add_argument('--target-fps', type=int, default=30,
                        help='Target frames per second')
    parser.add_argument('--no-eeg', action='store_true',
                        help='Disable EEG features')
    parser.add_argument('--no-eye', action='store_true',
                        help='Disable eye tracking features')
    parser.add_argument('--no-video', action='store_true',
                        help='Disable video features')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level='INFO')
    
    # Create preprocessor
    preprocessor = DROZYPreprocessor(
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        use_eeg=not args.no_eeg,
        use_eye=not args.no_eye,
        use_video=not args.no_video,
        sequence_length=args.sequence_length,
        stride=args.stride,
        target_fps=args.target_fps
    )
    
    # Process data
    processed_data = preprocessor.process_all()
    
    # Save
    preprocessor.save_processed_data(processed_data)
    
    logger.info("DROZY preprocessing complete!")


if __name__ == '__main__':
    main()