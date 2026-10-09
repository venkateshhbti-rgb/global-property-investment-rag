import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_TITLE: str = "Property Investment RAG Consultant"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Mode Configuration
    LOCAL_MODE: bool = True  # Set to False when adding OPENAI_API_KEY

    # OpenAI Configuration (Optional - leave empty for local mode)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Auth / storage
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    DATA_STORE_PATH: str = "./data_store.json"
    MARKET_CACHE_PATH: str = "./market_cache.json"

    # Vector Store Configuration
    CHROMA_DB_PATH: str = "./chroma_db"
    VECTOR_STORE_NAME: str = "property_investment_db"

    # Data Paths
    DATA_BASE_PATH: str = "../data"  # each sub-folder (e.g. Dubai, London, Singapore) is one market

    # RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_K: int = 5

    # CORS Configuration
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
