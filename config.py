import os
from typing import Optional
from pydantic_settings import BaseSettings


class GeminiConfig(BaseSettings):
    """Configuration for Gemini Live API"""
    
    api_key: str
    model: str = "gemini-live-2.5-flash-preview"
    voice_name: str = "Aoede"  # Available: Aoede, Charon, Fenrir, Puck
    system_instruction: str = "You are a helpful AI assistant. Respond naturally and conversationally."
    
    class Config:
        env_prefix = "GEMINI_"


class ServerConfig(BaseSettings):
    """Server configuration"""
    
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    reload: bool = True
    
    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_prefix = "SERVER_"


class Settings:
    """Application settings"""
    
    def __init__(self):
        # Check for required environment variables
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required!")
        
        self.gemini = GeminiConfig(api_key=google_api_key)
        self.server = ServerConfig()


# Global settings instance
settings = Settings()