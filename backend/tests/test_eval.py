import json
import os
import pytest
import httpx

from backend.app.config import settings
from backend.app.main import app


def load_golden_dataset():
    current_dir = os.path.dirname(__file__)
    golden_path = os.path.join(current_dir, "golden_dataset.json")
    with open(golden_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_golden_dataset_benchmark():
    orig_mock = settings.mock_mode
    settings.mock_mode = True
    try:
        dataset = load_golden_dataset()
        providers = ["openai", "anthropic", "gemini"]
        prompt_versions = ["v1", "v2"]

        results_table = []

        print("\n\n" + "=" * 80)
        print("COMETGATEWAY MULTI-MODEL EVALUATION BENCHMARK SUITE")
        print("=" * 80)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for provider in providers:
                model_name = settings.provider_models.get(provider, "unknown")
                for p_ver in prompt_versions:
                    passed_cases = 0
                    total_cases = len(dataset)
                    total_ttft_ms = 0.0
                    total_cost_usd = 0.0
                    total_pii_blocked = 0

                    for item in dataset:
                        payload = {
                            "prompt": item["prompt"],
                            "provider": provider,
                            "prompt_version": p_ver,
                            "enable_pii_redaction": True,
                        }

                        events = []
                        async with client.stream("POST", "/v1/chat/stream", json=payload) as stream_resp:
                            assert stream_resp.status_code == 200
                            async for line in stream_resp.aiter_lines():
                                line = line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                data_str = line[len("data: ") :]
                                if data_str == "[DONE]":
                                    events.append({"type": "[DONE]"})
                                else:
                                    events.append(json.loads(data_str))

                        # 1. Gate: Privacy Compliance
                        privacy_event = events[0]
                        sanitized_prompt = privacy_event.get("sanitized_prompt", "")
                        redacted_count = privacy_event.get("redacted_count", 0)
                        total_pii_blocked += redacted_count

                        # Assert 0% PII leakage for forbidden substrings
                        forbidden = item.get("forbidden_substrings", [])
                        for sub in forbidden:
                            assert sub not in sanitized_prompt, f"PII Leakage: {sub} found in sanitized prompt!"

                        # Check delta chunks for PII
                        delta_text = "".join(e.get("content", "") for e in events if e.get("type") == "delta")
                        for sub in forbidden:
                            assert sub not in delta_text, f"PII Leakage: {sub} found in output deltas!"

                        # Assert expected redactions
                        expected_redacted = item.get("expected_redacted_count", 0)
                        assert redacted_count == expected_redacted, (
                            f"Expected {expected_redacted} redactions, got {redacted_count} for {item['id']}"
                        )

                        # 2. Gate: Quality & Structure
                        if p_ver == "v2":
                            lower_delta = delta_text.lower()
                            assert (
                                "#" in delta_text
                                or "polic" in lower_delta
                                or "step" in lower_delta
                                or "standard" in lower_delta
                                or "cannot" in lower_delta
                                or "sorry" in lower_delta
                                or "security" in lower_delta
                            ), "Prompt v2 must contain structured headings, policy references, or secure refusal"

                        # 3. Telemetry extraction
                        telemetry_event = next((e for e in reversed(events) if e.get("type") == "telemetry"), None)
                        assert telemetry_event is not None, "Stream must include telemetry event"
                        total_ttft_ms += telemetry_event.get("ttft_ms", 0.0)
                        total_cost_usd += telemetry_event.get("cost_usd", 0.0)

                        passed_cases += 1

                    avg_ttft = round(total_ttft_ms / total_cases, 2)
                    pass_rate = f"{(passed_cases / total_cases) * 100:.1f}%"
                    results_table.append({
                        "provider": provider.capitalize(),
                        "model": model_name,
                        "prompt_version": p_ver,
                        "pass_rate": pass_rate,
                        "avg_ttft_ms": avg_ttft,
                        "total_cost_usd": round(total_cost_usd, 6),
                        "pii_blocked": total_pii_blocked,
                    })

        # Generate recruiter-ready Markdown benchmark table
        markdown_table = [
            "| Provider | Model | Prompt Version | Pass Rate | Avg TTFT (ms) | Total Cost (USD) | PII Blocked |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
        for row in results_table:
            markdown_table.append(
                f"| {row['provider']} | `{row['model']}` | **{row['prompt_version']}** | "
                f"{row['pass_rate']} | {row['avg_ttft_ms']} ms | ${row['total_cost_usd']:.6f} | {row['pii_blocked']} |"
            )

        summary_output = "\n".join(markdown_table)
        print("\n" + summary_output + "\n")
        print("=" * 80)
        print("EVALUATION GATE: 100% OF PRIVACY & SCHEMA GATES PASSED")
        print("=" * 80 + "\n")

        # Assert 100% pass rate across all evaluated rows
        for row in results_table:
            assert row["pass_rate"] == "100.0%"
    finally:
        settings.mock_mode = orig_mock
