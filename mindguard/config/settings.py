"""Application settings management."""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class APIConfig:
    """API configuration."""
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    workers: int = int(os.getenv("API_WORKERS", "4"))
    reload: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    debug: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    secret_key: str = os.getenv("API_SECRET_KEY", "dev-secret-key-change-in-production")
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])


@dataclass
class ModelConfig:
    """Model configuration."""
    path: Path = Path(os.getenv("MODEL_PATH", "models/weights/mindguard_best.pt"))
    onnx_path: Path = Path(os.getenv("MODEL_ONNX_PATH", "models/weights/mindguard.onnx"))
    device: str = os.getenv("MODEL_DEVICE", "cpu")
    confidence_threshold: float = float(os.getenv("MODEL_CONFIDENCE_THRESHOLD", "0.7"))
    inference_frequency: int = int(os.getenv("MODEL_INFERENCE_FREQUENCY", "5"))
    batch_size: int = int(os.getenv("MODEL_BATCH_SIZE", "32"))


@dataclass
class CollectorConfig:
    """Data collector configuration."""
    camera_id: int = int(os.getenv("CAMERA_ID", "0"))
    camera_fps: int = int(os.getenv("CAMERA_FPS", "30"))
    camera_width: int = 640
    camera_height: int = 480
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    audio_channels: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    keyboard_sampling_rate: int = int(os.getenv("KEYBOARD_SAMPLING_RATE", "100"))
    screen_capture_fps: int = int(os.getenv("SCREEN_CAPTURE_FPS", "5"))
    buffer_size: int = 1000


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = os.getenv("LOG_LEVEL", "INFO")
    format: str = os.getenv("LOG_FORMAT", "json")
    file: Optional[Path] = Path("logs/app.log") if os.getenv("LOG_FILE") else None


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = os.getenv("DATABASE_URL", "sqlite:///data/mindguard.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")


@dataclass
class FeatureFlags:
    """Feature flags."""
    enable_voice_analysis: bool = os.getenv("ENABLE_VOICE_ANALYSIS", "true").lower() == "true"
    enable_screen_monitoring: bool = os.getenv("ENABLE_SCREEN_MONITORING", "true").lower() == "true"
    enable_federated_learning: bool = os.getenv("ENABLE_FEDERATED_LEARNING", "false").lower() == "true"
    privacy_mode: bool = os.getenv("PRIVACY_MODE", "true").lower() == "true"


@dataclass
class Settings:
    """Main settings container."""
    api: APIConfig = field(default_factory=APIConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    collectors: CollectorConfig = field(default_factory=CollectorConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    
    def __post_init__(self):
        """Create necessary directories."""
        # Create logs directory
        if self.logging.file:
            self.logging.file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create models directory
        self.model.path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create data directory
        Path("data").mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "debug": self.api.debug
            },
            "model": {
                "device": self.model.device,
                "inference_frequency": self.model.inference_frequency
            },
            "features": {
                "voice_analysis": self.features.enable_voice_analysis,
                "screen_monitoring": self.features.enable_screen_monitoring,
                "privacy_mode": self.features.privacy_mode
            }
        }


# Global settings instance
settings = Settings()