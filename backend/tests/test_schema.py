import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
import litellm

from backend.app.config import settings
from backend.app.main import app
from backend.app.schemas import MetricsSummaryResponse, TelemetryMetrics


@pytest.mark.asyncio
async def test_sse_event_contract():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "prompt": "Test student query with UTD ID 2025123456 and email user@utdallas.edu",
            "provider": "openai",
            "prompt_version": "v1",
            "enable_pii_redaction": True,
        }
        events = []
        async with client.stream("POST", "/v1/chat/stream", json=payload) as stream_resp:
            assert stream_resp.status_code == 200
            assert "text/event-stream" in stream_resp.headers["content-type"]
            async for line in stream_resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    events.append({"type": "[DONE]"})
                else:
                    events.append(json.loads(data))

        assert len(events) >= 4, "Stream must contain privacy, at least one delta, telemetry, and [DONE]"
        assert events[0]["type"] == "privacy"
        assert events[0]["redacted_count"] == 2
        assert "2025123456" not in events[0]["sanitized_prompt"]
        assert "user@utdallas.edu" not in events[0]["sanitized_prompt"]
        assert len(events[0]["entities"]) == 2

        # Delta events
        delta_events = [e for e in events if e["type"] == "delta"]
        assert len(delta_events) > 0
        for d in delta_events:
            assert "content" in d and isinstance(d["content"], str)

        # Telemetry event (second-to-last)
        telemetry_event = events[-2]
        assert telemetry_event["type"] == "telemetry"
        # Validate through Pydantic
        metrics_obj = TelemetryMetrics.model_validate(telemetry_event)
        assert metrics_obj.ttft_ms > 0
        assert metrics_obj.total_ms >= metrics_obj.ttft_ms
        assert metrics_obj.prompt_tokens > 0
        assert metrics_obj.completion_tokens > 0
        assert metrics_obj.cost_usd >= 0

        # Final event
        assert events[-1]["type"] == "[DONE]"


@pytest.mark.asyncio
async def test_provider_fallback_gate():
    # Helper async generator for mock litellm stream
    async def mock_gemini_stream(*args, **kwargs):
        class MockDelta:
            content = "This is a fallback response from Gemini Flash."

        class MockChoice:
            delta = MockDelta()

        class MockChunk:
            choices = [MockChoice()]

        yield MockChunk()

    orig_mock_mode = settings.mock_mode
    settings.mock_mode = False

    try:
        async def mock_acompletion(model, *args, **kwargs):
            if "gpt" in model or "openai" in model:
                raise litellm.RateLimitError(
                    message="OpenAI rate limit exceeded (Simulated 429)",
                    llm_provider="openai",
                    model=model,
                )
            elif "gemini" in model:
                return mock_gemini_stream()
            raise ValueError(f"Unexpected model: {model}")

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                payload = {
                    "prompt": "Campus network status query",
                    "provider": "openai",
                    "prompt_version": "v1",
                    "enable_pii_redaction": False,
                }
                events = []
                async with client.stream("POST", "/v1/chat/stream", json=payload) as stream_resp:
                    assert stream_resp.status_code == 200
                    async for line in stream_resp.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[len("data: ") :]
                        if data == "[DONE]":
                            events.append({"type": "[DONE]"})
                        else:
                            events.append(json.loads(data))

                telemetry_event = events[-2]
                assert telemetry_event["type"] == "telemetry"
                assert telemetry_event["fallback_triggered"] is True, "Fallback must be triggered on RateLimitError"
                assert "gemini" in telemetry_event["model_used"].lower()
    finally:
        settings.mock_mode = orig_mock_mode


@pytest.mark.asyncio
async def test_missing_key_preflight_failover():
    async def mock_gemini_stream(*args, **kwargs):
        class MockDelta:
            content = "Failover response from Gemini due to missing Anthropic key."

        class MockChoice:
            delta = MockDelta()

        class MockChunk:
            choices = [MockChoice()]

        yield MockChunk()

    orig_mock_mode = settings.mock_mode
    orig_anthropic_key = settings.anthropic_api_key
    orig_gemini_key = settings.gemini_api_key

    settings.mock_mode = False
    settings.anthropic_api_key = "your_anthropic_api_key_here"  # Unconfigured placeholder
    settings.gemini_api_key = "valid_test_gemini_key"

    try:
        with patch("litellm.acompletion", side_effect=lambda model, *args, **kwargs: mock_gemini_stream()):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                payload = {
                    "prompt": "Test query without Anthropic credentials",
                    "provider": "anthropic",
                    "prompt_version": "v1",
                    "enable_pii_redaction": False,
                }
                events = []
                async with client.stream("POST", "/v1/chat/stream", json=payload) as stream_resp:
                    assert stream_resp.status_code == 200
                    async for line in stream_resp.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[len("data: ") :]
                        if data == "[DONE]":
                            events.append({"type": "[DONE]"})
                        else:
                            events.append(json.loads(data))

                # Ensure zero error events were emitted
                error_events = [e for e in events if e.get("type") == "error"]
                assert len(error_events) == 0, f"Unexpected error event: {error_events}"

                telemetry_event = events[-2]
                assert telemetry_event["type"] == "telemetry"
                assert telemetry_event["fallback_triggered"] is True
                assert "gemini" in telemetry_event["model_used"].lower()
    finally:
        settings.mock_mode = orig_mock_mode
        settings.anthropic_api_key = orig_anthropic_key
        settings.gemini_api_key = orig_gemini_key


@pytest.mark.asyncio
async def test_gemini_503_secondary_retry():
    async def mock_secondary_gemini_stream(*args, **kwargs):
        class MockDelta:
            content = "Response from dynamically discovered secondary Gemini Flash after 503 spike."

        class MockChoice:
            delta = MockDelta()

        class MockChunk:
            choices = [MockChoice()]

        yield MockChunk()

    orig_mock_mode = settings.mock_mode
    orig_gemini_key = settings.gemini_api_key
    orig_chain = list(settings.gemini_fallback_chain)
    settings.mock_mode = False
    settings.gemini_api_key = "valid_test_gemini_key"
    settings.gemini_fallback_chain = ["gemini/discovered-primary-flash-lite", "gemini/discovered-secondary-flash"]
    settings.provider_models["gemini"] = "gemini/discovered-primary-flash-lite"

    try:
        primary_model = "gemini/discovered-primary-flash-lite"
        secondary_model = "gemini/discovered-secondary-flash"

        async def mock_failing_primary(model, *args, **kwargs):
            if model == primary_model:
                raise litellm.APIError(
                    status_code=503,
                    message="503 UNAVAILABLE - The model is overloaded. Please try again later.",
                    llm_provider="gemini",
                    model=model,
                )
            elif model == secondary_model:
                return mock_secondary_gemini_stream()
            raise ValueError(f"Unexpected retry model: {model}")

        with patch("litellm.acompletion", side_effect=mock_failing_primary):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                payload = {
                    "prompt": "Test query hitting Gemini 503 spike",
                    "provider": "gemini",
                    "prompt_version": "v1",
                    "enable_pii_redaction": False,
                }
                events = []
                async with client.stream("POST", "/v1/chat/stream", json=payload) as stream_resp:
                    assert stream_resp.status_code == 200
                    async for line in stream_resp.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[len("data: ") :]
                        if data == "[DONE]":
                            events.append({"type": "[DONE]"})
                        else:
                            events.append(json.loads(data))

                # Ensure zero error events were emitted
                error_events = [e for e in events if e.get("type") == "error"]
                assert len(error_events) == 0, f"Unexpected error event: {error_events}"

                telemetry_event = events[-2]
                assert telemetry_event["type"] == "telemetry"
                assert telemetry_event["fallback_triggered"] is True
                assert telemetry_event["model_used"] == secondary_model
    finally:
        settings.mock_mode = orig_mock_mode
        settings.gemini_api_key = orig_gemini_key
        settings.gemini_fallback_chain = orig_chain
        settings.provider_models["gemini"] = orig_chain[0] if orig_chain else "gemini/gemini-flash-lite-latest"


@pytest.mark.asyncio
async def test_dynamic_gemini_discovery():
    from backend.app.config import resolve_available_gemini_models

    mock_api_response = {
        "models": [
            {
                "name": "models/text-embedding-004",
                "supportedGenerationMethods": ["embedContent"],
            },
            {
                "name": "models/gemini-1.5-pro",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/gemini-2.0-flash",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/gemini-2.5-flash-lite-latest",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/gemini-robotics-experimental",
                "supportedGenerationMethods": ["generateContent"],
            },
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_api_response

    orig_chain = list(settings.gemini_fallback_chain)
    try:
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            discovered = await resolve_available_gemini_models("test-live-key")
            assert len(discovered) >= 3
            # Tier 0 (flash-lite) must be ranked first
            assert discovered[0] == "gemini/gemini-2.5-flash-lite-latest"
            # Non-generation and robotics must be excluded
            assert not any("embed" in m for m in discovered)
            assert not any("robotics" in m for m in discovered)
            assert settings.provider_models["gemini"] == discovered[0]
            assert settings.gemini_fallback_chain == discovered
    finally:
        settings.gemini_fallback_chain = orig_chain
        settings.provider_models["gemini"] = orig_chain[0] if orig_chain else "gemini/gemini-flash-lite-latest"


@pytest.mark.asyncio
async def test_metrics_endpoint_contract():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        summary = MetricsSummaryResponse.model_validate(data)
        assert summary.total_requests >= 0
        assert summary.avg_ttft_ms >= 0.0
        assert summary.avg_total_ms >= 0.0
        assert summary.total_tokens >= 0
        assert summary.total_cost_usd >= 0.0
        assert isinstance(summary.recent_requests, list)
