from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scp"
OUT = ROOT / "reports" / "codegraph_20260826"


def module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def import_target(node: ast.AST, current: str) -> str | None:
    if not isinstance(node, ast.ImportFrom):
        return None
    if node.level:
        base = current.split(".")[:-node.level]
        if node.module:
            base += node.module.split(".")
        return ".".join(base)
    return node.module or ""


def resolve_target(target: str, modules: set[str]) -> str | None:
    if target in modules:
        return target
    matches = [name for name in modules if target.startswith(name + ".") or name.startswith(target + ".")]
    return max(matches, key=len) if matches else None


def build_graph() -> dict:
    files = sorted(SOURCE.rglob("*.py"))
    modules = {module_name(path) for path in files}
    nodes = []
    edges = []
    edge_seen = set()
    import_counts: Counter[str] = Counter()
    for path in files:
        name = module_name(path)
        data = path.read_bytes()
        try:
            tree = ast.parse(data.decode("utf-8"), filename=str(path))
            parse_status = "parsed"
        except (SyntaxError, UnicodeDecodeError) as exc:
            tree = ast.Module(body=[], type_ignores=[])
            parse_status = f"parse_error:{type(exc).__name__}"
        imports = []
        for node in ast.walk(tree):
            target = import_target(node, name)
            if target is None:
                continue
            imports.append(target)
            resolved = resolve_target(target, modules)
            if resolved and resolved != name:
                key = (name, resolved, "import")
                if key not in edge_seen:
                    edge_seen.add(key)
                    edges.append({"source": name, "target": resolved, "kind": "import"})
        layer = name.split(".")[1] if name.startswith("scp.") and len(name.split(".")) > 1 else "root"
        nodes.append({"id": name, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "layer": layer, "lines": data.count(b"\n") + 1, "sha256": "sha256:" + hashlib.sha256(data).hexdigest(), "parse_status": parse_status, "import_count": len(imports)})
        import_counts.update(imports)
    tokens = ("api_server", "ask_kernel", "task_kernel", "trace_ledger", "judge", "retriev", "govern", "policy", "verif", "evidence", "hands", "connector", "provider", "kill", "capab", "reconcil", "timeout")
    focused = [node for node in nodes if any(token in node["id"].lower() for token in tokens)]
    focused_ids = {node["id"] for node in focused}
    focused_edges = [edge for edge in edges if edge["source"] in focused_ids or edge["target"] in focused_ids]
    return {"schema_version": "scp-codegraph-v1", "generated_at": datetime.now(timezone.utc).isoformat(), "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "source_root": "scp", "node_count": len(nodes), "edge_count": len(edges), "nodes": nodes, "edges": edges, "focused_node_count": len(focused), "focused_edge_count": len(focused_edges), "focused_nodes": focused, "focused_edges": focused_edges, "top_import_targets": import_counts.most_common(30)}


def write_mermaid(graph: dict, path: Path, focused: bool) -> None:
    nodes = graph["focused_nodes"] if focused else graph["nodes"]
    edges = graph["focused_edges"] if focused else graph["edges"]
    ids = {node["id"]: f"n{i}" for i, node in enumerate(nodes)}
    lines = ["flowchart LR"]
    for node in nodes:
        label = node["id"].replace('"', "'")
        lines.append(f'    {ids[node["id"]]}["{label}<br/>{node["lines"]} lines"]')
    for edge in edges:
        if edge["source"] in ids and edge["target"] in ids:
            lines.append(f"    {ids[edge['source']]} --> {ids[edge['target']]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    graph = build_graph()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "codegraph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "codegraph_edges.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "target", "kind"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(graph["edges"])
    write_mermaid(graph, OUT / "codegraph_full.mmd", False)
    write_mermaid(graph, OUT / "codegraph_focused.mmd", True)
    summary = {key: graph[key] for key in ("schema_version", "generated_at", "commit", "source_root", "node_count", "edge_count", "focused_node_count", "focused_edge_count", "top_import_targets")}
    (OUT / "codegraph_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
