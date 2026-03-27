"""Logging configuration for MindGuard AI."""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger


class JSONFormatter:
    """Custom JSON formatter for structured logging."""
    
    def __call__(self, record: Dict[str, Any]) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record["level"].name,
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }
        
        # Add exception info if present
        if record.get("exception"):
            log_entry["exception"] = str(record["exception"])
        
        # Add extra fields
        if record.get("extra"):
            log_entry.update(record["extra"])
        
        return json.dumps(log_entry)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = True
) -> None:
    """Configure logging for the application."""
    
    # Remove default handler
    logger.remove()
    
    # Configure console output
    if json_format:
        logger.add(
            sys.stdout,
            format=JSONFormatter(),
            level=log_level,
            colorize=False
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )
    
    # Configure file output
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Main log file
        logger.add(
            log_file,
            format=JSONFormatter() if json_format else "{time} | {level} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation="1 day",
            retention="30 days",
            compression="zip"
        )
        
        # Error log file
        logger.add(
            log_file.with_suffix('.error.log'),
            format=JSONFormatter() if json_format else "{time} | {level} | {name}:{function}:{line} - {message}",
            level="ERROR",
            rotation="1 week",
            retention="3 months"
        )
    
    # Configure component-specific logs
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Interventions log
    logger.add(
        logs_dir / "interventions.log",
        format=JSONFormatter(),
        level="INFO",
        filter=lambda record: record["extra"].get("category") == "intervention",
        rotation="1 week"
    )
    
    # Performance log
    logger.add(
        logs_dir / "performance.log",
        format=JSONFormatter(),
        level="DEBUG",
        filter=lambda record: record["extra"].get("category") == "performance",
        rotation="100 MB"
    )


def get_logger(name: str, **kwargs) -> logger:
    """Get a configured logger instance."""
    return logger.bind(name=name, **kwargs)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self):
        """Get logger instance."""
        if not hasattr(self, "_logger"):
            self._logger = logger.bind(
                class_name=self.__class__.__name__,
                module=self.__class__.__module__
            )
        return self._logger


# Create module-level loggers
api_logger = logger.bind(category="api")
model_logger = logger.bind(category="model")
collector_logger = logger.bind(category="collector")
engine_logger = logger.bind(category="engine")
intervention_logger = logger.bind(category="intervention")