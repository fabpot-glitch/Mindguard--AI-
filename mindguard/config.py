# config.py
"""
Main configuration module for MindGuard AI.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


# ================= API CONFIG =================
@dataclass
class APIConfig:
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    workers: int = int(os.getenv("API_WORKERS", "4"))
    reload: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    debug: bool = os.getenv("API_DEBUG", "false").lower() == "true"
    secret_key: str = os.getenv("API_SECRET_KEY", "dev-secret-key")


# ================= WEBSOCKET CONFIG =================
@dataclass
class WebSocketConfig:
    max_connections: int = int(os.getenv("WS_MAX_CONNECTIONS", "100"))
    ping_interval: int = int(os.getenv("WS_PING_INTERVAL", "30"))
    ping_timeout: int = int(os.getenv("WS_PING_TIMEOUT", "10"))


# ================= MODEL CONFIG =================
@dataclass
class ModelConfig:
    path: Path = Path(os.getenv("MODEL_PATH", "./models/weights/mindguard_best.pt"))
    onnx_path: Path = Path(os.getenv("MODEL_ONNX_PATH", "./models/weights/mindguard.onnx"))
    device: str = os.getenv("MODEL_DEVICE", "cpu")
    confidence_threshold: float = float(os.getenv("MODEL_CONFIDENCE_THRESHOLD", "0.7"))
    inference_frequency: int = int(os.getenv("MODEL_INFERENCE_FREQUENCY", "5"))

    def __post_init__(self):
        if not self.path.exists() and not self.onnx_path.exists():
            print(f"⚠️ Warning: No model found at {self.path} or {self.onnx_path}")


# ================= COLLECTOR CONFIG =================
@dataclass
class CollectorConfig:
    camera_id: int = int(os.getenv("CAMERA_ID", "0"))
    camera_fps: int = int(os.getenv("CAMERA_FPS", "30"))
    camera_resolution: tuple = (640, 480)
    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    audio_channels: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    keyboard_sampling_rate: int = int(os.getenv("KEYBOARD_SAMPLING_RATE", "100"))
    screen_capture_fps: int = int(os.getenv("SCREEN_CAPTURE_FPS", "5"))


# ================= THRESHOLD CONFIG =================
@dataclass
class ThresholdConfig:
    fatigue_high: int = int(os.getenv("FATIGUE_HIGH_THRESHOLD", "80"))
    fatigue_critical: int = int(os.getenv("FATIGUE_CRITICAL_THRESHOLD", "90"))
    stress_high: int = int(os.getenv("STRESS_HIGH_THRESHOLD", "75"))
    attention_low: int = int(os.getenv("ATTENTION_LOW_THRESHOLD", "30"))
    intervention_cooldown: int = int(os.getenv("INTERVENTION_COOLDOWN", "120"))


# ================= LOGGING CONFIG =================
@dataclass
class LoggingConfig:
    level: str = os.getenv("LOG_LEVEL", "INFO")
    format: str = os.getenv("LOG_FORMAT", "json")
    file: Path = Path(os.getenv("LOG_FILE", "./logs/app.log"))


# ================= DATABASE CONFIG =================
@dataclass
class DatabaseConfig:
    url: str = os.getenv("DATABASE_URL", "sqlite:///./data/mindguard.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")


# ================= FEDERATED LEARNING CONFIG =================
@dataclass
class FederatedLearningConfig:
    enabled: bool = os.getenv("FL_ENABLED", "false").lower() == "true"
    server_url: str = os.getenv("FL_SERVER_URL", "http://localhost:8080")
    min_clients: int = int(os.getenv("FL_MIN_CLIENTS", "5"))
    rounds: int = int(os.getenv("FL_ROUNDS", "10"))


# ================= MAIN CONFIG =================
@dataclass
class Config:
    api: APIConfig = field(default_factory=APIConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    collectors: CollectorConfig = field(default_factory=CollectorConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    fl: FederatedLearningConfig = field(default_factory=FederatedLearningConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert main config to a dict for JSON export."""
        return {
            "api": vars(self.api),
            "websocket": vars(self.websocket),
            "model": vars(self.model),
            "collectors": vars(self.collectors),
            "thresholds": vars(self.thresholds),
            "logging": vars(self.logging),
            "database": vars(self.database),
            "fl": vars(self.fl),
        }

    def save_to_file(self, path: Path) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, path: Path) -> "Config":
        with open(path, "r") as f:
            data = json.load(f)
        os.environ.update({k.upper(): str(v) for k, v in data.get("api", {}).items()})
        return cls()


# ✅ GLOBAL INSTANCE
config = Config()