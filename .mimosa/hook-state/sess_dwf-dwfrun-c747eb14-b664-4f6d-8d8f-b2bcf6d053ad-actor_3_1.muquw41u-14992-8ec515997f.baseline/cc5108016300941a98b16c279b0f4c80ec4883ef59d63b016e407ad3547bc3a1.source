import asyncio
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scp.ask_kernel_adapter import AskKernelAdapter
from scp.task_kernel import TaskKernel

class MockRequest:
    def __init__(self, q):
        self.question = q
        self.contexts = []
        self.retrieved_context = ""
        self.session_id = "test-session"
        
async def mock_handler(req, request):
    return {"final_answer": "42"}

async def run():
    db_path = "data/benchmark_test_kernel.db"
    trace_path = "data/benchmark_test_trace.db"
    
    adapter = AskKernelAdapter(db_path, trace_path)
    
    with open("benchmark/gsm8k_sample_10.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    print("--- STARTING TOP 1% BENCHMARK SMOKE TEST ---")
    
    for i, line in enumerate(lines):
        data = json.loads(line)
        question = data["question"]
        print(f"\n[Q{i+1}] {question[:80]}...")
        
        req = MockRequest(question)
        try:
            res = await adapter.run_rag(req, request=None, handler=mock_handler)
            print(f"-> KERNEL RESULT: {str(res)[:150]}")
        except Exception as e:
            print(f"-> KERNEL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run())
