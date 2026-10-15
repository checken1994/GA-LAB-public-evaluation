# HỒ SƠ BÀN GIAO — ĐÁNH GIÁ ĐỘC LẬP (Independent Review Handoff)

Bạn (đánh giá viên độc lập) có thể tái hiện MỌI kiểm chứng dưới đây bằng lệnh thật.
Không cần tin lời nào trong báo cáo — chạy lại và so. HEAD đối chiếu: `d9d984a412ad`.

Interpreter: `C:\Users\check\AppData\Local\Programs\Python\Python312\python.exe` (repo dùng Python hệ thống, không venv).

## CL-1 · Vòng lặp audit đến 0 lỗi mở

```powershell
cd D:\scp
# Vòng 1 (AUDIT_FAILED - 1 lỗi): reports/audit/audit-20260929-011124.json
# Vòng 2 (AUDIT_READY 7/7):     reports/audit/audit-20260929-013303.json  (same-SHA 89a81e55)
# Vòng 3 giữa (AUDIT_FAILED - BOM): reports/audit/audit-20260929-042739.json
# Vòng 3 CUỐI (AUDIT_READY 7/7):   reports/audit/audit-20260929-045225.json (same-SHA 20e42ff9)
python -X utf8 -c "import json; r=json.load(open('reports/audit/audit-20260929-045225.json',encoding='utf-8')); print(r['overall_verdict'], r['commit'])"
git rev-parse HEAD          # -> 20e42ff9... == commit field trong report
```
Tiêu chí đạt: verdict cuối AUDIT_READY, report commit == HEAD lúc report sinh ra, 0 step FAIL.

## CL-2 · Không test giả / rỗng / hạ chuẩn

```powershell
# Full suite: 2515 passed / 27 skipped / 0 failed (bên trong audit trên)
python -X utf8 -m pytest tests/T00_integrity/test_meta_audit.py -q        # 39 passed (exit 0)
python -X utf8 -m pytest tests/T03_capability/test_egress_policy_unified.py -q   # 13 passed
python -X utf8 -m pytest tests/T02_contract/test_trace_ledger_oversize_get.py -q # 4 passed
python -X utf8 tools/t00_meta_audit.py                                    # 0 new regressions, exit 0
# Chống test-giấm: probe old-code là SCRIPT chạy tay (không nằm trong testpaths):
python -X utf8 scripts/probe_egress_numeric_spelling_old_code.py          # exit 0 = old bug tái hiện
# Kiểm tra không có pytest.fail vô điều kiện / assert True trong tests/:
python -X utf8 -c "import pathlib,re,sys
bad=[]
for p in pathlib.Path('tests').rglob('test_*.py'):
    t=p.read_text(encoding='utf-8',errors='replace')
    if re.search(r'pytest\.fail\(\s*[\'\"]OLD-CODE', t): bad.append(str(p))
    if re.search(r'\bassert\s+True\b', t): bad.append(str(p))
print('suspicious:', bad or 'NONE')"
# Kiểm delta-audit độc lập + cách xử lý: .openclaw/multi-agent/Agent5-Delta-Auditor.md
```
Tiêu chí đạt: exit 0 cho các lệnh trên; suspicious = NONE (hoặc chỉ file đã được delta-audit dẫn chiếu).

## CL-3 · Kiểm tra toàn bộ luồng chạy thật (allow + deny)

```powershell
# Yêu cầu: các port 8000/8081/3030/3000 đang rảnh (hoặc dùng port khác 809x)
cd D:\scp
python -X utf8 tools\live_flow_proof.py 8095
# Kỳ vọng: BOOT /health 200; READY judge+scheduler ok; AUTH JWT; ASK HTTP 200
#          verdict=PASS governance=UPHOLD (cần LLM key thật trong .env);
#          DB newest task COMPLETED; events gồm TASK_COMPLETED + CHECKPOINT_FINALIZED;
#          integrity_check ok; SHUTDOWN 000/refused
python -X utf8 tools\live_flow_proof.py 8096 --egress-deny
# Kỳ vọng: ASK withheld + governance KILL; DB task HUMAN_REVIEW; integrity ok
# Acceptance 12 cổng:
python -X utf8 scripts\run_scp_acceptance.py     # SCP ACCEPTANCE: PASS (12/12)
python -X utf8 -c "import json; r=json.load(open('reports/scp_acceptance_ci/acceptance.json',encoding='utf-8')); print(r['passed'],'/',r['total'],r['overall_pass'])"
```
Tiêu chí đạt: allow-path PASS/UPHOLD + COMPLETED + integrity ok; deny-path withheld+KILL; acceptance 12/12 overall_pass true, commit field == HEAD.

## CL-4 · Bug thật đã sửa — tái hiện old-code-fail

| Bug | Fix commit | Tái hiện |
|---|---|---|
| B1 unidecode thiếu manifest | `d1d062ed` | `python -X utf8 scripts/check_imports_vs_requirements.py` → exit 0 (PASS); git show `d1d062ed^:scp/requirements.txt` không có unidecode |
| B2 backpressure đếm HUMAN_REVIEW | `77d44816` | `python -X utf8 -m pytest tests/T04_kernel/test_admission_semantics_77d44816.py -q` → 3 passed; DB thật `data/ask_task_kernel.sqlite3` (chỉ đọc): HUMAN_REVIEW=199 |
| B3 oracle A12 chết | `d30aa307` | test đọc source: pending_review_count() trong cả 2 acceptance script |
| B4 egress numeric spelling | `1def66c1`+`527c3895` | `python -X utf8 -c "import sys; sys.path.insert(0,'.'); from scp.policy.egress import EgressPolicy,EgressMode; p=EgressPolicy(mode=EgressMode.OPEN,production_mode=False); p.enforce('http://0251.0376.0251.0376/latest/meta-data')"` → EgressDeniedError (cả decimal/hex/octal/n-part); probe old-code (CL-2) chứng minh cũ ALLOWED |
| B5 ledger split-brain | `ff5ef4f1` | `python -X utf8 -m pytest tests/T02_contract/test_unified_ledger_runtime_dir.py -q` → 2 passed |
| B6 transition-map authority | `f370c0ff` | `python -X utf8 -m pytest tests/T04_kernel/test_transition_map_authority.py -q` → 5 passed; journal không còn edge ngoài luật |
| Trace GET DoS | `d2f515ef` | `python -X utf8 -m pytest tests/T02_contract/test_trace_ledger_oversize_get.py -q` → 4 passed (byte-count: old 11.167.764 > new 4.194.304 ≤ 4MiB) |

## CL-5 · Điều phối đa Agent + Skill SCP bắt buộc

- Hồ sơ phân công: `.openclaw/multi-agent/ASSIGNMENTS.md` (5 Agent, mỗi Agent 1 skill SCP + phạm vi file + lệnh kiểm chứng + cấm commit).
- Báo cáo Agent: `Agent1-Security-Guard.md`, `Agent2-Kernel-Keeper.md` (+ MERGE-NOTES), `Agent4-Data-Steward.md`, `Agent5-Delta-Auditor.md` — mỗi file ghi skill đã đọc, findings nhãn OBSERVED/SUPPORTED_INFERENCE/UNPROVEN.
- Trạng thái tổng: `.openclaw/multi-agent/CAMPAIGN-STATUS.json` · Báo cáo hoàn thành: `COMPLETION-REPORT.md`.
- Sự cố stash-conflict 02:50: forensics `Agent2-Kernel-Keeper-MERGE-NOTES.md` + `pre-recovery-snapshot.diff` (snapshot toàn bộ trước can thiệp).

## CL-6 · Giới hạn đã kê khai (không giấu)

1. Full `pytest tests/` trên máy này có thể bị SIGKILL ~10 phút bởi môi trường exec (đã gặp riêng từng dir); audit tổng cuối chạy trọn qua runner của `run_full_audit.py` (2515/0).
2. Backlog 199 HUMAN_REVIEW trong DB thật KHÔNG bị xóa (quy tắc không đụng data owner) — admission không còn bị chặn; human review là việc của owner.
3. Không có đích scp/VPS cấu hình sẵn trên máy → scp-ngoài-máy chưa thực hiện (chi tiết COMPLETION-REPORT §6); thay thế: mọi artifact pin SHA/checksum nội bộ.
4. Hardening đề xuất (không phải lỗi mở): rebuild_projection map-validation, telemetry 0.8×cap, WAITING_APPROVAL vào STATES, WS-hub audit của Agent 3 chưa trọn.
5. FA-14 proposal chờ owner duyệt: `PROPOSAL-FA-14-infrastructure-delegation.md`.

## CL-7 · Tiêu chí chấp nhận của đánh giá độc lập

Đánh giá PASS khi: (a) CL-1 verdict AUDIT_READY + same-SHA; (b) CL-2 các lệnh exit 0, không phát hiện test giả mới; (c) CL-3 allow PASS/UPHOLD + deny withheld/KILL + acceptance 12/12; (d) CL-4 các test fix đều xanh và ít nhất 1 old-code tái hiện được (probe exit 0); (e) mọi vấn đề đánh giá viên nêu ra được xử lý hoặc chấp nhận có lý do trước khi kết thúc.
