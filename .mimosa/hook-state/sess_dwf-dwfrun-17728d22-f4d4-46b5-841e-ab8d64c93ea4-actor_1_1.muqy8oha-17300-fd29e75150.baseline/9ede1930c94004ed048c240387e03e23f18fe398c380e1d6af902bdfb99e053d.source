#!/usr/bin/env python3
"""
Adversarial Penetration Testing Probe: GAP-08 Token Forgery & Cryptographic Attacks
Target: CapabilityAuthority.validate() and CapabilityToken HMAC-SHA256 signature verification.

Executed by: Challenger 1 (teamwork_preview_challenger)
Standards: SCP DNA (29 Principles), Zero-Trust, Fail-Closed, FA-01 to FA-10, Exploit Mandate (FA-09).
"""

import hashlib
import hmac
import json
import os
import random
import string
import sys
import tempfile
import time
from pathlib import Path

# Ensure scp is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure test secret is set in environment for imports
TARGET_SECRET = b"production-master-secret-key-32-chars-ok!"
os.environ["SCP_CAPABILITY_SECRET"] = TARGET_SECRET.decode("utf-8")

from scp.core.capability_token import (
    CapabilityToken,
    InvalidTokenSignatureError,
    compute_token_signature,
    verify_token_signature,
)
from scp.security.capability_epoch import (
    CapabilityAuthority,
    parse_capability_token,
)

# [S311/B311-fix] RNG riêng cho probe (fuzz token id / signature garbage). KHÔNG có
# mục đích bảo mật: các giá trị này chỉ là dữ liệu test cố tình kỳ vọng bị
# validate() từ chối — không token/secret thật cần unguessable. Dùng instance
# SystemRandom riêng (nguồn os.urandom) thay cho global RNG để (1) tách biệt
# với mọi lời random.seed() của module khác, (2) làm rõ ràng tại call site rằng
# đây là nguồn ngẫu nhiên phi bảo mật, và (3) triệt tiêu B311 của bandit trên
# instantiation (pattern: scp/security/gcg_attack.py `_GCG_RNG`).
_PROBE_RNG = random.SystemRandom()


def run_test_case(name: str, fn) -> tuple[bool, str]:
    try:
        fn()
        return True, "PASSED (Rejected fail-closed as expected)"
    except AssertionError as ae:
        return False, f"SECURITY FAILURE (Accepted forged/tampered token!): {ae}"
    except Exception as exc:
        return False, f"UNEXPECTED ERROR: {type(exc).__name__}: {exc}"


def main():
    print("=" * 80)
    print("CHALLENGER 1 ADVERSARIAL PENETRATION TEST SUITE: TOKEN FORGERY & CRYPTO ATTACKS")
    print(f"Target Secret: {TARGET_SECRET[:8].decode()}... (length: {len(TARGET_SECRET)})")
    print("=" * 80)

    total_attacks = 0
    blocked_attacks = 0
    failed_attacks = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        state_path = Path(tmp_dir) / "capability_state.json"
        authority = CapabilityAuthority(state_path=state_path, secret=TARGET_SECRET)

        # Baseline check: legitimate token must validate
        legit_token = authority.issue("hands:pc.read")
        assert authority.validate(legit_token, required_subject="hands:pc.read") is True, "Legitimate token failed validation!"
        print("[BASELINE] Legitimate token issued and verified: PASS\n")

        # ----------------------------------------------------------------------
        # CATEGORY 1: Forging tokens out of thin air without the secret
        # ----------------------------------------------------------------------
        print("--- CATEGORY 1: Out-of-Thin-Air Forgery Attacks ---")

        thin_air_tests = [
            ("Unsigned token dataclass", CapabilityToken("hands:pc.write_file", 0, "forge-1", time.time(), "")),
            ("Random 64-char hex signature", CapabilityToken("hands:pc.write_file", 0, "forge-2", time.time(), "a" * 64)),
            ("All-zero 64-char signature", CapabilityToken("hands:pc.write_file", 0, "forge-3", time.time(), "0" * 64)),
            ("All-f 64-char signature", CapabilityToken("hands:pc.write_file", 0, "forge-4", time.time(), "f" * 64)),
            ("Short random alphanumeric string", CapabilityToken("hands:pc.write_file", 0, "forge-5", time.time(), "random_sig")),
            ("Forged via dict deserialization", parse_capability_token({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "forge-dict", "issued_at": time.time(), "signature": "bad" * 16
            })),
            ("Forged via JSON string deserialization", parse_capability_token(json.dumps({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "forge-json", "issued_at": time.time(), "signature": "deadbeef" * 8
            }))),
        ]

        for desc, forged in thin_air_tests:
            total_attacks += 1
            try:
                authority.validate(forged, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] {desc}: ACCEPTED!")
                failed_attacks.append(desc)
            except InvalidTokenSignatureError as err:
                blocked_attacks += 1
                print(f"  [BLOCKED] {desc}: InvalidTokenSignatureError: {err}")
            except Exception as e:
                print(f"  [ERROR] {desc}: Unexpected exception {type(e).__name__}: {e}")
                failed_attacks.append(f"{desc} (unexpected: {e})")

        # ----------------------------------------------------------------------
        # CATEGORY 2: Forging tokens with old fallback secret & known defaults
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 2: Known/Stale Secret Forgery Attacks ---")

        known_secrets = [
            (b"dev-secret-do-not-use-in-prod-12345", "Old GAP-09 dev fallback secret"),
            (b"secret", "Common default 'secret'"),
            (b"password", "Common default 'password'"),
            (b"default", "Common default 'default'"),
            (b"admin", "Common default 'admin'"),
            (b"changeme", "Common default 'changeme'"),
            (b"12345678", "Common numeric default"),
            (b"scp-secret", "Predictable project-name secret"),
        ]

        for fake_secret, desc in known_secrets:
            total_attacks += 1
            tid = f"known-sec-{_PROBE_RNG.randint(1000, 9999)}"
            iat = round(time.time(), 6)
            sig = compute_token_signature(fake_secret, "hands:pc.write_file", 0, tid, iat)
            token = CapabilityToken(
                subject="hands:pc.write_file",
                epoch=0,
                token_id=tid,
                issued_at=iat,
                signature=sig,
            )
            try:
                authority.validate(token, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] Signed with {desc}: ACCEPTED!")
                failed_attacks.append(f"Signed with {desc}")
            except InvalidTokenSignatureError as err:
                blocked_attacks += 1
                print(f"  [BLOCKED] Signed with {desc}: InvalidTokenSignatureError")
            except Exception as e:
                print(f"  [ERROR] Signed with {desc}: {type(e).__name__}: {e}")
                failed_attacks.append(f"Signed with {desc} ({e})")

        # ----------------------------------------------------------------------
        # CATEGORY 3: Weak / Mismatched Key Attacks
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 3: Weak and Mismatched Key Attacks ---")

        weak_keys = [
            (b"", "Empty key (b'')"),
            (b"   ", "Whitespace key"),
            (b"\x00" * 32, "Null bytes 32-byte key"),
            (b"production-master-secret-key-32-chars-o", "Truncated target secret (by 1 char)"),
            (b"production-master-secret-key-32-chars-ok!EXTRA", "Extended target secret"),
            (b"Production-Master-Secret-Key-32-Chars-Ok!", "Case-altered target secret"),
            (b"another-authority-secret-key-here-12345", "Different authority secret"),
        ]

        for wkey, desc in weak_keys:
            total_attacks += 1
            tid = f"weak-key-{_PROBE_RNG.randint(1000, 9999)}"
            iat = round(time.time(), 6)
            sig = compute_token_signature(wkey, "hands:pc.write_file", 0, tid, iat)
            token = CapabilityToken(
                subject="hands:pc.write_file",
                epoch=0,
                token_id=tid,
                issued_at=iat,
                signature=sig,
            )
            try:
                authority.validate(token, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] Signed with {desc}: ACCEPTED!")
                failed_attacks.append(f"Signed with {desc}")
            except InvalidTokenSignatureError as err:
                blocked_attacks += 1
                print(f"  [BLOCKED] Signed with {desc}: InvalidTokenSignatureError")
            except Exception as e:
                print(f"  [ERROR] Signed with {desc}: {type(e).__name__}: {e}")
                failed_attacks.append(f"Signed with {desc} ({e})")

        # ----------------------------------------------------------------------
        # CATEGORY 4: Bit-Flipping and Signature Truncation/Mutation Attacks
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 4: Bit-Flipping & Signature Mutation Attacks ---")

        base_token = authority.issue("hands:pc.write_file")
        orig_sig = base_token.signature

        # Single bit flips at multiple offsets
        for offset in [0, 1, 15, 31, 32, 47, 62, 63]:
            total_attacks += 1
            flipped_char = "1" if orig_sig[offset] == "0" else "0"
            flipped_sig = orig_sig[:offset] + flipped_char + orig_sig[offset + 1:]
            token = CapabilityToken(
                subject=base_token.subject,
                epoch=base_token.epoch,
                token_id=base_token.token_id,
                issued_at=base_token.issued_at,
                signature=flipped_sig,
            )
            try:
                authority.validate(token, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] Bit-flip at offset {offset}: ACCEPTED!")
                failed_attacks.append(f"Bit-flip at offset {offset}")
            except InvalidTokenSignatureError:
                blocked_attacks += 1
                print(f"  [BLOCKED] Bit-flip at offset {offset}: InvalidTokenSignatureError")

        # Signature truncation tests
        for trunc_len in [63, 60, 48, 32, 16, 8, 4, 1]:
            total_attacks += 1
            token = CapabilityToken(
                subject=base_token.subject,
                epoch=base_token.epoch,
                token_id=base_token.token_id,
                issued_at=base_token.issued_at,
                signature=orig_sig[:trunc_len],
            )
            try:
                authority.validate(token, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] Signature truncated to {trunc_len} chars: ACCEPTED!")
                failed_attacks.append(f"Truncated signature ({trunc_len} chars)")
            except InvalidTokenSignatureError:
                blocked_attacks += 1
                print(f"  [BLOCKED] Signature truncated to {trunc_len} chars: InvalidTokenSignatureError")

        # Signature extension tests
        for ext_suffix in ["a", "0000", "deadbeef" * 8]:
            total_attacks += 1
            token = CapabilityToken(
                subject=base_token.subject,
                epoch=base_token.epoch,
                token_id=base_token.token_id,
                issued_at=base_token.issued_at,
                signature=orig_sig + ext_suffix,
            )
            try:
                authority.validate(token, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] Signature extended by {len(ext_suffix)} chars: ACCEPTED!")
                failed_attacks.append(f"Extended signature (+{len(ext_suffix)} chars)")
            except InvalidTokenSignatureError:
                blocked_attacks += 1
                print(f"  [BLOCKED] Signature extended by {len(ext_suffix)} chars: InvalidTokenSignatureError")

        # Hex casing mutation (HMAC hex is lowercase, test uppercase)
        total_attacks += 1
        token = CapabilityToken(
            subject=base_token.subject,
            epoch=base_token.epoch,
            token_id=base_token.token_id,
            issued_at=base_token.issued_at,
            signature=orig_sig.upper(),
        )
        try:
            authority.validate(token, required_subject="hands:pc.write_file")
            print("  [CRITICAL LEAK] Uppercase signature: ACCEPTED!")
            failed_attacks.append("Uppercase signature")
        except InvalidTokenSignatureError:
            blocked_attacks += 1
            print("  [BLOCKED] Uppercase signature: InvalidTokenSignatureError")

        # Null byte injection in signature
        total_attacks += 1
        token = CapabilityToken(
            subject=base_token.subject,
            epoch=base_token.epoch,
            token_id=base_token.token_id,
            issued_at=base_token.issued_at,
            signature=orig_sig + "\x00",
        )
        try:
            authority.validate(token, required_subject="hands:pc.write_file")
            print("  [CRITICAL LEAK] Null byte in signature: ACCEPTED!")
            failed_attacks.append("Null byte in signature")
        except InvalidTokenSignatureError:
            blocked_attacks += 1
            print("  [BLOCKED] Null byte in signature: InvalidTokenSignatureError")

        # ----------------------------------------------------------------------
        # CATEGORY 5: Payload Tampering & Privilege Escalation Attacks
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 5: Payload Modification & Privilege Escalation Attacks ---")

        # Issue low-privilege token
        low_priv_token = authority.issue("hands:pc.read")

        payload_attacks = [
            ("Elevate subject to hands:pc.write_file", {"subject": "hands:pc.write_file"}),
            ("Elevate subject to hands:pc.bash_exec", {"subject": "hands:pc.bash_exec"}),
            ("Elevate subject to root wildcard '*'", {"subject": "*"}),
            ("Elevate subject to admin", {"subject": "admin"}),
            ("Increment epoch by 1 (future evasion)", {"epoch": low_priv_token.epoch + 1}),
            ("Increment epoch by 100", {"epoch": low_priv_token.epoch + 100}),
            ("Decrement epoch to -1", {"epoch": -1}),
            ("Decrement epoch to -100", {"epoch": -100}),
            ("Swap token_id to attacker string", {"token_id": "attacker-chosen-token-id"}),
            ("Swap token_id to another valid uuid", {"token_id": "00000000000000000000000000000000"}),
            ("Manipulate timestamp: add 10 seconds", {"issued_at": low_priv_token.issued_at + 10.0}),
            ("Manipulate timestamp: subtract 10 seconds", {"issued_at": low_priv_token.issued_at - 10.0}),
            ("Manipulate timestamp precision (+0.000001)", {"issued_at": round(low_priv_token.issued_at + 0.000001, 6)}),
            ("Manipulate timestamp to 0.0", {"issued_at": 0.0}),
        ]

        for desc, overrides in payload_attacks:
            total_attacks += 1
            token = CapabilityToken(
                subject=overrides.get("subject", low_priv_token.subject),
                epoch=overrides.get("epoch", low_priv_token.epoch),
                token_id=overrides.get("token_id", low_priv_token.token_id),
                issued_at=overrides.get("issued_at", low_priv_token.issued_at),
                signature=low_priv_token.signature,
            )
            try:
                # Validate against target subject
                target_sub = overrides.get("subject", low_priv_token.subject)
                authority.validate(token, required_subject=target_sub)
                print(f"  [CRITICAL LEAK] {desc}: ACCEPTED!")
                failed_attacks.append(desc)
            except InvalidTokenSignatureError:
                blocked_attacks += 1
                print(f"  [BLOCKED] {desc}: InvalidTokenSignatureError")
            except Exception as e:
                print(f"  [ERROR] {desc}: {type(e).__name__}: {e}")
                failed_attacks.append(f"{desc} ({e})")

        # Test epoch decrement on advanced authority (epoch = 5)
        with tempfile.TemporaryDirectory() as tmp_adv:
            adv_auth = CapabilityAuthority(state_path=Path(tmp_adv) / "caps.json", secret=TARGET_SECRET)
            for _ in range(5):
                adv_auth.restore()
            adv_token = adv_auth.issue("hands:pc.read")
            assert adv_token.epoch == 5, f"Expected epoch 5, got {adv_token.epoch}"

            for target_epoch in [4, 3, 2, 1, 0, -1]:
                total_attacks += 1
                dec_desc = f"Decrement epoch from 5 to {target_epoch}"
                tampered_dec = CapabilityToken(
                    subject=adv_token.subject,
                    epoch=target_epoch,
                    token_id=adv_token.token_id,
                    issued_at=adv_token.issued_at,
                    signature=adv_token.signature,
                )
                try:
                    adv_auth.validate(tampered_dec, required_subject="hands:pc.read")
                    print(f"  [CRITICAL LEAK] {dec_desc}: ACCEPTED!")
                    failed_attacks.append(dec_desc)
                except InvalidTokenSignatureError:
                    blocked_attacks += 1
                    print(f"  [BLOCKED] {dec_desc}: InvalidTokenSignatureError")

        # Delimiter confusion attempt:
        # Can attacker provide subject with colons to mimic canonical fields?
        total_attacks += 1
        confused_subject = "hands:pc.read:0:tid:100.000000"
        crafted_sig = compute_token_signature(TARGET_SECRET, "hands:pc.read", 0, "tid", 100.0)
        crafted_token = CapabilityToken(
            subject=confused_subject,
            epoch=0,
            token_id="tid2",
            issued_at=100.0,
            signature=crafted_sig,
        )
        try:
            authority.validate(crafted_token, required_subject=confused_subject)
            print("  [CRITICAL LEAK] Canonical delimiter confusion attack: ACCEPTED!")
            failed_attacks.append("Canonical delimiter confusion")
        except InvalidTokenSignatureError:
            blocked_attacks += 1
            print("  [BLOCKED] Canonical delimiter confusion attack: InvalidTokenSignatureError")

        # ----------------------------------------------------------------------
        # CATEGORY 6: Submitting Legacy Tokens Without Signature
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 6: Legacy Unsigned / Absent Signature Ingestion ---")

        legacy_cases = [
            ("Legacy dataclass with empty signature string", CapabilityToken("hands:pc.write_file", 0, "leg-1", time.time(), "")),
            ("Legacy dataclass with whitespace signature", CapabilityToken("hands:pc.write_file", 0, "leg-2", time.time(), "   ")),
            ("Legacy dataclass with None signature", CapabilityToken("hands:pc.write_file", 0, "leg-3", time.time(), None)),  # type: ignore
            ("Legacy dict without signature key", parse_capability_token({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "leg-dict-1", "issued_at": time.time()
            })),
            ("Legacy dict with signature=None", parse_capability_token({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "leg-dict-2", "issued_at": time.time(), "signature": None
            })),
            ("Legacy dict with signature=''", parse_capability_token({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "leg-dict-3", "issued_at": time.time(), "signature": ""
            })),
            ("Legacy JSON str without signature key", parse_capability_token(json.dumps({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "leg-json-1", "issued_at": time.time()
            }))),
            ("Legacy JSON str with signature=null", parse_capability_token(json.dumps({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "leg-json-2", "issued_at": time.time(), "signature": None
            }))),
            ("Legacy JSON str with signature=''", parse_capability_token(json.dumps({
                "subject": "hands:pc.write_file", "epoch": 0, "token_id": "leg-json-3", "issued_at": time.time(), "signature": ""
            }))),
        ]

        for desc, leg_tok in legacy_cases:
            total_attacks += 1
            try:
                authority.validate(leg_tok, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] {desc}: ACCEPTED!")
                failed_attacks.append(desc)
            except InvalidTokenSignatureError as err:
                blocked_attacks += 1
                print(f"  [BLOCKED] {desc}: InvalidTokenSignatureError: {err}")
            except Exception as e:
                print(f"  [ERROR] {desc}: {type(e).__name__}: {e}")
                failed_attacks.append(f"{desc} ({e})")

        # ----------------------------------------------------------------------
        # CATEGORY 7: High-Volume Adversarial Fuzzing Stress Test (500 tokens)
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 7: High-Volume Adversarial Fuzzing (500 Iterations) ---")

        fuzz_count = 500
        fuzz_blocked = 0
        fuzz_leaked = 0

        subjects = ["hands:pc.read", "hands:pc.write_file", "hands:pc.bash_exec", "admin:all", "root", "", " " * 5]
        
        for i in range(fuzz_count):
            total_attacks += 1
            mode = i % 5
            sub = _PROBE_RNG.choice(subjects)
            ep = _PROBE_RNG.randint(-5, 100)
            tid = "".join(_PROBE_RNG.choices(string.ascii_letters + string.digits, k=_PROBE_RNG.randint(0, 36)))
            iat = _PROBE_RNG.uniform(0, 2000000000)

            if mode == 0:
                # Completely random signature length and chars
                sig = "".join(_PROBE_RNG.choices(string.printable, k=_PROBE_RNG.randint(0, 128)))
            elif mode == 1:
                # Random hex signature
                sig = "".join(_PROBE_RNG.choices(string.hexdigits.lower(), k=64))
            elif mode == 2:
                # Empty or whitespace
                sig = _PROBE_RNG.choice(["", " ", "   ", "\t", "\n"])
            elif mode == 3:
                # Signed with a random random secret
                rnd_sec = "".join(_PROBE_RNG.choices(string.ascii_letters, k=32)).encode()
                sig = compute_token_signature(rnd_sec, sub, ep, tid, iat)
            else:
                # Legitimate sig with single mutation
                legit_sig = compute_token_signature(TARGET_SECRET, sub, ep, tid, iat)
                mut_idx = _PROBE_RNG.randint(0, len(legit_sig) - 1)
                sig = legit_sig[:mut_idx] + ("x" if legit_sig[mut_idx] != "x" else "y") + legit_sig[mut_idx + 1:]

            fuzz_tok = CapabilityToken(subject=sub, epoch=ep, token_id=tid, issued_at=iat, signature=sig)
            try:
                authority.validate(fuzz_tok, required_subject=sub)
                fuzz_leaked += 1
                failed_attacks.append(f"Fuzz iteration #{i} (mode {mode})")
            except InvalidTokenSignatureError:
                fuzz_blocked += 1
                blocked_attacks += 1

        # ----------------------------------------------------------------------
        # CATEGORY 8: Boundary Type Mutations (Non-string signatures & types)
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 8: Boundary Type & Signature Object Mutations ---")

        type_mutations = [
            ("Integer signature (123456789)", 123456789),
            ("Boolean False signature", False),
            ("Boolean True signature", True),
            ("Float signature (3.14159)", 3.14159),
            ("Bytes signature (b'deadbeef'*8)", b"deadbeef" * 8),
            ("Empty list signature", []),
            ("Dictionary signature", {"sig": "bad"}),
        ]

        for desc, sig_val in type_mutations:
            total_attacks += 1
            tok = CapabilityToken("hands:pc.write_file", 0, "type-mut", time.time(), sig_val)  # type: ignore
            try:
                authority.validate(tok, required_subject="hands:pc.write_file")
                print(f"  [CRITICAL LEAK] {desc}: ACCEPTED!")
                failed_attacks.append(desc)
            except InvalidTokenSignatureError:
                blocked_attacks += 1
                print(f"  [BLOCKED] {desc}: InvalidTokenSignatureError")
            except Exception as e:
                print(f"  [ERROR] {desc}: {type(e).__name__}: {e}")
                failed_attacks.append(f"{desc} ({e})")

        # Non-token objects passed to validate() must return False fail-closed
        non_tokens = [
            ("None object", None),
            ("Generic object()", object()),
            ("Plain string", "not-a-token"),
            ("Integer", 12345),
            ("Plain dict", {"subject": "hands:pc.write_file", "epoch": 0}),
        ]
        for desc, obj in non_tokens:
            total_attacks += 1
            res = authority.validate(obj)  # type: ignore
            if res is False:
                blocked_attacks += 1
                print(f"  [BLOCKED] {desc}: safely rejected (returned False)")
            else:
                print(f"  [CRITICAL LEAK] {desc}: returned {res}!")
                failed_attacks.append(desc)

        # ----------------------------------------------------------------------
        # CATEGORY 9: Unicode, Emojis, and Special Characters in Subject
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 9: Unicode, Emojis, and Special Characters in Subject ---")

        unicode_tests = [
            ("Vietnamese subject", "hands:pc.tiếng_việt_đọc", "hands:pc.tiếng_việt_ghi"),
            ("Emoji subject", "hands:pc.🛡️", "hands:pc.💀"),
            ("Path traversal in subject", "hands:pc.read/../../etc/passwd", "hands:pc.write/../../etc/passwd"),
            ("Newline in subject", "hands:pc.read\nINJECT", "hands:pc.write\nINJECT"),
            ("Null byte in subject", "hands:pc.read\x00extra", "hands:pc.write\x00extra"),
        ]

        for desc, valid_sub, tampered_sub in unicode_tests:
            total_attacks += 1
            u_tok = authority.issue(valid_sub)
            assert authority.validate(u_tok, required_subject=valid_sub) is True, f"Failed baseline for {desc}"

            tampered_u_tok = CapabilityToken(
                subject=tampered_sub,
                epoch=u_tok.epoch,
                token_id=u_tok.token_id,
                issued_at=u_tok.issued_at,
                signature=u_tok.signature,
            )
            try:
                authority.validate(tampered_u_tok, required_subject=tampered_sub)
                print(f"  [CRITICAL LEAK] Tampered {desc}: ACCEPTED!")
                failed_attacks.append(f"Tampered {desc}")
            except InvalidTokenSignatureError:
                blocked_attacks += 1
                print(f"  [BLOCKED] Tampered {desc}: InvalidTokenSignatureError")

        # ----------------------------------------------------------------------
        # CATEGORY 10: Authority State File Tampering / Revocation Invariant
        # ----------------------------------------------------------------------
        print("\n--- CATEGORY 10: State File Tampering & Revocation Invariant ---")

        state_token = authority.issue("hands:pc.status")
        assert authority.validate(state_token, required_subject="hands:pc.status") is True

        # Sub-test 10.1: Revocation invalidates valid token fail-closed (returns False)
        total_attacks += 1
        authority.revoke(reason="adversarial drill", actor="challenger_1")
        if authority.validate(state_token, required_subject="hands:pc.status") is False:
            blocked_attacks += 1
            print("  [BLOCKED] Valid token rejected after revocation (returned False)")
        else:
            print("  [CRITICAL LEAK] Valid token accepted after revocation!")
            failed_attacks.append("Revocation bypass")

        # Sub-test 10.2: Corrupt state file causes fail-closed rejection
        total_attacks += 1
        authority.restore(reason="restored for corruption test", actor="challenger_1")
        fresh_token = authority.issue("hands:pc.status")
        assert authority.validate(fresh_token, required_subject="hands:pc.status") is True

        # Corrupt the state file on disk
        state_path.write_text("CORRUPTED_NOT_JSON!!!", encoding="utf-8")
        if authority.validate(fresh_token, required_subject="hands:pc.status") is False:
            blocked_attacks += 1
            print("  [BLOCKED] Corrupt state file rejected fail-closed (returned False)")
        else:
            print("  [CRITICAL LEAK] Corrupt state file accepted token!")
            failed_attacks.append("Corrupt state file bypass")

    print("\n" + "=" * 80)
    print("PENETRATION TEST SUMMARY")
    print(f"Total Adversarial Attacks Attempted: {total_attacks}")
    print(f"Successfully Blocked Fail-Closed:   {blocked_attacks}")
    print(f"Bypasses / Leaks Detected:          {len(failed_attacks)}")
    print(f"Block Rate:                          {(blocked_attacks / total_attacks) * 100:.2f}%")
    print("=" * 80)

    if len(failed_attacks) == 0 and blocked_attacks == total_attacks:
        print("\nFINAL PENETRATION VERDICT: APPROVE (100% of attacks blocked fail-closed)")
        return 0
    else:
        print(f"\nFINAL PENETRATION VERDICT: REQUEST_CHANGES ({len(failed_attacks)} attacks succeeded)")
        for fa in failed_attacks[:20]:
            print(f"  - {fa}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
