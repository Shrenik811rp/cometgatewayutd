import asyncio
import json
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import httpx
from backend.app.main import app


async def run_verification():
    print("=== Starting Phase 2 Verification ===")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Health check
        print("\n--- 1. Testing GET /health ---")
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200, f"Expected 200, got {health_resp.status_code}"
        health_data = health_resp.json()
        print("Health Response:", health_data)
        assert health_data["status"] == "ok"
        assert "mock_mode" in health_data

        # 2. SSE Chat Stream with PII
        print("\n--- 2. Testing POST /v1/chat/stream with UTD ID & Email ---")
        prompt_with_pii = (
            "Hello, my UTD student ID is 2025123456 and my email is netid@utdallas.edu. "
            "How do I connect to CometNet Wi-Fi?"
        )
        payload = {
            "prompt": prompt_with_pii,
            "provider": "openai",
            "prompt_version": "v2",
            "enable_pii_redaction": True,
        }

        events = []
        async with client.stream("POST", "/v1/chat/stream", json=payload) as stream_resp:
            assert stream_resp.status_code == 200, f"Expected 200, got {stream_resp.status_code}"
            assert "text/event-stream" in stream_resp.headers["content-type"]

            async for line in stream_resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_part = line[len("data: ") :]
                if data_part == "[DONE]":
                    events.append({"type": "[DONE]"})
                else:
                    events.append(json.loads(data_part))

        print(f"Total SSE Events Received: {len(events)}")
        event_types = [e["type"] for e in events]
        print(f"Event Types Sequence: {event_types}")

        # Assert sequence: privacy first, deltas in middle, telemetry, then [DONE]
        assert event_types[0] == "privacy", "First event must be 'privacy'"
        assert event_types[-1] == "[DONE]", "Last event must be '[DONE]'"
        assert event_types[-2] == "telemetry", "Second-to-last event must be 'telemetry'"
        assert "delta" in event_types[1:-2], "Delta events must appear in the stream"

        # Verify privacy event
        privacy_event = events[0]
        print("\nPrivacy Event Payload:")
        print(json.dumps(privacy_event, indent=2))
        assert privacy_event["redacted_count"] == 2
        assert "2025123456" not in privacy_event["sanitized_prompt"]
        assert "netid@utdallas.edu" not in privacy_event["sanitized_prompt"]
        assert "[REDACTED_UTD_ID]" in privacy_event["sanitized_prompt"]
        assert "[REDACTED_EMAIL]" in privacy_event["sanitized_prompt"]

        # Verify telemetry event
        telemetry_event = events[-2]
        print("\nTelemetry Event Payload:")
        print(json.dumps(telemetry_event, indent=2))
        assert telemetry_event["ttft_ms"] > 0
        assert telemetry_event["total_ms"] >= telemetry_event["ttft_ms"]
        assert telemetry_event["redacted_count"] == 2
        assert telemetry_event["prompt_tokens"] > 0
        assert telemetry_event["completion_tokens"] > 0

        # 3. Metrics Summary
        print("\n--- 3. Testing GET /v1/metrics ---")
        metrics_resp = await client.get("/v1/metrics")
        assert metrics_resp.status_code == 200, f"Expected 200, got {metrics_resp.status_code}"
        metrics_data = metrics_resp.json()
        print("Metrics Summary Response:")
        print(json.dumps(metrics_data, indent=2))
        assert metrics_data["total_requests"] >= 1
        assert metrics_data["total_pii_redacted"] >= 2
        assert len(metrics_data["recent_requests"]) >= 1

    print("\n=== Phase 2 Verification 100% SUCCEEDED ===")


if __name__ == "__main__":
    asyncio.run(run_verification())
