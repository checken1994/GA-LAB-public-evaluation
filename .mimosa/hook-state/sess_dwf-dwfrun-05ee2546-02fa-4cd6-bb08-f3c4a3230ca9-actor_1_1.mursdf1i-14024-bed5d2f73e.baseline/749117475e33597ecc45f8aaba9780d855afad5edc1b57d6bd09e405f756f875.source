from pathlib import Path

REQUIRED_CHILD_SAFE_LINES = {
    "SCP_EVOLUTION_AUTO=0",
    "SCP_EVOLUTION_ENABLED=0",
    "SCP_WHY_LLM_ENABLED=0",
    "SCP_SUBSYSTEM_TELEMETRY_ENABLED=1",
    "SCP_FAST_LEARNING_CYCLE_TIMEOUT_SECONDS=300",
}


def test_supervisor_recreates_required_child_safe_boundaries():
    root = Path(__file__).resolve().parents[2]
    supervisor = (root / "scripts" / "ops" / "scp_247_supervisor.ps1").read_text(encoding="utf-8")
    for line in REQUIRED_CHILD_SAFE_LINES:
        assert f"'{line}'" in supervisor


def test_dashboard_receives_scheduler_admin_boundary():
    root = Path(__file__).resolve().parents[2]
    supervisor = (root / "scripts" / "ops" / "scp_247_supervisor.ps1").read_text(encoding="utf-8")
    assert "'dashboard'))" in supervisor
    assert "$env:SCP_SCHEDULER_ADMIN_TOKEN = $adminToken" in supervisor
    assert "$env:SCP_SCHEDULER_ADMIN_TOKEN_FILE = $AdminTokenFile" in supervisor


def test_supervisor_manages_llm_bridge():
    root = Path(__file__).resolve().parents[2]
    supervisor = (root / "scripts" / "ops" / "scp_247_supervisor.ps1").read_text(encoding="utf-8")
    assert "Name = 'llm-bridge'" in supervisor
    assert "$env:SCP_LLM_BRIDGE_PORT = '8081'" in supervisor


def test_supervisor_rebuilds_stale_dashboard_before_starting_standalone_server():
    root = Path(__file__).resolve().parents[2]
    supervisor = (root / "scripts" / "ops" / "scp_247_supervisor.ps1").read_text(encoding="utf-8")
    assert "$DashboardStandaloneServer = Join-Path $DashboardDir '.next\\standalone\\server.js'" in supervisor
    assert "$DashboardBuildId = Join-Path $DashboardDir '.next\\BUILD_ID'" in supervisor
    assert "$DashboardNextCli = Join-Path $DashboardDir 'node_modules\\next\\dist\\bin\\next'" in supervisor
    assert "function Ensure-DashboardDependencies" in supervisor
    assert "'DASHBOARD_DEPENDENCY_INSTALL_FAILED'" in supervisor
    assert "@('install', '--frozen-lockfile')" in supervisor
    assert "function Get-DashboardBuildState" in supervisor
    assert "'DASHBOARD_BUILD_REFRESHED'" in supervisor
    assert "'DASHBOARD_BUILD_FAILED'" in supervisor
    assert "'DASHBOARD_BUILD_REFRESH_BLOCKED'" in supervisor
    assert "@('run', 'build')" in supervisor
    assert "-and $buildFresh -and (Test-HttpHealthy $service.Url)" in supervisor


def test_supervisor_sets_dashboard_proxy_contract_explicitly():
    root = Path(__file__).resolve().parents[2]
    supervisor = (root / "scripts" / "ops" / "scp_247_supervisor.ps1").read_text(encoding="utf-8")
    assert "$env:SCP_INTERNAL_URL = 'http://127.0.0.1:8000'" in supervisor
    assert "$env:LOOP_SCHEDULER_URL = 'http://127.0.0.1:3030'" in supervisor
    assert "$oldScpInternalUrl = $env:SCP_INTERNAL_URL" in supervisor
    assert "$oldLoopSchedulerUrl = $env:LOOP_SCHEDULER_URL" in supervisor


def test_supervisor_runtime_map_matches_dashboard_proxy_and_uses_production_start():
    root = Path(__file__).resolve().parents[2]
    supervisor = (root / "scripts" / "ops" / "scp_247_supervisor.ps1").read_text(encoding="utf-8")
    assert "Args = @('-m', 'scp', '8000')" in supervisor
    assert "Port = 8000; Url = 'http://127.0.0.1:8000/health'" in supervisor
    assert "Name = 'dashboard'; File = $bun; Args = @('run', 'start')" in supervisor
    assert "Args = @('run', 'dev')" in supervisor


def test_supervisor_health_probe_requires_success_status_not_any_non_5xx():
    root = Path(__file__).resolve().parents[2]
    supervisor = (root / "scripts" / "ops" / "scp_247_supervisor.ps1").read_text(encoding="utf-8")
    assert "return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)" in supervisor
    assert "return ($response.StatusCode -lt 500)" not in supervisor
