import asyncio
import json
import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scp.ask_kernel_adapter import AskKernelAdapter

class MockRequest:
    def __init__(self, q, ans):
        self.question = q
        self.contexts = [f"The verified answer is exactly {ans}"]
        self.retrieved_context = ""
        self.session_id = f"test-session-{uuid.uuid4()}"
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
        
    for i, line in enumerate(lines):
        data = json.loads(line)
        question = data["question"]
        gold_ans = data["gold_answer"]
        req = MockRequest(question, gold_ans)
        
        response = await mock_handler(req, None)
        task = adapter.begin(req.question, req.contexts, "", req.session_id)
        verification = adapter.verify_response(req, response, task)
        print(f"\n[Q{i+1}] {gold_ans}")
        print(f"VERIFICATION VERDICT: {verification['verdict']}")
        print(f"FAILURES: {verification.get('failures', [])}")

if __name__ == "__main__":
    asyncio.run(run())
