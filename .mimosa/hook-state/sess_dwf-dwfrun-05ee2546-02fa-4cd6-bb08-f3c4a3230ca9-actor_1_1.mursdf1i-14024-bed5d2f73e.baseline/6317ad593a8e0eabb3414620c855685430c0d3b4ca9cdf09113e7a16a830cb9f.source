"""[AUDIT-FIX low-10] Contract test — /api/scp/ask conversation_history cap.

Root cause (external audit low-10): route.ts forward conversation_history
không có size cap (chỉ slice(-8) theo số item) → client bơm item hàng chục MB
→ payload upstream phình to tùy ý.

Fix: dashboard/src/lib/scp-history.ts capConversationHistory() — max 8 item
mới nhất, mỗi item ≤ 4KB serialized, tổng ≤ 32KB, flag `truncated` báo rõ
trong payload (conversation_history_truncated).

Regression: runtime thật qua bun -e (pure lib import) + static check route.
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ASK_ROUTE = ROOT / "dashboard" / "src" / "app" / "api" / "scp" / "ask" / "route.ts"
HISTORY_LIB = ROOT / "dashboard" / "src" / "lib" / "scp-history.ts"
DASHBOARD_DIR = ROOT / "dashboard"

RUNTIME_SCRIPT = r"""
const { capConversationHistory, CONVERSATION_HISTORY_MAX_TOTAL_BYTES } =
  await import("./src/lib/scp-history.ts");

function bytesOf(v) {
  return new TextEncoder().encode(JSON.stringify(v)).length;
}
function fail(msg) {
  console.error("FAIL " + msg);
  process.exit(1);
}

// 1. Oversize TOTAL: 20 item x ~4KB → giữ item MỚI NHẤT, tổng ≤ 32KB, flag.
const chunk = "x".repeat(3800);
const many = Array.from({ length: 20 }, (_, i) => ({
  role: "user",
  content: `${chunk}-${i}`,
}));
let r = capConversationHistory(many);
if (r.items.length < 1 || r.items.length > 8) fail(`items=${r.items.length}`);
if (bytesOf(r.items) > CONVERSATION_HISTORY_MAX_TOTAL_BYTES) fail("total > 32KB");
if (r.truncated !== true) fail("oversize total phải đặt truncated=true");
// item mới nhất (i=19) phải được giữ — cap giữ MỚI, drop CŨ.
const lastKept = JSON.stringify(r.items[r.items.length - 1]);
if (!lastKept.includes("x-19") && !lastKept.includes("19")) {
  fail("item mới nhất không được giữ: " + lastKept.slice(0, 60));
}

// 2. Oversize SINGLE item: content 100KB → cắt xuống ≤ 4KB, kèm marker.
const huge = [{ role: "user", content: "y".repeat(100_000) }];
r = capConversationHistory(huge);
if (r.items.length !== 1) fail(`single items=${r.items.length}`);
const kept = r.items[0];
if (bytesOf(kept) > 4096) fail(`oversize item vẫn ${bytesOf(kept)} bytes`);
if (!kept.content.endsWith("…")) fail("content cắt phải có marker '…'");
if (r.truncated !== true) fail("oversize item phải đặt truncated=true");

// 3. History bình thường → giữ nguyên, không flag.
const normal = [
  { role: "user", content: "xin chào" },
  { role: "assistant", content: "chào bạn" },
  { role: "user", content: "pH trung tính là bao nhiêu?" },
];
r = capConversationHistory(normal);
if (r.items.length !== 3) fail(`normal items=${r.items.length}`);
if (r.truncated !== false) fail("history nhỏ không được flag truncated");
if (r.items[2].content !== "pH trung tính là bao nhiêu?") fail("content bị đổi");

// 4. Item không hợp lệ bị loại → flag.
r = capConversationHistory([{ role: "user" }, "junk-string", 42, null]);
if (r.items.length !== 1) fail(`invalid-filter items=${r.items.length}`);
if (r.truncated !== true) fail("loại item không hợp lệ phải flag");

// 5. Non-array → rỗng, an toàn.
r = capConversationHistory("not-an-array");
if (r.items.length !== 0) fail("non-array phải trả rỗng");

// 6. [HARD-CAP-SERIALIZED-FIX] content 5000 x "\n": raw 5000 bytes nhưng
// serialized mỗi "\n" escape thành 2 bytes → budget raw cũ (maxItemBytes-16)
// nghĩ là đã cắt vừa (~4080 raw) nhưng serialized vẫn ~8KB. Phải cap theo
// JSON.stringify thật: item cuối cùng ≤ 4096 bytes serialized.
r = capConversationHistory([{ role: "user", content: "\n".repeat(5000) }]);
if (r.items.length !== 1) fail(`escaped-newline items=${r.items.length}`);
if (bytesOf(r.items[0]) > 4096) {
  fail(`escaped-newline item vẫn ${bytesOf(r.items[0])} bytes serialized > 4096`);
}
if (r.items[0].content.endsWith("\n") && !r.items[0].content.endsWith("…")) {
  fail("escaped-newline content phải được cắt kèm marker");
}
if (r.truncated !== true) fail("escaped-newline item phải flag truncated");

// 7. [HARD-CAP-SERIALIZED-FIX] oversized field KHÁC content phải bị cắt
// (marker tối giản), không được pass whole.
r = capConversationHistory([
  { role: "user", content: "ok", attachments: "z".repeat(100_000) },
]);
if (r.items.length !== 1) fail(`non-content-big items=${r.items.length}`);
if (bytesOf(r.items[0]) > 4096) {
  fail(`non-content big field vẫn ${bytesOf(r.items[0])} bytes > 4096`);
}
if (r.items[0].content !== "…[truncated]") {
  fail("item oversized vì field khác content phải thay bằng marker: " + JSON.stringify(r.items[0]).slice(0, 80));
}
if (r.truncated !== true) fail("non-content big field phải flag truncated");

// 8. Tổng chốt ≤ 32KB với mixed oversized items.
const mixed = Array.from({ length: 12 }, (_, i) => ({
  role: "user",
  content: "w".repeat(90_000),
  index: i,
}));
r = capConversationHistory(mixed);
if (bytesOf(r.items) > CONVERSATION_HISTORY_MAX_TOTAL_BYTES) fail("mixed total > 32KB");

console.log("HISTORY_CAP_OK");
"""


def test_ask_route_uses_cap_and_flag():
    source = ASK_ROUTE.read_text(encoding="utf-8")
    assert "capConversationHistory(body.conversation_history)" in source
    assert "conversation_history_truncated" in source
    # slice(-8) thô phải đã bị thay
    assert 'body.conversation_history.slice(-8)' not in source


def test_history_lib_exists_and_exports_pure_function():
    source = HISTORY_LIB.read_text(encoding="utf-8")
    assert "export function capConversationHistory" in source
    assert "CONVERSATION_HISTORY_MAX_TOTAL_BYTES = 32 * 1024" in source


@pytest.mark.parametrize("marker", ["HISTORY_CAP_OK"])
def test_history_cap_runtime_behavior(marker):
    result = subprocess.run(
        ["bun", "-e", RUNTIME_SCRIPT],
        cwd=str(DASHBOARD_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"history cap runtime FAIL:\n{result.stdout}\n{result.stderr}"
    )
    assert marker in result.stdout
