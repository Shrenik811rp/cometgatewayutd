import json
import logging
import os
from typing import Any, Dict, List
import aiosqlite
from backend.app.config import settings
from backend.app.schemas import MetricsSummaryResponse, TelemetryMetrics

logger = logging.getLogger("telemetry")


def get_db_path() -> str:
    url = settings.database_url
    raw_path = url
    if ":///" in url:
        raw_path = url.split(":///", 1)[1]
    elif "://" in url:
        raw_path = url.split("://", 1)[1]
    abs_path = os.path.abspath(raw_path)
    dirname = os.path.dirname(abs_path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
    return abs_path


async def init_db(db_path: str = None) -> None:
    path = db_path or get_db_path()
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)

    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                request_id TEXT NOT NULL,
                model_used TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                ttft_ms REAL NOT NULL,
                total_ms REAL NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                redacted_count INTEGER NOT NULL,
                fallback_triggered INTEGER NOT NULL,
                mcp_tools_used TEXT DEFAULT '[]'
            )
            """
        )
        # Check and migrate existing schema if mcp_tools_used column is absent
        async with db.execute("PRAGMA table_info(request_logs)") as cursor:
            cols = [row[1] for row in await cursor.fetchall()]
            if "mcp_tools_used" not in cols:
                await db.execute("ALTER TABLE request_logs ADD COLUMN mcp_tools_used TEXT DEFAULT '[]'")
        await db.commit()


async def ensure_db_initialized(db: aiosqlite.Connection) -> None:
    async with db.execute("PRAGMA table_info(request_logs)") as cursor:
        cols = [row[1] for row in await cursor.fetchall()]
        if not cols:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    ttft_ms REAL NOT NULL,
                    total_ms REAL NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    redacted_count INTEGER NOT NULL,
                    fallback_triggered INTEGER NOT NULL,
                    mcp_tools_used TEXT DEFAULT '[]'
                )
                """
            )
            await db.commit()
        elif "mcp_tools_used" not in cols:
            await db.execute("ALTER TABLE request_logs ADD COLUMN mcp_tools_used TEXT DEFAULT '[]'")
            await db.commit()


async def log_telemetry(metrics: TelemetryMetrics, db_path: str = None) -> None:
    path = db_path or get_db_path()

    # 1. Insert into SQLite
    async with aiosqlite.connect(path) as db:
        await ensure_db_initialized(db)
        await db.execute(
            """
            INSERT INTO request_logs (
                timestamp, request_id, model_used, prompt_version,
                ttft_ms, total_ms, prompt_tokens, completion_tokens,
                cost_usd, redacted_count, fallback_triggered, mcp_tools_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics.timestamp,
                metrics.request_id,
                metrics.model_used,
                metrics.prompt_version,
                metrics.ttft_ms,
                metrics.total_ms,
                metrics.prompt_tokens,
                metrics.completion_tokens,
                metrics.cost_usd,
                metrics.redacted_count,
                1 if metrics.fallback_triggered else 0,
                json.dumps(metrics.mcp_tools_used),
            ),
        )
        await db.commit()

    # 2. Emit single sanitized JSON line to stdout (Splunk / SIEM ready, 0 raw prompt/PII)
    structured_log = {
        "event": "llm_telemetry",
        **metrics.model_dump(),
    }
    print(json.dumps(structured_log), flush=True)


async def get_metrics_summary(db_path: str = None) -> MetricsSummaryResponse:
    path = db_path or get_db_path()

    async with aiosqlite.connect(path) as db:
        await ensure_db_initialized(db)
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(AVG(ttft_ms), 0.0) as avg_ttft_ms,
                COALESCE(AVG(total_ms), 0.0) as avg_total_ms,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0.0) as total_cost_usd,
                COALESCE(SUM(redacted_count), 0) as total_pii_redacted,
                COALESCE(SUM(fallback_triggered), 0) as fallback_count
            FROM request_logs
            """
        ) as cursor:
            row = await cursor.fetchone()
            total_requests = row["total_requests"] if row else 0
            avg_ttft_ms = round(row["avg_ttft_ms"], 2) if row else 0.0
            avg_total_ms = round(row["avg_total_ms"], 2) if row else 0.0
            total_tokens = row["total_tokens"] if row else 0
            total_cost_usd = round(row["total_cost_usd"], 6) if row else 0.0
            total_pii_redacted = row["total_pii_redacted"] if row else 0
            fallback_count = row["fallback_count"] if row else 0

        async with db.execute(
            """
            SELECT 
                timestamp, request_id, model_used, prompt_version,
                ttft_ms, total_ms, prompt_tokens, completion_tokens,
                cost_usd, redacted_count, fallback_triggered,
                COALESCE(mcp_tools_used, '[]') as mcp_tools_used
            FROM request_logs
            ORDER BY id DESC
            LIMIT 10
            """
        ) as cursor:
            rows = await cursor.fetchall()
            recent_requests: List[Dict[str, Any]] = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("mcp_tools_used"), str):
                    try:
                        item["mcp_tools_used"] = json.loads(item["mcp_tools_used"])
                    except Exception:
                        item["mcp_tools_used"] = []
                recent_requests.append(item)


    return MetricsSummaryResponse(
        total_requests=total_requests,
        avg_ttft_ms=avg_ttft_ms,
        avg_total_ms=avg_total_ms,
        total_tokens=total_tokens,
        total_cost_usd=total_cost_usd,
        total_pii_redacted=total_pii_redacted,
        fallback_count=fallback_count,
        recent_requests=recent_requests,
    )
