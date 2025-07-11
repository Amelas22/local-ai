"""
Database configuration fix to prioritize environment variables over .env file
"""

import os
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration for metadata storage"""

    url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/clerk_legal_ai",
        ),
        env="DATABASE_URL",
    )
    echo: bool = Field(False, env="DATABASE_ECHO")
    pool_size: int = Field(5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(10, env="DATABASE_MAX_OVERFLOW")

    class Config:
        # Don't use env_prefix for DATABASE_URL to avoid conflicts
        env_prefix = ""
        # Prioritize environment variables over .env file
        env_file = None  # Disable .env file loading for this class

    @property
    def async_url(self) -> str:
        """Get async version of database URL"""
        return self.url.replace("postgresql://", "postgresql+asyncpg://")
