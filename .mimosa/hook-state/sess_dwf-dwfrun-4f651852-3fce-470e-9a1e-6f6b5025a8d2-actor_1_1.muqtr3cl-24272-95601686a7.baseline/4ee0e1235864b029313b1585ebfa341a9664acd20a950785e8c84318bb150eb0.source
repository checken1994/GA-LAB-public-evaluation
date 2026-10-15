import tempfile
from pathlib import Path

import pytest

from scp.hands.hands_executor import HandsExecutor
from scp.hands.planner import HandsPlanner
from scp.pc_control.pc_controller import PCController
from scp.security.autonomous_governor import AutonomousCapabilityGovernor
from scp.security.capability_epoch import CapabilityAuthority


@pytest.mark.asyncio
async def test_autonomous_mode_e2e_reality(monkeypatch):
    """FA-13 E2E test for Governor -> Planner -> HandsExecutor -> PCController."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target_file = tmp_path / "hello.txt"
        
        # 1. Setup the full reality chain
        authority = CapabilityAuthority(str(tmp_path / "caps.sqlite3"))
        # Force issue a transport token for the controller setup
        authority.issue("hands")
        
        governor = AutonomousCapabilityGovernor(authority)
        controller = PCController(working_dir=str(tmp_path), capability_authority=authority)
        executor = HandsExecutor(
            controller=controller,
            capability_authority=authority,
            data_dir=tmp_path,
        )
        planner = HandsPlanner(
            executor=executor,
            autonomous_governor=governor,
        )
        planner.plan_path = tmp_path / "plans.jsonl"
        # Enable autonomous mode for the test
        planner.autonomous_mode = True
        monkeypatch.setenv("SCP_AUTONOMOUS_MODE", "1")
        
        # 2. Create an autonomous plan (no human)
        plan_data = planner.create_plan(
            goal="Test autonomous capability",
            steps=[
                {
                    "stepId": "s1",
                    "action": "pc.write_file",
                    "params": {
                        "path": str(tmp_path / "hello.txt"),
                        "content": "autonomous_success"
                    }
                }
            ],
            metadata={"task_id": "t_e2e"}
        )
        plan_id = plan_data["planId"]
        
        # 3. Execute!
        # The planner should consult governor, governor issues token, planner passes it to executor,
        # executor verifies 'hands:pc.execute', controller executes it.
        result = await planner.run_plan(plan_id=plan_id)
        
        # 4. Verify postconditions
        print("RESULT:", result)
        assert result["success"] is True
        
        # 5. Verify the actual physical file was created (Reality proof)
        assert target_file.exists()
        content = target_file.read_text().strip()
        assert "autonomous_success" in content
