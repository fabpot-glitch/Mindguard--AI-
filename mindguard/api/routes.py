"""API routes for MindGuard AI."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import asyncio

from api.schemas import (
    CognitiveStateResponse,
    InterventionResponse,
    AlertResponse,
    StatisticsResponse,
    CalibrationRequest,
    CalibrationResponse,
    UserSettings,
    HealthResponse
)
from api.websocket_manager import WebSocketManager
from api.dependencies import (
    get_cognitive_engine,
    get_intervention_engine,
    get_websocket_manager,
    get_current_user,
    verify_api_key,
    standard_limiter,
    strict_limiter,
    validate_websocket_origin
)
from engine.cognitive_engine import CognitiveEngine
from engine.intervention_engine import InterventionEngine
from collectors.eye_collector import EyeCollector
from config.thresholds import get_fatigue_level, compute_fatigue
from config.logging_config import get_logger

router = APIRouter(prefix="/api/v1")
logger = get_logger(__name__)
websocket_manager = WebSocketManager()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    _: str = Depends(standard_limiter)
):
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@router.get("/state", response_model=CognitiveStateResponse)
async def get_current_state(
    request: Request,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(standard_limiter)
):
    """Get current cognitive state."""
    state = engine.get_current_state()
    if not state:
        raise HTTPException(status_code=503, detail="Engine not ready")

    state["user_id"] = user["id"]

    logger.info(f"State retrieved for user {user['id']}")
    return state


@router.get("/state/history", response_model=List[CognitiveStateResponse])
async def get_state_history(
    request: Request,
    limit: int = 100,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(standard_limiter)
):
    """Get cognitive state history."""
    history = list(engine.state_history)[-limit:]
    return [h["state"] for h in history]


@router.get("/intervention/active", response_model=Optional[InterventionResponse])
async def get_active_intervention(
    request: Request,
    engine: InterventionEngine = Depends(get_intervention_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(standard_limiter)
):
    """Get currently active intervention."""
    return engine.get_active_intervention()


@router.post("/intervention/{intervention_id}/complete")
async def complete_intervention(
    request: Request,
    intervention_id: str,
    engine: InterventionEngine = Depends(get_intervention_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(strict_limiter)
):
    """Mark intervention as completed."""
    success = engine.complete_intervention(intervention_id)
    if not success:
        raise HTTPException(status_code=404, detail="Intervention not found")

    logger.info(f"Intervention {intervention_id} completed by user {user['id']}")
    return {"status": "completed", "intervention_id": intervention_id}


@router.post("/intervention/{intervention_id}/dismiss")
async def dismiss_intervention(
    request: Request,
    intervention_id: str,
    engine: InterventionEngine = Depends(get_intervention_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(strict_limiter)
):
    """Dismiss intervention."""
    success = engine.dismiss_intervention(intervention_id)
    if not success:
        raise HTTPException(status_code=404, detail="Intervention not found")

    logger.info(f"Intervention {intervention_id} dismissed by user {user['id']}")
    return {"status": "dismissed", "intervention_id": intervention_id}


@router.get("/intervention/history", response_model=List[InterventionResponse])
async def get_intervention_history(
    request: Request,
    limit: int = 10,
    engine: InterventionEngine = Depends(get_intervention_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(standard_limiter)
):
    """Get intervention history."""
    return engine.get_intervention_history(limit)


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    request: Request,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    intervention_engine: InterventionEngine = Depends(get_intervention_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(standard_limiter)
):
    """Get system statistics."""
    return StatisticsResponse(
        cognitive=engine.get_statistics(),
        interventions=intervention_engine.get_statistics(),
        collectors=engine.collector_manager.get_statistics()
    )


@router.post("/calibration/start", response_model=CalibrationResponse)
async def start_calibration(
    request: Request,
    calibration_req: CalibrationRequest,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(strict_limiter)
):
    """Start calibration process."""
    engine.pause()

    try:
        results = {}
        for collector_name in calibration_req.collectors:
            collector = engine.collector_manager.collectors.get(collector_name)
            if collector:
                success = await asyncio.to_thread(collector.calibrate)
                results[collector_name] = success

        success = all(results.values())
        message = "Calibration completed" if success else "Partial calibration success"

        logger.info(f"Calibration completed for user {user['id']}: {results}")

        return CalibrationResponse(
            success=success,
            results=results,
            message=message
        )

    finally:
        engine.resume()


@router.post("/settings")
async def update_settings(
    request: Request,
    settings: UserSettings,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(strict_limiter)
):
    """Update user settings."""
    from config import config

    if settings.thresholds:
        for key, value in settings.thresholds.items():
            if hasattr(config.thresholds, key):
                setattr(config.thresholds, key, value)

    if settings.notification_preferences:
        pass

    logger.info(f"Settings updated for user {user['id']}")
    return {"status": "updated", "settings": settings.dict(exclude_unset=True)}


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    engine: CognitiveEngine = Depends(get_cognitive_engine)
):
    """WebSocket endpoint for real-time updates with live biometric processing."""
    if not await validate_websocket_origin(websocket):
        await websocket.close(code=1008)
        return

    await websocket_manager.connect(websocket)
    client_id = id(websocket)

    # One EyeCollector per connection — no shared global state between users
    eye = EyeCollector()

    try:
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat()
        })

        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30
                )

                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    message = {"type": "ping", "data": data}

                msg_type = message.get("type")

                # ── Ping / heartbeat ──────────────────────────────────
                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })

                # ── Pub/sub ───────────────────────────────────────────
                elif msg_type == "subscribe":
                    topics = message.get("topics", [])
                    for topic in topics:
                        websocket_manager.subscribe(websocket, topic)
                    await websocket.send_json({
                        "type": "subscribed",
                        "topics": topics
                    })

                elif msg_type == "unsubscribe":
                    topics = message.get("topics", [])
                    for topic in topics:
                        websocket_manager.unsubscribe(websocket, topic)

                # ── Pull current engine state ─────────────────────────
                elif msg_type == "get_state":
                    state = engine.get_current_state()
                    if state:
                        await websocket.send_json({
                            "type": "state_update",
                            "data": state,
                            "timestamp": datetime.now().isoformat()
                        })

                # ── Live biometric frame from browser ─────────────────
                elif msg_type == "sensor_data":
                    frame_b64   = message.get("frame", "")
                    wpm         = float(message.get("wpm", 0))
                    error_count = int(message.get("error_count", 0))
                    mouse_vel   = float(message.get("mouse_vel", 0))

                    # Run MediaPipe in thread pool — keeps event loop free
                    if frame_b64:
                        eye_metrics = await asyncio.to_thread(
                            eye.process_frame, frame_b64
                        )
                    else:
                        eye_metrics = {
                            "blink_rate":    0.0,
                            "perclos":       0.0,
                            "face_detected": False
                        }

                    fatigue = compute_fatigue(eye_metrics["perclos"], wpm)

                    state_payload = {
                        "fatigue_score":   fatigue,
                        "fatigue_level":   get_fatigue_level(fatigue),
                        "confidence":      0.88 if eye_metrics["face_detected"] else 0.50,
                        "trend":           0.001,
                        "session_average": fatigue,
                        "active_modalities": ["eye", "keyboard", "voice", "screen"],
                        "modality_weights": {
                            "eye":      0.35,
                            "keyboard": 0.30,
                            "voice":    0.20,
                            "screen":   0.15,
                        },
                        "metrics": {
                            "blink_rate": eye_metrics["blink_rate"],
                            "wpm":        wpm,
                            "perclos":    eye_metrics["perclos"],
                            "error_rate": error_count / max(wpm, 1),
                            "pitch_var":  18.0,
                            "mouse_vel":  mouse_vel,
                        }
                    }

                    await websocket.send_json({
                        "event": "state_update",
                        "data":  state_payload
                    })

                    logger.debug(
                        f"Client {client_id} | fatigue={fatigue} "
                        f"blink={eye_metrics['blink_rate']} "
                        f"perclos={eye_metrics['perclos']} "
                        f"face={'yes' if eye_metrics['face_detected'] else 'no'}"
                    )

                # ── Reset per-session counters ────────────────────────
                elif msg_type == "reset":
                    eye.reset()
                    logger.info(f"EyeCollector reset for client {client_id}")
                    await websocket.send_json({
                        "type":   "reset",
                        "status": "ok",
                        "timestamp": datetime.now().isoformat()
                    })

                # ── Unknown message type ──────────────────────────────
                else:
                    logger.warning(
                        f"Unknown message type '{msg_type}' from client {client_id}"
                    )
                    await websocket.send_json({
                        "type":    "error",
                        "message": f"Unknown message type: {msg_type}"
                    })

            except asyncio.TimeoutError:
                # 30s with no message — send heartbeat to keep connection alive
                await websocket.send_json({
                    "type":      "heartbeat",
                    "timestamp": datetime.now().isoformat()
                })

            except WebSocketDisconnect:
                break

            except Exception as e:
                logger.error(f"WebSocket error for client {client_id}: {e}")
                break

    except WebSocketDisconnect:
        pass

    except Exception as e:
        logger.error(f"WebSocket fatal error for client {client_id}: {e}")

    finally:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket client {client_id} disconnected")


@router.get("/events/stream")
async def stream_events(
    request: Request,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(standard_limiter)
):
    """Server-Sent Events (SSE) stream for real-time updates."""

    async def event_generator():
        last_state = None

        while True:
            try:
                if await request.is_disconnected():
                    break

                state = engine.get_current_state()

                if state and state != last_state:
                    yield f"data: {json.dumps({'type': 'state', 'data': state})}\n\n"
                    last_state = state

                yield ": heartbeat\n\n"

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"SSE error: {e}")
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/collectors/status")
async def get_collectors_status(
    request: Request,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(standard_limiter)
):
    """Get status of all collectors."""
    return engine.collector_manager.get_status()


@router.post("/engine/pause")
async def pause_engine(
    request: Request,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(strict_limiter)
):
    """Pause the cognitive engine."""
    engine.pause()
    logger.info(f"Engine paused by user {user['id']}")
    return {"status": "paused"}


@router.post("/engine/resume")
async def resume_engine(
    request: Request,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(strict_limiter)
):
    """Resume the cognitive engine."""
    engine.resume()
    logger.info(f"Engine resumed by user {user['id']}")
    return {"status": "resumed"}


@router.post("/engine/reset")
async def reset_engine(
    request: Request,
    engine: CognitiveEngine = Depends(get_cognitive_engine),
    user: dict = Depends(get_current_user),
    _: str = Depends(strict_limiter)
):
    """Reset the cognitive engine calibration."""
    engine.reset_calibration()
    logger.info(f"Engine reset by user {user['id']}")
    return {"status": "reset"}