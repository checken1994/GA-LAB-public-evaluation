# Plan — Triển khai Giai đoạn 1 & Giai đoạn 2 SCP (Agent OS)

## Mục tiêu
Triển khai toàn diện Giai đoạn 1 & Giai đoạn 2 theo chỉ thị từ parent/user:
1. Kết nối dữ liệu chuyên ngành vào `scp/runtime/domain_data_fork.py` và `scp/runtime/question_router.py` (USGS Earthquake, Biology, Geology, ConfigLoader cho các API cần key).
2. Tái cấu trúc `_ask_impl.py` thành Pipeline Pattern trong `scp/api_server_parts/pipeline/` (security, lookup, generation, verification, ledger) đảm bảo 2.745+ test hiện hành giữ nguyên màu xanh.
3. Xây dựng hộp thư tự học offline `data/inbox_knowledge/` qua `scp/knowledge/inbox_watcher.py` tích hợp `claim_extractor`, `antibody_system`, và `learning.sqlite`.
4. Chạy kiểm chứng toàn bộ tests sau khi hoàn thành. Không được delete/skip/xfail bất kỳ test nào.

## Kiến trúc & Module Phân tách

### Track 1: Domain Data Fork & Question Router
- Khảo sát các DataSource hiện có trong `scp/data_sources/` và router hiện có trong `scp/runtime/question_router.py` và `scp/runtime/domain_data_fork.py`.
- Tích hợp USGS Earthquake, Biology, Geology Data Sources.
- Xây dựng hoặc tích hợp ConfigLoader cho API keys cần thiết, đảm bảo fail-closed khi thiếu key hoặc network lỗi.
- Đảm bảo routing chính xác câu hỏi chuyên ngành vào đúng data fork.

### Track 2: Pipeline Pattern Refactor cho _ask_impl.py
- Vị trí: `scp/api_server_parts/pipeline/`
- Các stages:
  1. Security Stage (token validation, rate limit, prompt injection check, governance check)
  2. Lookup Stage (domain data fork, local/external lookups, cache)
  3. Generation Stage (LLM generation, synthesis)
  4. Verification Stage (crosscheck, reality judge, honest abstain)
  5. Ledger Stage (audit ledger append, HMAC record, trace)
- `_ask_impl.py` trở thành orchestrator mỏng gọi qua pipeline, tương thích 100% với signature và side-effects hiện tại để bảo toàn 2.745+ tests.

### Track 3: Offline Self-Learning Inbox
- Vị trí: `data/inbox_knowledge/` và `scp/knowledge/inbox_watcher.py`
- Tích hợp `claim_extractor`, `antibody_system`, và `learning.sqlite`.
- Cơ chế quét định kỳ file trong `data/inbox_knowledge/`, bóc tách claims, kiểm tra độc tố/antibody, lưu trữ bền vững vào `learning.sqlite`.

### Track 4: Comprehensive Verification & Audit Gate
- Kiểm thử đầy đủ: `pytest tests/` (2.745+ tests pass, 0 fail).
- T00 Meta-Audit: `python tools/t00_meta_audit.py`
- Forensic Integrity Audit & Reality Verifier (FA-01 đến FA-13).

## Lộ trình Thực hiện
- **Bước 1**: Dispatch 3 Explorers khảo sát song song 3 mảng:
  - Explorer 1: Khảo sát `domain_data_fork.py`, `question_router.py`, các DataSources (USGS, Biology, Geology), ConfigLoader.
  - Explorer 2: Khảo sát cấu trúc chi tiết của `_ask_impl.py`, các caller, test suite liên quan đến ask endpoint, thiết kế chi tiết Pipeline Pattern.
  - Explorer 3: Khảo sát `inbox_watcher.py`, `claim_extractor`, `antibody_system`, `learning.sqlite`, kiến trúc knowledge hiện tại.
- **Bước 2**: Tổng hợp báo cáo survey, chốt interface contracts.
- **Bước 3**: Triển khai Milestone theo chu trình Explorer -> Worker -> Reviewers (2) -> Challengers (2) -> Forensic Auditor -> Gate.
- **Bước 4**: Kiểm chứng tổng thể.
