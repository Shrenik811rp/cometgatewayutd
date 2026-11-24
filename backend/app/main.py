from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastmcp import Client

from backend.app.config import resolve_available_gemini_models, settings
from backend.app.mcp_server import mcp
from backend.app.privacy import redact_pii
from backend.app.router import stream_model_response
from backend.app.schemas import ChatRequest, MetricsSummaryResponse, PrivacyReport
from backend.app.telemetry import get_metrics_summary, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite telemetry database table on startup
    await init_db()
    # Dynamic Gemini model auto-discovery if live key is provided
    if not settings.mock_mode and settings.gemini_api_key:
        await resolve_available_gemini_models(settings.gemini_api_key)
    yield


app = FastAPI(
    title="CometGateway API",
    description="Multi-Model GenAI Orchestration & Evaluation Engine (UT Dallas CometAI-inspired)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Vite frontend, Vercel deployments, and local testing
cors_origins = (
    ["*"]
    if settings.allowed_origins.strip() == "*"
    else [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "mock_mode": settings.mock_mode,
    }


@app.get("/v1/mcp/status")
async def get_mcp_status():
    try:
        async with Client(mcp) as client:
            tools_result = await client.list_tools()
            tools_list = []
            for t in tools_result:
                tools_list.append({
                    "name": getattr(t, "name", str(t)),
                    "description": getattr(t, "description", "") or "",
                })
            return {
                "status": "online",
                "server": "UTD-OIT-Tools",
                "transport": "in-memory",
                "tool_count": len(tools_list),
                "tools": tools_list,
            }
    except Exception as exc:
        return {
            "status": "offline",
            "server": "UTD-OIT-Tools",
            "error": str(exc),
        }


@app.get("/v1/metrics", response_model=MetricsSummaryResponse)
async def get_metrics():
    return await get_metrics_summary()


@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    if request.enable_pii_redaction:
        privacy_report = redact_pii(request.prompt)
    else:
        privacy_report = PrivacyReport(
            original_text=request.prompt,
            sanitized_text=request.prompt,
            redacted_count=0,
            entities=[],
        )

    return StreamingResponse(
        stream_model_response(request, privacy_report),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
