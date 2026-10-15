#!/usr/bin/env python
"""SCP Typed Evaluation CLI — TypeSafe SystemOne compatible client.

Allows LLMs, agents, subagents, and automated workflows to evaluate state/code/plans
against structured questions (noul/choice/score) using the SCP Independent Verifier API.

Usage:
    # Run built-in demo:
    python tools/scp_eval.py --demo

    # Direct evaluation with noul, choice, and score:
    python tools/scp_eval.py --state "Thủ đô của Việt Nam là Hà Nội." \\
        --noul is_accurate="Is this statement factually accurate?" \\
        --choice verdict=PASS|FAIL|UNKNOWN \\
        --score confidence_level="low|medium|high|certain"

    # Evaluate a file (diff, plan, log):
    python tools/scp_eval.py --file path/to/diff.patch \\
        --noul is_safe="Does this diff avoid breaking existing contracts?" \\
        --choice risk_level=low|medium|high|critical

Keys:
    Reads SCP_API_KEY, SCP_AUTH_TOKEN_SECRET, or SCP_ADMIN_KEY from env or repo .env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = os.environ.get("SCP_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_MODEL = "scp-eval-latest"
DEFAULT_TIMEOUT = 60.0
REPO_ROOT = Path(__file__).resolve().parents[1]

# [SEC-S6] SSRF guard: the outbound eval POST is routed through the repo's
# validated fetch choke point (scheme allowlist + egress policy + pinned IP).
sys.path.insert(0, str(REPO_ROOT))
from scp.security.url_safety import safe_urlopen


def load_api_key() -> str:
    """Read API key from env or .env file."""
    for key_name in ("SCP_API_KEY", "SCP_AUTH_TOKEN_SECRET", "SCP_ADMIN_KEY", "SCP_JWT_SECRET"):
        val = os.environ.get(key_name, "").strip()
        if val:
            return val
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k in ("SCP_API_KEY", "SCP_AUTH_TOKEN_SECRET", "SCP_ADMIN_KEY") and v:
                return v
    return ""


def build_questions(args: argparse.Namespace) -> dict:
    questions: dict = {}
    for spec in args.noul or []:
        name, _, instructions = spec.partition("=")
        if not name or not instructions:
            raise SystemExit(f"--noul requires format name='question': {spec!r}")
        questions[name] = {"type": "noul", "instructions": instructions}
    for spec in args.choice or []:
        name, _, options = spec.partition("=")
        opts = [o for o in options.split("|") if o]
        if not name or len(opts) < 2:
            raise SystemExit(f"--choice requires format name=opt1|opt2|...: {spec!r}")
        questions[name] = {
            "type": "choice",
            "instructions": "Choose one option.",
            "criteria": {opt: None for opt in opts},
        }
    for spec in args.score or []:
        name, _, levels = spec.partition("=")
        lvls = [l for l in levels.split("|") if l]
        if not name or len(lvls) < 2:
            raise SystemExit(f"--score requires format name=level1|level2|...: {spec!r}")
        questions[name] = {"type": "score", "instructions": "Rate the level.", "criteria": lvls}
    if not questions:
        raise SystemExit("Need at least one question: --noul / --choice / --score (or --demo).")
    return questions


def demo_payload() -> dict:
    return {
        "state": (
            "SCP is a self-correcting agent platform implementing Zero-Trust, "
            "deterministic postcondition verifiers, and multi-LLM consensus."
        ),
        "model": DEFAULT_MODEL,
        "questions": {
            "is_valid_architecture": {
                "type": "noul",
                "instructions": "Does this state describe an active verifiable architecture?",
            },
            "risk_assessment": {
                "type": "choice",
                "instructions": "Assess the risk level of this system state.",
                "criteria": {"low": None, "medium": None, "high": None, "critical": None},
            },
            "stability_score": {
                "type": "score",
                "instructions": "Score the overall stability.",
                "criteria": ["experimental", "beta", "production_candidate", "proven"],
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="SCP Typed Evaluation CLI (TypeSafe-compatible)")
    parser.add_argument("--state", help="State / content to evaluate")
    parser.add_argument("--file", help="Path to file to evaluate (diff, code, plan, log)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--noul", action="append", metavar="NAME='QUESTION'")
    parser.add_argument("--choice", action="append", metavar="NAME=opt1|opt2|...")
    parser.add_argument("--score", action="append", metavar="NAME=level1|level2|...")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--demo", action="store_true", help="Run quick demo example")
    args = parser.parse_args()

    state_text = args.state or ""
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            raise SystemExit(f"File not found: {args.file}")
        state_text = file_path.read_text(encoding="utf-8", errors="replace")

    payload = demo_payload() if args.demo else {
        "state": state_text,
        "model": args.model,
        "questions": build_questions(args),
    }
    if not args.demo and not payload["state"]:
        raise SystemExit("Missing --state or --file (or use --demo).")

    api_key = load_api_key()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{args.base_url.rstrip('/')}/v1/systemone"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        # Eval client targets the configured SCP gateway (loopback default),
        # so internal hosts are explicitly allowed while scheme, egress
        # policy, IP pinning and redirects stay validated.
        with safe_urlopen(req, timeout=args.timeout, allow_internal=True) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
    except Exception as exc:
        print(f"Transport error contacting {url}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if status in (401, 403):
        print(f"HTTP {status} — auth failed (check SCP_API_KEY/SCP_ADMIN_KEY in .env)", file=sys.stderr)
        return 2
    if status == 422:
        print(f"HTTP 422 Unprocessable Entity — body: {body[:500]}", file=sys.stderr)
        return 3
    if status >= 400:
        print(f"HTTP {status} — body: {body[:500]}", file=sys.stderr)
        return 1

    print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
