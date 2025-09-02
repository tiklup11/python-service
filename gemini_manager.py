import logging
from typing import Optional, AsyncGenerator, Dict, Any

try:
    from google import genai
    from google.genai import types
except ImportError:
    raise ImportError("Please install: pip install google-genai")

logger = logging.getLogger(__name__)


class GeminiAudioManager:
    """Manages connection and communication with Gemini Live API"""
    
    def __init__(self, api_key: str, model: str = "gemini-live-2.5-flash-preview", voice_name: str = "Aoede"):
        self.api_key = api_key
        self.model = model
        self.voice_name = voice_name
        self.client: Optional[genai.Client] = None
        self.session = None
        self.is_connected = False
        
        self._config = self._build_config()
        
    def _build_config(self) -> Dict[str, Any]:
        """Build configuration for Gemini Live API"""
        return {
            "response_modalities": ["AUDIO"],
            "generation_config": {
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": self.voice_name
                        }
                    }
                }
            },
            "system_instruction": "You are a helpful AI assistant. Respond naturally and conversationally."
        }
        
    async def connect(self) -> None:
        """Establish connection to Gemini Live API"""
        try:
            logger.info("Connecting to Gemini Live API...")
            
            self.client = genai.Client(api_key=self.api_key)
            
            self.session = await self.client.aio.live.connect(
                model=self.model,
                config=self._config
            ).__aenter__()
            
            self.is_connected = True
            logger.info(f"Successfully connected to Gemini Live API with model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live API: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close connection to Gemini Live API"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
                logger.info("Gemini Live API session closed")
            
            self.is_connected = False
            self.session = None
            
        except Exception as e:
            logger.error(f"Error disconnecting from Gemini: {e}")
    
    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio data to Gemini"""
        if not self.session:
            raise RuntimeError("No active Gemini session")
        
        try:
            await self.session.send_realtime_input(
                audio=types.Blob(
                    data=audio_data,
                    mime_type="audio/pcm;rate=16000"
                )
            )
            logger.debug(f"Sent {len(audio_data)} bytes to Gemini")
            
        except Exception as e:
            logger.error(f"Error sending audio to Gemini: {e}")
            raise
    
    async def receive_responses(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Generator that yields responses from Gemini"""
        if not self.session:
            raise RuntimeError("No active Gemini session")
        
        try:
            async for response in self.session.receive():
                logger.debug(f"Received response from Gemini: {type(response)}")
                
                if hasattr(response, 'server_content') and response.server_content:
                    server_content = response.server_content
                    
                    if hasattr(server_content, 'model_turn') and server_content.model_turn:
                        model_turn = server_content.model_turn
                        
                        if hasattr(model_turn, 'parts') and model_turn.parts:
                            for part in model_turn.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    audio_data = part.inline_data.data
                                    logger.debug(f"Yielding {len(audio_data)} bytes of audio")
                                    yield {
                                        'type': 'audio',
                                        'data': audio_data,
                                        'interrupted': getattr(server_content, 'interrupted', False),
                                        'turn_complete': getattr(server_content, 'turn_complete', False)
                                    }
                                
                                if hasattr(part, 'text') and part.text:
                                    logger.info(f"Gemini text response: {part.text}")
                                    yield {
                                        'type': 'text',
                                        'text': part.text,
                                        'interrupted': getattr(server_content, 'interrupted', False),
                                        'turn_complete': getattr(server_content, 'turn_complete', False)
                                    }
                
                elif hasattr(response, 'tool_call') and response.tool_call:
                    logger.info(f"Received tool call: {response.tool_call}")
                
                else:
                    logger.debug(f"Unhandled response type: {response}")
                    
        except Exception as e:
            logger.error(f"Error receiving from Gemini: {e}")
            raise