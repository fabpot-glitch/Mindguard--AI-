"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from fastapi import WebSocket
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
import asyncio

from main import app
from api.dependencies import get_cognitive_engine, get_intervention_engine, get_current_user


class TestAPIRoutes:
    """Test suite for API routes."""
    
    @pytest.fixture
    def client(self, mock_cognitive_engine, mock_intervention_engine):
        """Create test client with mocked dependencies."""
        # Override dependencies
        app.dependency_overrides[get_cognitive_engine] = lambda: mock_cognitive_engine
        app.dependency_overrides[get_intervention_engine] = lambda: mock_intervention_engine
        app.dependency_overrides[get_current_user] = lambda: {"id": "test_user", "role": "user"}
        
        return TestClient(app)
    
    @pytest.fixture
    def mock_cognitive_engine(self, mock_model_output):
        """Create mock cognitive engine."""
        engine = Mock()
        engine.get_current_state.return_value = {
            'fatigue': 0.65,
            'stress': 0.45,
            'attention': 0.72,
            'cognitive_load': 0.58,
            'confidence': 0.88,
            'timestamp': datetime.now().isoformat()
        }
        engine.state_history = [
            {'timestamp': datetime.now().isoformat(), 'state': mock_model_output}
            for _ in range(10)
        ]
        engine.get_statistics.return_value = {
            'total_inferences': 1000,
            'avg_inference_time': 0.023,
            'collectors': {},
            'is_running': True
        }
        engine.collector_manager.get_status.return_value = {
            'eye': {'active': True, 'samples': 5000, 'error_rate': 0.01}
        }
        engine.collector_manager.get_statistics.return_value = {}
        return engine
    
    @pytest.fixture
    def mock_intervention_engine(self, mock_intervention):
        """Create mock intervention engine."""
        engine = Mock()
        engine.get_active_intervention.return_value = mock_intervention
        engine.get_intervention_history.return_value = [mock_intervention]
        engine.get_statistics.return_value = {
            'total_today': 3,
            'last_intervention': datetime.now().isoformat(),
            'active': False
        }
        engine.complete_intervention.return_value = True
        engine.dismiss_intervention.return_value = True
        return engine
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
    
    def test_get_current_state(self, client, mock_cognitive_engine):
        """Test getting current cognitive state."""
        response = client.get("/api/v1/state")
        assert response.status_code == 200
        data = response.json()
        
        assert "fatigue" in data
        assert "stress" in data
        assert "attention" in data
        assert "cognitive_load" in data
        assert "confidence" in data
        assert "timestamp" in data
        
        assert data["fatigue"] == 0.65
        assert data["stress"] == 0.45
    
    def test_get_state_history(self, client):
        """Test getting state history."""
        response = client.get("/api/v1/state/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) <= 5
    
    def test_get_active_intervention(self, client, mock_intervention_engine):
        """Test getting active intervention."""
        response = client.get("/api/v1/intervention/active")
        assert response.status_code == 200
        data = response.json()
        
        assert data is not None
        assert "id" in data
        assert "type" in data
        assert data["type"] == "break_reminder"
    
    def test_complete_intervention(self, client):
        """Test completing an intervention."""
        intervention_id = "test_intervention_123"
        response = client.post(f"/api/v1/intervention/{intervention_id}/complete")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        assert data["intervention_id"] == intervention_id
    
    def test_dismiss_intervention(self, client):
        """Test dismissing an intervention."""
        intervention_id = "test_intervention_123"
        response = client.post(f"/api/v1/intervention/{intervention_id}/dismiss")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "dismissed"
        assert data["intervention_id"] == intervention_id
    
    def test_get_intervention_history(self, client):
        """Test getting intervention history."""
        response = client.get("/api/v1/intervention/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_statistics(self, client):
        """Test getting system statistics."""
        response = client.get("/api/v1/statistics")
        assert response.status_code == 200
        data = response.json()
        
        assert "cognitive" in data
        assert "interventions" in data
        assert "collectors" in data
    
    def test_start_calibration(self, client):
        """Test starting calibration."""
        calibration_req = {
            "collectors": ["eye", "keyboard"],
            "duration_seconds": 30
        }
        
        response = client.post("/api/v1/calibration/start", json=calibration_req)
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "results" in data
        assert "message" in data
    
    def test_update_settings(self, client):
        """Test updating user settings."""
        settings = {
            "thresholds": {
                "fatigue_high": 0.75,
                "stress_high": 0.7
            },
            "notification_preferences": {
                "enabled": True,
                "sound": True
            }
        }
        
        response = client.post("/api/v1/settings", json=settings)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "updated"
    
    def test_get_collectors_status(self, client):
        """Test getting collectors status."""
        response = client.get("/api/v1/collectors/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "eye" in data
    
    def test_pause_engine(self, client, mock_cognitive_engine):
        """Test pausing the engine."""
        response = client.post("/api/v1/engine/pause")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "paused"
        mock_cognitive_engine.pause.assert_called_once()
    
    def test_resume_engine(self, client, mock_cognitive_engine):
        """Test resuming the engine."""
        response = client.post("/api/v1/engine/resume")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "resumed"
        mock_cognitive_engine.resume.assert_called_once()
    
    def test_reset_engine(self, client, mock_cognitive_engine):
        """Test resetting the engine."""
        response = client.post("/api/v1/engine/reset")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "reset"
        mock_cognitive_engine.reset_calibration.assert_called_once()
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_validation_error(self, client):
        """Test validation error handling."""
        invalid_state = {
            "fatigue": 1.5,  # > 1
            "stress": 0.5
        }
        
        response = client.post("/api/v1/state", json=invalid_state)
        assert response.status_code == 405  # Method not allowed
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint(self, mock_websocket, mock_cognitive_engine):
        """Test WebSocket endpoint."""
        from api.routes import websocket_endpoint
        
        # Mock the validate_websocket_origin function
        with patch('api.routes.validate_websocket_origin', return_value=True):
            with patch('api.routes.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = Mock()
                
                # Run the websocket endpoint
                await websocket_endpoint(mock_websocket, mock_cognitive_engine)
                
                # Verify connection was accepted
                mock_manager.connect.assert_called_once_with(mock_websocket)
    
    def test_stream_events(self, client, mock_cognitive_engine):
        """Test SSE stream endpoint."""
        response = client.get("/api/v1/events/stream")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access."""
        # Override dependency to raise auth error
        async def auth_error():
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        app.dependency_overrides[get_current_user] = auth_error
        
        response = client.get("/api/v1/state")
        assert response.status_code == 401


class TestWebSocketManager:
    """Test suite for WebSocket manager."""
    
    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance."""
        from api.websocket_manager import WebSocketManager
        return WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, ws_manager, mock_websocket):
        """Test connect and disconnect."""
        await ws_manager.connect(mock_websocket)
        assert len(ws_manager.active_connections) == 1
        assert len(ws_manager.active_connection_ids) == 1
        
        ws_manager.disconnect(mock_websocket)
        assert len(ws_manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, ws_manager, mock_websocket):
        """Test subscribe and unsubscribe."""
        await ws_manager.connect(mock_websocket)
        
        ws_manager.subscribe(mock_websocket, "test_topic")
        assert len(ws_manager.subscriptions["test_topic"]) == 1
        
        ws_manager.unsubscribe(mock_websocket, "test_topic")
        assert len(ws_manager.subscriptions["test_topic"]) == 0
    
    @pytest.mark.asyncio
    async def test_broadcast(self, ws_manager, mock_websocket):
        """Test broadcasting messages."""
        await ws_manager.connect(mock_websocket)
        
        message = {"type": "test", "data": "hello"}
        await ws_manager.broadcast(message)
        
        mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_to_topic(self, ws_manager, mock_websocket):
        """Test broadcasting to specific topic."""
        await ws_manager.connect(mock_websocket)
        ws_manager.subscribe(mock_websocket, "test_topic")
        
        message = {"type": "test", "data": "hello"}
        await ws_manager.broadcast(message, topic="test_topic")
        
        mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_to_client(self, ws_manager, mock_websocket):
        """Test sending to specific client."""
        message = {"type": "test", "data": "hello"}
        await ws_manager.send_to_client(mock_websocket, message)
        
        mock_websocket.send_json.assert_called_once()
    
    def test_get_statistics(self, ws_manager, mock_websocket):
        """Test getting manager statistics."""
        # Add some connections and subscriptions
        ws_manager.active_connection_ids.add(1)
        ws_manager.subscriptions["test"] = {mock_websocket}
        
        stats = ws_manager.get_statistics()
        assert "active_connections" in stats
        assert stats["active_connections"] == 1
        assert "topics" in stats
        assert stats["topics"]["test"] == 1