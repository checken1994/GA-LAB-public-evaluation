import sys
from pathlib import Path
import shutil
import subprocess

path = Path(str(Path(__file__).resolve().parents[1] / "scp" / "api" / "routes" / "batch_benchmark_routes.py"))
backup = path.with_name(path.name + ".bak-rag-before-patch-20260817")
raw = path.read_text(encoding="utf-8-sig")
if "scp_batch_rag_v1" in raw:
    print("already_patched")
    raise SystemExit(0)
shutil.copy2(path, backup)
old = '''question = str(item.get("question", ""))[:4000]
    payload = {
        "question": question,
        "ai_answer": str(item.get("ai_answer", ""))[:4000],
        "source": "scp_batch_benchmark_v1",
    }'''
new = '''question = str(item.get("question", ""))[:4000]
    contexts = item.get("contexts", [])
    if isinstance(contexts, str):
        contexts = [contexts]
    contexts = [str(value)[:12000] for value in contexts if str(value).strip()]
    retrieved_context = "\\n\\n".join(contexts[:8])
    ground_truth = str(item.get("ground_truth", item.get("expected_answer", "")))[:4000]
    rag_question = question
    if retrieved_context:
        rag_question = (
            "Bạn đang trả lời theo chế độ RAG có kiểm chứng. Chỉ dùng CONTEXT bên dưới. "
            "Nếu context không đủ, trả lời rõ NO_EVIDENCE và không đoán. "
            "Khi trả lời, nêu các chunk_id/evidence nếu có.\\n\\n"
            f"CONTEXT:\\n{retrieved_context}\\n\\nQUESTION:\\n{question}"
        )
    payload = {
        "question": rag_question,
        "ai_answer": str(item.get("ai_answer", ""))[:4000],
        "source": "scp_batch_rag_v1",
        "contexts": contexts,
        "retrieved_context": retrieved_context,
        "ground_truth": ground_truth,
        "rag_enabled": bool(contexts),
    }'''
if old not in raw:
    raise RuntimeError("payload block not found; no changes made")
raw = raw.replace(old, new, 1)
old2 = '''                return {
                    "index": index,
                    "id": item.get("id", index),
                    "question": question,
                    "attempts": attempts,
                    "ok": True,
                    "httpStatus": response.status_code,
                    "response": body,
                    "completedAt": time.time(),
                }'''
new2 = '''                if isinstance(body, dict):
                    body.setdefault("rag_enabled", bool(contexts))
                    body.setdefault("retrieved_context_count", len(contexts))
                    body.setdefault("ground_truth_present", bool(ground_truth))
                return {
                    "index": index,
                    "id": item.get("id", index),
                    "question": question,
                    "attempts": attempts,
                    "ok": True,
                    "httpStatus": response.status_code,
                    "response": body,
                    "retrieved_contexts": contexts,
                    "ground_truth": ground_truth,
                    "completedAt": time.time(),
                }'''
if old2 not in raw:
    raise RuntimeError("response block not found; no changes made")
raw = raw.replace(old2, new2, 1)
path.write_text(raw, encoding="utf-8")
subprocess.run([sys.executable, "-m", "py_compile", str(path)], check=True)
print(f"patched={path}")
print(f"backup={backup}")
