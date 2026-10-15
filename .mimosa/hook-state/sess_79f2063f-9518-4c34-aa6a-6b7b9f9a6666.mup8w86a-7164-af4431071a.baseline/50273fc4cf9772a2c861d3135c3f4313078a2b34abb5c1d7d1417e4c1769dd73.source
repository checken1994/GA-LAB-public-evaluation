from pathlib import Path
import json
import urllib.request
import os

def download_benchmark(name, url, out_name):
    print(f"Downloading {name} - World Gold Standard...")
    out_path = os.path.join(str(Path(__file__).resolve().parent / "benchmark"), out_name)
    try:
        urllib.request.urlretrieve(url, out_path)
        print(f"Success! {name} saved to: {out_path}")
    except Exception as e:
        print(f"Error downloading {name}: {e}")

if __name__ == "__main__":
    # 1. HumanEval (OpenAI) - World standard for Code & OS Sandbox capabilities
    download_benchmark(
        "HumanEval (Code Execution)", 
        "https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz", 
        "HumanEval.jsonl.gz"
    )
    
    # 2. TruthfulQA - World standard for Anti-Hallucination & Fail-Closed (Perfect for SCP's WhyGate)
    download_benchmark(
        "TruthfulQA (Anti-Hallucination)", 
        "https://raw.githubusercontent.com/sylinrl/TruthfulQA/main/TruthfulQA.csv", 
        "TruthfulQA_Gold.csv"
    )
