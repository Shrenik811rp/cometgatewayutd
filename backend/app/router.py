import asyncio
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
import litellm

from backend.app.config import settings
from backend.app.mcp_server import run_mcp_tool_for_prompt
from backend.app.privacy import redact_pii
from backend.app.schemas import ChatRequest, PrivacyReport, TelemetryMetrics
from backend.app.telemetry import log_telemetry

SYSTEM_PROMPTS: Dict[str, str] = {
    "v1": (
        "You are CometAI, a concise, helpful campus IT assistant for The University of Texas at Dallas (UTD). "
        "Answer student and faculty questions directly, accurately, and politely."
    ),
    "v2": (
        "You are CometAI Enterprise, a structured, policy-grounded UT Dallas OIT assistant. "
        "Structure your answers with clear headings, actionable steps, and cite official UTD Information "
        "Security Standards, FERPA privacy guidelines, and campus IT governance best practices where applicable. "
        "Always remind users never to share unencrypted passwords, SSNs, or student records in chat."
    ),
}

MOCK_RESPONSES = {
    "v1": {
        "openai": "To connect to UTD CometNet Wi-Fi, select 'CometNet' from your device's Wi-Fi settings and log in with your UTD NetID and password. If you experience authentication issues, visit the OIT Help Desk on the first floor of the McDermott Library.",
        "anthropic": "For UTD NetID password resets, navigate to netid.utdallas.edu and select 'Self-Service Password Reset'. Complete the Duo Mobile 2FA prompt to confirm your identity and establish a new compliant passphrase.",
        "gemini": "UT Dallas provides Microsoft 365 and Galaxy portal access to all active students. Log in at galaxy.utdallas.edu using your NetID. If your student account is locked, contact the OIT Help Desk at 972-883-2911.",
        "cometai": "UT Dallas CometAI (cometai.utdallas.edu) sovereign gateway authenticated. Your query has been routed through OIT's high-speed campus inference cluster.",
    },
    "v2": {
        "openai": (
            "### UTD OIT Guidance: Campus Network Access\n\n"
            "**Policy Reference:** UTD Information Security Standard (ISS-03: Network Access)\n\n"
            "1. **Primary Network:** Select the **CometNet** SSID on your campus-registered device.\n"
            "2. **Authentication:** Provide your active **NetID** credentials.\n"
            "3. **Governance & Privacy:** In accordance with UTD Acceptable Use Policy, peer-to-peer sharing and unauthorized network sniffing are strictly prohibited.\n\n"
            "*Need escalation? Contact OIT Help Desk at assist@utdallas.edu or (972) 883-2911.*"
        ),
        "anthropic": (
            "### UTD OIT Guidance: Identity & Access Management\n\n"
            "**Policy Reference:** UTD FERPA & Access Governance Standard (IAM-01)\n\n"
            "1. **Identity Verification:** Access https://netid.utdallas.edu.\n"
            "2. **Multi-Factor Requirement:** Authenticate via registered Duo Mobile push notification.\n"
            "3. **Data Protection Notice:** Student records (FERPA) and passwords must never be transmitted via unencrypted communication channels.\n\n"
            "*Support: OIT Help Desk, McDermott Library (Room MC 1.106).*"
        ),
        "gemini": (
            "### UTD OIT Guidance: Enterprise Applications & Galaxy Portal\n\n"
            "**Policy Reference:** UT Dallas IT Enterprise Application Security (APP-04)\n\n"
            "1. **Access Portal:** Navigate to https://galaxy.utdallas.edu.\n"
            "2. **Student Center:** View class schedules, financial aid, and registration status.\n"
            "3. **FERPA Compliance:** Ensure your student ID and confidential data remain protected during public terminal sessions.\n\n"
            "*Escalation: Call OIT Support at 972-883-2911.*"
        ),
        "cometai": (
            "### UTD OIT Guidance: CometAI Sovereign Enterprise Cluster\n\n"
            "**Policy Reference:** UT Dallas Generative AI Governance & FERPA Standard (EAI-01)\n\n"
            "1. **Inference Enclave:** Operating on UT Dallas Sovereign CometAI Cluster (`cometai.utdallas.edu`).\n"
            "2. **Data Classification:** Verified FERPA DCL-2 Protection; zero unredacted PII is transmitted or logged.\n"
            "3. **Campus Policy:** AI usage is governed by the UT Dallas Student Code of Conduct and IT Acceptable Use Guidelines.\n\n"
            "*Support: cometai.utdallas.edu • OIT Help Desk: (972) 883-2911.*"
        ),
    },
}


def is_valid_key(key: Optional[str]) -> bool:
    if not key:
        return False
    k = key.strip().lower()
    if not k or "your_" in k or "_key_here" in k or k == "placeholder":
        return False
    return True


def get_model_for_request(request: ChatRequest) -> str:
    if request.model:
        return request.model
    provider = request.provider.lower()
    return settings.provider_models.get(provider, settings.provider_models["openai"])


def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    # Match pricing key
    pricing = settings.pricing_per_1k.get(model_name)
    if not pricing:
        # Fallback search by model prefix
        for key, p in settings.pricing_per_1k.items():
            if key in model_name or model_name in key:
                pricing = p
                break
    if not pricing:
        pricing = {"input": 0.00015, "output": 0.00060}

    input_cost = (prompt_tokens / 1000.0) * pricing["input"]
    output_cost = (completion_tokens / 1000.0) * pricing["output"]
    return round(input_cost + output_cost, 6)


async def stream_model_response(
    request: ChatRequest,
    privacy_report: PrivacyReport,
) -> AsyncGenerator[str, None]:
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    prompt_version = request.prompt_version if request.prompt_version in SYSTEM_PROMPTS else "v1"
    system_prompt = SYSTEM_PROMPTS[prompt_version]
    model_name = get_model_for_request(request)

    # 1. Event 1: Privacy scrubbing report
    privacy_event = {
        "type": "privacy",
        "request_id": request_id,
        "sanitized_prompt": privacy_report.sanitized_text,
        "redacted_count": privacy_report.redacted_count,
        "entities": [e.model_dump() for e in privacy_report.entities],
    }
    yield f"data: {json.dumps(privacy_event)}\n\n"

    # 2. Governed UTD OIT MCP Tool Execution (Only pre-sanitized text is passed)
    mcp_tools_used: List[str] = []
    try:
        mcp_res = await run_mcp_tool_for_prompt(privacy_report.sanitized_text)
        if mcp_res:
            mcp_tools_used.append(mcp_res.get("tool", "unknown_tool"))
            mcp_event = {
                "type": "mcp_tool",
                **mcp_res,
            }
            yield f"data: {json.dumps(mcp_event)}\n\n"
    except Exception as mcp_err:
        # Never break stream if MCP tool throws
        error_mcp_event = {
            "type": "mcp_tool",
            "server": "UTD-OIT-Tools",
            "tool": "error",
            "input": {},
            "output": {"error": str(mcp_err)},
        }
        yield f"data: {json.dumps(error_mcp_event)}\n\n"

    start_time = time.perf_counter()
    first_chunk_time: Optional[float] = None
    accumulated_content = []
    fallback_triggered = False

    # 3. Events: Delta stream
    if settings.mock_mode:
        # Simulated realistic TTFT (120ms to 200ms in live, fast in pytest)
        ttft_delay = 0.005 if "pytest" in sys.modules else 0.14
        await asyncio.sleep(ttft_delay)
        first_chunk_time = time.perf_counter()

        provider_key = request.provider.lower()
        if provider_key not in ["openai", "anthropic", "gemini", "cometai"]:
            provider_key = "openai"

        mock_text = MOCK_RESPONSES.get(prompt_version, {}).get(provider_key, MOCK_RESPONSES["v1"]["openai"])
        # Split text into tokens / small phrase chunks
        chunks = [word + " " for word in mock_text.split(" ")]

        token_delay = 0.001 if "pytest" in sys.modules else 0.02
        for chunk in chunks:
            accumulated_content.append(chunk)
            delta_event = {"type": "delta", "content": chunk}
            yield f"data: {json.dumps(delta_event)}\n\n"
            await asyncio.sleep(token_delay)
    else:
        # Live multi-model routing via LiteLLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": privacy_report.sanitized_text},
        ]

        async def get_litellm_stream(target_model: str):
            extra_kwargs: Dict[str, Any] = {}
            if "cometai" in target_model.lower() and settings.cometai_api_key:
                extra_kwargs["api_base"] = settings.cometai_base_url
                extra_kwargs["api_key"] = settings.cometai_api_key
            elif "gemini" in target_model.lower() and settings.gemini_api_key:
                extra_kwargs["api_key"] = settings.gemini_api_key
            elif ("gpt" in target_model.lower() or "openai" in target_model.lower()) and settings.openai_api_key:
                extra_kwargs["api_key"] = settings.openai_api_key
            elif "claude" in target_model.lower() and settings.anthropic_api_key:
                extra_kwargs["api_key"] = settings.anthropic_api_key

            return await litellm.acompletion(
                model=target_model,
                messages=messages,
                stream=True,
                **extra_kwargs,
            )

        primary_gemini = settings.provider_models.get("gemini", "gemini/gemini-3.5-flash-lite")
        gemini_secondaries = ["gemini/gemini-2.5-flash", "gemini/gemini-2.0-flash"]

        # Pre-flight check: verify if requested provider has configured API key
        req_provider = request.provider.lower()
        has_key = True
        if req_provider == "openai":
            has_key = is_valid_key(settings.openai_api_key)
        elif req_provider == "anthropic":
            has_key = is_valid_key(settings.anthropic_api_key)
        elif req_provider == "cometai":
            has_key = is_valid_key(settings.cometai_api_key)
        elif req_provider == "gemini":
            has_key = is_valid_key(settings.gemini_api_key)

        gemini_available = is_valid_key(settings.gemini_api_key) or bool(settings.gemini_api_key)

        candidates: List[str] = []
        if req_provider in ["openai", "anthropic", "cometai"] and not has_key and gemini_available:
            # Immediate failover to Gemini without calling missing provider or emitting error banner
            fallback_triggered = True
            candidates.append(primary_gemini)
            for m in gemini_secondaries:
                if m != primary_gemini and m not in candidates:
                    candidates.append(m)
        else:
            candidates.append(model_name)
            if "gemini" not in model_name.lower() and primary_gemini not in candidates:
                candidates.append(primary_gemini)
            for m in gemini_secondaries:
                if m not in candidates:
                    candidates.append(m)

        last_err: Optional[Exception] = None
        for candidate in candidates:
            if candidate != model_name:
                fallback_triggered = True

            try:
                stream = await get_litellm_stream(candidate)
                async for chunk in stream:
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()

                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        accumulated_content.append(delta)
                        delta_event = {"type": "delta", "content": delta}
                        yield f"data: {json.dumps(delta_event)}\n\n"

                # Successfully completed streaming from this candidate
                model_name = candidate
                last_err = None
                break
            except Exception as stream_err:
                last_err = stream_err
                fallback_triggered = True
                # If content was already emitted to the user, do not restart with another model
                if accumulated_content:
                    model_name = candidate
                    break
                # Zero tokens were streamed: retry against next candidate model (e.g. secondary Gemini)
                continue

        # If all candidates failed and zero content tokens were streamed, emit graceful error event
        if not accumulated_content and last_err is not None:
            error_event = {
                "type": "error",
                "message": f"Upstream provider error: {str(last_err)}",
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"
            return

    # End timing and compute telemetry metrics
    end_time = time.perf_counter()
    if first_chunk_time is None:
        first_chunk_time = end_time

    ttft_ms = round((first_chunk_time - start_time) * 1000.0, 2)
    total_ms = round((end_time - start_time) * 1000.0, 2)

    full_response = "".join(accumulated_content)
    # Estimate token counts (approx 4 chars per token)
    prompt_tokens = max(1, len(privacy_report.sanitized_text + system_prompt) // 4)
    completion_tokens = max(1, len(full_response) // 4)
    cost_usd = calculate_cost(model_name, prompt_tokens, completion_tokens)

    metrics = TelemetryMetrics(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        model_used=model_name,
        prompt_version=prompt_version,
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        redacted_count=privacy_report.redacted_count,
        fallback_triggered=fallback_triggered,
        mcp_tools_used=mcp_tools_used,
    )

    # Log to SQLite and stdout
    await log_telemetry(metrics)

    # 4. Final Events: Telemetry and [DONE]
    telemetry_event = {
        "type": "telemetry",
        **metrics.model_dump(),
    }
    yield f"data: {json.dumps(telemetry_event)}\n\n"
    yield "data: [DONE]\n\n"

