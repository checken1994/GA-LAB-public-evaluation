from pathlib import Path
import json
import urllib.request
import os

def _contained_in_repo(p: str) -> bool:
    """[SEC-S4] Containment guard: every file this script touches must resolve
    inside the repository benchmark tree (paths are __file__-derived; this
    blocks traversal if the derivation is ever made configurable)."""
    return Path(p).resolve().is_relative_to(Path(__file__).resolve().parent.parent)

def download_gsm8k_sample():
    print("Downloading GSM8K (Middle School Math) - Global TOP 1% Standard...")
    url = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"

    out_path = str(Path(__file__).resolve().parent / "benchmark" / "gsm8k_test_top1.jsonl")
    try:
        urllib.request.urlretrieve(url, out_path)
        print(f"Success! Saved to: {out_path}")

        # Extract 10 questions for a quick smoke test
        with open(out_path, "r", encoding="utf-8") as f:
            lines = [next(f) for _ in range(10)]

        sample_path = str(Path(__file__).resolve().parent / "benchmark" / "gsm8k_sample_10.jsonl")
        # [SEC-S4] Containment check before writing
        if not (_contained_in_repo(out_path) and _contained_in_repo(sample_path)):
            raise SystemExit("SEC-S4: derived path escapes repository benchmark tree")
        with Path(sample_path).open("w", encoding="utf-8") as f_out:
            f_out.writelines(lines)
        print(f"Created 10-question sample file: {sample_path}")
        
    except Exception as e:
        print(f"Error downloading GSM8K: {e}")

if __name__ == "__main__":
    download_gsm8k_sample()
