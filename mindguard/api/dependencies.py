# api/dependencies.py
from pathlib import Path
from typing import Optional

# Correct import for config
from config import config

# Example dependency functions
def get_model_path() -> Path:
    return config.model.path

def get_api_host() -> str:
    return config.api.host

def get_api_port() -> int:
    return config.api.port

# Placeholder for engines (can be set in main.py)
cognitive_engine: Optional["CognitiveEngine"] = None
intervention_engine: Optional["InterventionEngine"] = None

def get_cognitive_engine() -> Optional["CognitiveEngine"]:
    return cognitive_engine

def get_intervention_engine() -> Optional["InterventionEngine"]:
    return intervention_engine