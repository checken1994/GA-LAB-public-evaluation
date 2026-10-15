import json
from pathlib import Path

repo = Path("D:/scp")
with open(repo / ".agents/explorer_survey_1/subsystems_data.json", encoding="utf-8") as f:
    subs = json.load(f)

# Subsystem descriptions based on architecture docs and code inspection
subsystem_roles = {
    "api": "HTTP REST and WebSocket API layer exposing FastAPI endpoints, routers, and request handlers for clients/dashboard.",
    "api_server_parts": "Extracted request execution, background tasks, and lifespan logic unbundled from api_server.py.",
    "audit_engine": "Hermetic audit and verification pipeline engine; currently isolated deadzone subsystem.",
    "audit_r8": "Historical Round 8 audit artifacts, self-audits, and findings data (0 Python files).",
    "audit_r9": "Historical Round 9 audit artifacts, self-audits, and findings data (0 Python files).",
    "autofix": "Autonomous error detection, AST transformation, semantic code patching, and self-healing engine.",
    "benchmark": "Benchmark execution framework, baseline comparisons, and accuracy/anti-hallucination measurement.",
    "brain": "Memory and error indexing subsystem; stores and retrieves error traces and operational history.",
    "calibration": "Confidence calibration engine ensuring model uncertainty estimates align with reality.",
    "capabilities": "Fine-grained system capability registry, verification, and boundary enforcement.",
    "consolidator": "State consolidation and reconciliation across distributed background worker cycles.",
    "contracts": "Formal schema contracts, interface specifications, and invariant assertions.",
    "core": "Core orchestration, lifecycle governance, consensus adjudication, learning ledgers, and token security.",
    "data_sources": "Domain data connectors and external evidence scrapers (geography, chemistry, wikidata, etc.).",
    "epistemic": "Epistemic evidence tracking, certainty boundaries, and factual knowledge provenance.",
    "experience": "Historical experience accumulation, lesson synthesis, and episodic case memory.",
    "forecast": "Predictive outcome scoring and prospective error risk estimation.",
    "foundation": "Low-level system primitives, abstract base classes, and core interface definitions.",
    "governance": "Ethical and architectural rule enforcement, privacy write gates, and retention policies.",
    "hands": "Physical agent execution tools: OS command execution, task planning, and browser/UI interactions.",
    "history": "Long-term historical session logs, audit traces, and event chronicle storage.",
    "interfaces": "Public interface contracts and protocol specifications for external integration.",
    "knowledge": "Knowledge base management, domain vector stores, antibody patterns, and reputation tracking.",
    "learning": "Continual learning loop, RL-HF feedback processing, and policy parameter adaptation.",
    "llm_gateway": "Unified multi-provider LLM routing, token pricing, egress guard, and failover management.",
    "mcp_server": "Model Context Protocol (MCP) server implementation for external tool integration.",
    "meta": "Self-reflective cognitive reasoning, falsification engine, WHY gate, and logical validation.",
    "observability": "System telemetry, OpenTelemetry export, Prometheus metrics, and execution logging.",
    "pc_control": "Desktop/OS automation controller (GUI, keyboard, mouse, window management).",
    "persistence": "Database persistence abstractions, connection pools, and migration management.",
    "policy": "Access control policies, security rule evaluation, and policy decision points.",
    "prediction": "Time-series and sequence prediction models for agent behavior and error anticipation.",
    "rag": "Retrieval-Augmented Generation pipeline combining local knowledge bases with LLM prompts.",
    "release": "Release identity verification, build reproducibility gates, and commit validation.",
    "risk_intelligence": "Dynamic security risk scoring, anomaly detection, and vulnerability assessments.",
    "runtime": "Execution runtime containing reality judge, domain SLM experts, and ask pipeline orchestration.",
    "sandbox_evaluator": "Isolated execution sandbox for validating generated code and untrusted commands.",
    "security": "Fail-Closed Security layer: JWT guards, attack detection, egress policy, and token boundaries.",
    "self_model": "Internal representation of system capabilities, operational boundaries, and health status.",
    "task_kernel_parts": "Underlying TaskKernel state machine implementation, lease management, and event journaling.",
    "tests": "Embedded internal tests, chaos recovery, and property tests co-located in scp package.",
    "web_control": "Web automation engine: headless browser (Playwright), search scraping, and web navigation.",
    "world_state": "Dynamic environment modeling, world state tracking, and state delta computation.",
}

table_rows = []
for name, data in sorted(subs.items()):
    role = subsystem_roles.get(name, "SCP functional component.")
    god_files_summary = f"{len(data['god_files'])} god files" if data['god_files'] else "None"
    table_rows.append({
        "name": name,
        "path": data["path"],
        "files": data["file_count"],
        "loc": data["loc"],
        "role": role,
        "god_files_count": len(data["god_files"]),
        "god_files": data["god_files"],
        "outbound_count": len(data["outbound"]),
        "outbound": data["outbound"],
        "inbound_count": len(data["inbound"]),
        "inbound": data["inbound"]
    })

with open(repo / ".agents/explorer_survey_1/catalog_table.json", "w", encoding="utf-8") as f:
    json.dump(table_rows, f, indent=2)

print("Generated catalog table with 43 subsystems.")
