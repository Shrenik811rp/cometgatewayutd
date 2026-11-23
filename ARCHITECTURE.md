# CometGateway — System Architecture & Design Specification

## 1. Repository Structure
```text
comet-gateway/
├── GEMINI.md                     # Agent rules & state-tracking protocol
├── ARCHITECTURE.md               # Technical blueprint & contracts (this file)
├── PROGRESS.md                   # Live phase & checkpoint tracker
├── .env.example                  # Environment variables template
├── docker-compose.yml            # Multi-container orchestration (backend + frontend)
├── .github/
│   └── workflows/
│       └── ci.yml                # Automated pytest & typecheck pipeline
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI entry point, CORS, health & chat endpoints
│   │   ├── config.py             # Pydantic Settings (.env loader, model pricing map)
│   │   ├── schemas.py            # Pydantic request, SSE chunk, telemetry & eval schemas
│   │   ├── privacy.py            # FERPA/PII redaction engine (UTD ID, SSN, Email, Phone)
│   │   ├── router.py             # LiteLLM async streaming orchestrator + fallback logic
│   │   └── telemetry.py          # SQLite async logger + sanitized JSON stdout emitter
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py           # Pytest fixtures & mock LLM stream helpers
│       ├── golden_dataset.json   # 12 UTD campus IT & FERPA adversarial test cases
│       ├── test_privacy.py       # Unit tests asserting PII never leaks upstream
│       ├── test_schema.py        # Validates SSE event structure & JSON-mode outputs
│       └── test_eval.py          # Prompt v1 vs v2 regression & quality benchmark
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx               # Main split-pane demo dashboard
        ├── types.ts              # TypeScript interfaces matching backend schemas
        ├── api/
        │   └── streamClient.ts   # Fetch-based SSE stream parser
        └── components/
            ├── HeaderBar.tsx     # Model selector, PII toggle, Prompt version toggle
            ├── PromptPanel.tsx   # Input box + 1-click FERPA sample presets
            ├── ResponsePanel.tsx # Live markdown/text stream + redacted prompt preview
            └── TelemetryBar.tsx  # TTFT, Total Latency, Token Count, Cost, PII Redacted