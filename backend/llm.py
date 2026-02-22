"""LiteLLM Router singleton — all LLM calls go through this, never raw SDKs.

Design decisions:
- Single shared Router instance (module-level singleton via get_router())
- Primary model: openai/gpt-4o — best reasoning for agent tasks
- Fallback model: gemini/gemini-2.5-pro — automatic on any primary error
- API keys loaded from environment at first call; empty string default prevents
  crash on import when keys are not yet set
- The `gemini/` prefix is required by LiteLLM for Google Gemini models
  (using `google/` or bare model names will cause routing errors)
"""

import os

from litellm import Router

_router: Router | None = None


def get_router() -> Router:
    """Get or create the LiteLLM Router with primary (OpenAI) and fallback (Gemini).

    Thread-safe via Python's GIL for the simple singleton assignment.
    Returns the same Router instance on every call after initialization.
    """
    global _router
    if _router is None:
        _router = Router(
            model_list=[
                {
                    "model_name": "primary",
                    "litellm_params": {
                        "model": "openai/gpt-4o",
                        "api_key": os.environ.get("OPENAI_API_KEY", ""),
                    },
                },
                {
                    "model_name": "fallback",
                    "litellm_params": {
                        "model": "gemini/gemini-2.5-pro",
                        "api_key": os.environ.get("GEMINI_API_KEY", ""),
                    },
                },
            ],
            fallbacks=[{"primary": ["fallback"]}],
        )
    return _router
