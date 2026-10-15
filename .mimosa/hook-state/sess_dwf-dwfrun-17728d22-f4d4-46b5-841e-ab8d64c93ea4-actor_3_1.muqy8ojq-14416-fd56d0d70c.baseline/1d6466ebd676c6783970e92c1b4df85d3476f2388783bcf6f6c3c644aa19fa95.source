import asyncio
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scp.ask_kernel_adapter import AskKernelAdapter

class MockRequest:
    def __init__(self, q, ans):
        self.question = q
        self.contexts = [f"The verified answer is exactly {ans}"]
        self.retrieved_context = ""
        self.session_id = "test-session"
        self.expected_ans = ans
        
async def mock_handler(req, request):
    return {
        "final_answer": req.expected_ans,
        "verdict": "PASS",
        "governance_decision": "UPHOLD",
        "v98_classification": {"provenance": "input_context_only"}
    }

async def run():
    db_path = "data/benchmark_test_kernel.db"
    trace_path = "data/benchmark_test_trace.db"
    
    adapter = AskKernelAdapter(db_path, trace_path)
    
    with open("benchmark/human_verified_gold.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    print("--- RUNNING: WHEN AI PROVES IRONCLAD EVIDENCE ---")
    
    for i, line in enumerate(lines):
        data = json.loads(line)
        question = data["question"]
        gold_ans = data["gold_answer"]
        print(f"\n[Q{i+1}] {question}")
        
        req = MockRequest(question, gold_ans)
        try:
            res = await adapter.run_rag(req, request=None, handler=mock_handler)
            print(f"-> KERNEL ALLOWED THIS: {res}")
        except Exception as e:
            print(f"-> KERNEL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run())
