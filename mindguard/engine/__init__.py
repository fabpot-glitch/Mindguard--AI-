"""Engine package for MindGuard AI core functionality.

This package contains the core processing engines for cognitive state estimation,
intervention management, calibration, and state tracking.
"""

from engine.cognitive_engine import CognitiveEngine
from engine.intervention_engine import InterventionEngine, Intervention, InterventionType, InterventionLevel
from engine.calibration import Calibrator, CalibrationProfile
from engine.feature_normalizer import FeatureNormalizer
from engine.state_tracker import StateTracker, StatePoint

__all__ = [
    'CognitiveEngine',
    'InterventionEngine',
    'Intervention',
    'InterventionType',
    'InterventionLevel',
    'Calibrator',
    'CalibrationProfile',
    'FeatureNormalizer',
    'StateTracker',
    'StatePoint'
]

__version__ = '1.0.0'