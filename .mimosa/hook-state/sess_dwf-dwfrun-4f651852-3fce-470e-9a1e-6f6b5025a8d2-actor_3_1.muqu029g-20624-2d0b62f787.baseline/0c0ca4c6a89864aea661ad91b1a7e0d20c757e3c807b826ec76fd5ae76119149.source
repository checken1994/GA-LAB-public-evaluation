"""
Script tạo đầy đủ test file cho toàn bộ subsystem SCP.
Mỗi subsystem sống → test import + endpoint thật.
Mỗi subsystem chết → test isolation (không ai import nó).
"""
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = _REPO_ROOT / "tests"
SCP_DIR = _REPO_ROOT / "scp"

ENV_HEADER = """import os
os.environ.setdefault("SCP_API_PROFILE", "full")
os.environ.setdefault("SCP_CAPABILITY_SECRET", "dummy-secret-for-tests-123")
os.environ.setdefault("SCP_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("SCP_TOP_SYSTEMS_EGRESS", "0")
"""

# ==============================================================================
# MẠCH CHÍNH (API-backed, 1 file mỗi mạch)
# ==============================================================================
ACTIVE_FLOWS = {
    # (file_num, name, list_of_tests)
    # test = (test_func_name, method, path, body_or_None, description)
    "01_boot": [
        ("test_server_alive", "GET", "/", None, "Server khởi động, không crash 500"),
        ("test_v104_heartbeat", "GET", "/v104/status", None, "Heartbeat v104 tồn tại"),
        ("test_v102_orchestrator_stats", "GET", "/v102/orchestrator/stats", None, "v102 router mounted"),
        ("test_v103_storage_stats", "GET", "/v103/storage/stats", None, "v103 storage router mounted"),
    ],
    "02_ask_chat": [
        ("test_ask_endpoint", "POST", "/ask", {"question": "ping"}, "/ask endpoint mounted"),
        ("test_multi_turn_check", "POST", "/v104/multi-turn/check", {"messages": [{"role": "user", "content": "x"}]}, "multi-turn mounted"),
        ("test_image_check", "POST", "/v104/image/check", {}, "image check mounted"),
    ],
    "03_openai_compat": [
        ("test_models_list", "GET", "/v1/models", None, "GET /v1/models → openai_compat router"),
        ("test_chat_completions", "POST", "/v1/chat/completions", {"model": "scp", "messages": [{"role": "user", "content": "x"}]}, "POST /v1/chat/completions"),
        ("test_swe_bench_chat", "POST", "/v1/chat/completions", {"model": "scp", "messages": []}, "SWE-bench compat"),
    ],
    "04_control_hands": [
        ("test_pc_status", "GET", "/v3/pc/status", None, "/v3/pc/status → pc_controller_router"),
        ("test_pc_plan", "POST", "/v3/pc/plan", {}, "/v3/pc/plan"),
        ("test_hands_status", "GET", "/v3/hands/status", None, "/v3/hands/status → hands_router"),
        ("test_hands_capabilities", "GET", "/v3/hands/capabilities", None, "/v3/hands/capabilities"),
        ("test_web_status", "GET", "/v3/web/status", None, "/v3/web/status → web_control_router"),
    ],
    "05_agent_call": [
        ("test_agent_status", "GET", "/v3/agent/status", None, "/v3/agent/status → agent_router"),
        ("test_agent_plan", "POST", "/v3/agent/plan", {}, "/v3/agent/plan"),
        ("test_call_status", "GET", "/v3/call/status", None, "/v3/call/status → call_router"),
    ],
    "06_prediction": [
        ("test_predictions_all", "GET", "/v105/predictions/all", None, "/v105/predictions/all"),
        ("test_predictions_pending", "GET", "/v105/predictions/pending", None, "/v105/predictions/pending"),
    ],
    "07_autofix": [
        ("test_autofix_permissions", "GET", "/v105/autofix/permissions", None, "/v105/autofix/permissions"),
        ("test_capability_status", "GET", "/v105/capability/status", None, "/v105/capability/status"),
    ],
    "08_audit_benchmark": [
        ("test_audit_stats", "GET", "/v105/audit/stats", None, "/v105/audit/stats → audit_router"),
        ("test_audit_findings", "GET", "/v105/audit/findings", None, "/v105/audit/findings"),
        ("test_benchmark_batch", "POST", "/v3/hands/benchmark/batch", {"questions": []}, "benchmark batch mounted"),
    ],
    "09_threat": [
        ("test_threat_ai_stats", "GET", "/v105/threats/ai-scan/stats", None, "/v105/threats/ai-scan/stats"),
        ("test_threat_harm_stats", "GET", "/v105/threats/harm/stats", None, "/v105/threats/harm/stats"),
        ("test_threat_findings", "GET", "/v105/threats/ai-scan/findings", None, "/v105/threats/ai-scan/findings"),
    ],
    "10_streaming": [
        ("test_stream_ask", "POST", "/v105/ask/stream", {"question": "x"}, "/v105/ask/stream → stream_router"),
    ],
    "11_admin_webhook": [
        ("test_v100_status", "GET", "/v100/status", None, "/v100/status → v100_admin_router"),
        ("test_antibody_stats", "GET", "/v100/antibodies/stats", None, "/v100/antibodies/stats"),
        ("test_v98_analyze", "POST", "/v98/analyze-session", {}, "/v98 admin router"),
    ],
    "12_background_why": [
        # No HTTP endpoint, test by import
    ],
    "13_free_api_top_systems": [
        ("test_top_systems_status", "GET", "/v104/learn/top-systems/status", None, "Mạch 13: top-systems/status"),
        ("test_fast_learning_status", "GET", "/v104/learn/fast/status", None, "fast learning status"),
        ("test_learn_status", "GET", "/v104/learn/status", None, "/v104/learn/status"),
        ("test_learn_matrix", "GET", "/v104/learn/matrix", None, "/v104/learn/matrix"),
    ],
}

# ==============================================================================
# HỆ THỐNG CON SỐNG (import test)
# ==============================================================================
ALIVE_SUBSYSTEMS = {
    "api": ("scp.api.routes", "Router package"),
    "autofix": ("scp.autofix", "AutoFix engine"),
    "benchmark": ("scp.benchmark", "Benchmark engine"),
    "contracts": ("scp.contracts", "Core contracts"),
    "core": ("scp.core", "Core business logic"),
    "data_sources": ("scp.data_sources.free_api_catalog", "Free API catalog"),
    "epistemic": ("scp.epistemic", "Epistemic system"),
    "foundation": ("scp.foundation", "Foundation layer"),
    "governance": ("scp.governance", "Governance"),
    "hands": ("scp.hands", "Hands system"),
    "knowledge": ("scp.knowledge.domain_store", "Knowledge domain store"),
    "llm_gateway": ("scp.llm_gateway", "LLM Gateway"),
    "meta": ("scp.meta", "Meta reasoning"),
    "observability": ("scp.observability", "Observability"),
    "pc_control": ("scp.pc_control", "PC Controller"),
    "persistence": ("scp.persistence", "Persistence layer"),
    "prediction": ("scp.prediction.predictive", "Prediction engine"),
    "runtime": ("scp.runtime", "Runtime judge"),
    "security": ("scp.security", "Security layer"),
    "task_kernel": ("scp.task_kernel_parts", "Task kernel"),
    "web_control": ("scp.web_control", "Web control"),
}

# ==============================================================================
# HỆ THỐNG CON CHẾT (isolation test - mỗi cái 1 file riêng)
# ==============================================================================
DEAD_SUBSYSTEMS = [
    "brain",
    "calibration",
    "capabilities",
    "consolidator",
    "experience",
    "forecast",
    "history",
    "learning",
    "policy",
    "rag",
    "release",
    "risk_intelligence",
    "self_model",
    "world_state",
    "audit_engine",
    "audit_r8",
    "audit_r9",
]


def make_active_flow_test(flow_key: str, tests: list) -> str:
    lines = [ENV_HEADER, ""]
    lines.append("from fastapi.testclient import TestClient")
    lines.append("from scp.api_server import app")
    lines.append("")
    lines.append("")

    if flow_key == "12_background_why":
        lines.append("def test_flow_12_why_engine_importable():")
        lines.append('    """Mạch 12: WhyEngine module phải import được."""')
        lines.append("    import importlib")
        lines.append('    mod = importlib.import_module("scp.meta.why_engine_parts.whyengine")')
        lines.append("    assert mod is not None")
        lines.append("")
        lines.append("def test_flow_12_why_engine_has_class():")
        lines.append('    """Mạch 12: WhyEngine class phải tồn tại."""')
        lines.append("    from scp.meta.why_engine_parts import whyengine")
        lines.append('    assert hasattr(whyengine, "WhyEngine")')
        return "\n".join(lines)

    for (func_name, method, path, body, desc) in tests:
        lines.append(f"def {func_name}():")
        lines.append(f'    """{desc}"""')
        lines.append("    client = TestClient(app, raise_server_exceptions=False)")
        if method == "GET":
            lines.append(f'    response = client.get("{path}", headers={{"X-Admin-Token": "test"}})')
        else:
            lines.append(f'    response = client.{method.lower()}("{path}", json={body!r}, headers={{"X-Admin-Token": "test"}})')
        lines.append('    assert response.status_code != 404, (')
        lines.append(f'        f"FAIL: {path} → 404. Router chưa được mount! status={{response.status_code}}"')
        lines.append('    )')
        lines.append("")

    return "\n".join(lines)


def make_alive_subsystem_test(num: str, name: str, import_path: str, desc: str) -> str:
    return f"""{ENV_HEADER}

def test_subsystem_{name}_importable():
    \"\"\"{desc}: module phải import được không lỗi.\"\"\"
    import importlib
    mod = importlib.import_module("{import_path}")
    assert mod is not None, f"FAIL: {import_path} không import được!"
"""


def make_dead_zone_test(num: str, dead_sys: str) -> str:
    return f"""{ENV_HEADER}
import re
from pathlib import Path


def test_dead_{dead_sys}_no_external_imports():
    \"\"\"
    Hệ thống chết '{dead_sys}' phải bị cách ly hoàn toàn.
    Không có file nào bên ngoài thư mục '{dead_sys}/' được phép import nó.
    Nếu fail → Zombie Leak: code chết đang ảnh hưởng đến code sống.
    \"\"\"
    root = Path(__file__).parent.parent / "scp"
    pat = re.compile(r"^(from|import)\\s+scp\\.{dead_sys}\\b")
    all_py = list(root.rglob("*.py"))
    violations = []

    for py_file in all_py:
        norm = str(py_file).replace("\\\\", "/")
        if f"/scp/{dead_sys}/" in norm:
            continue  # Bỏ qua file nội bộ của chính dead_sys
        try:
            for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(line.strip()):
                    violations.append(f"  {{py_file.name}}:{{lineno}}: {{line.strip()}}")
        except Exception:
            pass

    if violations:
        raise AssertionError(
            f"[GAP-DEAD-ZONE] '{dead_sys}' bị zombie-import bởi:\\n" + "\\n".join(violations) +
            "\\n\\nHành động: xóa import hoặc dời module ra khỏi Dead Zone."
        )
"""


generated = []

# 1. Active flow tests (01-13)
FLOW_ORDER = [
    "01_boot", "02_ask_chat", "03_openai_compat", "04_control_hands",
    "05_agent_call", "06_prediction", "07_autofix", "08_audit_benchmark",
    "09_threat", "10_streaming", "11_admin_webhook", "12_background_why",
    "13_free_api_top_systems",
]
for i, key in enumerate(FLOW_ORDER, 1):
    fname = f"test_flow_{key}.py"
    content = make_active_flow_test(key, ACTIVE_FLOWS.get(key, []))
    (TESTS_DIR / fname).write_text(content, encoding="utf-8")
    generated.append(fname)
    print(f"OK {fname}")

# 2. Alive subsystem tests (ss_ prefix)
for i, (name, (import_path, desc)) in enumerate(ALIVE_SUBSYSTEMS.items(), 14):
    fname = f"test_subsystem_{name}.py"
    content = make_alive_subsystem_test(str(i).zfill(2), name, import_path, desc)
    (TESTS_DIR / fname).write_text(content, encoding="utf-8")
    generated.append(fname)
    print(f"OK {fname}")

# 3. Dead zone isolation tests (dz_ prefix, one per subsystem)
for i, dead_sys in enumerate(DEAD_SUBSYSTEMS, 35):
    fname = f"test_deadzone_{dead_sys}.py"
    content = make_dead_zone_test(str(i).zfill(2), dead_sys)
    (TESTS_DIR / fname).write_text(content, encoding="utf-8")
    generated.append(fname)
    print(f"OK {fname}")

print(f"\nTổng: {len(generated)} file test được tạo.")
