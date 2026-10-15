import asyncio
import json
import time
import urllib.request
import sys
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass
import subprocess
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scp.security.jwt_guard import create_access_token
# [AUDIT-20260909 S6a] Mọi request HTTP đi qua safe_urlopen — validate scheme,
# chặn IP nội bộ trừ khi allow_internal (server benchmark chạy trên localhost).
from scp.security.url_safety import safe_urlopen

import urllib.error

BASE_URL = os.environ.get("SCP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

async def run_exam(file_path):
    print(f"--- STARTING EXAM: {file_path} ---")
    
    # 1. Pre-flight check
    try:
        req = urllib.request.Request(f"{BASE_URL}/health", method="GET")  # noqa: S310 — validated by safe_urlopen
        with safe_urlopen(req, timeout=10, allow_internal=True) as response:
            pass
    except Exception as e:
        print("ERROR: SCP Server is not running. Please run `python -m scp` first.")
        return

    # 2. Đọc file đề thi
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    print(f"-> Đã tải {len(lines)} câu hỏi. Đang gọi API server...")
    
    raw_results_file = "raw_results.jsonl"

    # [SEC-S4] Containment: raw results must stay inside the CWD.
    if not Path(raw_results_file).resolve().is_relative_to(Path.cwd().resolve()):
        raise SystemExit(f"rejected unsafe results path: {raw_results_file}")

    # 3. Gửi câu hỏi và lưu raw response
    with Path(raw_results_file).open("w", encoding="utf-8") as out_f:
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            question = data.get("question", "")
            
            body = json.dumps({
                "question": question,
                "session_id": f"benchmark-test-{time.time()}",
                "contexts": [],
                "source": "scp_batch_benchmark_v1"
            }).encode('utf-8')
            
            token = create_access_token({"sub": "benchmark-runner"})
            req = urllib.request.Request(f"{BASE_URL}/ask", data=body, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}, method="POST")
            
            api_response = {}
            try:
                with safe_urlopen(req, timeout=None, allow_internal=True) as response:
                    api_response = json.loads(response.read().decode('utf-8'))
                    print(f"[Câu {i+1}] {question[:50]}... -> XONG")
            except Exception as e:
                print(f"[Câu {i+1}] LỖI KẾT NỐI API: {e}")
                api_response = {"error": str(e)}
                
            # Lưu raw kết quả để grader chấm điểm độc lập
            out_data = {
                "question": question,
                "gold_answer": data.get("gold_answer") or data.get("answer"),
                "api_response": api_response
            }
            out_f.write(json.dumps(out_data, ensure_ascii=False) + "\n")
            
    print(f"\n--- ĐÃ LƯU KẾT QUẢ THÔ VÀO {raw_results_file} ---")
    print("-> Gọi Grader độc lập (DNA #5, DNA #14) để chấm điểm...")
    
    dataset_type = "truthfulqa" if "truthfulqa" in str(file_path).lower() else "gsm8k"
    
    grader_path = os.path.join(os.path.dirname(__file__), "grader.py")
    subprocess.run([sys.executable, grader_path, raw_results_file, "--dataset", dataset_type])

if __name__ == "__main__":
    file_target = sys.argv[1] if len(sys.argv) > 1 else "benchmark/gsm8k_sample_10.jsonl"
    asyncio.run(run_exam(file_target))
