import json
import os
import time

from scp.llm_gateway import chat_sync


def run(task: str) -> dict:
    started = time.perf_counter()
    try:
        answer, provider = chat_sync(
            "Reply with exactly OK. Do not explain.",
            system_prompt="You are a bounded local test provider.",
            task=task,
        )
        return {
            "task": task,
            "status": "PASS" if answer else "EMPTY",
            "answer_len": len(answer or ""),
            "provider": provider,
            "elapsed_sec": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "task": task,
            "status": "EXCEPTION",
            "error_type": type(exc).__name__,
            "error": str(exc)[:240],
            "elapsed_sec": round(time.perf_counter() - started, 3),
        }


print(json.dumps({
    "provider_mode": os.environ.get("SCP_LLM_PROVIDER_MODE"),
    "model_autofix": os.environ.get("OLLAMA_MODEL_AUTOFIX"),
    "model_why": os.environ.get("OLLAMA_MODEL_WHY"),
    "results": [run("autofix"), run("why")],
}, ensure_ascii=True))
