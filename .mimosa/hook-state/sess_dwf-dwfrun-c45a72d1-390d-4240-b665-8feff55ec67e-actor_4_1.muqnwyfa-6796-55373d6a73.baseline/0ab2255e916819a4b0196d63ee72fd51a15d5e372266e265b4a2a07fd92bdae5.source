"""
SCP Bypass Encryptor — at-rest encryption for bypass patterns.

TẠI SAO module này tồn tại?
  data/bypasses/*.jsonl chứa attack patterns SCP đã detect. Nếu attacker
  exfil được files này → biết SCP đã detect gì → adapt attack. Encrypt at-rest
  = thêm 1 lớp defense-in-depth.

TẠI SAO Fernet (symmetric)?
  - Đơn giản, không cần key management phức tạp
  - Key derive từ SCP_ENCRYPTION_KEY env var (human-controlled)
  - Nếu không có env var → generate + persist to data/.encryption_key
    (chỉ hoạt động local, không production-ready)

TẠI SAO không encrypt ngay khi write?
  - Performance: encrypt only khi SCP_ENCRYPT_BYPASSES=1
  - Default OFF — opt-in, không break existing flow
  - Khi ON: every append_bypass() encrypts before write

Safety:
  - Key rotation support (rotate_key())
  - Thread-safe (Lock)
  - Backup before encrypt file

[A1 fail-closed] Khi encryption được yêu cầu (SCP_ENCRYPT_BYPASSES=1) mà
package `cryptography` thiếu hoặc key không khả dụng, module RAISE thay vì
tự downgrade im lặng sang plaintext (fail-open cũ đã bị loại bỏ — audit A1).
Plaintext chỉ tồn tại ở mode có chủ đích: SCP_ENCRYPT_BYPASSES != "1"
(encryptor không được tạo) và ở read-path backward-compat cho file legacy.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger("scp.security.bypass_encrypt")

# Lazy import cryptography — availability probe (False = package missing)
_Fernet = None
def _get_fernet():
    """Probe for the cryptography package. Returns Fernet class, or False."""
    global _Fernet
    if _Fernet is None:
        try:
            from cryptography.fernet import Fernet
            _Fernet = Fernet
        except ImportError:
            logger.error(
                "[bypass_encrypt] cryptography not installed — encryption "
                "UNAVAILABLE (fail-closed: encrypt/rotate operations will raise)"
            )
            _Fernet = False
    return _Fernet


def _require_fernet():
    """[A1 fail-closed] Return the Fernet class or raise RuntimeError.

    Encryption operations must never degrade to plaintext when cryptography
    is missing: the caller explicitly requested at-rest encryption, so a
    missing dependency is a hard configuration error, not a soft fallback.
    """
    Fernet = _get_fernet()
    if not Fernet:
        raise RuntimeError(
            "bypass_encrypt: cryptography package is required for at-rest "
            "encryption but is not installed (fail-closed, no plaintext "
            "fallback). Install it: pip install -r scp/requirements.txt "
            "or unset SCP_ENCRYPT_BYPASSES to run in intentional plaintext mode."
        )
    return Fernet


class BypassEncryptor:
    """At-rest encryption for bypass patterns."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.bypasses_dir = self.data_dir / "bypasses"
        self.bypasses_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = self.data_dir / ".encryption_key"
        self._lock = threading.Lock()
        self._key = self._load_or_generate_key()
        # [A1 fail-closed] The encryptor is only constructed when encryption is
        # explicitly requested (SCP_ENCRYPT_BYPASSES=1). Refuse to construct a
        # broken encryptor that would silently write plaintext.
        _require_fernet()

    def _load_or_generate_key(self) -> bytes:
        """Load key from env var or file. Generate if neither exists."""
        # Env var takes priority
        env_key = os.environ.get("SCP_ENCRYPTION_KEY", "")
        if env_key:
            # Derive Fernet-compatible key from env var (must be 32 url-safe base64 bytes)
            import base64
            derived = base64.urlsafe_b64encode(hashlib.sha256(env_key.encode()).digest())
            logger.info("[bypass_encrypt] Key loaded from SCP_ENCRYPTION_KEY env var")
            return derived

        # Load from file
        if self.key_file.exists():
            key = self.key_file.read_bytes().strip()
            logger.info("[bypass_encrypt] Key loaded from file")
            return key

        # Generate new key
        Fernet = _get_fernet()
        if not Fernet:
            return b""  # encryption disabled
        key = Fernet.generate_key()
        try:
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # owner-only read/write
            logger.warning(
                "[bypass_encrypt] Generated new key — saved to data/.encryption_key. "
                "Set SCP_ENCRYPTION_KEY env var for production."
            )
        except Exception as e:
            logger.warning(f"[bypass_encrypt] Could not persist key: {e}", exc_info=True)
        return key

    def encrypt_bypass(self, bypass_dict: dict) -> bytes:
        """Encrypt a bypass dict → bytes.

        [A1 fail-closed] Raises RuntimeError when cryptography is unavailable
        or the key is missing — never returns plaintext as a silent fallback.
        """
        Fernet = _require_fernet()
        if not self._key:
            raise RuntimeError(
                "bypass_encrypt: no encryption key available (fail-closed, "
                "no plaintext fallback). Set SCP_ENCRYPTION_KEY."
            )
        with self._lock:
            f = Fernet(self._key)
            plaintext = json.dumps(bypass_dict, ensure_ascii=False).encode("utf-8")
            return f.encrypt(plaintext)

    def decrypt_bypass(self, encrypted: bytes) -> dict:
        """Decrypt bytes → bypass dict.

        Read-path compat is intentional here: plaintext JSON is accepted for
        files written while SCP_ENCRYPT_BYPASSES=0 (legacy/intentional mode),
        and per-line failures return {} so callers skip the line (R5-3
        contract) — this is a read degradation, never a plaintext write.
        """
        Fernet = _get_fernet()
        if not Fernet or not self._key:
            # Encryption was disabled — parse as plaintext JSON
            try:
                return json.loads(encrypted.decode("utf-8"))
            except Exception as e:
                logger.warning(f"[bypass_encrypt] Decrypt (plaintext) failed: {e}", exc_info=True)
                return {}
        with self._lock:
            f = Fernet(self._key)
            try:
                plaintext = f.decrypt(encrypted)
                return json.loads(plaintext.decode("utf-8"))
            except Exception as e:
                logger.warning(f"[bypass_encrypt] Decrypt failed: {e}", exc_info=True)
                return {}

    # [SCP-DNA-FIX R5-3] Public read-path hook — decrypt_bypass is now reachable
    # from the read path (shard.py:_score_data_quality). Previously encrypt_bypass
    # WAS called on write but decrypt_bypass was NEVER called on read → when
    # SCP_ENCRYPT_BYPASSES=1, the duplicate-detection read path in
    # `_score_data_quality` saw Fernet tokens as text, `json.loads()` failed
    # silently inside `except Exception: continue`, and signature-dedup was
    # silently broken. This classmethod is the single entry point for any read
    # path that needs to recover a bypass dict from a stored line.
    @classmethod
    def decrypt_bypass_if_enabled(cls, line: str | bytes, encryptor: BypassEncryptor | None = None) -> dict:
        """[SCP-DNA-FIX R5-3] Decrypt a stored bypass line if encryption is enabled.

        Tries plaintext JSON first (backward compat for files written when
        SCP_ENCRYPT_BYPASSES=0). If that fails AND an encryptor is provided,
        delegates to `encryptor.decrypt_bypass(...)`.

        Args:
            line: a single line read from `data/bypasses/{date}.jsonl`
                  (may be plaintext JSON OR a url-safe-base64 Fernet token).
            encryptor: the BypassEncryptor singleton from shard._get_bypass_encryptor()
                       — pass None when SCP_ENCRYPT_BYPASSES=0 (plaintext mode).

        Returns:
            dict on success, empty dict {} on any failure (logged at debug).
            Callers should treat `{}` as "skip this line" (matches existing
            `except Exception: continue` semantics in shard.py:_score_data_quality).
        """
        if not line:
            return {}
        # Normalize to bytes
        if isinstance(line, str):
            raw = line.strip().encode("utf-8")
        else:
            raw = line.strip()
        if not raw:
            return {}

        # Try plaintext JSON first (covers SCP_ENCRYPT_BYPASSES=0 + historical files)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug('BypassEncryptor.decrypt_bypass_if_enabled: json.JSONDecodeError, UnicodeDecodeError ignored', exc_info=True)  # fall through to decryption attempt

        # If encryption is enabled, try decrypting as a Fernet token
        if encryptor is None:
            # No encryptor available and plaintext parse failed → unreadable line
            logger.debug("[bypass_encrypt] decrypt_bypass_if_enabled: line is not JSON and no encryptor provided")
            return {}
        try:
            return encryptor.decrypt_bypass(raw)
        except Exception as e:
            logger.debug(f"[bypass_encrypt] decrypt_bypass_if_enabled: decrypt failed: {e}", exc_info=True)
            return {}

    def encrypt_file(self, filepath: Path) -> Path:
        """Encrypt a bypass JSONL file in-place. Returns backup path.

        [A1 fail-closed] An explicit encrypt request raises when cryptography
        is unavailable — it no longer silently skips (leaving plaintext).
        """
        Fernet = _require_fernet()
        if not self._key:
            raise RuntimeError(
                "bypass_encrypt: no encryption key available (fail-closed, "
                "no plaintext fallback). Set SCP_ENCRYPTION_KEY."
            )

        if not filepath.exists():
            return filepath

        # Backup
        bak_path = filepath.with_suffix(filepath.suffix + ".bak")
        bak_path.write_bytes(filepath.read_bytes())

        # Encrypt each line
        with self._lock:
            f = Fernet(self._key)
            lines = filepath.read_text(encoding="utf-8").splitlines()
            encrypted_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    enc = f.encrypt(line.encode("utf-8"))
                    encrypted_lines.append(enc.decode("utf-8"))
                except Exception as e:
                    logger.warning(f"[bypass_encrypt] Line encrypt failed: {e}", exc_info=True)
            filepath.write_text("\n".join(encrypted_lines) + "\n", encoding="utf-8")
            logger.info(f"[bypass_encrypt] Encrypted {len(encrypted_lines)} lines in {filepath.name}")
        return bak_path

    def decrypt_file(self, filepath: Path) -> dict:
        """Decrypt a bypass JSONL file → aggregated dict (for audit)."""
        Fernet = _get_fernet()
        if not filepath.exists():
            return {"error": "file not found"}

        with self._lock:
            if not Fernet or not self._key:
                # Plaintext
                lines = filepath.read_text(encoding="utf-8").splitlines()
                return {"count": len([line for line in lines if line.strip()]), "encrypted": False}

            f = Fernet(self._key)
            lines = filepath.read_text(encoding="utf-8").splitlines()
            decrypted = 0
            failed = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    f.decrypt(line.encode("utf-8"))
                    decrypted += 1
                except Exception:
                    logger.warning('BypassEncryptor.decrypt_file: Exception not handled', exc_info=True)
                    failed += 1
            return {"count": decrypted, "failed": failed, "encrypted": True}

    def rotate_key(self) -> None:
        """Generate new key + re-encrypt all bypass files.

        [A1 fail-closed] Raises when cryptography is unavailable instead of
        returning silently (rotation request must not be a silent no-op).
        """
        Fernet = _require_fernet()

        old_key = self._key
        # Decrypt all files with old key, then re-encrypt with new key
        new_key = Fernet.generate_key()
        bypass_files = list(self.bypasses_dir.glob("*.jsonl"))

        with self._lock:
            old_fernet = Fernet(old_key)
            new_fernet = Fernet(new_key)
            for bf in bypass_files:
                try:
                    lines = bf.read_text(encoding="utf-8").splitlines()
                    reencrypted = []
                    dropped = 0
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            plaintext = old_fernet.decrypt(line.encode("utf-8"))
                            new_enc = new_fernet.encrypt(plaintext)
                            reencrypted.append(new_enc.decode("utf-8"))
                        except Exception:
                            # [SEC-FIX rotate-mixed 2026-09-26] PRE-FIX: the
                            # un-decryptable line was appended AS-IS, so after
                            # rotation the file stayed a plaintext/ciphertext
                            # mix — a legacy plaintext attack pattern survived
                            # rotation in the clear (probe-confirmed). Fail-closed
                            # now: DROP the line and name the count in a WARNING
                            # so the operator can re-ingest it deliberately.
                            dropped += 1
                            logger.warning(
                                "[bypass_encrypt] Rotate %s: line %d is not decryptable "
                                "with the old key (plaintext legacy or corrupted) — "
                                "DROPPED, never left in the clear",
                                bf.name,
                                dropped,
                            )
                    if dropped:
                        logger.warning(
                            "[bypass_encrypt] Rotate %s: dropped %d un-decryptable "
                            "line(s) — mixed plaintext/ciphertext state is not allowed "
                            "after rotation",
                            bf.name,
                            dropped,
                        )
                    bf.write_text("\n".join(reencrypted) + "\n", encoding="utf-8")
                except Exception as e:
                    logger.warning(f"[bypass_encrypt] Rotate failed for {bf.name}: {e}", exc_info=True)

            # Save new key
            self._key = new_key
            self.key_file.write_bytes(new_key)
            self.key_file.chmod(0o600)
            logger.info(f"[bypass_encrypt] Key rotated — re-encrypted {len(bypass_files)} files")
