"""All the backend settings in one place.

Import `settings` from here rather than reading os.environ around the codebase.
Real environment variables win, then backend/.env, then the defaults below. A
fresh checkout should run with just the API keys filled in.

Settings are checked at import so a typo fails on startup instead of twenty
minutes into a run.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# This file sits at backend/app/config.py, so the backend folder is two levels
# up. Working off the file path rather than the current directory means the
# database ends up in the same place wherever you start the server from.
_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All backend configuration, sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=(_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- Provider credentials -------------------------------------------------
    # Not required at import so the app can boot (and /health can answer) with
    # credentials absent; the call that needs one fails with a clear provider error.
    openai_api_key: str = ""
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    firecrawl_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""

    # -- Model routing --------------------------------------------------------
    # "primary" handles agent synthesis; "mini" handles cheap utility calls.
    # Each falls back to the other provider, so one outage is not fatal.
    primary_model: str = "openai/gpt-4o"
    fallback_model: str = "gemini/gemini-3.6-flash"
    mini_model: str = "openai/gpt-4o-mini"
    mini_fallback_model: str = "gemini/gemini-3.5-flash-lite"

    # -- LLM request behaviour ------------------------------------------------
    # Sized from measured latency: the sales call runs 15-34s on the primary and
    # ~44s on the fallback, so a ceiling near 30s reads normal variance as failure.
    request_timeout_seconds: float = Field(default=90.0, gt=0)
    llm_num_retries: int = Field(default=2, ge=0)
    rate_limit_retries: int = Field(default=3, ge=0)
    timeout_retries: int = Field(default=2, ge=0)
    server_error_retries: int = Field(default=2, ge=0)
    router_allowed_fails: int = Field(default=3, ge=1)
    router_cooldown_seconds: int = Field(default=30, ge=0)

    # -- Agent sampling -------------------------------------------------------
    # Lower for analysis, higher for creative copy.
    research_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    profile_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    audience_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    content_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    sales_temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    ads_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    image_prompt_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    critic_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    # Must accommodate the fallback, which is a thinking model and charges its
    # reasoning against the same budget (measured: 5.9k reasoning + 6.1k output).
    # At 8000 it truncated mid-JSON and failed the run.
    content_max_tokens: int = Field(default=16000, gt=0)

    # -- Agent 0 external calls ----------------------------------------------
    search_timeout_seconds: float = Field(default=25.0, gt=0)
    scrape_timeout_seconds: float = Field(default=25.0, gt=0)
    aeo_query_timeout_seconds: float = Field(default=60.0, gt=0)
    quick_extract_timeout_seconds: float = Field(default=10.0, gt=0)
    press_results_per_search: int = Field(default=5, gt=0)
    competitor_results_per_search: int = Field(default=8, gt=0)
    max_press_items: int = Field(default=10, gt=0)

    # The AEO check asks two engines the same question. These skip the router,
    # because a fallback would file one engine's answer under the other's name.
    aeo_first_model: str = "openai/gpt-4o"
    aeo_second_model: str = "gemini/gemini-3.6-flash"

    # -- Prompt context trimming ---------------------------------------------
    # The scraped page is ~80% of the research blob and every downstream agent
    # embeds the whole thing. Trimming it saves ~37k tokens per run.
    site_content_prompt_chars: int = Field(default=1500, gt=0)

    # -- Image generation -----------------------------------------------------
    # OpenAI retired dall-e-3; gpt-image-1 is current and returns base64.
    image_model: str = "gpt-image-1"
    image_size: str = "1024x1024"
    image_timeout_seconds: float = Field(default=120.0, gt=0)
    image_cap_per_run: int = Field(default=3, ge=0)

    # -- Voice ----------------------------------------------------------------
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    elevenlabs_timeout_seconds: float = Field(default=30.0, gt=0)

    # -- Storage --------------------------------------------------------------
    # Relative paths resolve against the backend directory, so the app behaves
    # the same regardless of the working directory it was launched from.
    chroma_path: str = "./chroma_data"
    chroma_collection: str = "blitz_pipeline"
    # In-memory Chroma for tests: no files, no locking, far faster.
    chroma_in_memory: bool = False
    # Blitz uses Chroma as a key-value store — it reads by id and by run_id
    # filter, and never runs a similarity query. The default embedding function
    # therefore loads an ONNX model and embeds every document for nothing
    # (measured 0.52s vs 0.03s per client). Disabling it is safe for the current
    # access pattern and is what tests use; left on by default so that enabling
    # semantic retrieval later does not require a data migration.
    chroma_disable_embeddings: bool = False
    sqlite_path: str = "./blitz.db"

    # -- HTTP -----------------------------------------------------------------
    # Empty means "development": allow the local Vite dev-server port range.
    # Any real deployment must set CORS_ORIGINS or the browser will be blocked.
    cors_origins: str = ""
    dev_cors_port_start: int = 5173
    dev_cors_port_end: int = 5200

    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @property
    def allowed_origins(self) -> list[str]:
        """Origins permitted by CORS, falling back to the dev port range."""
        configured = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if configured:
            return configured
        return [
            f"http://localhost:{port}"
            for port in range(self.dev_cors_port_start, self.dev_cors_port_end)
        ]

    def resolve_path(self, value: str) -> Path:
        """Resolve a configured path against the backend directory if relative."""
        path = Path(value)
        return path if path.is_absolute() else (_BACKEND_DIR / path)

    @property
    def chroma_dir(self) -> Path:
        return self.resolve_path(self.chroma_path)

    @property
    def sqlite_file(self) -> Path:
        return self.resolve_path(self.sqlite_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings, constructed once."""
    return Settings()


settings = get_settings()
