# Antigravity Agent Operating Instructions — CometGateway

## 1. Project Context & Goal
We are building **CometGateway**, a modular Multi-Model GenAI Orchestration & Evaluation Engine designed to mirror UT Dallas OIT's **CometAI** architecture. 
- **Target Audience:** UT Dallas OIT Enterprise Technology Innovation & Services (ETIS) engineering recruiters.
- **Core Pillars:** 
  1. Vendor-agnostic multi-model routing (OpenAI, Anthropic Claude, Google Gemini) with SSE streaming.
  2. Pre-inference FERPA/PII data privacy enforcement (stripping SSNs, emails, and 10-digit UTD IDs).
  3. Structured telemetry (TTFT, total latency, token count, estimated cost, redacted entity count).
  4. Automated Pytest evaluation suite (privacy gate, Pydantic schema validation, prompt drift/quality benchmark).

## 2. Strict Tech Stack & Constraints
- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, LiteLLM (`acompletion`), `aiosqlite` (for telemetry storage), `pytest` + `pytest-asyncio`.
- **Privacy Engine:** Lightweight regex + Presidio-compatible entity scanner (ensure zero heavy model downloads block startup; use fast regex/spaCy `en_core_web_sm` or deterministic pattern matchers for UTD IDs `202\d{7}`, SSNs, emails, and phone numbers so tests run in <2 seconds).
- **Frontend:** TypeScript, React 18, Vite, Tailwind CSS (single-screen demo dashboard).
- **DevOps:** Docker, `docker-compose.yml`, GitHub Actions (`.github/workflows/ci.yml`).
- **Rule:** Never hardcode API keys. Always read `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` from `.env`, and support a `MOCK_MODE=true` environment flag so the entire UI and test suite run cleanly even without live API credits.

## 3. Mandatory State-Tracking Protocol (CRITICAL)
Before writing any code on a new prompt:
1. **Read `PROGRESS.md` and `ARCHITECTURE.md`** to verify the exact current phase, checkpoint, and file paths.
2. **Execute only the next unchecked checkpoint** (or the specific phase requested by the user). Keep changes modular and test each file as you create it.
3. **Update `PROGRESS.md` immediately** after completing any checkpoint:
   - Change `[ ]` to `[x]` for completed items.
   - Update the `Current Status` header (`Active Phase`, `Last Completed Checkpoint`, `Next Action`, and `Known Issues/Notes`).
4. **Verify before advancing:** Run `pytest` or syntax/type checks at the end of every phase before marking the phase complete.