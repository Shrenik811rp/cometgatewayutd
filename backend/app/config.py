import re
from typing import Any, Dict, List, Optional
import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_GEMINI_FALLBACK = [
    "gemini/gemini-flash-lite-latest",
    "gemini/gemini-flash-latest",
]


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

    # Dynamic Gemini Fallback Chain (populated via Google Models API)
    gemini_fallback_chain: List[str] = Field(default_factory=lambda: list(DEFAULT_GEMINI_FALLBACK))

    # Default Provider-to-Model Mapping
    provider_models: Dict[str, str] = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini/gemini-flash-lite-latest",
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
    }


settings = Settings()


def get_model_pricing(model_name: str) -> Dict[str, float]:
    """
    Wildcard / prefix fallback for dynamic pricing lookup.
    Automatically assigns appropriate rates for dynamically discovered Gemini Flash-Lite / Flash models.
    """
    m = model_name.lower()
    if model_name in settings.pricing_per_1k:
        return settings.pricing_per_1k[model_name]
    for k, p in settings.pricing_per_1k.items():
        if k in m or m in k:
            return p

    # Dynamic wildcard fallbacks
    if "flash-lite" in m:
        return {"input": 0.00030, "output": 0.00250}
    if "hydrogen" in m:
        return {"input": 0.00150, "output": 0.00750}
    if "flash" in m:
        return {"input": 0.00010, "output": 0.00040}
    if "claude" in m or "anthropic" in m:
        return {"input": 0.00080, "output": 0.00400}
    if "gpt" in m or "openai" in m:
        return {"input": 0.00015, "output": 0.00060}

    return {"input": 0.00015, "output": 0.00060}


def parse_gemini_sort_key(model_id: str):
    """
    Sort key for Gemini models:
    1. Tier: flash-lite (0) > hydrogen / flash (1) > other text (2)
    2. Version recency: numeric version tuples descending
    3. Latest alias preferred
    """
    m = model_id.lower()
    if "flash-lite" in m:
        tier = 0
    elif "hydrogen" in m or "flash" in m:
        tier = 1
    else:
        tier = 2

    # Extract all digits for semantic version sorting
    nums = [int(n) for n in re.findall(r"\d+", m)]
    ver_tuple = tuple(nums[:3]) if nums else (0, 0)
    is_latest = 1 if ("latest" in m or "default" in m) else 0

    return (tier, [-x for x in ver_tuple], -is_latest, m)


async def resolve_available_gemini_models(api_key: str) -> List[str]:
    """
    Query Google Generative Language Models API at runtime.
    Discovers, filters, and ranks all available Gemini generation models.
    Sets settings.gemini_fallback_chain and updates settings.provider_models['gemini'].
    """
    if not api_key:
        if not settings.gemini_fallback_chain:
            settings.gemini_fallback_chain = list(DEFAULT_GEMINI_FALLBACK)
        settings.provider_models["gemini"] = settings.gemini_fallback_chain[0]
        return settings.gemini_fallback_chain

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    excluded_keywords = [
        "embed", "embedding", "vision", "audio", "tts",
        "image", "imagen", "robotics", "deprecated", "aqa",
    ]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                if not settings.gemini_fallback_chain:
                    settings.gemini_fallback_chain = list(DEFAULT_GEMINI_FALLBACK)
                settings.provider_models["gemini"] = settings.gemini_fallback_chain[0]
                return settings.gemini_fallback_chain

            data = resp.json()
            raw_models: List[Dict[str, Any]] = data.get("models", [])
            valid_candidates: List[str] = []

            for m in raw_models:
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "")  # e.g. "models/gemini-1.5-flash"
                base_id = name.replace("models/", "").strip()
                base_lower = base_id.lower()

                # Generation support + gemini check
                if "generateContent" not in methods or "gemini" not in base_lower:
                    continue

                # Exclude embeddings, vision-only, tts, robotics, etc.
                if any(bad in base_lower for bad in excluded_keywords):
                    continue

                litellm_id = f"gemini/{base_id}"
                if litellm_id not in valid_candidates:
                    valid_candidates.append(litellm_id)

            if valid_candidates:
                valid_candidates.sort(key=parse_gemini_sort_key)
                settings.gemini_fallback_chain = valid_candidates
                settings.provider_models["gemini"] = valid_candidates[0]
                return valid_candidates

    except Exception:
        pass

    if not settings.gemini_fallback_chain:
        settings.gemini_fallback_chain = list(DEFAULT_GEMINI_FALLBACK)
    settings.provider_models["gemini"] = settings.gemini_fallback_chain[0]
    return settings.gemini_fallback_chain

