from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Hosted Supabase Settings
    SUPABASE_URL: str = Field(..., description="Hosted Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase publishable anon key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role secret key")
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string with sslmode=require")

    # Supabase Auth Settings
    JWT_AUDIENCE: str = Field(default="authenticated", description="Expected JWT audience")
    JWT_JWKS_URL: str = Field(..., description="JWKS endpoint URL for hosted Supabase Auth")

    # LLM Settings
    GROQ_API_KEY: str = Field(..., description="API key for Groq Cloud")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Model name to use on Groq")
    LLM_PROVIDER: Literal["groq", "local"] = Field(default="groq", description="Provider flag for LLM abstraction")

    # ChromaDB Vector Store
    CHROMA_HOST: str = Field(default="localhost", description="ChromaDB host")
    CHROMA_PORT: int = Field(default=8000, description="ChromaDB port")

    # Storage & Cache Paths
    HF_HOME: str = Field(default="./hf_cache", description="HuggingFace model weight cache directory")

    # Application & Rate Limiting
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8080)
    RATE_LIMIT_PER_MINUTE_AUTH: int = Field(default=60, description="Per-user rate limit for authenticated endpoints")
    RATE_LIMIT_PER_MINUTE_ANON: int = Field(default=10, description="Per-IP rate limit for unauthenticated endpoints")

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_sslmode(cls, v: str) -> str:
        """Enforces S-12: Hosted Supabase connection string must enforce TLS (sslmode=require)."""
        if "sslmode=require" not in v.lower() and "sslmode=verify-full" not in v.lower():
            raise ValueError(
                "DATABASE_URL must enforce TLS with sslmode=require (RULES.md S-12)"
            )
        return v


settings = Settings()  # type: ignore
