# -*- coding: utf-8 -*-
"""Golden-benchmark runner: evaluate an OpenAI-compatible chat API on standard LLM benchmarks.

Usage examples:
    python run_golden.py --suite mmlu --limit 50 \
        --endpoint https://api.openai.com/v1 --api-key sk-... --model gpt-4o-mini \
        --label plain --out results_plain.json

    python run_golden.py --suite gsm8k --limit 100 \
        --endpoint http://localhost:8000/v1 --api-key EMPTY --model my-model \
        --label scp --out results_scp.json

Notes:
- Stdlib + repo-internal scp.security only. No third-party installs required.
- Suites: mmlu | gsm8k | hellaswag | truthfulqa (JSONL files under <script_dir>/<suite>/).
- Scoring:
    * mmlu / hellaswag / truthfulqa: extract the chosen letter (A-D) from the reply.
    * gsm8k: extract the LAST number in the reply and compare numerically with gold.
- Rate limiting: 1 request/second by default (tune with --delay).
- Retries: 3 retries on HTTP 429 / 5xx / network errors with backoff 5s, 15s, 30s.
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scp.security.url_safety import safe_urlopen  # noqa: E402

SUITES = ("mmlu", "gsm8k", "hellaswag", "truthfulqa")

RETRY_BACKOFF = [5, 15, 30]  # seconds
TRANSIENT_HTTP = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_items(suite, limit):
    folder = os.path.join(SCRIPT_DIR, suite)
    files = sorted(glob.glob(os.path.join(folder, "*.jsonl")))
    if not files:
        raise FileNotFoundError(f"no .jsonl dataset found in {folder}; run download_datasets.py first")
    path = files[0]
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
            if limit and len(items) >= limit:
                break
    return path, items


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def format_choices(choices):
    return "\n".join(f"{chr(ord('A') + i)}. {c}" for i, c in enumerate(choices))


def build_prompt(suite, item):
    if suite in ("mmlu", "hellaswag", "truthfulqa"):
        if suite == "mmlu":
            head = ("The following is a multiple choice question (answered by experts). "
                    "Respond with ONLY the letter of the correct option.")
        elif suite == "hellaswag":
            head = ("Pick the most sensible continuation of the context. "
                    "Respond with ONLY the letter of the correct option.")
        else:  # truthfulqa
            head = ("Pick the statement that is factually true (avoid common misconceptions). "
                    "Respond with ONLY the letter of the correct option.")
        return (f"{head}\n\nQuestion: {item['question']}\n\n"
                f"{format_choices(item['choices'])}\n\nAnswer letter:")
    # gsm8k
    return ("Solve the following grade-school math problem step by step. "
            "End your reply with a single line in the format: Answer: <number>\n\n"
            f"Problem: {item['question']}")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def normalize_number(s):
    s = str(s).strip().replace(",", "").replace("$", "").rstrip(".")
    try:
        return float(s)
    except ValueError:
        return None


def extract_choice_letter(text, num_choices=4):
    """Extract the selected option letter (A..D) from a model reply."""
    if not text:
        return None
    t = text.strip()
    valid = [chr(ord("A") + i) for i in range(num_choices)]

    # 1) The whole reply is (almost) just the letter, e.g. "B", "B.", "(C)"
    m = re.fullmatch(r"[\(\[]?\s*([A-Da-d])\s*[\)\].:]*", t)
    if m:
        return m.group(1).upper()

    # 2) "answer is: C" / "Answer: B" / "Dap an: A" (last such match wins)
    matches = re.findall(
        r"(?:answer|answers|dap an|đáp án|option|choice|lựa chọn)\D{0,12}?([A-Da-d])\b",
        t, flags=re.IGNORECASE)
    if matches:
        cand = matches[-1].upper()
        if cand in valid:
            return cand

    # 3) Letter followed by punctuation, e.g. "C)" or "B." (last match wins)
    matches = re.findall(r"\b([A-D])[\)\].:]", t)
    if matches:
        return matches[-1]

    # 4) Last standalone uppercase letter token
    matches = re.findall(r"\b([A-D])\b", t)
    if matches:
        return matches[-1]
    return None


def extract_last_number(text):
    if not text:
        return None
    nums = re.findall(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not nums:
        return None
    return normalize_number(nums[-1])


def score_response(suite, item, text):
    """Return (pred, correct). pred may be None; correct may be False on parse failure."""
    if suite == "gsm8k":
        gold = normalize_number(item["gold"])
        pred = extract_last_number(text)
        if pred is None or gold is None:
            return (None, False) if pred is None else (pred, False)
        return pred, abs(pred - gold) < 1e-6
    # choice-based suites
    gold = item["gold"]
    pred = extract_choice_letter(text)
    return pred, (pred is not None and pred == gold)


# ---------------------------------------------------------------------------
# API client (OpenAI chat-completions compatible)
# ---------------------------------------------------------------------------

def completions_url(endpoint):
    ep = endpoint.strip().rstrip("/")
    if ep.endswith("/chat/completions"):
        return ep
    return ep + "/chat/completions"


def call_api(endpoint, api_key, model, prompt, timeout=180):
    """POST one chat completion. Returns (text, latency_ms). Retries on 429/5xx/network errors."""
    url = completions_url(endpoint)
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 512,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    last_err = None
    for attempt in range(len(RETRY_BACKOFF) + 1):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            # [SSRF gate] B310: the endpoint is caller-supplied (CLI --endpoint),
            # so the fetch must go through safe_urlopen. allow_internal=True is
            # intentional: the documented usage includes loopback SCP endpoints
            # (e.g. http://localhost:8000/v1) chosen explicitly by the operator.
            with safe_urlopen(req, timeout=timeout, allow_internal=True) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            ms = (time.perf_counter() - t0) * 1000.0
            text = body["choices"][0]["message"]["content"] or ""
            return text, ms
        except urllib.error.HTTPError as e:
            ms = (time.perf_counter() - t0) * 1000.0
            last_err = f"HTTP {e.code}: {e.read(200)!r}"
            if e.code in TRANSIENT_HTTP and attempt < len(RETRY_BACKOFF):
                time.sleep(RETRY_BACKOFF[attempt])
                continue
            raise RuntimeError(last_err)
        except Exception as e:  # network errors, timeouts, bad JSON
            last_err = f"{type(e).__name__}: {e}"
            if attempt < len(RETRY_BACKOFF):
                time.sleep(RETRY_BACKOFF[attempt])
                continue
            raise RuntimeError(last_err)
    raise RuntimeError(last_err or "unreachable")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _jailed_results_path(out):
    """Resolve the results output path and jail it under the working directory.

    Relative --out values historically resolved against cwd; any path that
    resolves outside cwd is refused fail-closed (path-traversal guard).
    """
    base = Path.cwd().resolve()
    candidate = Path(out)
    resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
    if resolved != base and base not in resolved.parents:
        raise ValueError(f"--out path escapes working directory: {out}")
    return str(resolved)


def main(argv=None):
    p = argparse.ArgumentParser(description="Golden LLM benchmark runner (stdlib only)")
    p.add_argument("--suite", required=True, choices=SUITES)
    p.add_argument("--limit", type=int, default=0, help="max items to run (0 = all in file)")
    p.add_argument("--endpoint", required=True, help="base URL, e.g. https://api.openai.com/v1")
    p.add_argument("--api-key", default="", help="API key (Bearer)")
    p.add_argument("--model", required=True)
    p.add_argument("--out", default="results.json", help="output results.json path")
    p.add_argument("--label", default="plain", help="run label, e.g. 'scp' or 'plain'")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests (rate limit)")
    args = p.parse_args(argv)

    dataset_path, items = load_items(args.suite, args.limit)
    n = len(items)
    print(f"[run] suite={args.suite} label={args.label} model={args.model} n={n}")
    print(f"[run] dataset={dataset_path}")
    print(f"[run] endpoint={args.endpoint} delay={args.delay}s")

    per_item = []
    latencies = []
    correct_count = 0
    for idx, item in enumerate(items):
        prompt = build_prompt(args.suite, item)
        err = None
        try:
            text, ms = call_api(args.endpoint, args.api_key, args.model, prompt)
            latencies.append(ms)
        except Exception as e:  # noqa: BLE001 - record failure and continue
            text, ms = "", None
            err = str(e)
        pred, ok = score_response(args.suite, item, text)
        correct_count += int(ok)
        entry = {"id": item["id"], "gold": item["gold"], "pred": pred,
                 "correct": bool(ok), "ms": ms}
        if err:
            entry["error"] = err
        per_item.append(entry)
        status = "OK " if ok else ("ERR" if err else "miss")
        print(f"  [{idx + 1}/{n}] {item['id']} gold={item['gold']} pred={pred} {status}")
        if err:
            print(f"        {err[:160]}")
        if idx < n - 1 and args.delay > 0:
            time.sleep(args.delay)

    acc = correct_count / n if n else 0.0
    lat_avg = sum(latencies) / len(latencies) if latencies else 0.0
    results = {
        "suite": args.suite,
        "label": args.label,
        "model": args.model,
        "endpoint": args.endpoint,
        "n": n,
        "correct": correct_count,
        "accuracy": round(acc, 4),
        "latency_avg_ms": round(lat_avg, 1),
        "per_item": per_item,
    }
    out_path = _jailed_results_path(args.out)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"[done] accuracy={acc:.2%} ({correct_count}/{n}) latency_avg={lat_avg:.0f}ms -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
