#!/usr/bin/env python3
"""Setup script for MindGuard AI package."""

from setuptools import setup, find_packages
import os
import sys

# Package metadata
NAME = "mindguard-ai"
VERSION = "1.0.0"
DESCRIPTION = "Real-Time Cognitive Load & Burnout Prevention System"
LONG_DESCRIPTION = """
MindGuard AI is an intelligent system that monitors cognitive fatigue in real-time 
using multimodal signals and intervenes proactively before burnout or errors occur.

Key Features:
- Multimodal data fusion (webcam, keyboard, screen, voice)
- Real-time cognitive state estimation
- Proactive intervention system
- Privacy-first design with on-device processing
- Federated learning capabilities
- Comprehensive dashboard and analytics
"""

AUTHOR = "MindGuard AI Team"
AUTHOR_EMAIL = "team@mindguard.ai"
URL = "https://github.com/mindguard-ai/mindguard"
LICENSE = "MIT"

# Read requirements from file
def read_requirements(filename):
    """Read requirements from file."""
    requirements = []
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("--"):
                # Handle platform-specific markers
                if "; platform_system" in line:
                    requirements.append(line)
                else:
                    requirements.append(line.split("#")[0].strip())
    return requirements

# Read long description from README
def read_long_description():
    """Read long description from README file."""
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return LONG_DESCRIPTION

# Determine requirements
install_requires = read_requirements("requirements.txt")

# Additional platform-specific dependencies
extras_require = {
    "dev": read_requirements("requirements-dev.txt"),
    "gpu": [
        "cuda-python>=12.0",
        "nvidia-ml-py3>=7.352.0",
        "torch>=2.1.0+cu118",
    ],
    "onnx": [
        "onnx>=1.15.0",
        "onnxruntime-gpu>=1.16.0",
    ],
    "viz": [
        "matplotlib>=3.8.0",
        "seaborn>=0.13.0",
        "plotly>=5.18.0",
    ],
    "docs": [
        "mkdocs>=1.5.0",
        "mkdocs-material>=9.4.0",
        "mkdocstrings>=0.24.0",
    ],
    "test": [
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-asyncio>=0.21.0",
    ],
    "mlflow": [
        "mlflow>=2.8.0",
        "wandb>=0.16.0",
    ],
    "distributed": [
        "celery>=5.3.0",
        "ray>=2.9.0",
    ],
    "windows": [
        "pywin32>=306",
        "pywinhook>=1.6.2",
    ],
    "linux": [
        "python-xlib>=0.33",
    ],
    "macos": [
        "pyobjc>=10.0",
    ],
}

# Add all extras for convenience
extras_require["all"] = []
for group in extras_require.values():
    if isinstance(group, list):
        extras_require["all"].extend(group)
    else:
        for deps in group.values():
            extras_require["all"].extend(deps)

# Package classifiers
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Healthcare Industry",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Developers",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Operating System :: OS Independent",
    "Natural Language :: English",
]

# Entry points for console scripts
entry_points = {
    "console_scripts": [
        "mindguard = mindguard.cli:main",
        "mindguard-train = mindguard.scripts.train:main",
        "mindguard-evaluate = mindguard.scripts.evaluate:main",
        "mindguard-server = mindguard.main:run_server",
        "mindguard-collect = mindguard.scripts.collect:main",
        "mindguard-calibrate = mindguard.scripts.calibrate:main",
    ],
}

# Package data (non-Python files to include)
package_data = {
    "mindguard": [
        "config/*.yaml",
        "config/*.json",
        "models/weights/.gitkeep",
        "data/.gitkeep",
        "logs/.gitkeep",
    ],
}

# Data files (outside package)
data_files = [
    ("etc/mindguard", ["config/logging_config.py", "config/thresholds.py"]),
    ("share/mindguard", ["README.md", "LICENSE"]),
]

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    license=LICENSE,
    classifiers=classifiers,
    keywords="cognitive-load fatigue-detection ai healthcare monitoring",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    include_package_data=True,
    package_data=package_data,
    data_files=data_files,
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points=entry_points,
    python_requires=">=3.9",
    zip_safe=False,
    
    # Additional metadata
    project_urls={
        "Documentation": "https://docs.mindguard.ai",
        "Source": "https://github.com/mindguard-ai/mindguard",
        "Tracker": "https://github.com/mindguard-ai/mindguard/issues",
        "Discord": "https://discord.gg/mindguard",
        "Twitter": "https://twitter.com/mindguard_ai",
    },
    
    # Dependency links (for packages not on PyPI)
    dependency_links=[],
    
    # Test suite
    test_suite="tests",
    
    # Scripts (for backward compatibility)
    scripts=[
        "scripts/preprocess_deap.py",
        "scripts/preprocess_drozy.py",
        "scripts/seed_data.py",
    ],
)

# Post-installation message
def _post_install():
    """Print post-installation message."""
    print("\n" + "="*60)
    print("MindGuard AI installed successfully!")
    print("="*60)
    print("\nQuick Start:")
    print("  mindguard-server        # Start the API server")
    print("  mindguard-calibrate     # Run calibration")
    print("  mindguard-train         # Train models")
    print("\nDocumentation: https://docs.mindguard.ai")
    print("GitHub: https://github.com/mindguard-ai/mindguard")
    print("="*60 + "\n")

if "install" in sys.argv:
    _post_install()