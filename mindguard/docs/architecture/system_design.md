# MindGuard AI - System Design Document

## 1. System Overview

MindGuard AI is a real-time cognitive load monitoring and burnout prevention system that uses multimodal data fusion to estimate cognitive states and provide proactive interventions. The system processes data from multiple sensors (webcam, keyboard, screen, microphone) to detect fatigue, stress, attention levels, and cognitive load.

### 1.1 Core Objectives
- Real-time cognitive state estimation (5Hz inference)
- Multimodal data fusion (4+ input modalities)
- Privacy-first design (on-device processing)
- Proactive intervention system
- Personalized thresholds and baselines
- Low latency (<100ms end-to-end)
- High accuracy (>85% correlation with ground truth)

### 1.2 Key Features
- **Real-time Monitoring**: Continuous tracking of cognitive metrics at 5Hz
- **Multimodal Fusion**: Combines eye tracking, keyboard dynamics, screen activity, and voice analysis
- **AI-Powered Predictions**: Transformer-based neural network with 2M parameters
- **Intervention System**: Smart alerts with 5 intervention types and adaptive timing
- **Privacy Preserving**: All processing local, no raw data transmitted, federated learning ready
- **Adaptive Thresholds**: Personalizes to individual baselines within 24 hours
- **Cross-Platform**: Windows, macOS, Linux support
- **Scalable**: 1000+ concurrent users with horizontal scaling

### 1.3 Technical Stack
| Layer | Technologies |
|-------|-------------|
| Frontend | React, Recharts, WebSocket, Material-UI |
| API Gateway | FastAPI, Uvicorn, WebSockets, JWT |
| Core Engine | Python 3.10+, asyncio, multiprocessing |
| ML Framework | PyTorch 2.0+, Transformers, ONNX |
| Computer Vision | OpenCV, MediaPipe, DeepFace |
| Audio Processing | Librosa, SoundDevice, Wav2Vec |
| Database | PostgreSQL 15, Redis 7, MinIO |
| Monitoring | Prometheus, Grafana, ELK Stack |
| Deployment | Docker, Kubernetes, GitHub Actions |

## 2. High-Level Architecture
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ CLIENT LAYER │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ Web Dashboard │ │ Mobile App │ │ CLI Tool │ │
│ │ - React │ │ - React Native│ │ - Python CLI │ │
│ │ - Recharts │ │ - Native APIs │ │ - Data Export │ │
│ │ - WebSocket │ │ - Push Notif │ │ - Batch Mode │ │
│ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘ │
│ │ │ │ │
│ └────────────────────┼────────────────────┘ │
│ │ │
│ HTTPS/WSS (TLS 1.3) │
└────────────────────────────────┼───────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ API GATEWAY │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ FastAPI Application │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │ │
│ │ │ REST Routes │ │ WebSocket │ │ Auth/JWT │ │ Rate Limit │ │ │
│ │ │ /api/v1/* │ │ /ws │ │ Bearer │ │ 100/min │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │ │
│ │ │ Request │ │ Response │ │ CORS │ │ Metrics │ │ │
│ │ │ Validation │ │ Compression│ │ Security │ │ /metrics │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┼───────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ CORE ENGINE │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Cognitive Engine (5Hz) │ │
│ │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │ │
│ │ │ State Tracker │ │ Feature │ │ Model │ │ │
│ │ │ - Rolling window│ │ Normalizer │ │ Inference │ │ │
│ │ │ - Trend calc │ │ - Z-score │ │ - PyTorch │ │ │
│ │ │ - History (1k) │ │ - Min-max │ │ - ONNX RT │ │ │
│ │ └─────────────────┘ └─────────────────┘ └─────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│ │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Intervention Engine (1Hz) │ │
│ │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │ │
│ │ │ Alert Detection│ │ Intervention │ │ Cooldown │ │ │
│ │ │ - Thresholds │ │ Selection │ │ Manager │ │ │
│ │ │ - Anomaly │ │ - 5 types │ │ - 120s │ │ │
│ │ │ - Rules engine │ │ - Priority │ │ - Daily limit │ │ │
│ │ └─────────────────┘ └─────────────────┘ └─────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│ │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Calibration & Personalization │ │
│ │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │ │
│ │ │ Baseline │ │ Adaptive │ │ User │ │ │
│ │ │ Setup │ │ Thresholds │ │ Profile │ │ │
│ │ │ - 30s collect │ │ - EMA update │ │ - Preferences │ │ │
│ │ │ - Per user │ │ - Deviation │ │ - History │ │ │
│ │ └─────────────────┘ └─────────────────┘ └─────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┼───────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ COLLECTOR LAYER │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Collector Manager (20Hz) │ │
│ │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │ │
│ │ │ Synchronization│ │ Buffer Mgr │ │ Feature │ │ │
│ │ │ - 100ms window │ │ - Queue │ │ Aggregation │ │ │
│ │ │ - Timestamp │ │ - Circular │ │ - Windowing │ │ │
│ │ │ - Alignment │ │ - Overflow │ │ - Stats │ │ │
│ │ └─────────────────┘ └─────────────────┘ └─────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│ │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ Eye Tracker │ │ Keyboard │ │ Screen │ │ Voice │ │
│ │ (30Hz) │ │ Monitor │ │ Monitor │ │ Analyzer │ │
│ │ │ │ (100Hz) │ │ (5Hz) │ │ (2Hz) │ │
│ ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤ │
│ │ Features: │ │ Features: │ │ Features: │ │ Features: │ │
│ │ - EAR │ │ - WPM │ │ - App name │ │ - Pitch │ │
│ │ - Blink rate│ │ - Variance │ │ - Switches │ │ - Energy │ │
│ │ - PERCLOS │ │ - Hesitation│ │ - Idle time │ │ - MFCCs │ │
│ │ - Pupil │ │ - Hold time │ │ - Focus │ │ - Speech rate│ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
└────────────────────────────────┼───────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ ML LAYER │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Fusion Model (Transformer) │ │
│ │ │ │
│ │ Eye Feats ──► Modality ──┐ │ │
│ │ (5-dim) Encoder │ │ │
│ │ (64-dim) │ │ │
│ │ ▼ │ │
│ │ KB Feats ──► Modality ──► Cross-Modal ──► Fusion ──► Fatigue Head │ │
│ │ (5-dim) Encoder Attention Layer (sigmoid) │ │
│ │ (64-dim) │ │ │ │
│ │ ▲ │ │ │ │
│ │ Screen ──► Modality ──┘ │ │ ├──► Stress Head │ │
│ │ (5-dim) Encoder │ │ │ (sigmoid) │ │
│ │ (64-dim) │ │ │ │ │
│ │ │ │ ├──► Attention Head │ │
│ │ Voice ──► Modality ──┐ │ │ │ (sigmoid) │ │
│ │ (8-dim) Encoder │ │ │ │ │
│ │ (64-dim) │ │ ├──► Load Head │ │
│ │ └────┘ │ (sigmoid) │ │
│ │ │ │ │
│ │ └──► Confidence Head │ │
│ │ (sigmoid) │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│ │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ Training Pipeline │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │ │
│ │ │ DEAP Dataset│ │ DROZY Dataset│ │ SEED │ │ Custom │ │ │
│ │ │ (32 subj) │ │ (14 subj) │ │ Dataset │ │ Collection │ │ │
│ │ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │ │
│ │ └────────────────┼─────────────────┼────────────────┘ │ │
│ │