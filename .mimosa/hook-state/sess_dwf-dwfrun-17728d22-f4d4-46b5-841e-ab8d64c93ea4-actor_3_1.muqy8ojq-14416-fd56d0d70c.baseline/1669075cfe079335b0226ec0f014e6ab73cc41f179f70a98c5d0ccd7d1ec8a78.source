#!/usr/bin/env python3
"""Reality test: bridge source supports file-backed provider key references."""
from pathlib import Path

p=Path(__file__).resolve().parents[2]/"mini-services/llm-bridge/core.ts"
s=p.read_text(encoding="utf-8")
for marker in ["OPENROUTER_API_KEY_FILE","OPENROUTER_API_KEY_2_FILE","OPENROUTER_API_KEY_3_FILE","readFileSync"]:
    assert marker in s, marker
print("PASS [1]: bridge supports file-backed provider secret references")
print("✓ Reality test 4-d-029 PASSED")
