from __future__ import annotations

from pathlib import Path

path = Path(str(Path(__file__).resolve().parent.parent / "scp" / "api_server.py"))
text = path.read_text(encoding="utf-8")
needle = "from scp.api.routes.hands_routes import router as hands_router\n app.include_router(hands_router)"
if needle in text:
    replacement = needle + "\n from scp.api.routes.batch_benchmark_routes import router as batch_benchmark_router\n app.include_router(batch_benchmark_router)"
    text = text.replace(needle, replacement, 1)
else:
    alt = "from scp.api.routes.hands_routes import router as hands_router\n    app.include_router(hands_router)"
    if alt in text:
        replacement = alt + "\n    from scp.api.routes.batch_benchmark_routes import router as batch_benchmark_router\n    app.include_router(batch_benchmark_router)"
        text = text.replace(alt, replacement, 1)
    elif "batch_benchmark_routes" in text:
        print("batch router already registered")
        raise SystemExit(0)
    else:
        raise SystemExit("Hands router registration block not found")
path.write_text(text, encoding="utf-8")
print("registered batch benchmark router")
