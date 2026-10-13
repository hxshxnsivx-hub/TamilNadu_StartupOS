"""Application configuration, loaded from environment (.env)."""

from functools import lru_cache
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings. See .env.example for the full list."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "Vanigam"
    log_level: str = "INFO"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vanigam"
    postgres_user: str = "vanigam"
    postgres_password: str = "vanigam"
    database_url: str | None = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3 / MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "vanigam-documents"
    s3_region: str = "us-east-1"

    # Managed-API providers (swappable adapters)
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model_main: str = "claude-sonnet-5-5"
    llm_model_router: str = "claude-haiku-4-5-20251001"
    # Council seats: many short parallel calls on a shared cached prefix.
    llm_model_fast: str = "claude-haiku-4-5-20251001"
    # Model tokens per conversation (0: no cap). Past it the council runs on rules;
    # the conversation itself keeps going.
    session_token_budget: int = 0

    # Free models (app/agents/providers.py). The mentor tries, in this order, every
    # provider that is configured: a failure or a used-up free quota moves the turn to
    # the next one; templates are the last resort.
    llm_order: str = "anthropic,gemini,ollama"
    # Google Gemini API, free tier: a key from aistudio.google.com, no payment.
    # On the free tier Google may use the text to improve its products.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"  # the conversation, with tools
    gemini_model_fast: str = "gemini-3.5-flash-lite"  # review-panel seats: many short calls
    gemini_thinking: str = "low"  # minimal | low | medium | high: low keeps replies quick
    # Ollama on this machine: offline backup. Empty model = not used.
    # Small models on a CPU are slow and unreliable with tools, so Ollama rewords the
    # reply the code built (facts and question included) rather than calling tools.
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = ""  # e.g. gemma3:4b

    # Mentor voice: Sarvam AI speech (app/voice). Without a key the browser's own
    # speech is used. One speaker for every language keeps the mentor's voice the same.
    # The key is SARVAM_API_KEY, shared with translation below.
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"
    sarvam_tts_pace: float = 0.95  # a touch slower than default: a mentor, not an announcer
    sarvam_stt_model: str = "saaras:v4"
    voice_cache_dir: str = ".cache/voice"
    # Gemini text-to-speech (same free key as above): speaks any sentence the model
    # writes, in Tamil, Hindi or English. Voices from the Gemini voice list, one per
    # language; the style is the delivery for every sentence.
    gemini_tts_model: str = "gemini-3.8-flash-tts"
    gemini_tts_voice_en: str = "Sadaltager"  # "knowledgeable"
    gemini_tts_voice_hi: str = "Sadaltager"
    gemini_tts_voice_ta: str = "Sulafat"  # "warm"
    gemini_tts_style: str = (
        "a calm, warm mentor speaking to a young founder: unhurried, encouraging, clear"
    )

    translation_provider: str = "sarvam"
    sarvam_api_key: str = ""

    embedding_provider: str = "cohere"
    cohere_api_key: str = ""
    embedding_dim: int = 1024

    verification_provider: str = "surepass"
    verification_api_key: str = ""

    # Prior-art research sources (app/research). All optional: a source without a
    # required key is reported as "not searched", never silently skipped.
    openalex_api_key: str = ""  # free key; without it OpenAlex allows a small shared daily budget
    patentsview_api_key: str = ""  # free key from PatentsView; patents are skipped without it
    github_token: str = ""  # raises GitHub's search rate limit
    research_cache_dir: str = ".cache/research"
    research_cache_days: int = 7
    # Requests per research source per UTC day (0: no cap). Counted in Redis when it runs.
    research_daily_limit: int = 0

    # Where ideation conversations are saved: "database", "memory", or "auto"
    # (the database when it answers and the agent_sessions table exists).
    agent_store: Literal["auto", "database", "memory"] = "auto"

    # Rate limits
    rate_limit_per_user_per_min: int = 100
    rate_limit_global_per_min: int = 1000

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_url(self) -> str:
        """Async SQLAlchemy URL — explicit DATABASE_URL wins, else assembled."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (import-safe; reads env once)."""
    return Settings()
