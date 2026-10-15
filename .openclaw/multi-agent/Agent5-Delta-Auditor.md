# Bao cao Agent 5 -- Delta Auditor -- SCP Audit Vong 3
- HEAD khi bat dau: 275dbbac (worktree sach, tru file bao cao nay + .openclaw/tmp/ untracked)
- Skill da doc:
  - D:\scp\.openclaw\multi-agent\ASSIGNMENTS.md
  - D:\scp\.agents\skills\scp-delta-audit\SKILL.md
  - D:\scp\.agents\skills\scp-reality-verifier\SKILL.md
  - D:\scp\.agents\skills\scp-dna\SKILL.md
- Ghi chu pham vi: task giao "7 commit" nhung git log d30aa307^..275dbbac thuc te chua 9 commit
  (ngoai 7 da liet ke con co d2f515ef, b1144dfb -- cap fix+test trace-GET cua Agent 4 -- va docs
  commit 275dbbac). Delta Auditor audit TOAN BO 9 de khong co mu vung.
- Trang thai: HOAN THANH.

## Probe FA-09 da tu chay (python 3.12, -X utf8 -m pytest <file> -q, cwd D:\scp)

| # | Test file | Ket qua quan sat | Exit |
|---|---|---|---|
| P1 | tests/T04_kernel/test_admission_semantics_77d44816.py | 3 passed in 1.00s | 0 |
| P2 | tests/T05_gateway/test_gateway_402_breaker.py + test_gateway_hedge_pool.py | 6 passed in 0.74s | 0 |
| P3 | tests/T03_capability/test_egress_policy_unified.py | 12 passed in 1.20s | 0 |
| P4 | tests/T03_capability/test_egress_numeric_spelling_old_code_probe.py | 1 failed, 1 passed | 1 |
| P5 | tests/T02_contract/test_unified_ledger_runtime_dir.py + tests/T04_kernel/test_unified_ledger_runtime_path_agent4.py | 6 passed in 1.04s | 0 |
| P6 | tests/T04_kernel/test_transition_map_authority.py | 5 passed in 0.81s | 0 |
| P7 | tests/T02_contract/test_trace_ledger_oversize_get.py | 4 passed in 1.59s | 0 |

Probe runtime bo sung (python -c, chi doc): _numeric_host_to_ip + EgressPolicy.enforce voi 6
spelling dac biet, va socket.gethostbyname doi chieu -- chi tiet o F4.

---

## Findings per commit

### 1) d30aa307 -- fix(acceptance): A12 review-backlog oracle -- VERDICT: CONFIRMED_OK [OBSERVED]
- Fix co that: [OBSERVED] in_flight_count() @ scp/task_kernel_parts/taskkernel.py:2123 (docstring:
  loai TERMINAL lan HUMAN_REVIEW) va pending_review_count() @ :2143 deu ton tai; oracle cu so
  in_flight_count() == len(expected_review_ids) la 0==3 vinh vien sau 77d44816 -> doi sang
  pending_review_count() trong run_scp_acceptance.py:901-908 va run_scp_acceptance_ci.py:105-111
  la dung contract moi. [SUPPORTED_INFERENCE] cho hanh vi pre-77d44816 (khong revert de chay lai
  oracle cu -- ton ngan sach).
- Test manh: 3 test. R1 la text-pin (grep source) -- cung nhung pin dung contract that; R2 la test
  hanh vi end-to-end: backlog HUMAN_REVIEW khong chan intake, ask RUNNING that van bi backpressure
  fail-closed (pytest.raises KernelError). Khong rong, khong tautology.
- Ha chuan ngam: khong thay (khong skip/xfail, khong ha assertion).
- Probe: P1 EXIT=0.

### 2) 0d61f32c -- test(gateway): pin 402/429 breaker + hedge pool -- VERDICT: CONFIRMED_OK (additive)
- Test co that + manh: [OBSERVED] 6 test chay xanh (P2). Breaker that (failure_threshold default 3
  @ scp/llm_gateway/client.py:161-164, dem o :202/:221); test dung _call_model fake (khong
  network), co autouse fixture reset dead-model cache (isolation tot), monkeypatch env dung hygiene.
  test_402 assert breaker OPEN sau du threshold; hedge pool: provider disabled bi loai khoi pool,
  chain all-disabled fail-closed (None,"none"), EnvCompat khong key -> enabled=False.
- Claim old-code-fail: [SUPPORTED_INFERENCE] -- docstring mo ta bug substring-matcher bo qua
  sentinel digit-free; toi KHONG tu revert client.py de chung minh old-red (chi static reading +
  test docstring). Khong nang cap thanh OBSERVED.
- Ha chuan ngam: khong. NHUNG [LOW] test_429_sentinel_single_hit_counts_one_breaker_failure assert
  _consecutive_failures >= 1 trong khi ten/docstring claim "EXACTLY ONCE" -- neu bug dem 2 lan/ask
  thi test van xanh. Nen la == 1 (sau khi xac nhan hanh vi that).
- Probe: P2 EXIT=0.

### 3) ff5ef4f1 -- fix(trace): unified ledger writer joins runtime_paths -- VERDICT: CONFIRMED_OK [OBSERVED]
- Fix co that: [OBSERVED] _unified_ledger_path gio tra runtime_data_dir()/trace_ledger.jsonl
  (SCP_DATA_DIR-aware), khop reader _trace_impl.
- Test manh: parametrize co/khong SCP_DATA_DIR; assert writer == reader byte-for-byte; test o
  commit f370c0ff (test_legacy_cwd_resolution_would_split_brain) tai dung thuat toan cu va chung
  minh phan ky voi reader duoi SCP_DATA_DIR -- la mo phong thuat toan cu chu khong chay code cu
  that -> [SUPPORTED_INFERENCE] cho old-code-fail, hop ly va du manh.
- Ha chuan ngam: khong (huong fail-closed, khong doi hanh vi default).
- Probe: P5 EXIT=0 (6 passed).

### 4) 1def66c1 -- fix(security): block numeric IPv4 spellings -- VERDICT: CONFIRMED_OK cho pham vi da va
  + F4 RESIDUAL: REGRESSION_RISK [MEDIUM]
- Fix co that: [OBSERVED] _numeric_host_to_ip (decimal + hex, hoa/thuong, chan overflow >32bit) +
  re-check fail-closed trong is_cloud_metadata khi ip_address() raise; test pin: helper 7 case,
  detect decimal/hex, enforce chan o CA 3 mode, khong over-block 8.8.8.8 dang numeric.
  Probe P3 EXIT=0 (12 passed).
- F4a [MEDIUM -- REGRESSION_RISK, live-probe]: cac dang numeric con sot khong duoc chuan hoa:
  0170.0254.0251.0376 (octal-dotted, inet_aton/Linux semantics == 169.254.169.254),
  0251.0176.0126.0066 (octal-dotted), 0xA9FE.0xA9FE, 169.254.0xA9.FE, 0169.0254.0169.0254
  -> helper tra None va enforce() ALLOWED trong OPEN mode (da chay that, OBSERVED tren Windows).
  Docstring NOI RO known limit nay (khong giau) va dua vao "SSRF DNS-resolution checks at fetch
  time": toi xac nhan scp/core/url_fetcher.py co _resolve_public_ips qua socket.getaddrinfo +
  pin IP + re-validate tung hop redirect ([SUPPORTED_INFERENCE] layer fetch-time co che -- nhung
  chi che duoc cac duong egress di qua url_fetcher; khong chung minh duoc trong ngan sach rang
  MOI duong egress deu di qua no).
  Kha nang khai thac phu thuoc platform: Windows gethostbyname TU CHOI octal-dotted (OBSERVED,
  Errno 11001), Linux/inet_aton CHAP NHAN -> noi chay Linux, spelling octal-dotted van co the la
  lo hong neu co duong egress khong qua url_fetcher.
  Trailing dot 169.254.169.254.: AN TOAN (strip "." roi ip_address parse thanh cong -> DENIED,
  OBSERVED) -- tra loi cau hoi cua Coordinator: case nay khong bo sot.
- Ket luan F4: fix that va dung cho decimal/hex-single-integer; residual octal/mixed-dotted la
  fail-open con sot (khong phai regression moi dua vao), muc MEDIUM vi (a) da duoc name lam known
  limit, (b) co layer fetch-time che phan lon, (c) exploitability phu thuoc platform + route.

### 5) f370c0ff -- fix(kernel): transition-map authority -- VERDICT: CONFIRMED_OK [OBSERVED]
- Fix co that: [OBSERVED] ALLOWED_TRANSITIONS them RETRY_SCHEDULED tu RUNNING/WAITING_TOOL/VERIFYING;
  _legal_or_nearest() guard trong commit_failed + set_task_kill; kill tu VERIFYING/RECOVERING ->
  reroute FAILED (fail-closed), ghi kill_reroute/transition_reroute + planned_retry vao journal
  reason/payload (audit-visible).
- Test manh: 5 test assert tung edge journal KHONG out-of-law, hash_chain_valid sau moi thao tac,
  hanh vi QUEUED->CANCELLED giu nguyen, payload pins, vong kiem tra map/code agreement. Khong rong.
- Ha chuan ngam: khong thay. Luu y thiet ke (khong phai ha chuan): reroute doi terminal state quan
  sat duoc (kill tu VERIFYING gio ra FAILED thay vi CANCELLED) -- dung chu dich fail-closed, ops
  can biet.
- Old-code-fail: docstring ghi co probe truc tiep tai 0d61f32c thay 4 edge out-of-law --
  [SUPPORTED_INFERENCE] (khong tu revert); cac test edge-legality tu dung vang doc lap.
- Probe: P6 EXIT=0 (5 passed).

### 6) a028ef69 -- test(security): old-code-fail probe -- VERDICT: FAKE_OR_WEAKENED
  [BLOCKER -- khong phai test gia, nhung la test DO VINH VIEN trong suite chuan]
- F6a [BLOCKER, OBSERVED]: file nam o tests/T03_capability/test_egress_numeric_spelling_old_code_probe.py
  -- ben trong pytest.ini testpaths (testpaths = tests tests/internal). KHONG co conftest/addopts/
  marker nao loai no (grep toan repo: khong co reference nao toi old_code_probe; tests/conftest.py
  khong co deselect/addopts). Probe that: P4 = 1 failed, 1 passed, EXIT=1 -- pytest tests/ chuan
  se DO mai mai vi pytest.fail(...) vo dieu kien cuoi test_old_code_allowed_decimal_metadata_spelling
  (skipif chi nay khi thieu file archived). Tra loi cau hoi cua Coordinator: DUNG, day la test se-
  red-vinh-vien trong suite chinh va hien KHONG duoc dam bao ngoai suite chuan.
- F6b [HIGH, OBSERVED]: probe phu thuoc .openclaw/tmp/egress_head.py -- file UNTRACKED (git status:
  ?? .openclaw/tmp/). Tren may khac / clean checkout: skipif nay -> probe bi SKIP tham lang, bang
  chung old-code-fail khong tai lap duoc tu repo. Huong dung: archived copy phai nam trong repo
  (ngoai testpaths), va probe phai nam ngoai testpaths hoac duoc gate bang marker + addopts deselect,
  hoac doi thanh probe chay-on-demand (scripts/).
- Thiet ke anti-vacuous cua probe (fail-loud neu archived copy unexpectedly blocks) la TOT -- van
  de duy nhat la vi tri + dependency untracked lam suite chuan do vinh vien.
- Ghi chu trung thuc: Agent1 bao "verify per-file 113 passed" -- con so do khong the bao gom file
  nay (no FAIL khi chay). Khong phai cao buoc gian lan: chay per-file kieu chon-loc da bo sot
  chinh probe nay.

### 7) d2f515ef -- fix(trace): bounded ledger scan -- VERDICT: CONFIRMED_OK [OBSERVED]
- Fix co that: [OBSERVED] _LEDGER_SCAN_LIMIT_BYTES = 32MB; _scan_recent_match doc seek-to-end tru
  window, skip dong torn, mirror predicate cua TraceLedger.get_trace; _load_ledger_record giu nguyen
  hanh vi cho file nho; giu verify_on_init=False (GET khong ghi).
- Test manh (b1144dfb): ledger synthetic hash-chained 20k entries; chung minh old-path doc >4MB
  (counter that qua Path.read_text) trong khi new-path tra dung entry (hash+seq) -- old-code-fail
  co do dem thuc. Equivalence cho file nho; torn-line; default limit pin.
- F7 [MEDIUM -- test do sai syscall tren new-path]: _ReadTextBytesCounter chi instrument
  Path.read_text, nhung _scan_recent_match doc bang binary handle.read(window) ->
  new_counter.bytes_read == 0 va assertion new_counter.bytes_read <= 4MB PASS VACUOUS. Boundedness
  cua new-path hien duoc bao dam boi cau truc code (doc dung window bytes) + hang so monkeypatch,
  KHONG boi phep do trong test. Docstring test ("counting actual bytes... the fixed path never
  does") claim manh hon cai no do. Khong phai fake test (result-equivalence + old-cost la that),
  nhung can va assertion (dem binary read) hoac sua docstring.

### 8) b1144dfb -- test file cua d2f515ef -- xem F7 o tren (commit chi them test;
  VERDICT: CONFIRMED_OK kem F7 [MEDIUM]). Probe: P7 EXIT=0 (4 passed).

### 9) 275dbbac -- docs/dossier -- VERDICT: CONFIRMED_OK [LOW housekeeping]
- Chi them file .openclaw/multi-agent/ -- khong nam trong testpaths, khong anh huong suite.
- F9 [LOW]: chua 3 ban copy test (test_admission_semantics_77d44816.py, test_gateway_402_breaker.py,
  test_gateway_hedge_pool.py) -- se tro dan khoi ban trong tests/ (drift); neu ai chay
  pytest .openclaw/multi-agent cung luc voi tests/ se gap trung basename. Them nua, dossier ghi
  "7 commit" trong khi range that la 9. De nghi: xoa ban copy hoac them README canh bao.

---

## Da verify (tong hop lenh + exit)
- 7 lenh pytest (P1-P7 o bang tren) + 1 probe python -c cho egress spellings + socket doi chieu.
  Exit status tung lenh da ghi. Khong chay git write; khong sua file product/test; khong dung .env;
  khong kill service.

## Chua xu ly / open questions
1. Khong tu revert tung fix de chay old-code-red that (ngoaai tru y nghia qua P4): cac claim
   old-code-fail cua 0d61f32c, f370c0ff la SUPPORTED_INFERENCE (docstring + static). Ngan sach
   15 phut khong cho phep full mutation testing 9 commit.
2. F4a: can quyet dinh kien truc -- mo rong _numeric_host_to_ip cho octal/mixed-dotted (rui ro
   over-block thap vi host all-digits co leading-zero khong phai ten mien hop le) HOAC chung minh
   moi duong egress bat buoc qua url_fetcher.
3. Cau hoi cho Coordinator: verify "113 passed" cua Agent 1 chay dung to hop file nao (F6a cho
   thay probe do khong the nam trong con so do).

---

## TONG KET CHO COORDINATOR
- Da chat van: 9/9 commit (7 theo task + 2 phat hien them trong range d2f515ef/b1144dfb + 1 docs
  275dbbac).
- VERDICT per commit: CONFIRMED_OK = 7 (d30aa307, 0d61f32c, ff5ef4f1, 1def66c1*, f370c0ff,
  d2f515ef + b1144dfb, 275dbbac) | FAKE_OR_WEAKENED = 1 (a028ef69 -- BLOCKER F6a/F6b) |
  REGRESSION_RISK = 1 (F4a residual tren 1def66c1 -- MEDIUM). (*1def66c1: fix dung pham vi va,
  kem finding residual.)
- Findings theo muc: BLOCKER 1 (F6a suite chuan do vinh vien + F6b dependency untracked),
  HIGH 1 (F6b tinh tu goc tai lap bang chung), MEDIUM 2 (F4a octal/mixed spellings; F7 assertion
  boundedness vacuous), LOW 2 (0d61f32c ">=1" vs "exactly once"; F9 stale copies + "7 vs 9
  commits" trong dossier).
- PHAI xu ly truoc khi chot vong audit:
  1. F6a/F6b (BLOCKER): chuyen test_egress_numeric_spelling_old_code_probe.py ra ngoai testpaths
     (hoac marker + deselect) va archive egress_head.py vao repo de probe tai lap duoc; bat buoc
     chay lai pytest tests/ -q toan bo sau khi xu ly.
  2. F4a (MEDIUM): chot phuong an cho octal/mixed numeric spellings (mo rong helper hoac chung
     minh fetch-time coverage cho moi egress path).
  3. F7 (MEDIUM): va phep do boundedness trong test_trace_ledger_oversize_get.py (instrument
     binary read) hoac ha docstring xuong dung muc bang chung.
  4. LOW tuy y: == 1 cho 429 counter test (sau khi xac nhan); don cop tests trong
     .openclaw/multi-agent; sua "7 commit" -> 9 trong dossier.
- Ket luan tong: cac FIX deu CO THAT va co test regression khop contract (khong phat hien fake
  fix, khong phat hien skip/xfail moi, khong phat hien ha assertion co chu dich); duy nhat 1
  commit TEST (a028ef69) co hygiene loi nghiem trong lam suite chuan do, va 1 fix security con
  known-gap co chu dich can Coordinator ra quyet dinh.

## Pham vi da audit (file)
Diff-mo cua 9 commit: scp/task_kernel_parts/taskkernel.py, scp/task_kernel_parts/definitions.py,
scp/ask_kernel_adapter.py, scp/policy/egress.py, scp/api_server_parts/_trace_impl.py,
scp/llm_gateway/client.py (doc), scp/core/url_fetcher.py (doc), scripts/run_scp_acceptance.py,
scripts/run_scp_acceptance_ci.py, pytest.ini, tests/conftest.py (kiem tra deselect) + 7 file test
moi. Tong: 16 file doc/phan tich, 7 file test chay probe that.
- HEAD ket thuc: 275dbbac (khong thay doi, worktree sach).
