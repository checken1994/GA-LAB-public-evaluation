# Báo cáo Agent 1 Security Guard — SCP Audit Vòng 3 (lần chạy 2)
- HEAD khi bắt đầu: 0d61f32cc321e587efe7cfbfc9dc091f5279622b (OBSERVED via git rev-parse, chỉ đọc)
- Skill đã đọc: D:\scp\.agents\skills\scp-capability-security-review\SKILL.md; D:\scp\.agents\skills\scp-dna\SKILL.md; D:\scp\.openclaw\multi-agent\ASSIGNMENTS.md
- Quy tắc: KHÔNG git write, KHÔNG đụng .agents/*, .env/secrets, KHÔNG kill service 8000/8081/3030/3000. Chỉ đọc + file-edit + pytest.
- Phạm vi dự kiến: scp/security/ (38 py) + scp/capabilities/ (5 py) + scp/policy/ (3 py); ưu tiên egress guard, capability verify, policy gate, auth helpers.
- Giới hạn bằng chứng: PASS = "không thấy lỗi trong phạm vi đã đọc" (DNA #22).

## Log tăng dần (minh bạch tiến độ)
- 03:06 [OBSERVED][MEDIUM] scp/policy/egress.py:79-104 (is_cloud_metadata/is_loopback) — host dạng integer/hex literal (vd `http://2851990292/` = 169.254.169.254, `0xA9FEA9FE`) làm ipaddress.ip_address raise ValueError → is_cloud_metadata=False →Invariant 1 ("unconditionally blocked in all modes") bị né trong OPEN mode; OS resolver (inet_aton) chấp nhận dạng này. ALLOWLIST/DENY vẫn chặn (fail-closed) vì host không khớp allowlist. Chưa vá — đang audit tiếp.
- 03:06 [OBSERVED-OK] scp/policy/egress.py — mode env không hợp lệ → DENY (fail-closed); production_mode + mode ngoài {deny,allowlist} → raise; EgressDeniedError redact query string trước khi vào message (med-1). Không thấy fail-open.
- 03:06 [OBSERVED-OK] scp/security/egress_static_scan.py — exemption chỉ khi scope có enforce_egress_policy ở line <= call; validate_url không exempt (V-EE-1 lesson). Thiết kế fail-closed, limits được nêu rõ.
- 03:08 [OBSERVED-OK] scp/security/auth.py — canonical verify_admin: rate-limit 5/60s per-IP (bucket theo TCP peer, không tin X-Forwarded-For — chống spoof), 401 khi chưa cấu hình (không dev bypass), compare_digest, eviction bucket theo LRU-timestamp (SEC-FIX 2026-09-26). Fail-closed.
- 03:08 [OBSERVED-OK] secret_loader.py / env_loader.py / provider_keys.py / auth_config.py — không log giá trị secret; conflict direct-vs-file fail-closed; placeholder bị bỏ; config_digest (brute-force oracle) đã bị xóa. jwt_guard.py: thiếu SCP_JWT_SECRET → RuntimeError (fail-closed); verify_api_key dùng compare_digest; exception broad `(InvalidTokenError, Exception)` nhưng vẫn raise 401 — LOW, không vá.
- 03:10 [OBSERVED-OK] scp/security/capability_epoch.py — CapabilityAuthority: corrupt state file → revoked=True (fail-closed); validate() verify HMAC signature TRƯỚC (GAP-08), check epoch == current epoch + not revoked tại thời điểm gọi (PEP sát driver); revoke/restore đều tăng epoch → token cũ chết. parse_capability_token trả None khi lỗi. Không thấy fail-open.
- 03:10 [OBSERVED-OK] production_guard.py — production mode chặn bypass flags, ép egress deny/allowlist, ép HTTPS khi host không loopback, password >=16; raise trước khi đụng secret. tier1_guard.py — deterministic, fail-closed.
- 03:12 [OBSERVED-OK] confirmation_store.py — is_confirmed fail-closed với target rỗng (AUDIT-FIX 2026-09-24), single-use consume (P3-07), peek consume=False (F7-RECUR), redact secret trước khi persist JSONL (S-L5). LOW (không vá): consume không được persist vào JSONL → crash+restart có thể replay confirmation đã consume trong TTL; write-fail chỉ log warning nhưng record vẫn sống trong memory cache.
- 03:12 [OBSERVED-OK] dos_protection.py — lock toàn bộ state (4-b-010), throttle branch đã được gán _last_throttle (4-b-009), release_slot chống leak slot, status 429 + Retry-After. half_open cho phép nhiều request probe song song (LOW, by design).
- 03:14 [OBSERVED-OK] os_sandbox.py — execute_bounded: validate token trước, Windows Job Object fail-closed (ImportError/isolation failure → raise, KHÔNG fallback unisolated), Linux bắt buộc bwrap, dead-proxy env, timeout 15s; write_bounded chặn path traversal bằng resolve()+relative_to(cwd). KNOWN LIMITATION (raw socket/file read trong job object) được ghi rõ.
- 03:14 [OBSERVED-OK] memory_guard.py — NFKC + homoglyph normalize chống jailbreak kiểu Cyrillic; session map có bound (SEC-FIX 2026-09-26).
- 03:16 [OBSERVED-OK] scp/capabilities/tools.py — SafeCommandRunnerTool: BLOCKED_PATTERNS + cấm multiline/chaining/redirect/subexpression; READ_ONLY_ALLOWLIST (git chỉ dạng read, đã deny --no-index/--output); workspace tier đòi L3 + confirmation_id thật từ HumanConfirmationStore (P1-SEC-03 chống self-attestation); egress enforce trên URL/IP trong command; timeout+taskkill; stdout/stderr bounded. LOW (design): L0 tools (sys.inspect/workspace.analyze) không check capability token per-call — phụ thuộc dispatcher, bounded bởi rate-limit + path confinement + sensitive-pattern deny.
- 03:17 [OBSERVED-OK] capabilities/rag.py, vector_db.py, voice.py, __init__.py — không có egress/fs nguy hiểm; SQL parameterized; temp file được dọn (4-a-013). retry_policy.py: auto-retry WAITING_APPROVAL sau timeout — semantics retry_fn thuộc TaskKernel (Agent 2); ghi SUPPORTED_INFERENCE-LOW: cần bảo đảm retry_fn không requeue bỏ qua approval gate.
- 03:17 [SUPPORTED_INFERENCE][LOW] scp/policy/attack_policy.py — default governance_decision = UPHOLD → phase 0 (không phản công): fail-safe, không fail-open nguy hiểm.
- 03:21 [FIX] scp/policy/egress.py — đã vá: helper `_numeric_host_to_ip` (decimal/hex 32-bit → dotted-quad, pure math) + `is_cloud_metadata` normalize numeric spelling trước khi kết luận (fail-closed). Smoke probe: old-code cho phép `http://2852039166/latest/meta-data` trong OPEN mode; new-code raise EgressDeniedError (cả int + hex form). Đang viết regression test trong tests/T03_capability/.
- 03:26 [VERIFY-1] pytest tests/T03_capability/test_egress_policy_unified.py -q → 12 passed, EXIT=0 (bao gồm regression mới: numeric-host metadata bypass). Verify toàn suite đang chạy nền (T03 có tests spawn server/subprocess nên chạy lâu); sẽ ghi exit status khi xong.
- 03:39 [VERIFY-2] Per-file runs (patch-adjacent + audited modules), pytest -q, Python312:
  - test_egress_enforcement.py → 26 passed, 2 skipped (container opt-in), EXIT=0
  - test_egress_policy_unified.py → 12 passed (gồm regression mới), EXIT=0
  - test_zonefix_policy_gate_chain.py → 4 passed, EXIT=0
  - test_flow_29_policy_scp_standard.py → 1 passed, EXIT=0
  - test_zonefix_egress_redirect.py → 3 passed, EXIT=0
  - test_os_sandbox.py → 5 passed, EXIT=0
  - test_confirmation_store_fail_closed.py → 7 passed, EXIT=0
  - test_auth_rate_limit_eviction.py → 4 passed, EXIT=0
  - test_auth_config_no_secret_oracle.py → 3 passed, EXIT=0
  - test_capability_secret_fail_closed.py → 13 passed, EXIT=0
  - test_dos_quota_pairing.py → 9 passed, EXIT=0
  - test_security_store_bounds.py → 6 passed, EXIT=0
  - test_capability_token_hmac_signing.py → 20 passed, EXIT=0
  Tổng: 113 passed, 2 skipped, 0 failed trên 13 file thuộc phạm vi audit + vùng bị patch.

## Phạm vi đã audit (26 file đọc trực tiếp, toàn phần + probe)
- Ưu tiên cao: scp/policy/egress.py, scp/security/url_safety.py, scp/security/egress_static_scan.py, scp/security/capability_epoch.py, scp/security/auth.py, scp/security/auth_config.py, scp/security/jwt_guard.py, scp/security/secret_loader.py, scp/security/env_loader.py, scp/security/provider_keys.py
- Guards: scp/security/production_guard.py, tier1_guard.py, memory_guard.py, os_sandbox.py, confirmation_store.py, dos_protection.py, request_context.py, attack_policy.py
- Capabilities: scp/capabilities/tools.py, rag.py, vector_db.py, voice.py, __init__.py
- Policy: scp/policy/retry_policy.py
- Quét phụ: Select-String toàn bộ 46 file .py trong 3 thư mục cho pattern shell=True / verify=False / CERT_NONE / _create_unverified → 0 match (OBSERVED).
- Các file security còn lại (12 file phân tích attack/detection: predictor, threat_detector, unified_detector, response_monitor, escalation, counter_response, attack_memory, attack_crawler, threat_simulator, multi_turn_tracker, canary_monitor, bypass_encrypt...) KHÔNG đọc đầy đủ trong lần chạy này do giới hạn thời gian → PASS chỉ áp dụng cho phạm vi trên.

## Findings
| # | Trạng thái | Vị trí | Bằng chứng | Mức |
|---|---|---|---|---|
| F1 | OBSERVED → ĐÃ FIX | scp/policy/egress.py:79-104 (is_cloud_metadata/is_loopback, pre-fix) | Probe 03:21: `EgressPolicy(mode=open).enforce('http://2852039166/latest/meta-data')` CHO PHÉP (2852039166 = 169.254.169.254 dạng decimal-integer). Attack path: tool/command cho phép OPEN mode (vd SCP_EGRESS_MODE=open ngoài production) → agent fetch URL dạng integer → ipaddress.ip_address raise ValueError → is_cloud_metadata=False → Invariant 1 bị né → IMDS credential theft nếu chạy trên cloud. ipaddress không parse được nhưng OS resolver (inet_aton) thì có. | MEDIUM |
| F2 | OBSERVED (đồng root-cause F1) | scp/policy/egress.py is_loopback (pre-fix) | `is_loopback('2130706433')` = False (2130706433 = 127.0.0.1) → không tạo lỗ hổng mới (ALLOWLIST vẫn chặn; loopback-miss chỉ làm chặn hơi nhiều), nhưng cùng nguyên nhân parsing không đồng nhất với resolver. | LOW |
| F3 | OBSERVED | scp/security/confirmation_store.py:151-198 | consume=True đổi status=CONSUMED trong memory cache nhưng không append JSONL → crash/restart trước khi TTL hết hạn có thể replay confirmation đã dùng (append-only log vẫn thấy CONFIRMED cuối). Chỉ ảnh hưởng restart window + cần có confirmation_id. | LOW |
| F4 | OBSERVED (by design, LOW) | scp/security/dos_protection.py half_open | khi circuit half_open, mọi request trong chu kỳ đều được qua (không single-probe token) → burst lặp lại mỗi CIRCUIT_RESET_TIME. | LOW |
| F5 | OBSERVED (design note) | scp/capabilities/tools.py L0 tools | sys.inspect / workspace.analyze không yêu cầu capability token per-call; ràng buộc bởi rate-limiter + path confinement + sensitive-deny. Phụ thuộc dispatcher cấp trên enforce capability_level. | LOW |
| F6 | SUPPORTED_INFERENCE | scp/policy/retry_policy.py:64-76 | auto-retry requeue task WAITING_APPROVAL sau timeout — nếu retry_fn của TaskKernel không đi qua lại approval gate thì task tự chạy không approval. Nằm ngoài phạm vi file của Agent 1 (task_kernel = Agent 2). | LOW |
| F7 | OBSERVED (không vá) | scp/security/jwt_guard.py:56 `except (jwt.InvalidTokenError, Exception)` | broad-except nhưng vẫn raise 401 fail-closed; chỉ là code-smell. | LOW |
| F8 | UNPROVEN | scp/security/escalation.py, counter_response.py, predictor.py, threat_detector.py, unified_detector.py, response_monitor.py, attack_memory.py, attack_crawler.py, threat_simulator.py, multi_turn_tracker.py, canary_monitor.py, bypass_encrypt.py | Chưa audit đầy đủ trong 15 phút lần này (đã liệt kê, ưu tiên đã chọn egress/auth/policy). Không có finding — chỉ là khoảng trống by evidence. | — |

## Đã fix
- scp/policy/egress.py: thêm `_numeric_host_to_ip` (decimal/hex 32-bit → dotted-quad, pure math, có KNOWN LIMIT ghi rõ: mixed-radix dotted forms chưa normalize, do SSRF DNS-check ở fetch time đảm nhiệm) + `is_cloud_metadata` normalize numeric spelling trước khi kết luận → fail-closed. Patch small + rollback đơn giản (revert 2 hunk). KHÔNG đụng .agents/, .env, spec/, không git.
- Regression test: tests/T03_capability/test_egress_policy_unified.py::test_numeric_host_spellings_of_metadata_blocked_in_all_modes — pin: helper conversion, detection decimal+hex, enforce bị chặn ở CẢ 3 mode, và không over-block public IP dạng numeric (8.8.8.8 = 134744072 vẫn cho phép ở OPEN).
- Chứng minh old-code-fail: probe trước khi vá (03:21) in `ENFORCE int-form: ALLOWED`; sau vá raise EgressDeniedError (đã trích trong log tăng dần).

## Đã verify (lệnh chạy thật, Python312 theo task)
- `python -X utf8 -m pytest tests/T03_capability -q` (toàn suite): KHÔNG hoàn thành trong môi trường lần này — 3 lần chạy đều bị external kill ~5 phút (session bị SIGKILL; 2 lần của tôi + quan sát thấy Agent khác cũng bị y hệt khi chạy T02_contract). Đây là giới hạn môi trường, KHÔNG phải test fail — evidence: không có exit marker nào của tôi, output dừng ở 7% với 72/72 chấm ĐẠT (0 fail). ĐÃ CẤP: thay bằng per-file runs bên dưới.
- `pytest tests/T03_capability/test_egress_enforcement.py -q` → 26 passed, 2 skipped, EXIT=0
- `pytest tests/T03_capability/test_egress_policy_unified.py -q` → 12 passed, EXIT=0 (gồm regression mới)
- `pytest tests/T03_capability/test_zonefix_policy_gate_chain.py -q` → 4 passed, EXIT=0
- `pytest tests/T03_capability/test_flow_29_policy_scp_standard.py -q` → 1 passed, EXIT=0
- `pytest tests/T03_capability/test_zonefix_egress_redirect.py -q` → 3 passed, EXIT=0
- `pytest tests/T03_capability/test_os_sandbox.py -q` → 5 passed, EXIT=0
- `pytest tests/T03_capability/test_confirmation_store_fail_closed.py -q` → 7 passed, EXIT=0
- `pytest tests/T03_capability/test_auth_rate_limit_eviction.py -q` → 4 passed, EXIT=0
- `pytest tests/T03_capability/test_auth_config_no_secret_oracle.py -q` → 3 passed, EXIT=0
- `pytest tests/T03_capability/test_capability_secret_fail_closed.py -q` → 13 passed, EXIT=0
- `pytest tests/T03_capability/test_dos_quota_pairing.py -q` → 9 passed, EXIT=0
- `pytest tests/T03_capability/test_security_store_bounds.py -q` → 6 passed, EXIT=0
- `pytest tests/T03_capability/test_capability_token_hmac_signing.py -q` → 20 passed, EXIT=0
- Tổng cộng: 113 passed, 2 skipped (container opt-in), 0 failed.
- Vệ sinh môi trường: đã kill các process pytest/session mồ côi DO TÔI tạo ra (PID 22384, 20240 + 2 session shell). Đã kiểm tra Get-NetTCPConnection TRƯỚC khi kill: KHÔNG đụng PID giữ port 8000/8081/3030/3000 (24740, 1748, 8520, 21528 còn nguyên). Process pytest T02_contract của Agent khác (PID 5788) không bị đụng.

## Chưa xử lý / open questions
1. Toàn suite `pytest tests/T03_capability -q` một-lần-cần được chạy lại khi môi trường không kill session ~5 phút (hoặc cài pytest-timeout/xdist). Đến đó mới coi là "full-suite green".
2. F3 (confirmation replay sau restart) — đề xuất: append status đổi vào JSONL trong consume/revoke, hoặc re-derive trạng thái từ JSONL khi load cache. Cần decision của Coordinator (thay đổi format log).
3. F6 cần Agent 2 xác nhận retry_fn đi qua approval gate.
4. 12 file security chưa đọc đầy đủ (F8) — đề xuất chạy lại Agent 1 lần 3 hoặc để Agent 5 sample vùng này.
5. Loopback int-spelling (F2) hiện KHÔNG được convert ở is_loopback — chủ đích chỉ vá metadata block (min-change); nếu muốn đồng bộ, normalize cả is_loopback (không ảnh hưởng security vì hướng ngược lại).
