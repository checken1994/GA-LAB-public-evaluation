---
name: scp-continuous-operations-loop
description: Thiết kế và vận hành vòng lặp agent liên tục/định kỳ cho SCP theo mô hình discover → qualify → authorize → execute → independently verify → persist → reconcile/escalate, với durable state, budget/kill-switch, maker-checker separation và SCP evidence/recovery gates. Dùng khi cần daily triage, PR/CI watcher, recurring maintenance, autonomous loop, scheduler, unattended agent, hoặc biến một chuỗi prompt thủ công thành loop có kiểm soát.
status: candidate
---

# SCP Continuous Operations Loop

## Mục tiêu

Skill này lấp khoảng trống giữa **SCP verification/governance** và **vận hành agent lặp lại theo thời gian**. Nó không thay thế `scp-dna`, `scp-capability-security-review`, `scp-reality-verifier`, `scp-computer-use-recovery`, `scp-learning-loop-guard` hay `scp-release-evidence-gate`; nó điều phối các skill đó thành một vòng vận hành bền vững.

> Candidate status: skill này chưa được coi là normative ground truth cho tới khi qua `scp-skill-review` C1–C6 với bằng chứng Integration trở lên và independent verifier.

## Core Operating Loop

Mọi loop phải đi qua các pha sau, theo đúng thứ tự logic:

1. **Discover** — Tìm work item từ nguồn đã khai báo: issue, PR, CI, dependency signal, queue, schedule hoặc runtime alert.
2. **Qualify** — Xác định mục tiêu, non-goals, scope, risk tier, freshness và stop condition. Input mơ hồ phải `UNKNOWN`/`HUMAN_REVIEW`, không tự đoán.
3. **Authorize** — Kiểm tra task-scoped capability, policy, denylist/allowlist, budget và approval cần thiết bằng `scp-capability-security-review`.
4. **Plan Small** — Chia thành thay đổi nhỏ, reversible, có checkpoint/rollback. Không batch lớn chỉ để giảm số vòng.
5. **Execute** — Maker/implementer thực hiện đúng scope. Không được tự tuyên bố thành công.
6. **Independent Verify** — Checker/verifier tách khỏi maker về session/role và, khi claim quan trọng, ưu tiên khác lineage. Chạy Reality probe/test thật; phân loại evidence Static/Integration/End-to-end/Recovery.
7. **Persist State** — Ghi state machine-readable: input identity, exact revision/SHA, attempt, action, evidence refs, budget spent, verdict, next eligible action và timestamps.
8. **Reconcile** — Nếu response bị mất hoặc side effect có thể đã xảy ra, không retry mù. Dùng `scp-computer-use-recovery`/domain recovery để xác định postcondition trước khi thử lại.
9. **Escalate / Commit / Sleep** — Chỉ commit/chuyển trạng thái khi postcondition được chứng minh. Nếu vượt risk/budget/attempt limit thì pause + escalate. Nếu chưa đến cadence tiếp theo thì sleep.

Vòng chuẩn:

```text
DISCOVER
  ↓
QUALIFY ──ambiguous──> UNKNOWN / HUMAN_REVIEW
  ↓
AUTHORIZE ──denied───> BLOCKED
  ↓
PLAN SMALL
  ↓
EXECUTE (maker)
  ↓
VERIFY (independent checker)
  ├─ proven + postcondition met ─> PERSIST SUCCESS
  ├─ disproven ─────────────────> PERSIST FAILURE → bounded retry/replan
  └─ side-effect unknown ───────> RECONCILING
                                      ↓
                           observe before retry
  ↓
BUDGET / ATTEMPT / RISK GATE
  ├─ within bounds ─> next iteration
  └─ exceeded ──────> PAUSED / HUMAN_REVIEW
```

## Autonomy Levels

Không nhảy thẳng sang unattended. Dùng maturity rollout sau:

| Level | Quyền tự động | Điều kiện tối thiểu |
|---|---|---|
| `L0_DRAFT` | Chỉ mô tả loop, chưa chạy | Goal + scope + state schema |
| `L1_REPORT` | Tự discover/triage, chỉ báo cáo | Durable state + no write side effects |
| `L2_ASSISTED` | Được thực hiện thay đổi nhỏ trong allowlist | Capability gate + independent verifier + rollback |
| `L3_UNATTENDED` | Chạy định kỳ không cần người nhìn từng vòng | Recovery evidence, kill switch, budget caps, stable verifier history, no unresolved high-risk gaps |

**Không được suy maturity từ file/config presence.** L3 cần quan sát runtime nhiều vòng trên exact policy/version hiện hành; một lần PASS không đủ.

## Durable State Contract

Loop không được dùng chat history làm source of truth. State tối thiểu phải có:

```yaml
loop_id: <stable-id>
policy_revision: <revision-or-hash>
workspace_revision: <exact-sha-or-version>
item_id: <issue/pr/job/signal-id>
item_fingerprint: <stable-content-hash-or-version>
attempt: <integer>
phase: DISCOVER|QUALIFY|AUTHORIZE|PLAN|EXECUTE|VERIFY|RECONCILE|PAUSED|DONE
maker_identity: <agent/session/model-lineage>
verifier_identity: <agent/session/model-lineage>
risk_tier: <declared-tier>
capability_refs: []
actions: []
evidence_refs: []
postcondition: <explicit-condition>
verdict: PROVEN|STRONGLY_SUPPORTED|HYPOTHESIS|DISPROVEN|UNKNOWN|BLOCKED
budget_used: <measured>
next_action: <bounded-next-step>
updated_at: <timestamp>
```

### State invariants

- State write phải atomic hoặc transactionally replaceable.
- `DONE` không được ghi nếu verifier chưa xác nhận postcondition ở evidence level phù hợp.
- Restart phải đọc state trước khi hành động mới.
- Resolved/closed items phải được prune/archive theo policy, không để stale item kích hoạt lại.
- Human override phải lưu provenance, không silently overwrite machine state.

## Maker / Checker Separation

Bắt buộc:

- Maker không được tự set verdict `PROVEN` cho thay đổi của chính mình.
- Checker phải nhận **claim + artifact/evidence**, không chỉ nhận lời giải thích của maker.
- Với security, release, recovery hoặc authority change: verifier phải độc lập đủ để tránh shared blind spot; nếu cùng model/lineage thì verdict tối đa là `STRONGLY_SUPPORTED` cho tới khi có independent lineage hoặc executable falsification mạnh hơn.
- “N agent đồng ý” không tự động là independent consensus.

## Scheduling & Trigger Rules

Mỗi loop phải khai báo:

- trigger: event, interval hoặc condition;
- cadence phù hợp tốc độ thay đổi của signal;
- first-run behavior;
- deduplication key để cùng event không chạy lặp;
- max concurrent items;
- quiet/off-hours policy nếu có;
- stop/pause condition;
- stale-input TTL/freshness rule.

Không dùng cadence nhanh hơn khả năng verifier/recovery xử lý backlog. Backlog tăng liên tục là failure signal, không phải lý do tăng concurrency vô hạn.

## Budget & Kill Switch

Mỗi loop phải có budget machine-readable:

- max iterations per item;
- max automatic writes/PRs/actions per window;
- token/API/tool budget;
- wall-clock/runtime budget;
- retry/backoff bounds;
- hard kill switch;
- authority riêng cho việc nâng budget.

Agent **không được tự nâng cap** để hoàn thành mục tiêu. Vượt budget → `PAUSED`/`HUMAN_REVIEW` hoặc policy-defined external authority.

## Risk Gates & Denylist

Mặc định không unattended đối với:

- secrets/credentials;
- authentication/authorization;
- payments/billing;
- production infrastructure;
- irreversible data deletion;
- privilege/capability issuance;
- dependency/supply-chain change chưa có policy riêng;
- thay đổi vượt file/diff/risk threshold của project.

Các action trên phải đi qua `scp-capability-security-review` và approval policy hiện hành. Skill này không cấp quyền.

## Recovery: Observe Before Retry

Nếu timeout/disconnect/crash xảy ra sau khi action có thể đã commit:

1. Chuyển `RECONCILING`.
2. Xác định idempotency key/logical action ID.
3. Quan sát remote/local postcondition độc lập.
4. Nếu side effect đã xảy ra: persist kết quả, không retry.
5. Nếu chưa xảy ra và retry-safe: retry trong bound.
6. Nếu không phân biệt được: `UNKNOWN`/`HUMAN_REVIEW`, không đoán.

Đây là hard rule chống duplicate side effect.

## Verification & Promotion Gate

Để promote loop từ L1→L2 hoặc L2→L3, yêu cầu tối thiểu:

- nhiều run thật trên dữ liệu/event khác nhau;
- verifier bắt được ít nhất một failure/negative case, không chỉ green path;
- restart/recovery test cho durable state;
- duplicate-event/idempotency test;
- budget exhaustion/kill-switch test;
- permission-denied test;
- stale-input test;
- evidence gắn exact policy revision + exact code/workspace revision.

Promotion verdict phải dùng `scp-reality-verifier` và, nếu ảnh hưởng release, `scp-release-evidence-gate`.

## Anti-Patterns

Cấm coi các mẫu sau là loop production-ready:

- cron + prompt nhưng không có durable state;
- maker tự kiểm tra và tự `DONE`;
- retry mọi exception mà không reconcile side effect;
- auto-merge mặc định;
- state chỉ nằm trong chat/context window;
- cùng một event chạy nhiều lần vì không có dedupe key;
- loop tiếp tục khi budget/attempt cap đã vượt;
- tăng timeout/retry để che flake;
- “3 agent đồng ý” nhưng cùng lineage và không có Reality probe;
- notification mọi vòng dù không cần hành động;
- L3 chỉ vì đã có scheduler/config file.

## Interaction with Existing SCP Skills

| Giai đoạn | Skill phải gọi khi phù hợp |
|---|---|
| Qualify / reasoning | `scp-dna` |
| Authorization / external write | `scp-capability-security-review` |
| Task-state durability | `scp-task-kernel-review` |
| Browser/web action | `scp-web-orchestration-safety` |
| Provider/API failure | `scp-gateway-resilience` |
| Unknown side effect / crash | `scp-computer-use-recovery` |
| Continuous learning/autofix | `scp-learning-loop-guard` |
| Runtime process/readiness | `scp-runtime-audit` |
| Result verification | `scp-reality-verifier` |
| Release claim | `scp-release-evidence-gate` |
| Loop/skill architecture review | `scp-skill-review` |

## Output Contract

Khi thiết kế/audit một continuous loop, trả về:

1. Goal + explicit non-goals
2. Trigger/cadence/freshness
3. Work-item identity + dedupe rule
4. State schema + restart behavior
5. Maker/checker topology + lineage note
6. Capability/risk gates
7. Budget + retry + kill switch
8. Recovery/reconciliation path
9. Evidence plan + promotion level
10. Remaining unknowns

Không kết thúc bằng “production-ready” nếu chưa có runtime evidence tương ứng.

## Provenance / Design Sources

Skill này được tạo từ khoảng trống quan sát được giữa SCP Skills hiện có và các operational-loop practices phổ biến: durable state, recurring discovery, maker/checker split, staged autonomy, budget caps, kill switch và escalation. Loop Engineering (`cobusgreyling/loop-engineering`) được dùng như một lineage tham khảo cho operational patterns; các yêu cầu epistemic, capability, Reality, recovery và release vẫn do SCP DNA/Skills kiểm soát.

Không sao chép implementation hay coi upstream pattern là proof. Mọi rule được áp vào SCP phải được xác minh bằng repo/runtime evidence.
