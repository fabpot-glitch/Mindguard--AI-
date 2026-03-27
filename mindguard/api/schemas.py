"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    timestamp: str
    version: str


class CognitiveStateResponse(BaseModel):
    """Cognitive state response schema."""
    fatigue: float = Field(..., ge=0, le=1, description="Fatigue level (0-1)")
    stress: float = Field(..., ge=0, le=1, description="Stress level (0-1)")
    attention: float = Field(..., ge=0, le=1, description="Attention level (0-1)")
    cognitive_load: float = Field(..., ge=0, le=1, description="Cognitive load (0-1)")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")
    timestamp: str = Field(..., description="ISO timestamp")
    trends: Optional[Dict[str, float]] = Field(None, description="Trend indicators")
    baseline_deviation: Optional[Dict[str, float]] = Field(None, description="Deviation from baseline")
    user_id: Optional[str] = Field(None, description="User ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fatigue": 0.75,
                "stress": 0.45,
                "attention": 0.62,
                "cognitive_load": 0.81,
                "confidence": 0.92,
                "timestamp": "2024-01-01T12:00:00Z",
                "trends": {"fatigue": 0.05, "stress": -0.02},
                "baseline_deviation": {"fatigue": 0.15, "stress": -0.10}
            }
        }
    )
    
    @validator('fatigue', 'stress', 'attention', 'cognitive_load', 'confidence')
    def validate_range(cls, v):
        """Validate value range."""
        if v < 0 or v > 1:
            raise ValueError('Value must be between 0 and 1')
        return v


class InterventionType(str, Enum):
    """Intervention type enum."""
    BREAK_REMINDER = "break_reminder"
    BREATHING_EXERCISE = "breathing_exercise"
    HYDRATION_REMINDER = "hydration_reminder"
    TASK_SWITCH_SUGGESTION = "task_switch_suggestion"
    STRETCH_REMINDER = "stretch_reminder"
    FOCUS_RECOVERY = "focus_recovery"
    ENERGY_BOOST = "energy_boost"
    MINDFULNESS_MOMENT = "mindfulness_moment"


class InterventionLevel(str, Enum):
    """Intervention level enum."""
    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    CRITICAL = "critical"


class InterventionResponse(BaseModel):
    """Intervention response schema."""
    id: str = Field(..., description="Unique intervention ID")
    type: InterventionType = Field(..., description="Type of intervention")
    level: InterventionLevel = Field(..., description="Severity level")
    message: str = Field(..., description="Intervention message")
    duration_seconds: int = Field(..., ge=10, le=600, description="Recommended duration")
    actions: List[str] = Field(default_factory=list, description="Available actions")
    timestamp: str = Field(..., description="ISO timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "int_1234567890",
                "type": "break_reminder",
                "level": "warning",
                "message": "Time for a short break. Your fatigue level is elevated.",
                "duration_seconds": 300,
                "actions": ["Take 5 min break", "Postpone", "Dismiss"],
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
    )


class AlertResponse(BaseModel):
    """Alert response schema."""
    type: str = Field(..., description="Alert type")
    level: str = Field(..., description="Alert level")
    value: float = Field(..., description="Current value")
    threshold: float = Field(..., description="Threshold that was crossed")
    timestamp: str = Field(..., description="ISO timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "high_fatigue",
                "level": "warning",
                "value": 0.85,
                "threshold": 0.80,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
    )


class CollectorStatus(BaseModel):
    """Collector status schema."""
    name: str
    active: bool
    samples: int
    last_sample: Optional[str]
    error_rate: float


class StatisticsResponse(BaseModel):
    """Statistics response schema."""
    cognitive: Dict[str, Any] = Field(..., description="Cognitive engine statistics")
    interventions: Dict[str, Any] = Field(..., description="Intervention statistics")
    collectors: Dict[str, CollectorStatus] = Field(..., description="Collector statuses")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cognitive": {
                    "total_inferences": 1500,
                    "avg_inference_time": 0.023,
                    "is_running": True
                },
                "interventions": {
                    "total_today": 3,
                    "active": False
                },
                "collectors": {
                    "eye": {"name": "eye", "active": True, "samples": 45000, "error_rate": 0.01}
                }
            }
        }
    )


class CalibrationRequest(BaseModel):
    """Calibration request schema."""
    collectors: List[str] = Field(
        default=["eye", "keyboard", "screen"],
        description="Collectors to calibrate"
    )
    duration_seconds: int = Field(
        default=30,
        ge=10,
        le=300,
        description="Calibration duration"
    )
    
    @validator('collectors')
    def validate_collectors(cls, v):
        """Validate collector names."""
        valid_collectors = {"eye", "keyboard", "screen", "voice"}
        for collector in v:
            if collector not in valid_collectors:
                raise ValueError(f"Invalid collector: {collector}. Must be one of {valid_collectors}")
        return v


class CalibrationResponse(BaseModel):
    """Calibration response schema."""
    success: bool = Field(..., description="Overall calibration success")
    results: Dict[str, bool] = Field(..., description="Per-collector results")
    message: str = Field(..., description="Calibration message")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "results": {"eye": True, "keyboard": True, "screen": True},
                "message": "Calibration completed"
            }
        }
    )


class ThresholdSettings(BaseModel):
    """Threshold settings schema."""
    fatigue_high: Optional[float] = Field(None, ge=0, le=1)
    fatigue_critical: Optional[float] = Field(None, ge=0, le=1)
    stress_high: Optional[float] = Field(None, ge=0, le=1)
    attention_low: Optional[float] = Field(None, ge=0, le=1)
    cognitive_load_high: Optional[float] = Field(None, ge=0, le=1)


class NotificationPreferences(BaseModel):
    """Notification preferences schema."""
    enabled: bool = True
    sound: bool = True
    desktop: bool = True
    min_level: InterventionLevel = InterventionLevel.WARNING
    quiet_hours_start: Optional[int] = Field(None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(None, ge=0, le=23)


class PrivacySettings(BaseModel):
    """Privacy settings schema."""
    local_processing_only: bool = True
    anonymize_data: bool = True
    data_retention_days: int = Field(7, ge=0, le=365)
    share_aggregates: bool = False


class UserSettings(BaseModel):
    """User settings schema."""
    thresholds: Optional[ThresholdSettings] = None
    notification_preferences: Optional[NotificationPreferences] = None
    privacy_settings: Optional[PrivacySettings] = None
    model_params: Optional[Dict[str, Any]] = Field(None, description="Model parameters")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thresholds": {
                    "fatigue_high": 0.75,
                    "stress_high": 0.70
                },
                "notification_preferences": {
                    "enabled": True,
                    "sound": True,
                    "min_level": "warning"
                }
            }
        }
    )


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""
    type: str = Field(..., description="Message type")
    data: Optional[Dict[str, Any]] = Field(None, description="Message data")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "state_update",
                "data": {"fatigue": 0.75},
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error detail")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Not Found",
                "detail": "Intervention not found",
                "request_id": "req_1234567890"
            }
        }
    )


class PaginatedResponse(BaseModel):
    """Paginated response schema."""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int