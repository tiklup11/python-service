import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import WebSocket, WebSocketDisconnect

from gemini_manager import GeminiAudioManager
from config import settings

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Handles WebSocket connections for audio streaming with Gemini"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    def _get_client_id(self, websocket: WebSocket) -> str:
        """Generate unique client ID for WebSocket connection"""
        return f"{websocket.client.host}:{websocket.client.port}"
    
    async def handle_connection(self, websocket: WebSocket) -> None:
        """Main WebSocket endpoint handler for audio streaming"""
        await websocket.accept()
        client_id = self._get_client_id(websocket)
        self.active_connections[client_id] = websocket
        
        logger.info(f"WebSocket connection accepted from {client_id}")
        
        session_manager = GeminiAudioManager(
            api_key=settings.gemini.api_key,
            model=settings.gemini.model,
            voice_name=settings.gemini.voice_name
        )
        
        try:
            await session_manager.connect()
            logger.info(f"Gemini session established for client {client_id}")
            
            await self._send_json(websocket, {
                "type": "connection_established",
                "message": "Connected to Gemini Live API",
                "timestamp": datetime.now().isoformat()
            })
            
            await asyncio.gather(
                self._forward_client_to_gemini(websocket, session_manager, client_id),
                self._forward_gemini_to_client(websocket, session_manager, client_id),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
            
            try:
                await self._send_json(websocket, {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            except:
                pass
        
        finally:
            await session_manager.disconnect()
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            logger.info(f"Cleaned up session for client {client_id}")
    
    async def _forward_client_to_gemini(
        self, 
        websocket: WebSocket, 
        session_manager: GeminiAudioManager, 
        client_id: str
    ) -> None:
        """Forward audio from client to Gemini"""
        try:
            while True:
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        audio_data = message["bytes"]
                        logger.debug(f"Received {len(audio_data)} bytes from client {client_id}")
                        await session_manager.send_audio(audio_data)
                        
                    elif "text" in message:
                        text_data = message["text"]
                        logger.info(f"Received text from client {client_id}: {text_data}")
                        
                        try:
                            json_data = json.loads(text_data)
                            await self._handle_control_message(websocket, json_data)
                        except json.JSONDecodeError:
                            pass
                
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error in client->gemini forwarding for {client_id}: {e}")
    
    async def _forward_gemini_to_client(
        self, 
        websocket: WebSocket, 
        session_manager: GeminiAudioManager, 
        client_id: str
    ) -> None:
        """Forward responses from Gemini to client"""
        try:
            async for response in session_manager.receive_responses():
                if response['type'] == 'audio':
                    await websocket.send_bytes(response['data'])
                    logger.debug(f"Sent {len(response['data'])} bytes to client {client_id}")
                    
                    await self._send_json(websocket, {
                        "type": "audio_metadata",
                        "bytes": len(response['data']),
                        "interrupted": response['interrupted'],
                        "turn_complete": response['turn_complete'],
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif response['type'] == 'text':
                    await self._send_json(websocket, {
                        "type": "text_response",
                        "text": response['text'],
                        "interrupted": response['interrupted'],
                        "turn_complete": response['turn_complete'],
                        "timestamp": datetime.now().isoformat()
                    })
                        
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected during Gemini forwarding")
        except Exception as e:
            logger.error(f"Error in gemini->client forwarding for {client_id}: {e}")
    
    async def _handle_control_message(self, websocket: WebSocket, json_data: Dict[str, Any]) -> None:
        """Handle control messages from client"""
        if json_data.get("type") == "ping":
            await self._send_json(websocket, {
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            })
    
    async def _send_json(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Send JSON data to WebSocket client"""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending JSON to WebSocket: {e}")


websocket_handler = WebSocketHandler()