"""Download world gold-standard benchmark datasets (one-off utility).

[audit-r2 2026-10-01 fixes]
- Path derivation: this script lives INSIDE benchmark/ — the old
  parent/"benchmark"/... pointed at a nonexistent double-subdir
  benchmark/benchmark/ and every write failed with FileNotFoundError.
- Network: raw urllib.request.urlretrieve (B310) replaced with
  scp.security.url_safety.safe_urlopen (egress gate + scheme/private-IP
  validation), streamed to disk via shutil.copyfileobj.
"""
import os
import shutil
import sys
import urllib.request
from pathlib import Path

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scp.security.url_safety import safe_urlopen  # noqa: E402

BENCHMARK_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parent.parent


def download_benchmark(name: str, url: str, out_name: str) -> None:
    print(f"Downloading {name} - World Gold Standard...")
    out_path = BENCHMARK_DIR / out_name
    # [SEC-S4] Containment check before writing anything
    if not out_path.resolve().is_relative_to(REPO_ROOT):
        print(f"Error downloading {name}: path escapes repository tree")
        return
    try:
        # [SEC-S4/B310] safe_urlopen enforces the egress policy and validates
        # the scheme + destination IP before any byte is fetched.
        with safe_urlopen(url, timeout=60) as resp, out_path.open("wb") as f_out:
            shutil.copyfileobj(resp, f_out)
        print(f"Success! {name} saved to: {out_path}")
    except Exception as e:
        print(f"Error downloading {name}: {e}")


if __name__ == "__main__":
    # 1. HumanEval (OpenAI) - World standard for Code & OS Sandbox capabilities
    download_benchmark(
        "HumanEval (Code Execution)",
        "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz",
        "HumanEval.jsonl.gz",
    )

    # 2. TruthfulQA - World standard for Anti-Hallucination & Fail-Closed (Perfect for SCP's WhyGate)
    download_benchmark(
        "TruthfulQA (Anti-Hallucination)",
        "https://raw.githubusercontent.com/sylinrl/TruthfulQA/main/TruthfulQA.csv",
        "TruthfulQA_Gold.csv",
    )
