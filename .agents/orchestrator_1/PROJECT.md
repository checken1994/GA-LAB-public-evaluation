# Project: SCP Unified Chatbot + SCP (Chatbot + Autonomous Verification + Backward Traceability)

## Architecture
- **Layer 1: Unified Chatbot Interaction Core (R1)**:
  - User interaction enters via HTTP `POST /ask` or WebSocket `/chat`.
  - Question Router (`scp/runtime/question_router.py`) identifies intents:
    - `LANE_CHATBOT` for conversational, identity, concept explanations, math, reasoning, and open discussions.
    - `LANE_FACTUAL` for queries making factual claims requiring knowledge grounding.
    - `LANE_SECURITY` for attacks, jailbreaks, prompt injection, and dangerous payloads.
  - Multi-turn conversation history is unified across both `/ask` and `/chat` using `session_id` and `ChatMemoryStore`.
  - Gate unblocking in `AskKernelAdapter.verify_response`:
    - Only fail-closed on true security threats (`governance == "KILL"`, security violations, SSRF, injection).
    - Remove mandatory `verdict == "PASS"` constraint for `LANE_CHATBOT`.
    - Eliminate redundant second call to `RealityJudge().judge_async` (reducing latency and false-positive escalation).
    - Eliminate `"web_fallback_not_used"` penalty so web-assisted facts are never withheld.
  - Dynamic bilingual prompt (Vietnamese & English) based on query language.

- **Layer 2: Autonomous Evidence Retrieval & Fact Separation (R2)**:
  - Autonomous retrieval triggers on factual queries when context is insufficient or when candidate answer contains claims with low confidence (< 0.7):
    1. Internal Knowledge Base (`knowledge.sqlite3` / `DomainKnowledgeStore`).
    2. Public Safe Web Search (`scp/web_control/internet_search.py` via `InternetSearch`).
  - Quarantine: Web search snippets pass through `inspect_untrusted` before synthesis.
  - Structured Response Synthesis:
    - `verified_facts`: list of claims with evidence citations (`claim`, `source`, `url`, `confidence`, `evidence_snippet`).
    - `llm_reasoning`: model synthesis, reasoning, conjecture, or conversational context.
    - `confidence_badge`: Badge metadata (`badge`: `FACT_VERIFIED` | `CONVERSATIONAL` | `UNVERIFIED_CONJECTURE`, `score`, `sources_consulted`, `transparency_notes`).

- **Layer 3: Backward Traceability Engine & API (R3)**:
  - End-to-end `trace_id` generation (`trace-<uuid>`) across `/ask` and WebSocket `/chat`.
  - Propagation of `trace_id` down through router, retrieval, crosscheck, why-gate, and kernel finalize.
  - Dedicated persistent SQLite `TraceStore` (`data/trace_store.sqlite3` with WAL mode):
    - Indexed by `trace_id`.
    - Stores query, routing decision, retrieval snippets, multi-LLM crosscheck verdicts, governance decisions, and final decision.
  - Endpoint: `GET /api/scp/v3/trace/{trace_id}` providing full causal history and DAG graph for external LLMs / auditors.

- **Layer 4: Dashboard Interactive Traceability UI (R4)**:
  - Next.js Web Dashboard (`dashboard/src/components/dashboard/scp-overview.tsx`).
  - Multi-turn chat message history display.
  - Dedicated display components for `verified_facts`, `llm_reasoning`, and `confidence_badge`.
  - "Truy vết quyết định" (Inspect Trace Tree) button on every assistant message.
  - `DecisionTraceDrawer` (`dashboard/src/components/dashboard/decision-trace-drawer.tsx`) utilizing Radix UI Sheet:
    - Fetches trace from Next.js proxy route `/api/scp/v3/trace/[trace_id]`.
    - Renders 5-stage causal breakdown: Query & Routing -> Retrieval & Sources -> Multi-LLM Crosscheck -> Governance & WHY Gate -> Fact-Separated Synthesis.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Chatbot Intent Routing | Categorize queries into LANE_CHATBOT, LANE_FACTUAL, LANE_SECURITY in `question_router.py` | M1 | Survey E1 |
| 2 | Gate Unblocking & No Withhold | Unblock normal conversational, identity, and reasoning questions in `AskKernelAdapter.verify_response` and `_ask_impl.py` | M1 | Survey E1 |
| 3 | Redundant Judge Removal | Remove redundant second `judge_async` call in `AskKernelAdapter.verify_response` | M1 | Survey E1 |
| 4 | Web Penalty Removal | Remove `web_fallback_not_used` check from `verify_response` | M1 | Survey E1 |
| 5 | Bilingual Interaction | Dynamic Vietnamese and English system prompts and responses | M1 | Survey E1 |
| 6 | Multi-turn Memory Unification | Unify `ChatMemoryStore` across `/ask` and `/chat` via `session_id` | M1 | Survey E1 |
| 7 | Fail-Closed Attack Boundary | Preserve strict fail-closed protection for jailbreaks, prompt injection, unauthorized commands, SSRF | M1 | Survey E3 |
| 8 | Autonomous KB Retrieval | Auto-query `knowledge.sqlite3` for unverified factual claims | M2 | Survey E1 |
| 9 | Autonomous Web Search | Auto-query safe web search (`InternetSearch`) when KB is insufficient | M2 | Survey E1 |
| 10 | Web Snippet Quarantine | Sanitize untrusted web search snippets before synthesis context | M2 | Survey E3 |
| 11 | Structured Fact Separation | Separate `verified_facts` (with citations) from `llm_reasoning` in response payload | M2 | Survey E1 |
| 12 | Confidence & Transparency Badge | Return confidence badge with score, sources, and transparency notes | M2 | Survey E1 |
| 13 | Trace ID Propagation | Generate and propagate `trace_id` across `/ask`, WebSocket `/chat`, and adapter finalize | M3 | Survey E2 |
| 14 | SQLite TraceStore Engine | Durable SQLite store in `data/trace_store.sqlite3` storing full causal history | M3 | Survey E2 |
| 15 | Trace Lookup API | Expose `GET /api/scp/v3/trace/{trace_id}` in FastAPI and route profiles | M3 | Survey E2 |
| 16 | Causal History Serialization | Record query, routing, retrieval snippets, crosscheck verdicts, and why-gate audit per trace | M3 | Survey E2 |
| 17 | Dashboard Chat History UI | Multi-turn chat message UI in Next.js `scp-overview.tsx` | M4 | Survey E2 |
| 18 | Fact & Badge UI Component | Visual badge and citation display for verified facts vs model reasoning | M4 | Survey E2 |
| 19 | Inspect Trace Tree Button | Attach "Truy vết quyết định" button to each assistant message | M4 | Survey E2 |
| 20 | Decision Trace Drawer | Radix Sheet slide-over modal visualizing 5-stage causal trace tree | M4 | Survey E2 |
| 21 | Dashboard Trace Proxy API | Next.js API route `/api/scp/v3/trace/[trace_id]` with SSRF protection | M4 | Survey E2 |
| 22 | Comprehensive E2E Test Suite | 4-Tier opaque-box test suite (`tests/T12_unified_chatbot/`) | M5 / E2E Track | Survey E3 |
| 23 | Meta-Audit & Non-Regression | Zero regressions on `pytest tests/` and `tools/t00_meta_audit.py` | M5 | Survey E3 |
| 24 | Adversarial Coverage Hardening | White-box coverage hardening (Tier 5) with challenger | M5 | Survey E3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Unified Chatbot Interaction Core | `scp/runtime/question_router.py`, `scp/ask_kernel_adapter.py`, `scp/api_server_parts/_ask_impl.py`, `scp/api/chat.py`, `scp/core/chat_memory.py` | none | DONE (worker: d8da2922, 163 T02 + 121 T07 passed, meta-audit clean) |
| 2 | M2: Autonomous Evidence Retrieval & Fact Separation | `scp/knowledge/`, `scp/web_control/internet_search.py`, `scp/api_server_parts/_ask_impl.py`, `scp/api/chat.py`, `scp/ask_kernel_adapter.py` | M1 | DONE (worker: 18c23f01, 10 M2 + 131 T07 + 163 T02 + 105 T12 passed, meta-audit clean) |
| 3 | M3: Backward Traceability Engine & API | `scp/core/trace_store.py`, `scp/api/routes/trace_routes.py`, `scp/api_server.py`, `scp/api/route_profile.py`, router/judge/why_gate integration | M1 | IN_PROGRESS (worker: 8f13dd3a) |
| 4 | M4: Dashboard Interactive Traceability UI | `dashboard/src/components/dashboard/`, `dashboard/src/app/api/scp/`, `dashboard/src/lib/` | M2, M3 | PLANNED |
| 5 | M5: Final Milestone (100% E2E Pass + Adversarial Hardening) | Full integration, `pytest tests/`, `tools/t00_meta_audit.py`, Tier 5 adversarial audit | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### Question Router ↔ Kernel Adapter & Ask Impl
- `route_question_async(question: str) -> RouteDecision`:
  - `intent`: `LANE_CHATBOT` | `LANE_FACTUAL` | `LANE_SECURITY` | `LOOKUP` | `ACTION`
  - `confidence`: float [0.0 - 1.0]
  - `language`: `"vi"` | `"en"` | `"other"`
  - `bypass_verdict_pass`: bool (True for `LANE_CHATBOT` unless security flags present)

### Autonomous Retrieval ↔ Synthesis Payload
- `verified_facts`: `list[dict]` with fields:
  - `claim`: str
  - `source`: str (`"knowledge_base"` | `"web_search"`)
  - `url`: Optional[str]
  - `confidence`: float [0.0 - 1.0]
  - `evidence_snippet`: str
- `llm_reasoning`: str
- `confidence_badge`: dict with fields:
  - `badge`: `"FACT_VERIFIED"` | `"CONVERSATIONAL"` | `"UNVERIFIED_CONJECTURE"`
  - `score`: float [0.0 - 1.0]
  - `sources_consulted`: list[str]
  - `transparency_notes`: str

### Trace Store ↔ Trace API & Dashboard
- Endpoint: `GET /api/scp/v3/trace/{trace_id}`
- Response schema:
  - `trace_id`: str (`trace-<hex>`)
  - `timestamp`: str (ISO 8601 UTC)
  - `session_id`: Optional[str]
  - `query`: str
  - `routing`: `{"intent": str, "lane": str, "language": str, "confidence": float}`
  - `retrieval`: `{"kb_hits": list, "web_search_hits": list, "retrieval_triggered": bool}`
  - `multi_llm_crosscheck`: `{"consensus": str, "primary": dict, "secondary": dict, "final": Any}`
  - `governance`: `{"governance_decision": str, "why_gate_decision": str, "audit_reasons": list}`
  - `final_decision`: `{"verdict": str, "badge": str, "verified_facts_count": int}`
  - `causal_graph`: `{"nodes": list[dict], "edges": list[dict]}`

## Code Layout
- `scp/runtime/question_router.py`: Question classification, intent, lane routing
- `scp/ask_kernel_adapter.py`: Kernel RAG adapter, `verify_response`, `_safe_response`
- `scp/api_server_parts/_ask_impl.py`: Core `/ask` pipeline implementation
- `scp/api/chat.py`: WebSocket `/chat` pipeline implementation
- `scp/core/chat_memory.py`: Multi-turn conversation store (`ChatMemoryStore`)
- `scp/core/trace_store.py`: SQLite-backed persistent Trace Store
- `scp/api/routes/trace_routes.py`: FastAPI route `GET /api/scp/v3/trace/{trace_id}`
- `dashboard/src/components/dashboard/scp-overview.tsx`: Dashboard chat and trace triggers
- `dashboard/src/components/dashboard/decision-trace-drawer.tsx`: Drawer for causal trace visualization
- `dashboard/src/app/api/scp/v3/trace/[trace_id]/route.ts`: Next.js proxy route for trace inspection
- `tests/T12_unified_chatbot/`: Comprehensive 4-tier E2E test suite
