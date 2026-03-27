"""Calibration module for establishing user baselines."""

import time
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import json
from pathlib import Path

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CalibrationProfile:
    """User-specific calibration profile."""
    
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Baseline values for each modality
    eye_baseline: Dict[str, float] = field(default_factory=dict)
    keyboard_baseline: Dict[str, float] = field(default_factory=dict)
    screen_baseline: Dict[str, float] = field(default_factory=dict)
    voice_baseline: Dict[str, float] = field(default_factory=dict)
    
    # Thresholds
    fatigue_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.8
    })
    
    stress_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'low': 0.3,
        'medium': 0.5,
        'high': 0.7
    })
    
    attention_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.8
    })
    
    load_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'low': 0.4,
        'medium': 0.6,
        'high': 0.8
    })
    
    # Adaptation rate (0-1)
    adaptation_rate: float = 0.1
    
    # Calibration data
    calibration_data: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'eye_baseline': self.eye_baseline,
            'keyboard_baseline': self.keyboard_baseline,
            'screen_baseline': self.screen_baseline,
            'voice_baseline': self.voice_baseline,
            'fatigue_thresholds': self.fatigue_thresholds,
            'stress_thresholds': self.stress_thresholds,
            'attention_thresholds': self.attention_thresholds,
            'load_thresholds': self.load_thresholds,
            'adaptation_rate': self.adaptation_rate
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CalibrationProfile':
        """Create from dictionary."""
        profile = cls(user_id=data['user_id'])
        profile.created_at = datetime.fromisoformat(data['created_at'])
        profile.updated_at = datetime.fromisoformat(data['updated_at'])
        profile.eye_baseline = data.get('eye_baseline', {})
        profile.keyboard_baseline = data.get('keyboard_baseline', {})
        profile.screen_baseline = data.get('screen_baseline', {})
        profile.voice_baseline = data.get('voice_baseline', {})
        profile.fatigue_thresholds = data.get('fatigue_thresholds', profile.fatigue_thresholds)
        profile.stress_thresholds = data.get('stress_thresholds', profile.stress_thresholds)
        profile.attention_thresholds = data.get('attention_thresholds', profile.attention_thresholds)
        profile.load_thresholds = data.get('load_thresholds', profile.load_thresholds)
        profile.adaptation_rate = data.get('adaptation_rate', 0.1)
        return profile


class Calibrator:
    """Handles user calibration and baseline establishment."""
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Initialize calibrator.
        
        Args:
            profiles_dir: Directory to store calibration profiles
        """
        self.profiles_dir = Path(profiles_dir) if profiles_dir else Path('data/profiles')
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles: Dict[str, CalibrationProfile] = {}
        self.current_calibration: Optional[Dict] = None
        self.calibration_start_time: Optional[datetime] = None
        
        logger.info(f"Calibrator initialized with profiles dir: {self.profiles_dir}")
    
    def start_calibration(self, user_id: str, duration_seconds: int = 30):
        """
        Start calibration process.
        
        Args:
            user_id: User identifier
            duration_seconds: Calibration duration
        """
        self.current_calibration = {
            'user_id': user_id,
            'duration': duration_seconds,
            'data': {
                'eye': [],
                'keyboard': [],
                'screen': [],
                'voice': []
            },
            'start_time': datetime.now()
        }
        self.calibration_start_time = datetime.now()
        
        logger.info(f"Started calibration for user {user_id} ({duration_seconds}s)")
    
    def add_calibration_data(self, modality: str, data: Dict[str, float]):
        """
        Add data point during calibration.
        
        Args:
            modality: Modality name ('eye', 'keyboard', 'screen', 'voice')
            data: Feature dictionary
        """
        if not self.current_calibration:
            return
        
        if modality in self.current_calibration['data']:
            self.current_calibration['data'][modality].append(data)
    
    def complete_calibration(self) -> Optional[CalibrationProfile]:
        """
        Complete calibration and compute baseline.
        
        Returns:
            Calibration profile if successful, None otherwise
        """
        if not self.current_calibration:
            logger.warning("No active calibration")
            return None
        
        user_id = self.current_calibration['user_id']
        
        # Compute baselines for each modality
        profile = CalibrationProfile(user_id=user_id)
        
        # Eye baseline
        if self.current_calibration['data']['eye']:
            eye_data = self.current_calibration['data']['eye']
            profile.eye_baseline = self._compute_baseline(eye_data, [
                'ear', 'blink_rate', 'perclos', 'pupil_dilation'
            ])
        
        # Keyboard baseline
        if self.current_calibration['data']['keyboard']:
            kb_data = self.current_calibration['data']['keyboard']
            profile.keyboard_baseline = self._compute_baseline(kb_data, [
                'typing_speed', 'rhythm_variance', 'hesitation_rate', 'avg_hold_time'
            ])
        
        # Screen baseline
        if self.current_calibration['data']['screen']:
            screen_data = self.current_calibration['data']['screen']
            profile.screen_baseline = self._compute_baseline(screen_data, [
                'app_switch_rate', 'focus_score', 'scroll_activity'
            ])
        
        # Voice baseline
        if self.current_calibration['data']['voice']:
            voice_data = self.current_calibration['data']['voice']
            profile.voice_baseline = self._compute_baseline(voice_data, [
                'pitch_mean', 'energy', 'speech_rate'
            ])
        
        # Adjust thresholds based on baseline
        self._adjust_thresholds(profile)
        
        # Save profile
        self.save_profile(profile)
        self.profiles[user_id] = profile
        
        # Clear current calibration
        self.current_calibration = None
        self.calibration_start_time = None
        
        logger.info(f"Completed calibration for user {user_id}")
        
        return profile
    
    def _compute_baseline(self, data: List[Dict], fields: List[str]) -> Dict[str, float]:
        """Compute baseline statistics from calibration data."""
        baseline = {}
        
        for field in fields:
            values = [d.get(field, 0) for d in data if field in d]
            if values:
                baseline[f'{field}_mean'] = float(np.mean(values))
                baseline[f'{field}_std'] = float(np.std(values))
                baseline[f'{field}_min'] = float(np.min(values))
                baseline[f'{field}_max'] = float(np.max(values))
        
        return baseline
    
    def _adjust_thresholds(self, profile: CalibrationProfile):
        """Adjust thresholds based on baseline values."""
        # Adjust fatigue thresholds based on eye baseline
        if 'ear_mean' in profile.eye_baseline:
            ear = profile.eye_baseline['ear_mean']
            # People with naturally lower EAR might have different thresholds
            if ear < 0.25:
                profile.fatigue_thresholds['high'] = 0.75
            elif ear > 0.35:
                profile.fatigue_thresholds['high'] = 0.85
        
        # Adjust based on typing speed
        if 'typing_speed_mean' in profile.keyboard_baseline:
            wpm = profile.keyboard_baseline['typing_speed_mean']
            if wpm < 30:  # Slow typer
                profile.attention_thresholds['low'] = 0.25
            elif wpm > 60:  # Fast typer
                profile.attention_thresholds['low'] = 0.35
    
    def get_profile(self, user_id: str) -> Optional[CalibrationProfile]:
        """Get calibration profile for user."""
        if user_id in self.profiles:
            return self.profiles[user_id]
        
        # Try to load from disk
        return self.load_profile(user_id)
    
    def update_profile(self, user_id: str, measurements: Dict[str, float]):
        """
        Update profile with new measurements (adaptive).
        
        Args:
            user_id: User identifier
            measurements: New measurements
        """
        profile = self.get_profile(user_id)
        if not profile:
            return
        
        # Update baselines using exponential moving average
        rate = profile.adaptation_rate
        
        for modality, baseline in [
            ('eye', profile.eye_baseline),
            ('keyboard', profile.keyboard_baseline),
            ('screen', profile.screen_baseline),
            ('voice', profile.voice_baseline)
        ]:
            for key, value in measurements.items():
                if key in baseline:
                    baseline[key] = (1 - rate) * baseline[key] + rate * value
        
        profile.updated_at = datetime.now()
        self.save_profile(profile)
    
    def save_profile(self, profile: CalibrationProfile):
        """Save profile to disk."""
        profile_path = self.profiles_dir / f"{profile.user_id}.json"
        
        with open(profile_path, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
        
        logger.debug(f"Saved profile for {profile.user_id}")
    
    def load_profile(self, user_id: str) -> Optional[CalibrationProfile]:
        """Load profile from disk."""
        profile_path = self.profiles_dir / f"{user_id}.json"
        
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'r') as f:
                data = json.load(f)
            profile = CalibrationProfile.from_dict(data)
            self.profiles[user_id] = profile
            logger.debug(f"Loaded profile for {user_id}")
            return profile
        except Exception as e:
            logger.error(f"Failed to load profile for {user_id}: {e}")
            return None
    
    def delete_profile(self, user_id: str):
        """Delete user profile."""
        if user_id in self.profiles:
            del self.profiles[user_id]
        
        profile_path = self.profiles_dir / f"{user_id}.json"
        if profile_path.exists():
            profile_path.unlink()
            logger.info(f"Deleted profile for {user_id}")
    
    def get_calibration_status(self) -> Dict[str, Any]:
        """Get current calibration status."""
        if not self.current_calibration:
            return {'status': 'idle'}
        
        elapsed = (datetime.now() - self.calibration_start_time).total_seconds()
        duration = self.current_calibration['duration']
        
        progress = min(100, (elapsed / duration) * 100)
        
        return {
            'status': 'calibrating',
            'user_id': self.current_calibration['user_id'],
            'progress': progress,
            'elapsed': elapsed,
            'remaining': max(0, duration - elapsed),
            'data_points': {
                modality: len(data)
                for modality, data in self.current_calibration['data'].items()
            }
        }