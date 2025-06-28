"""
Configuration settings for Clerk Legal AI System
Handles environment variables and configuration management
"""

import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator, computed_field
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass

# Load environment variables
load_dotenv()


class OpenAISettings(BaseSettings):
    """OpenAI API configuration"""
    api_key: str = Field(..., env="OPENAI_API_KEY")
    base_url: Optional[str] = Field(None, env="OPENAI_BASE_URL")
    organization: Optional[str] = Field(None, env="OPENAI_ORGANIZATION")
    embedding_model: str = "text-embedding-3-small"
    context_model: str = os.getenv("CONTEXT_LLM_MODEL", "gpt-4.1-nano")
    
    class Config:
        env_prefix = "OPENAI_"


class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration"""
    host: str = Field("localhost", env="QDRANT_HOST")
    port: int = Field(6333, env="QDRANT_PORT")
    api_key: Optional[str] = Field(None, env="QDRANT_API_KEY")
    https: bool = Field(False, env="QDRANT_HTTPS")
    prefer_grpc: bool = Field(False, env="QDRANT_PREFER_GRPC")
    timeout: int = Field(30, env="QDRANT_TIMEOUT")  # seconds
    grpc_port: int = Field(6334, env="QDRANT_GRPC_PORT")
    collection_name: str = Field("legal_documents", env="QDRANT_COLLECTION_NAME")
    hybrid_collection_name: str = Field("legal_documents_hybrid", env="QDRANT_HYBRID_COLLECTION_NAME")
    registry_collection_name: str = Field("document_registry", env="QDRANT_REGISTRY_COLLECTION_NAME")
    batch_size: int = Field(500, env="QDRANT_BATCH_SIZE")
    max_workers: int = Field(16, env="QDRANT_MAX_WORKERS")
    embedding_dimensions: int = Field(1536, env="QDRANT_EMBEDDING_DIMENSIONS")
    https: bool = os.getenv("QDRANT_HTTPS", "false").lower() == "true"

    # Qdrant-specific settings
    distance_metric: str = "cosine"
    hnsw_m: int = 32
    hnsw_ef_construct: int = 200
    quantization_enabled: bool = True
    quantization_type: str = "scalar"
    quantization_quantile: float = 0.95
    quantization: bool = True

    class Config:
        env_prefix = "QDRANT_"
    
    @property
    def url(self) -> str:
        """Get Qdrant connection URL"""
        protocol = "https" if self.https else "http"
        return f"{protocol}://{self.host}:{self.port}"


@dataclass
class BoxConfig:
    """Box API configuration"""
    client_id: str = os.getenv("BOX_CLIENT_ID", "")
    client_secret: str = os.getenv("BOX_CLIENT_SECRET", "")
    enterprise_id: str = os.getenv("BOX_ENTERPRISE_ID", "")
    jwt_key_id: str = os.getenv("BOX_JWT_KEY_ID", "")
    private_key: str = os.getenv("BOX_PRIVATE_KEY", "").replace("\\n", "\n")
    passphrase: str = os.getenv("BOX_PASSPHRASE", "")
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.private_key and not self.private_key.startswith('-----BEGIN'):
            raise ValueError("BOX_PRIVATE_KEY must be a valid PEM-formatted private key")



class DatabaseSettings(BaseSettings):
    """Database configuration for metadata storage"""
    url: str = Field(
        "postgresql://localhost/clerk_legal_ai",
        env="DATABASE_URL"
    )
    echo: bool = Field(False, env="DATABASE_ECHO")
    pool_size: int = Field(5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    
    class Config:
        env_prefix = "DATABASE_"


class CacheSettings(BaseSettings):
    """Cache configuration"""
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    cache_ttl: int = Field(3600, env="CACHE_TTL")  # seconds
    enable_cache: bool = Field(True, env="ENABLE_CACHE")
    
    class Config:
        env_prefix = "CACHE_"


class SecuritySettings(BaseSettings):
    """Security configuration"""
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    class Config:
        env_prefix = "SECURITY_"

class CostConfig(BaseSettings):
    """API cost tracking configuration"""
    enable_tracking: bool = Field(True, env="ENABLE_TRACKING")
    save_reports: bool = Field(True, env="SAVE_REPORTS")
    report_directory: str = Field("logs", env="REPORT_DIRECTORY")
    custom_pricing: Optional[Dict[str, Any]] = Field(None, env="CUSTOM_PRICING")

class DocumentProcessingSettings(BaseSettings):
    """Document processing configuration"""
    target_chunk_size: int = Field(1200, env="CHUNK_SIZE")
    chunk_size: int = target_chunk_size
    overlap_size: int = Field(200, env="CHUNK_OVERLAP")
    chunk_overlap: int = overlap_size
    chunk_variance: int = Field(100, env="CHUNK_VARIANCE")
    min_chunk_size: int = Field(500, env="MIN_CHUNK_SIZE")
    max_chunk_size: int = Field(1500, env="MAX_CHUNK_SIZE")
    batch_size: int = Field(10, env="PROCESSING_BATCH_SIZE")
    max_retries: int = Field(3, env="PROCESSING_MAX_RETRIES")
    retry_delay: int = Field(5, env="PROCESSING_RETRY_DELAY")
    max_file_size_mb: int = Field(100, env="MAX_FILE_SIZE_MB")
    supported_extensions: tuple = (".pdf",)
    ocr_enabled: bool = Field(False, env="OCR_ENABLED")
    
    class Config:
        env_prefix = "DOC_"
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024


class AISettings(BaseSettings):
    """AI model configuration"""
    default_model: str = Field("gpt-4.1-mini-2025-04-14", env="DEFAULT_AI_MODEL")
    temperature: float = Field(0.7, env="AI_TEMPERATURE")
    max_tokens: int = Field(4000, env="AI_MAX_TOKENS")
    embedding_model: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(1536, env="EMBEDDING_DIMENSIONS")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    class Config:
        env_prefix = "AI_"


class LoggingSettings(BaseSettings):
    """Logging configuration"""
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("json", env="LOG_FORMAT")  # json or text
    file_path: Optional[str] = Field(None, env="LOG_FILE_PATH")
    max_size_mb: int = Field(10, env="LOG_MAX_SIZE_MB")
    backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_prefix = "LOG_"

@dataclass
class CohereConfig:
    """Cohere API configuration for reranking"""
    api_key: str = os.getenv("COHERE_API_KEY", "")
    rerank_model: str = "rerank-v3.5"

class Settings(BaseSettings):
    """Main settings class aggregating all configurations"""
    
    # Sub-configurations
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    box: BoxConfig = Field(default_factory=BoxConfig)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    security: SecuritySettings = Field(default_factory=lambda: SecuritySettings(secret_key=os.getenv("SECRET_KEY", "dev-secret-key")))
    document_processing: DocumentProcessingSettings = Field(default_factory=DocumentProcessingSettings)
    ai: AISettings = Field(default_factory=AISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    cohere: CohereConfig = Field(default_factory=CohereConfig)
    openai: AISettings = Field(default_factory=AISettings)
    chunking: DocumentProcessingSettings = Field(default_factory=DocumentProcessingSettings)
    processing: DocumentProcessingSettings = Field(default_factory=DocumentProcessingSettings)
    vector: QdrantSettings = Field(default_factory=QdrantSettings)
    cost: CostConfig = Field(default_factory=CostConfig)

    # Application settings
    app_name: str = Field("Clerk Legal AI", env="APP_NAME")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    api_v1_prefix: str = Field("/api/v1", env="API_V1_PREFIX")
    cors_origins: str = Field("http://localhost:3000", env="CORS_ORIGINS")
    
    # Paths
    data_dir: Path = Field(Path("./data"), env="DATA_DIR")
    upload_dir: Path = Field(Path("./uploads"), env="UPLOAD_DIR")
    export_dir: Path = Field(Path("./exports"), env="EXPORT_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("data_dir", "upload_dir", "export_dir")
    @classmethod
    def validate_paths(cls, v):
        """Ensure paths are Path objects"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"
    
    def get_database_url(self, async_driver: bool = True) -> str:
        """Get database URL with appropriate driver"""
        url = self.database.url
        if async_driver and url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url
    
    def validate(self) -> bool:
        """Validate critical settings"""
        errors = []
        
        # Check OpenAI API key
        if not self.openai.api_key or self.openai.api_key == "your-api-key-here":
            errors.append("OpenAI API key not configured")
        
        # Check security settings
        if self.is_production and self.security.secret_key == "dev-secret-key":
            errors.append("Production secret key not configured")
        
        # Check Qdrant connection
        if self.is_production and self.qdrant.host == "localhost":
            errors.append("Production Qdrant host not configured")
        
        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False
        
        return True
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging"""
        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "debug": self.debug,
            "openai_configured": bool(self.openai.api_key),
            "box_configured": bool(self.box.client_id),
            "qdrant_host": self.qdrant.host,
            "database_configured": bool(self.database.url),
            "cache_enabled": self.cache.enable_cache,
            "cors_origins": self.cors_origins_list,
        }


# Create global settings instance
settings = Settings()

QdrantConfig = QdrantSettings
OpenAIConfig = OpenAISettings
ChunkingConfig = DocumentProcessingSettings
ProcessingConfig = DocumentProcessingSettings
VectorConfig = QdrantSettings




# Export commonly used settings
CHUNK_SIZE = settings.document_processing.chunk_size
CHUNK_OVERLAP = settings.document_processing.chunk_overlap
EMBEDDING_MODEL = settings.ai.embedding_model
DEFAULT_AI_MODEL = settings.ai.default_model