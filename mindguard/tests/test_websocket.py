"""Tests for WebSocket functionality."""

import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket, WebSocketDisconnect

from api.websocket_manager import WebSocketManager
from api.dependencies import validate_websocket_origin


class TestWebSocketManager:
    """Test suite for WebSocketManager."""
    
    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance."""
        return WebSocketManager()
    
    @pytest.mark.asyncio
    async def test_connect(self, ws_manager, mock_websocket):
        """Test client connection."""
        await ws_manager.connect(mock_websocket)
        
        assert len(ws_manager.active_connections) == 1
        assert len(ws_manager.active_connection_ids) == 1
        assert len(ws_manager.connection_info) == 1
        
        # Verify connection info
        ws_id = id(mock_websocket)
        assert ws_id in ws_manager.connection_info
        assert "connected_at" in ws_manager.connection_info[ws_id]
        assert ws_manager.connection_info[ws_id]["client_host"] == "127.0.0.1"
    
    @pytest.mark.asyncio
    async def test_disconnect(self, ws_manager, mock_websocket):
        """Test client disconnection."""
        await ws_manager.connect(mock_websocket)
        ws_manager.subscribe(mock_websocket, "test_topic")
        
        assert len(ws_manager.active_connections) == 1
        
        ws_manager.disconnect(mock_websocket)
        
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.subscriptions.get("test_topic", set())) == 0
    
    @pytest.mark.asyncio
    async def test_disconnect_async(self, ws_manager, mock_websocket):
        """Test async client disconnection."""
        await ws_manager.connect(mock_websocket)
        await ws_manager.subscribe_async(mock_websocket, "test_topic")
        
        assert len(ws_manager.active_connections) == 1
        
        await ws_manager.disconnect_async(mock_websocket)
        
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.subscriptions.get("test_topic", set())) == 0
    
    @pytest.mark.asyncio
    async def test_subscribe(self, ws_manager, mock_websocket):
        """Test topic subscription."""
        await ws_manager.connect(mock_websocket)
        
        ws_manager.subscribe(mock_websocket, "test_topic")
        
        assert "test_topic" in ws_manager.subscriptions
        assert mock_websocket in ws_manager.subscriptions["test_topic"]
        
        # Check connection info updated
        ws_id = id(mock_websocket)
        assert "test_topic" in ws_manager.connection_info[ws_id]["topics"]
    
    @pytest.mark.asyncio
    async def test_subscribe_async(self, ws_manager, mock_websocket):
        """Test async topic subscription."""
        await ws_manager.connect(mock_websocket)
        
        await ws_manager.subscribe_async(mock_websocket, "test_topic")
        
        assert "test_topic" in ws_manager.subscriptions
        assert mock_websocket in ws_manager.subscriptions["test_topic"]
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, ws_manager, mock_websocket):
        """Test topic unsubscription."""
        await ws_manager.connect(mock_websocket)
        ws_manager.subscribe(mock_websocket, "test_topic")
        
        assert mock_websocket in ws_manager.subscriptions["test_topic"]
        
        ws_manager.unsubscribe(mock_websocket, "test_topic")
        
        assert mock_websocket not in ws_manager.subscriptions["test_topic"]
    
    @pytest.mark.asyncio
    async def test_broadcast_all(self, ws_manager, mock_websocket):
        """Test broadcasting to all clients."""
        await ws_manager.connect(mock_websocket)
        
        message = {"type": "test", "data": "hello"}
        await ws_manager.broadcast(message)
        
        mock_websocket.send_text.assert_called_once()
        # Verify message content
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_message = json.loads(call_args)
        assert sent_message["type"] == "test"
        assert sent_message["data"] == "hello"
        assert "timestamp" in sent_message
    
    @pytest.mark.asyncio
    async def test_broadcast_topic(self, ws_manager, mock_websocket):
        """Test broadcasting to topic subscribers."""
        await ws_manager.connect(mock_websocket)
        ws_manager.subscribe(mock_websocket, "test_topic")
        
        # Create another client not subscribed
        mock_websocket2 = AsyncMock()
        mock_websocket2.client.host = "127.0.0.2"
        await ws_manager.connect(mock_websocket2)
        
        message = {"type": "test", "data": "topic_message"}
        await ws_manager.broadcast(message, topic="test_topic")
        
        # First client should receive
        mock_websocket.send_text.assert_called_once()
        # Second client should not receive
        mock_websocket2.send_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_to_client(self, ws_manager, mock_websocket):
        """Test sending to specific client."""
        message = {"type": "test", "data": "direct"}
        await ws_manager.send_to_client(mock_websocket, message)
        
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "test"
        assert sent_message["data"] == "direct"
    
    @pytest.mark.asyncio
    async def test_send_state(self, ws_manager, mock_websocket, mock_cognitive_state):
        """Test sending cognitive state."""
        await ws_manager.send_state(mock_websocket, mock_cognitive_state)
        
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "state_update"
        assert sent_message["data"] == mock_cognitive_state
    
    @pytest.mark.asyncio
    async def test_send_intervention(self, ws_manager, mock_websocket, mock_intervention):
        """Test sending intervention."""
        await ws_manager.send_intervention(mock_websocket, mock_intervention)
        
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "intervention"
        assert sent_message["data"] == mock_intervention
    
    @pytest.mark.asyncio
    async def test_broadcast_state(self, ws_manager, mock_websocket, mock_cognitive_state):
        """Test broadcasting state update."""
        await ws_manager.connect(mock_websocket)
        
        await ws_manager.broadcast_state(mock_cognitive_state)
        
        mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_intervention(self, ws_manager, mock_websocket, mock_intervention):
        """Test broadcasting intervention."""
        await ws_manager.connect(mock_websocket)
        
        await ws_manager.broadcast_intervention(mock_intervention)
        
        mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_disconnected_client(self, ws_manager, mock_websocket):
        """Test handling of disconnected client during broadcast."""
        await ws_manager.connect(mock_websocket)
        
        # Make send_text raise exception
        mock_websocket.send_text.side_effect = Exception("Connection lost")
        
        message = {"type": "test", "data": "hello"}
        await ws_manager.broadcast(message)
        
        # Client should be removed
        assert len(ws_manager.active_connections) == 0
    
    def test_get_connection_count(self, ws_manager, mock_websocket):
        """Test getting connection count."""
        assert ws_manager.get_connection_count() == 0
        
        ws_manager.active_connection_ids.add(1)
        assert ws_manager.get_connection_count() == 1
    
    def test_get_subscriber_count(self, ws_manager, mock_websocket):
        """Test getting subscriber count for topic."""
        assert ws_manager.get_subscriber_count("test_topic") == 0
        
        ws_manager.subscriptions["test_topic"].add(mock_websocket)
        assert ws_manager.get_subscriber_count("test_topic") == 1
    
    def test_get_statistics(self, ws_manager, mock_websocket):
        """Test getting manager statistics."""
        ws_manager.active_connection_ids.add(1)
        ws_manager.active_connection_ids.add(2)
        ws_manager.subscriptions["topic1"] = {mock_websocket}
        ws_manager.subscriptions["topic2"] = {mock_websocket, mock_websocket}
        
        stats = ws_manager.get_statistics()
        
        assert stats["active_connections"] == 2
        assert stats["topics"]["topic1"] == 1
        assert stats["topics"]["topic2"] == 2
    
    @pytest.mark.asyncio
    async def test_close_all(self, ws_manager, mock_websocket):
        """Test closing all connections."""
        await ws_manager.connect(mock_websocket)
        ws_manager.subscribe(mock_websocket, "test_topic")
        
        assert len(ws_manager.active_connections) == 1
        
        await ws_manager.close_all()
        
        assert len(ws_manager.active_connections) == 0
        assert len(ws_manager.subscriptions) == 0
        mock_websocket.close.assert_called_once()


class TestWebSocketValidation:
    """Test suite for WebSocket validation."""
    
    @pytest.mark.asyncio
    async def test_validate_origin_allowed(self, mock_websocket):
        """Test origin validation with allowed origin."""
        mock_websocket.headers = {"origin": "http://localhost:3000"}
        
        with patch('api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.api.cors_origins = ["http://localhost:3000"]
            
            result = await validate_websocket_origin(mock_websocket)
            assert result == True
    
    @pytest.mark.asyncio
    async def test_validate_origin_denied(self, mock_websocket):
        """Test origin validation with denied origin."""
        mock_websocket.headers = {"origin": "http://malicious-site.com"}
        
        with patch('api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.api.cors_origins = ["http://localhost:3000"]
            
            result = await validate_websocket_origin(mock_websocket)
            assert result == False
    
    @pytest.mark.asyncio
    async def test_validate_origin_missing(self, mock_websocket):
        """Test origin validation with missing origin."""
        mock_websocket.headers = {}
        
        with patch('api.dependencies.get_settings') as mock_settings:
            mock_settings.return_value.api.cors_origins = ["http://localhost:3000"]
            
            result = await validate_websocket_origin(mock_websocket)
            assert result == False


@pytest.mark.asyncio
async def test_websocket_endpoint_integration(
    mock_websocket,
    mock_cognitive_engine,
    mock_intervention_engine
):
    """Test WebSocket endpoint integration."""
    from api.routes import websocket_endpoint
    
    with patch('api.routes.validate_websocket_origin', return_value=True):
        with patch('api.routes.websocket_manager') as mock_manager:
            mock_manager.connect = AsyncMock()
            mock_manager.disconnect = Mock()
            mock_manager.subscribe = Mock()
            
            # Mock receive_text to simulate client messages
            mock_websocket.receive_text = AsyncMock(side_effect=[
                json.dumps({"type": "ping"}),
                json.dumps({"type": "subscribe", "topics": ["state"]}),
                WebSocketDisconnect()
            ])
            
            # Run the endpoint
            await websocket_endpoint(mock_websocket, mock_cognitive_engine)
            
            # Verify interactions
            mock_manager.connect.assert_called_once()
            mock_manager.disconnect.assert_called_once()
            
            # Should have sent pong response
            mock_websocket.send_json.assert_any_call({
                "type": "connection",
                "status": "connected",
                "timestamp": mock_websocket.send_json.call_args[0][0]["timestamp"]
            })