"""[F-06 regression 2026-09-25] Boot/shutdown log hygiene in the lifespan.

Runtime audit RUNTIME-AUDIT-20260925-0411 finding F-06 (LOW): the boot log
emitted '[R20-ROOT-FIX-REAL] Yielding NOW │<mojibake> port 8000 binds
immediately' — a triple-mangled UTF-8 separator plus a HARDCODED port 8000
while the server actually bound 8090 (argv override). The shutdown log carried
the same mojibake class in the '[GÄ‚Â  -šÂ§8]' external-trust tag.

Fix under test:
  * the yield message states the hand-off without a port number (the real
    bound port is only known to uvicorn after the lifespan yields, so any
    in-lifespan port text would be a guess);
  * the external-trust lines carry an ASCII tag;
  * every emitted log line covered here is pure ASCII, so no console encoding
    can re-mangle it.
"""
from __future__ import annotations

import inspect

from scp.api_server_parts import lifespan as lifespan_mod


def test_yielding_now_log_line_is_ascii_and_has_no_hardcoded_port():
    source = inspect.getsource(lifespan_mod)
    # Diagnostic intent preserved — the yield hand-off is still announced.
    assert "Yielding NOW" in source
    # Stale hardcoded port claim removed (F-06: printed 8000 while 8090 bound).
    assert "port 8000 binds" not in source
    log_lines = [
        line
        for line in source.splitlines()
        if "Yielding NOW" in line and "logger.info" in line
    ]
    assert len(log_lines) == 1, f"expected exactly one Yielding NOW log call, got {log_lines!r}"
    line = log_lines[0]
    assert line.isascii(), f"boot log line is not ASCII (mojibake risk): {line!r}"
    assert "8000" not in line, f"boot log line hardcodes a port: {line!r}"


def test_external_trust_log_lines_are_ascii_with_clean_tag():
    source = inspect.getsource(lifespan_mod)
    assert "[EXTERNAL-TRUST]" in source
    log_lines = [line for line in source.splitlines() if "[EXTERNAL-TRUST]" in line]
    assert len(log_lines) == 3, f"expected 3 external-trust log calls, got {log_lines!r}"
    for line in log_lines:
        assert line.isascii(), f"shutdown log line is not ASCII (mojibake risk): {line!r}"
    # The old mangled tag must not come back in any emitted line
    assert not any("logger." in line and "Ä‚" in line for line in source.splitlines())
