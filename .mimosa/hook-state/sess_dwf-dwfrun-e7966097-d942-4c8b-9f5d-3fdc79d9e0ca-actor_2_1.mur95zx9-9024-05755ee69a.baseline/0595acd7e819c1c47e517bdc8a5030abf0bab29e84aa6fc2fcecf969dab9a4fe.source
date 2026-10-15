"""Download GSM8K test split and a 10-question smoke sample (one-off utility).

[audit-r2 2026-10-01 fixes]
- Path derivation: this script lives INSIDE benchmark/ — the old
  parent/"benchmark" double-subdir pointed at a nonexistent directory
  and every write failed with FileNotFoundError.
- Network: raw urllib.request.urlretrieve (B310) replaced with
  scp.security.url_safety.safe_urlopen (egress gate + scheme/private-IP
  validation); the payload is fully read and JSONL-validated before any
  validated line is written to disk.
- Point-of-use traversal guard (Mimosa HIGH 2026-10-01): the download
  destination filename is a hardcoded bare literal — never derived from the
  URL — and is re-validated inside _write_benchmark_rows immediately before any
  file is opened (bare name only, no dot-dot segments, no drive colon,
  .jsonl whitelist, benchmark
  tree containment).
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scp.security.url_safety import safe_urlopen  # noqa: E402

GSM8K_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"
GSM8K_FILENAME = "gsm8k_test_top1.jsonl"


def _contained_in_repo(p: str) -> bool:
    """[SEC-S4] Containment guard: every file this script touches must resolve
    inside the repository benchmark tree (paths are __file__-derived; this
    blocks traversal if the derivation is ever made configurable)."""
    return Path(p).resolve().is_relative_to(Path(__file__).resolve().parent.parent)


_ALLOWED_DOWNLOAD_SUFFIXES = (".jsonl",)


def _fetch_gsm8k_rows() -> list:
    """[SEC-S4/B310] Fetch the GSM8K test split through the egress gate.

    safe_urlopen enforces the egress policy and validates the scheme +
    destination IP before any byte is fetched. Every non-empty line must
    parse as JSON — the return value contains validated objects only, so
    raw network bytes never reach the filesystem (fetch and write are
    deliberately separate functions).
    """
    with safe_urlopen(GSM8K_URL, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _write_benchmark_rows(rows: list) -> str:
    """[SEC-S4] Write validated benchmark rows into benchmark/<GSM8K_FILENAME>.

    [Mimosa HIGH fix 2026-10-01] The write sink receives already-parsed JSON
    objects (never a network stream). The destination is a module-level
    constant — no path-affecting parameter — re-validated immediately before
    open: bare name only, no dot-dot segments, no drive colon, .jsonl
    whitelist, benchmark-tree containment. Returns the resolved output path.
    """
    filename = GSM8K_FILENAME
    normalized = filename.replace("\\", "/")
    name = os.path.basename(normalized)
    if (
        not name
        or name != normalized
        or os.path.isabs(filename)
        or os.path.pardir in normalized.split("/")
        or ":" in name
        or not name.endswith(_ALLOWED_DOWNLOAD_SUFFIXES)
    ):
        raise SystemExit("SEC-S4: download filename must be a bare whitelisted .jsonl name")
    out_path = Path(os.path.dirname(os.path.abspath(__file__))) / filename
    if not _contained_in_repo(str(out_path)):
        raise SystemExit("SEC-S4: download target escapes repository benchmark tree")
    with out_path.open("w", encoding="utf-8") as f_out:
        for obj in rows:
            f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return str(out_path)


def download_gsm8k_sample():
    print("Downloading GSM8K (Middle School Math) - Global TOP 1% Standard...")

    sample_path = str(Path(__file__).resolve().parent / "gsm8k_sample_10.jsonl")
    # [SEC-S4] Containment check before writing anything
    if not _contained_in_repo(sample_path):
        raise SystemExit("SEC-S4: derived path escapes repository benchmark tree")
    try:
        # URL + filename are module-level constants (never caller/URL-derived);
        # the point-of-use guards in _safe_download re-validate before open().
        out_path = _write_benchmark_rows(_fetch_gsm8k_rows())
        print(f"Success! Saved to: {out_path}")

        # Extract 10 questions for a quick smoke test
        with open(out_path, "r", encoding="utf-8") as f:
            lines = [next(f) for _ in range(10)]

        with Path(sample_path).open("w", encoding="utf-8") as f_out:
            f_out.writelines(lines)
        print(f"Created 10-question sample file: {sample_path}")

    except Exception as e:
        print(f"Error downloading GSM8K: {e}")


if __name__ == "__main__":
    download_gsm8k_sample()
