from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "reports" / "codegraph_20260826" / "codegraph.json"
MATRIX = ROOT / "reports" / "scp_feature_completion_matrix_v2.json"
OUT = ROOT / "reports" / "codegraph_20260826"


def get_font() -> str:
    candidates = ["Noto Sans", "DejaVu Sans", "Arial"]
    available = {f.name for f in plt.matplotlib.font_manager.fontManager.ttflist}
    return next((name for name in candidates if name in available), "DejaVu Sans")


def node_segment(node_id: str) -> str:
    parts = node_id.split(".")
    if len(parts) < 2 or parts[0] != "scp":
        return "root / other"
    return parts[1]


def save_node_segments(graph: dict, font: str) -> Path:
    counts = Counter(node_segment(node["id"]) for node in graph["nodes"])
    labels, values = zip(*counts.most_common())
    plt.figure(figsize=(12, 7))
    bars = plt.barh(labels[::-1], values[::-1], color="#2563eb")
    plt.title("SCP codegraph: Python nodes by top-level package", fontname=font, fontsize=16, weight="bold")
    plt.xlabel("Node count", fontname=font)
    plt.ylabel("Package segment", fontname=font)
    for bar, value in zip(bars, values[::-1]):
        plt.text(value + max(values) * 0.01, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontname=font)
    plt.text(0.99, -0.18, f"Snapshot: {graph['commit']} | nodes={graph['node_count']} | internal edges={graph['edge_count']}", transform=plt.gca().transAxes, ha="right", fontsize=8, color="#475569", fontname=font)
    plt.tight_layout()
    path = OUT / "nodes_by_segment.png"
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    return path


def save_completion(matrix: dict, font: str) -> tuple[Path, Path]:
    features = matrix["features"]
    statuses = [item["status"] for item in features]
    order = ["RUNTIME_PROVEN", "INTEGRATION_PROVEN", "RELEASE_PROVEN", "STATIC_PROVEN_ONLY", "UNPROVEN", "BLOCKED"]
    counts = Counter(statuses)
    colors = {"RUNTIME_PROVEN":"#15803d", "INTEGRATION_PROVEN":"#22c55e", "RELEASE_PROVEN":"#0ea5e9", "STATIC_PROVEN_ONLY":"#eab308", "UNPROVEN":"#f97316", "BLOCKED":"#dc2626"}
    labels = [s for s in order if counts[s]]
    values = [counts[s] for s in labels]
    fig, ax = plt.subplots(figsize=(12, 7))
    left = 0
    for label, value in zip(labels, values):
        ax.barh(["15 tracked capabilities"], [value], left=left, color=colors[label], label=f"{label} ({value})")
        if value >= 2:
            ax.text(left + value / 2, 0, str(value), ha="center", va="center", color="white", weight="bold", fontname=font)
        left += value
    ax.set_xlim(0, len(features))
    ax.set_xlabel("Number of tracked capabilities", fontname=font)
    ax.set_title("SCP feature maturity by evidence level", fontname=font, fontsize=16, weight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False, prop={"family":font, "size":9})
    ax.text(0.99, -0.29, "Evidence maturity is not percentage of code implemented. UNPROVEN/BLOCKED score 0.", transform=ax.transAxes, ha="right", fontsize=8, color="#475569", fontname=font)
    fig.tight_layout()
    count_path = OUT / "feature_maturity_counts.png"
    fig.savefig(count_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    weights = matrix["weights"]
    score = sum(weights.get(status, 0.0) for status in statuses) / len(statuses) * 100
    proven = sum(status in {"RUNTIME_PROVEN", "INTEGRATION_PROVEN", "RELEASE_PROVEN"} for status in statuses)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.bar(["Release/runtime\nproven", "All tracked\ncapabilities"], [proven / len(statuses) * 100, score], color=["#15803d", "#f97316"], width=0.55)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Percent", fontname=font)
    ax.set_title("SCP evidence coverage (two honest views)", fontname=font, fontsize=16, weight="bold")
    for x, y in enumerate([proven / len(statuses) * 100, score]):
        ax.text(x, y + 3, f"{y:.1f}%", ha="center", weight="bold", fontname=font)
    ax.text(0.5, -0.18, f"{proven}/{len(statuses)} release/integration/runtime-proven; weighted score uses matrix weights", transform=ax.transAxes, ha="center", fontsize=8, color="#475569", fontname=font)
    fig.tight_layout()
    score_path = OUT / "feature_evidence_coverage.png"
    fig.savefig(score_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return count_path, score_path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    font = get_font()
    outputs = [save_node_segments(graph, font), *save_completion(matrix, font)]
    print(json.dumps({"font": font, "outputs": [str(path) for path in outputs]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
