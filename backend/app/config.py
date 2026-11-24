from typing import Dict, List, Optional
import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys & Flags
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    cometai_api_key: str = ""
    cometai_base_url: str = "https://cometai.utdallas.edu/api/v1"
    mock_mode: bool = True
    database_url: str = "sqlite+aiosqlite:///./telemetry.db"
    allowed_origins: str = "*"

    # Default Provider-to-Model Mapping
    provider_models: Dict[str, str] = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini/gemini-3.5-flash-lite",
        "cometai": "openai/cometai-default",
    }

    # Per-1K token pricing table (in USD: input, output)
    pricing_per_1k: Dict[str, Dict[str, float]] = {
        "gpt-4o-mini": {
            "input": 0.00015,
            "output": 0.00060,
        },
        "openai/cometai-default": {
            "input": 0.00015,
            "output": 0.00060,
        },
        "cometai-default": {
            "input": 0.00015,
            "output": 0.00060,
        },
        "claude-3-5-haiku-latest": {
            "input": 0.00080,
            "output": 0.00400,
        },
        "gemini/gemini-3.5-flash-lite": {
            "input": 0.00030,
            "output": 0.00250,
        },
        "gemini-3.5-flash-lite": {
            "input": 0.00030,
            "output": 0.00250,
        },
        "gemini/gemini-4-hydrogen": {
            "input": 0.00150,
            "output": 0.00750,
        },
        "gemini-4-hydrogen": {
            "input": 0.00150,
            "output": 0.00750,
        },
        "gemini/gemini-2.5-flash": {
            "input": 0.000075,
            "output": 0.00030,
        },
        "gemini-2.5-flash": {
            "input": 0.000075,
            "output": 0.00030,
        },
        "gemini/gemini-2.0-flash": {
            "input": 0.00010,
            "output": 0.00040,
        },
        "gemini-2.0-flash": {
            "input": 0.00010,
            "output": 0.00040,
        },
    }


settings = Settings()


async def resolve_latest_slim_gemini_model(api_key: str) -> str:
    """
    Dynamically discover Google Generative Language models via API.
    Auto-discovers and targets the latest/slimmest free-tier Flash-Lite or Hydrogen model.
    Falls back gracefully to gemini/gemini-3.5-flash-lite if unreachable or invalid.
    """
    fallback = "gemini/gemini-3.5-flash-lite"
    if not api_key:
        return fallback

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return fallback
            data = resp.json()
            models: List[Dict] = data.get("models", [])
            
            # Find candidate models supporting generateContent
            candidates = []
            for m in models:
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "")  # e.g. "models/gemini-1.5-flash"
                base_id = name.replace("models/", "")
                if "generateContent" in methods and "gemini" in base_id.lower():
                    candidates.append(base_id)

            # Preference hierarchy: flash-lite -> hydrogen -> flash
            flash_lite_models = [c for c in candidates if "flash-lite" in c.lower()]
            if flash_lite_models:
                # Pick the latest (sorted reverse)
                flash_lite_models.sort(reverse=True)
                return f"gemini/{flash_lite_models[0]}"

            hydrogen_models = [c for c in candidates if "hydrogen" in c.lower()]
            if hydrogen_models:
                hydrogen_models.sort(reverse=True)
                return f"gemini/{hydrogen_models[0]}"

            flash_models = [c for c in candidates if "flash" in c.lower()]
            if flash_models:
                flash_models.sort(reverse=True)
                return f"gemini/{flash_models[0]}"

            return fallback
    except Exception:
        return fallback

