"""WebSocket connection manager for real-time updates."""

from fastapi import WebSocket
from typing import Set, Dict, Any, Optional
import asyncio
import json
from datetime import datetime
from collections import defaultdict
import threading

from config.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manage WebSocket connections and broadcasts."""
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: Set[WebSocket] = set()
        self.active_connection_ids: Set[int] = set()  # Track IDs separately for logging
        self.subscriptions: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.connection_info: Dict[int, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()  # For async methods
        self._thread_lock = threading.Lock()  # For non-async methods
        
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            self.active_connections.add(websocket)
            ws_id = id(websocket)
            self.active_connection_ids.add(ws_id)
            self.connection_info[ws_id] = {
                "connected_at": datetime.now(),
                "client_host": websocket.client.host if websocket.client else "unknown",
                "topics": set()
            }
        
        logger.info(f"WebSocket client connected. Total: {len(self.active_connection_ids)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket (non-async version for callbacks)."""
        ws_id = id(websocket)
        
        # Use thread lock for non-async operations
        with self._thread_lock:
            # Remove from active connections
            if websocket in self.active_connections:
                self.active_connections.discard(websocket)
            
            # Remove from connection IDs
            self.active_connection_ids.discard(ws_id)
            
            # Remove from all subscriptions
            for topic in list(self.subscriptions.keys()):
                if websocket in self.subscriptions[topic]:
                    self.subscriptions[topic].discard(websocket)
            
            # Remove connection info
            if ws_id in self.connection_info:
                del self.connection_info[ws_id]
        
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connection_ids)}")
    
    async def disconnect_async(self, websocket: WebSocket):
        """Remove disconnected WebSocket (async version)."""
        ws_id = id(websocket)
        
        async with self._lock:
            # Remove from active connections
            self.active_connections.discard(websocket)
            
            # Remove from connection IDs
            self.active_connection_ids.discard(ws_id)
            
            # Remove from all subscriptions
            for topic in list(self.subscriptions.keys()):
                self.subscriptions[topic].discard(websocket)
            
            # Remove connection info
            if ws_id in self.connection_info:
                del self.connection_info[ws_id]
        
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connection_ids)}")
    
    def subscribe(self, websocket: WebSocket, topic: str):
        """
        Subscribe to a topic.
        
        Args:
            websocket: WebSocket connection
            topic: Topic to subscribe to
        """
        # Use thread lock for non-async operation
        with self._thread_lock:
            self.subscriptions[topic].add(websocket)
            
            # Update connection info
            ws_id = id(websocket)
            if ws_id in self.connection_info:
                self.connection_info[ws_id]["topics"].add(topic)
        
        logger.debug(f"Client subscribed to {topic}")
    
    async def subscribe_async(self, websocket: WebSocket, topic: str):
        """
        Subscribe to a topic (async version).
        
        Args:
            websocket: WebSocket connection
            topic: Topic to subscribe to
        """
        async with self._lock:
            self.subscriptions[topic].add(websocket)
            
            # Update connection info
            ws_id = id(websocket)
            if ws_id in self.connection_info:
                self.connection_info[ws_id]["topics"].add(topic)
        
        logger.debug(f"Client subscribed to {topic}")
    
    def unsubscribe(self, websocket: WebSocket, topic: str):
        """
        Unsubscribe from a topic.
        
        Args:
            websocket: WebSocket connection
            topic: Topic to unsubscribe from
        """
        with self._thread_lock:
            if topic in self.subscriptions:
                self.subscriptions[topic].discard(websocket)
                
                # Update connection info
                ws_id = id(websocket)
                if ws_id in self.connection_info:
                    self.connection_info[ws_id]["topics"].discard(topic)
        
        logger.debug(f"Client unsubscribed from {topic}")
    
    async def unsubscribe_async(self, websocket: WebSocket, topic: str):
        """
        Unsubscribe from a topic (async version).
        
        Args:
            websocket: WebSocket connection
            topic: Topic to unsubscribe from
        """
        async with self._lock:
            if topic in self.subscriptions:
                self.subscriptions[topic].discard(websocket)
                
                # Update connection info
                ws_id = id(websocket)
                if ws_id in self.connection_info:
                    self.connection_info[ws_id]["topics"].discard(topic)
        
        logger.debug(f"Client unsubscribed from {topic}")
    
    async def broadcast(self, message: Dict[str, Any], topic: Optional[str] = None):
        """
        Broadcast message to all or topic subscribers.
        
        Args:
            message: Message to broadcast
            topic: Optional topic to filter subscribers
        """
        if topic and topic in self.subscriptions:
            # Broadcast to topic subscribers
            async with self._lock:
                connections = list(self.subscriptions[topic])
            await self._broadcast_to_connections(connections, message, topic)
        else:
            # Broadcast to all connections
            async with self._lock:
                connections = list(self.active_connections)
            await self._broadcast_to_connections(connections, message, "all")
    
    async def _broadcast_to_connections(
        self,
        connections: list,
        message: Dict[str, Any],
        broadcast_type: str
    ):
        """Broadcast message to specific connections."""
        if not connections:
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        # Convert to JSON
        try:
            message_json = json.dumps(message)
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            return
        
        # Send to all connections
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to {broadcast_type}: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect_async(websocket)
        
        if broadcast_type == "all":
            logger.debug(f"Broadcast to {len(connections) - len(disconnected)} clients")
        else:
            logger.debug(f"Broadcast to {len(connections) - len(disconnected)} subscribers of {broadcast_type}")
    
    async def send_to_client(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific client."""
        try:
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            await self.disconnect_async(websocket)
    
    async def send_state(self, websocket: WebSocket, state: Any):
        """Send cognitive state to specific client."""
        if hasattr(state, 'dict'):
            state_data = state.dict()
        elif isinstance(state, dict):
            state_data = state
        else:
            state_data = {"state": str(state)}
        
        await self.send_to_client(websocket, {
            "type": "state_update",
            "data": state_data
        })
    
    async def send_intervention(self, websocket: WebSocket, intervention: Any):
        """Send intervention to specific client."""
        if hasattr(intervention, 'dict'):
            intervention_data = intervention.dict()
        elif isinstance(intervention, dict):
            intervention_data = intervention
        else:
            intervention_data = {"intervention": str(intervention)}
        
        await self.send_to_client(websocket, {
            "type": "intervention",
            "data": intervention_data
        })
    
    async def send_alert(self, websocket: WebSocket, alert: Dict[str, Any]):
        """Send alert to specific client."""
        await self.send_to_client(websocket, {
            "type": "alert",
            "data": alert
        })
    
    async def broadcast_state(self, state: Any):
        """Broadcast state update to all clients."""
        if hasattr(state, 'dict'):
            state_data = state.dict()
        elif isinstance(state, dict):
            state_data = state
        else:
            state_data = {"state": str(state)}
        
        await self.broadcast({
            "type": "state_update",
            "data": state_data
        })
    
    async def broadcast_intervention(self, intervention: Any):
        """Broadcast intervention to all clients."""
        if hasattr(intervention, 'dict'):
            intervention_data = intervention.dict()
        elif isinstance(intervention, dict):
            intervention_data = intervention
        else:
            intervention_data = {"intervention": str(intervention)}
        
        await self.broadcast({
            "type": "intervention",
            "data": intervention_data
        })
    
    async def broadcast_alert(self, alert: Dict[str, Any]):
        """Broadcast alert to all clients."""
        await self.broadcast({
            "type": "alert",
            "data": alert
        })
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        with self._thread_lock:
            return len(self.active_connection_ids)
    
    def get_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers to a topic."""
        with self._thread_lock:
            return len(self.subscriptions.get(topic, set()))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        with self._thread_lock:
            return {
                "active_connections": len(self.active_connection_ids),
                "topics": {
                    topic: len(subscribers)
                    for topic, subscribers in self.subscriptions.items()
                },
                "connections": [
                    {
                        "id": ws_id,
                        "connected_at": info["connected_at"].isoformat(),
                        "client_host": info["client_host"],
                        "topics": list(info["topics"])
                    }
                    for ws_id, info in self.connection_info.items()
                ]
            }
    
    async def close_all(self):
        """Close all active connections."""
        async with self._lock:
            connections = list(self.active_connections)
            for websocket in connections:
                try:
                    await websocket.close()
                except:
                    pass
            
            self.active_connections.clear()
            self.active_connection_ids.clear()
            self.subscriptions.clear()
            self.connection_info.clear()
        
        logger.info("All WebSocket connections closed")