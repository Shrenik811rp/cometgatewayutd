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
