# Top-agent lessons implemented in SCP

This note maps public, first-party design guidance to changes that can be inspected in the canonical GA-LAB repository.

| Source | Lesson | SCP implementation status |
|---|---|---|
| [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) and [tracing guide](https://openai.github.io/openai-agents-python/tracing/) | Small agent/tool primitives, explicit guardrails, workflow traces and parent-child spans | Implemented natively as a bounded trace contract; not claimed to be the SDK or an OpenTelemetry exporter |
| [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) | Prefer the simplest reliable workflow, clear tool interfaces and transparent control flow | Implemented by adding a small additive contract rather than copying a framework or adding another agent loop |
| [Temporal — Durable Execution](https://temporal.io/blog/what-is-durable-execution) | Persist workflow state so process failure does not silently lose progress | SCP already has TaskKernel checkpoint/lease/reconcile paths; Temporal-level distributed durable execution remains unclaimed |
| [MCP specification](https://modelcontextprotocol.io/specification/2026-07-28) | Explicit capabilities, cancellation, progress, errors and safe tool boundaries | SCP has capability/Hands controls and a staged protocol backlog; MCP conformance is not claimed |
| [Google A2A announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) | Agent identity, task lifecycle and artifact-oriented interoperability | Mapped to a future adapter backlog; no A2A interoperability claim |
| [OpenTelemetry GenAI observability](https://opentelemetry.io/blog/2026/genai-observability/) | Metadata-only telemetry by default; explicit opt-in for sensitive content; model/tool/token/duration dimensions | SCP hashes request content and redacts sensitive attributes; OTLP export and GenAI semantic conventions remain future work |
| [gVisor documentation](https://gvisor.dev/docs/) | Real isolation requires a distinct sandbox boundary, not a function named `sandbox` | SCP does not claim OS-level isolation; gVisor/Firecracker/container proof remains a separate blocked gate |

The implementation branch passed the repository release gate before merge and the merged main branch passed it afterward. The bounded smoke evidence is included separately and states exactly what was exercised. Nothing in this document upgrades RAG Gold/Ragas/ARES, human review, production readiness, or external protocol conformance without new evidence.
