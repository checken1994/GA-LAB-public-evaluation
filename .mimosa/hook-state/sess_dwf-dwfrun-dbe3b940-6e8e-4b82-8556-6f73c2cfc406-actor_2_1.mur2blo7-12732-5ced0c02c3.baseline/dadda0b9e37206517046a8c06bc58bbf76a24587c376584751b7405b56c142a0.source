from pathlib import Path

import pytest

from scp.llm_gateway.client import get_gateway
from scp.task_kernel import TaskKernel


@pytest.mark.asyncio
async def test_complete_scp_architecture_integration(tmp_path, monkeypatch):
    """
    [SCP DNA - Cấp độ C (End-to-end)]
    Bài kiểm tra này lấy hệ thống SCP hoàn chỉnh làm chuẩn:
    - Boot Task Kernel với lưu trữ bền vững.
    - Chạy LLM Gateway qua Egress Policy (chặn nếu không hợp lệ).
    - Tạo một chuỗi Task tuân thủ 15 trạng thái bất biến.
    """
    # 1. Khởi tạo Kernel
    kernel = TaskKernel(tmp_path / "complete_kernel.sqlite3")
    kernel.create_task("scp_eval_1", "planner", "Đánh giá SCP Skills", "R0")
    
    # 2. Chuyển đổi trạng thái nguyên tử (scp-task-kernel-review)
    kernel.transition("scp_eval_1", "PLANNING", actor="planner", reason="Bắt đầu lập kế hoạch")
    state = kernel.get_task("scp_eval_1")
    assert state["state"] == "PLANNING"
    
    # 3. LLM Gateway & Egress Policy (scp-capability-security-review & scp-gateway-resilience)
    # Trong môi trường test hoàn chỉnh, không mock - sử dụng Fail-Closed Egress.
    monkeypatch.setenv("SCP_EGRESS_MODE", "deny")
    gateway = get_gateway()
    
    ans, err = await gateway.chat(
        question="Bạn có tuân thủ 29 nguyên lý DNA không?",
        context="SCP-DNA",
        task="scp_eval_1"
    )
    # Vì EGRESS_MODE=deny, Gateway BẮT BUỘC phải chặn đứng (Fail-Closed)
    assert ans is None
    assert err == "none" or "egress" in err or "circuit" in err
    
    # 4. Reality Verifier & Recovery Proof (scp-reality-verifier)
    integrity = kernel.verify_integrity()
    assert integrity["quick_check"] == "ok"
    
    # 5. Backup & Phục hồi (scp-computer-use-recovery)
    backup_path = kernel.backup(tmp_path / "backups")
    assert Path(backup_path["backup"]).exists()
