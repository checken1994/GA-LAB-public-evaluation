# -*- coding: utf-8 -*-
"""Download golden-benchmark samples from HuggingFace datasets-server API.

Stdlib + repo-internal scp.security only (no pip installs). Writes UTF-8 JSONL files:
    {"id", "question", "choices"/"answer", "gold"}

Suites:
    mmlu       -> cais/mmlu, config "all", split test (150 rows)
    gsm8k      -> openai/gsm8k, config "main", split test (150 rows)
    hellaswag  -> Rowan/hellaswag, config "default", split validation (150 rows)
    truthfulqa -> truthfulqa/truthful_qa, config "multiple_choice", split validation (150 rows)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scp.security.url_safety import safe_urlopen  # noqa: E402

BASE = "https://datasets-server.huggingface.co/rows"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PAGE = 100  # datasets-server caps length at 100 per request

SUITES = {
    "mmlu": dict(repo="cais/mmlu", config="all", split="test", n=150),
    "gsm8k": dict(repo="openai/gsm8k", config="main", split="test", n=150),
    "hellaswag": dict(repo="Rowan/hellaswag", config="default", split="validation", n=150),
    "truthfulqa": dict(repo="truthfulqa/truthful_qa", config="multiple_choice", split="validation", n=150),
}


def fetch_rows(repo, config, split, offset, length, retries=3):
    q = urllib.parse.urlencode({
        "dataset": repo, "config": config, "split": split,
        "offset": offset, "length": length,
    })
    url = f"{BASE}?{q}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "golden-bench-downloader/1.0"})
            # [SSRF gate] B310: caller-visible URL goes through safe_urlopen so
            # scheme/egress/SSRF validation applies (BASE is pinned to the
            # HuggingFace datasets-server; internal IPs are not needed here).
            with safe_urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("rows") is None:
                raise RuntimeError(f"no 'rows' in response: {str(data)[:300]}")
            return [r["row"] for r in data["rows"]]
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"fetch failed for {url}: {last_err}")


def conv_mmlu(i, row):
    gold_letter = chr(ord("A") + int(row["answer"]))
    return {"id": f"mmlu-{i:04d}", "question": row["question"],
            "choices": [str(c) for c in row["choices"]], "gold": gold_letter,
            "subject": row.get("subject", "")}


def conv_gsm8k(i, row):
    ans = row["answer"]
    gold = ans.split("####")[-1].strip().replace(",", "")
    return {"id": f"gsm8k-{i:04d}", "question": row["question"],
            "answer": ans, "gold": gold}


def conv_hellaswag(i, row):
    label = row.get("label", "")
    gold = chr(ord("A") + int(label)) if str(label).strip() != "" else None
    ctx = (row.get("ctx", "") or "").strip()
    act = (row.get("activity_label", "") or "").strip()
    q = (act + ": " + ctx) if act else ctx
    return {"id": f"hellaswag-{i:04d}", "question": q,
            "choices": [str(e) for e in row["endings"]], "gold": gold}


def conv_truthfulqa(i, row):
    ch = row["mc1_targets"]["choices"]
    labels = row["mc1_targets"]["labels"]
    gold_idx = next((k for k, v in enumerate(labels) if int(v) == 1), None)
    gold = chr(ord("A") + gold_idx) if gold_idx is not None else None
    return {"id": f"truthfulqa-{i:04d}", "question": row["question"],
            "choices": [str(c) for c in ch], "gold": gold}


CONV = {"mmlu": conv_mmlu, "gsm8k": conv_gsm8k,
        "hellaswag": conv_hellaswag, "truthfulqa": conv_truthfulqa}


def _jailed_dataset_path(name, split, n):
    """Resolve the dataset output path and jail it under OUT_DIR (fail-closed).

    The suite name is a closed allowlist (SUITES keys) and the final path must
    resolve inside OUT_DIR; anything else is refused (path-traversal guard).
    """
    if name not in SUITES:
        raise ValueError(f"unknown dataset suite: {name}")
    out_path = Path(OUT_DIR) / name / f"{split}_{n}.jsonl"
    base = Path(OUT_DIR).resolve()
    resolved = out_path.resolve()
    if resolved != base and base not in resolved.parents:
        raise ValueError(f"dataset path escapes output dir: {out_path}")
    return resolved


def download_suite(name, spec):
    rows, offset = [], 0
    while len(rows) < spec["n"]:
        chunk = fetch_rows(spec["repo"], spec["config"], spec["split"], offset, PAGE)
        if not chunk:
            break
        rows.extend(chunk)
        offset += len(chunk)
        time.sleep(1.0)  # be polite to the API
    rows = rows[: spec["n"]]
    out_path = _jailed_dataset_path(name, spec["split"], len(rows))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with out_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(rows):
            item = CONV[name](i, r)
            if item["gold"] is None:
                continue  # skip unlabeled rows
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            kept += 1
    return str(out_path), kept


def verify(path):
    size = os.path.getsize(path)
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    sample = json.loads(lines[0])
    s = json.dumps(sample, ensure_ascii=False)
    print(f"VERIFY {path}")
    print(f"  lines={len(lines)} size={size} bytes")
    print(f"  sample: {s[:260]}")
    return len(lines), size


def main():
    results = {}
    for name, spec in SUITES.items():
        print(f"== downloading {name}: {spec['repo']} [{spec['config']}/{spec['split']}] n={spec['n']}")
        try:
            path, n = download_suite(name, spec)
            lines, size = verify(path)
            results[name] = {"ok": True, "path": path, "rows": lines, "bytes": size}
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}")
            results[name] = {"ok": False, "error": str(e)}
        time.sleep(1.0)
    print("\nSUMMARY " + json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
