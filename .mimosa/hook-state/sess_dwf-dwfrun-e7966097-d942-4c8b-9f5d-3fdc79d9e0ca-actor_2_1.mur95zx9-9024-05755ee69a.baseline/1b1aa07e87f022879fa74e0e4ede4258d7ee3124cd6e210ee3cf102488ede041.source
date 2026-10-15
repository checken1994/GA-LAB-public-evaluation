"""[A1] Fail-closed contract cho at-rest encryption của bypass patterns.

Audit claim (đã CONFIRMED trước fix): scp/security/bypass_encrypt.py dùng lazy
import `cryptography`; khi package thiếu, encrypt_bypass() TỰ DOWNGRADE im lặng
sang plaintext JSON (fail-open). Trên container thật, SCP_ENCRYPT_BYPASSES=1
được set nhưng cryptography không được cài → bypass records ghi plaintext.

Contract sau fix:
- Thiếu cryptography  → BypassEncryptor(...) raise RuntimeError (fail-closed).
- Thiếu cryptography  → encrypt_bypass()/encrypt_file()/rotate_key() raise,
  KHÔNG trả về plaintext.
- Có cryptography     → encrypt/decrypt round-trip đúng, ciphertext != plaintext.
- shard.write_bypass khi env=1 + thiếu dep → raise (không ghi plaintext).
- Mode plaintext có chủ đích (env != "1") vẫn hoạt động (encryptor không tạo).
"""

from __future__ import annotations

import json
import sys

import pytest

from scp.core.partition import shard as shard_module
from scp.security import bypass_encrypt as be_module
from scp.security.bypass_encrypt import BypassEncryptor

_TEST_KEY = "a1-failclosed-test-key"  # giá trị test, KHÔNG phải secret thật


def _quality_passing_record(tag: str) -> dict:
    """Record pass WHY/quality gate (attack_type known + question dài + sig)
    để write path thật sự chạy tới bước encrypt, không bị reject sớm."""
    return {
        "type": "BYPASS",
        "attack_type": "prompt_injection",
        "question": f"what is a prompt injection attack {tag}",
        "signatures": f"sig-{tag}-001",
    }


@pytest.fixture(autouse=True)
def _deterministic_key(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Key deterministic từ env + data dir cô lập trong tmp_path."""
    monkeypatch.setenv("SCP_ENCRYPTION_KEY", _TEST_KEY)
    monkeypatch.delenv("SCP_ENCRYPT_BYPASSES", raising=False)


@pytest.fixture(autouse=True)
def _why_gate_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test isolation: WHY gate có singleton state chéo từ các flow test chạy
    trước trong cùng process (từ chối write "learning") → pin WHY=ALLOW.
    Fault-isolation seam: WHY không phải subject under test của file này
    (file này test fail-closed của encrypt path)."""
    from scp.meta.why_gate import WhyDecision, WhyResult

    class _AllowGate:
        def gate(self, *_args, **_kwargs) -> WhyResult:
            return WhyResult(
                decision=WhyDecision.ALLOW,
                necessity_reason="test isolation — WHY pinned ALLOW",
            )

    monkeypatch.setattr("scp.meta.why_gate.get_why_gate", lambda: _AllowGate())


def _simulate_missing_cryptography(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fault-injection seam: buộc import `cryptography` raise ImportError như
    khi package thật sự không được cài. Phải block CẢ package gốc lẫn submodule
    `cryptography.fernet` (nếu chỉ block gốc, submodule đã cached vẫn import được)."""
    monkeypatch.setitem(sys.modules, "cryptography", None)
    monkeypatch.setitem(sys.modules, "cryptography.fernet", None)
    monkeypatch.setattr(be_module, "_Fernet", None)  # reset availability cache


def test_missing_cryptography_encryptor_init_raises(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """[A1] Thiếu cryptography → khởi tạo encryptor phải raise, không tạo được
    object sẽ âm thầm ghi plaintext."""
    _simulate_missing_cryptography(monkeypatch)
    with pytest.raises(RuntimeError, match="fail-closed"):
        BypassEncryptor(data_dir=str(tmp_path))


def test_missing_cryptography_encrypt_bypass_raises_no_plaintext(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """[A1] encrypt_bypass không được trả về plaintext JSON khi thiếu dep —
    đây chính là fail-open path cũ (audit claim)."""
    enc = BypassEncryptor(data_dir=str(tmp_path))  # crypto còn, init OK
    _simulate_missing_cryptography(monkeypatch)  # dep "biến mất"
    record = {"type": "BYPASS", "attack": "jailbreak", "signatures": "sig-1"}
    with pytest.raises(RuntimeError, match="fail-closed"):
        enc.encrypt_bypass(record)


def test_missing_cryptography_encrypt_file_and_rotate_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """[A1] encrypt_file/rotate_key là yêu cầu encrypt tường minh → phải raise
    thay vì skip/return im lặng (no-op)."""
    enc = BypassEncryptor(data_dir=str(tmp_path))  # crypto còn, init OK
    _simulate_missing_cryptography(monkeypatch)  # dep "biến mất"
    target = tmp_path / "2026-09-12.jsonl"
    target.write_text('{"type": "BYPASS"}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="fail-closed"):
        enc.encrypt_file(target)
    with pytest.raises(RuntimeError, match="fail-closed"):
        enc.rotate_key()


def test_encrypt_decrypt_roundtrip_with_real_cryptography(tmp_path) -> None:
    """[A1] Có cryptography: round-trip đúng VÀ output trên disk là ciphertext
    (Fernet token), không phải plaintext JSON."""
    enc = BypassEncryptor(data_dir=str(tmp_path))
    record = {"type": "BYPASS", "attack": "prompt-injection", "signatures": "sig-9"}
    encrypted = enc.encrypt_bypass(record)

    plaintext_bytes = json.dumps(record, ensure_ascii=False).encode("utf-8")
    assert encrypted != plaintext_bytes  # không bao giờ ghi plaintext khi env=1
    with pytest.raises(json.JSONDecodeError):
        json.loads(encrypted.decode("utf-8"))  # ciphertext không parse được như JSON

    assert enc.decrypt_bypass(encrypted) == record


def test_decrypt_bypass_legacy_plaintext_compat(tmp_path) -> None:
    """Read-path backward-compat có chủ đích: dòng plaintext JSON (ghi thời
    env=0) vẫn đọc được qua hook R5-3 — đây không phải downgrade write."""
    BypassEncryptor(data_dir=str(tmp_path))  # đảm bảo env key được materialize
    line = json.dumps({"type": "BYPASS", "attack": "legacy"}, ensure_ascii=False)
    legacy = BypassEncryptor.decrypt_bypass_if_enabled(line)
    assert legacy == {"type": "BYPASS", "attack": "legacy"}


def test_shard_write_bypass_fail_closed_when_crypto_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """[A1] Env=1 + thiếu cryptography → shard.write_bypass phải raise và
    KHÔNG được ghi dòng plaintext xuống disk (caller-level fail-closed)."""
    _simulate_missing_cryptography(monkeypatch)
    monkeypatch.setenv("SCP_ENCRYPT_BYPASSES", "1")
    monkeypatch.setattr(shard_module, "_BYPASS_ENCRYPTOR_SINGLETON", None)
    monkeypatch.setattr(shard_module, "DATA_DIR", tmp_path)  # singleton ghi vào tmp

    partitioner = shard_module.DataPartitioner(data_dir=tmp_path)
    bypass_dir = tmp_path / "bypasses"
    before = sorted(p.name for p in bypass_dir.glob("*.jsonl")) if bypass_dir.exists() else []

    with pytest.raises(RuntimeError, match="fail-closed"):
        partitioner.write_bypass(_quality_passing_record("fail-closed-missing-dep"))

    after = sorted(p.name for p in bypass_dir.glob("*.jsonl")) if bypass_dir.exists() else []
    assert after == before  # không có file nào được tạo/ghi thêm


def test_shard_write_bypass_encrypted_when_crypto_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """[A1] Env=1 + đủ dependency → file trên disk chứa Fernet token, không
    phải plaintext JSON; decrypt ngược ra đúng record."""
    monkeypatch.setenv("SCP_ENCRYPT_BYPASSES", "1")
    monkeypatch.setattr(shard_module, "_BYPASS_ENCRYPTOR_SINGLETON", None)
    monkeypatch.setattr(shard_module, "DATA_DIR", tmp_path)  # singleton ghi vào tmp

    partitioner = shard_module.DataPartitioner(data_dir=tmp_path)
    partitioner.write_bypass(_quality_passing_record("e2e-enc"))

    files = list((tmp_path / "bypasses").glob("*.jsonl"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8").strip()
    assert content  # có dòng
    with pytest.raises(json.JSONDecodeError):
        json.loads(content)  # KHÔNG phải plaintext JSON

    enc = BypassEncryptor(data_dir=str(tmp_path))
    assert enc.decrypt_bypass(content.encode("utf-8"))["question"].endswith("e2e-enc")


def test_shard_plaintext_mode_intentional_when_env_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Mode plaintext có chủ đích (env != "1"): encryptor không được tạo,
    write_bypass ghi JSON plaintext như thiết kế — không phải downgrade."""
    monkeypatch.delenv("SCP_ENCRYPT_BYPASSES", raising=False)
    monkeypatch.setattr(shard_module, "_BYPASS_ENCRYPTOR_SINGLETON", None)

    partitioner = shard_module.DataPartitioner(data_dir=tmp_path)
    partitioner.write_bypass(_quality_passing_record("env-off"))

    files = list((tmp_path / "bypasses").glob("*.jsonl"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert record["question"].endswith("env-off")  # plaintext parse được = intentional mode


# ===========================================================================
# [SEC-FIX rotate-mixed 2026-09-26] rotate_key() trước fix giữ nguyên dòng
# không decrypt được (plaintext legacy / corrupt) → sau rotation file vẫn là
# hỗn hợp plaintext+ciphertext (probe đã xác nhận). Contract mới: fail-closed —
# dòng không decrypt được bị DROP, WARNING phải nêu count.
# ===========================================================================

def test_rotate_key_drops_undecryptable_lines_no_mixed_state(tmp_path, caplog) -> None:
    import logging

    from cryptography.fernet import Fernet

    enc = BypassEncryptor(data_dir=str(tmp_path))
    target = tmp_path / "bypasses" / "2026-09-26.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    good = {"type": "BYPASS", "signature": "good-rotate-line"}
    target.write_text(
        enc.encrypt_bypass(good).decode("utf-8") + "\n"
        + json.dumps({"type": "PLAINTEXT-LEGACY"}) + "\n"
        + "corrupted-not-json\n",
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="scp.security.bypass_encrypt"):
        enc.rotate_key()

    after = [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # 1. Mọi dòng còn lại phải decrypt được với key MỚI (không raise).
    new_fernet = Fernet(enc._key)
    decrypted = [new_fernet.decrypt(ln.encode("utf-8")) for ln in after]
    assert len(decrypted) == 1
    assert json.loads(decrypted[0].decode("utf-8"))["signature"] == "good-rotate-line"
    # 2. Không còn plaintext legacy / dòng corrupt sau rotation.
    assert not any(ln.lstrip().startswith("{") for ln in after)
    assert "corrupted-not-json" not in target.read_text(encoding="utf-8")
    # 3. WARNING phải nêu đếm số dòng bị drop.
    assert any("dropped 2 un-decryptable" in r.getMessage() for r in caplog.records)
