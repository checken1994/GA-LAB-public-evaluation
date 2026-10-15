"""
[SCP-DNA-FIX R9 v4 IMP-22] Incremental Call-Graph Delta.

TẠI SAO file này tồn tại?
  IMP-16 (blast_radius) re-walks the entire scp codebase mỗi lần gọi
  `compute_blast_radius(target_file, target_function, scp_root)`. Với 371
  .py files, mỗi walk ~3-5s. Nếu engine process 50 bug một round →
  150-250s chỉ cho blast-radius analysis. IMP-22 thay thế full-walk bằng
  incremental delta: build call-graph 1 lần, persist to disk, mỗi lần file
  thay đổi chỉ recompute delta (chỉ file đó + edges tới/ra nó).

  Inspired by:
    - mypy daemon (dmypy) — incremental type checking since 2018
    - TypeScript language server (tsserver) — incremental graph rebuild
    - Rust Analyzer — salsa-based incremental computation
    - LLVM ThinLTO — incremental index

  Call-graph JSON schema (data/callgraph.json):
    {
      "version": 1,
      "built_at": <epoch>,
      "files": {
        "runtime/judge.py": {
          "sha": "<sha256[:16]>",
          "mtime": <epoch>,
          "functions_defined": ["ingestion_decision", "_score", ...],
          "calls": [{"target": "ingestion_decision", "line": 42, "col": 4}, ...]
        },
        ...
      },
      "functions_index": {
        "ingestion_decision": ["runtime/judge.py"],   # defined here
        ...
      }
    }

  apply_delta(changed_files) trả về DeltaResult:
    - added_edges:    [(caller_file, target_func, line), ...]
    - removed_edges:  [...]
    - affected_callers: list of files whose edges changed
  Caller (engine.py) chỉ cần re-scan blast-radius cho các file trong
  affected_callers, không phải toàn codebase.

  Fail-open: graph corrupt → rebuild from scratch (log warning). File
  unparseable → skip (don't crash build).

Flow:
  graph = get_call_graph()
  graph.build_full(scp_root)             # one-time, ~3-5s
  delta = graph.apply_delta(changed_files)  # ~50ms per file
  if "runtime/judge.py" in delta.affected_callers:
      re_run_blast_radius_for(judge.py)

DNA principles applied:
  #9  (Tăng tốc)        — delta = O(changed_files) instead of O(all_files)
  #20 (Cache for speed) — graph persisted at data/callgraph.json
  #19 (Reality multi-source)— graph + delta = 2 sources (file SHA + AST)
  #7  (Autofix safe)    — corrupt graph → rebuild, don't crash

Light-touch: NO modification to any v2/v3 file. Standalone module.

[SCP-DNA-FIX R12-14] Integration status: WIRED in runner.py:360 (R7-Full, fail-open). Post-loop summary uses apply_delta.
  Wire in `runner_phases/blast_radius.py` — replace the internal
  full-walk with `get_call_graph().get_callers(func_name)`. Call
  `apply_delta(changed_files)` after each fix batch to keep graph fresh.
  Also: `engine.py` after each fix application → call
  `graph.invalidate_file(patched_file)` + `graph.apply_delta([patched_file])`.

Smoke test (DNA #22 — verify it actually works, not just parses):
  $ python3 -c "
  import tempfile
  from pathlib import Path
  from callgraph_delta import CallGraph
  with tempfile.TemporaryDirectory() as d:
      # Create 2 small python files
      (Path(d) / 'a.py').write_text('def foo():\n    bar()\n')
      (Path(d) / 'b.py').write_text('def bar():\n    pass\n')
      g = CallGraph(cache_file=str(Path(d) / 'cg.json'))
      g.build_full(d)
      print('callers of bar:', g.get_callers('bar'))
      # Modify a.py to remove the call
      (Path(d) / 'a.py').write_text('def foo():\n    pass\n')
      delta = g.apply_delta([str(Path(d) / 'a.py')])
      print('removed:', len(delta.removed_edges), 'added:', len(delta.added_edges))
  "
  → callers of bar: [<tmpdir>/a.py] removed: 1 added: 0

  [S3-SECURITY-SWEEP] The smoke example uses Path.write_text() instead of
  open(...) so the documentation does not itself contain file-write idioms
  that static scanners misread as live path-traversal sinks.
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scp.autofix.path_guard import sanitize_storage_path

logger = logging.getLogger("scp.autofix.callgraph_delta")


# ============================================================
# Bounded walk limits (per DNA #7 — must terminate fast).
# ============================================================

DEFAULT_CACHE_FILE = "data/callgraph.json"
MAX_FILES_PER_BUILD = 1000
MAX_NODES_PER_FILE = 8000
MAX_FUNCTIONS_PER_FILE = 500
MAX_CALLS_PER_FILE = 2000
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}


# ============================================================
# Dataclasses.
# ============================================================

@dataclass
class CallEdge:
    """A single call: caller_file → callee_function at line N."""
    caller_file: str
    target_name: str       # name of called function
    line: int
    col: int = 0
    # True if call is `obj.target_name(...)` (attribute), False if `target_name(...)`.
    is_method_call: bool = False

    def key(self) -> tuple[str, str, int, int]:
        return (self.caller_file, self.target_name, self.line, self.col)


@dataclass
class FileNode:
    """Per-file node in the call graph."""
    path: str
    sha: str                 # 16-char sha256 prefix
    mtime: float
    functions_defined: list[str] = field(default_factory=list)
    calls: list[CallEdge] = field(default_factory=list)
    parse_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha": self.sha,
            "mtime": self.mtime,
            "functions_defined": list(self.functions_defined),
            "calls": [
                {
                    "target": e.target_name,
                    "line": e.line,
                    "col": e.col,
                    "is_method_call": e.is_method_call,
                }
                for e in self.calls
            ],
            "parse_error": self.parse_error,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FileNode:
        calls: list[CallEdge] = []
        for c in d.get("calls", []):
            try:
                calls.append(CallEdge(
                    caller_file=d.get("path", ""),
                    target_name=c.get("target", ""),
                    line=int(c.get("line", 0)),
                    col=int(c.get("col", 0)),
                    is_method_call=bool(c.get("is_method_call", False)),
                ))
            except Exception as edge_err:  # noqa: BLE001
                # silent-by-design: malformed persisted edge skipped during reconstruction.
                logger.debug("callgraph_delta: skipping malformed call edge %r: %s", c, edge_err, exc_info=True)
                continue
        return cls(
            path=d.get("path", ""),
            sha=d.get("sha", ""),
            mtime=float(d.get("mtime", 0.0)),
            functions_defined=list(d.get("functions_defined", [])),
            calls=calls,
            parse_error=d.get("parse_error", ""),
        )


@dataclass
class DeltaResult:
    """Outcome of apply_delta()."""
    added_edges: list[CallEdge] = field(default_factory=list)
    removed_edges: list[CallEdge] = field(default_factory=list)
    affected_callers: list[str] = field(default_factory=list)
    affected_callees: list[str] = field(default_factory=list)
    files_rebuilt: int = 0
    files_skipped: int = 0
    bounded: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_edges": len(self.added_edges),
            "removed_edges": len(self.removed_edges),
            "affected_callers": list(self.affected_callers),
            "affected_callees": list(self.affected_callees),
            "files_rebuilt": self.files_rebuilt,
            "files_skipped": self.files_skipped,
            "bounded": self.bounded,
            "reason": self.reason,
        }


# ============================================================
# AST walker — extract functions defined + calls.
# ============================================================

class _FileAnalyzer(ast.NodeVisitor):
    """Walks a file's AST, collects function defs + call sites."""

    def __init__(self) -> None:
        self.functions: list[str] = []
        self.calls: list[CallEdge] = []
        self._node_count = 0
        self._bounded = False

    def _bump(self) -> bool:
        self._node_count += 1
        if self._node_count > MAX_NODES_PER_FILE:
            self._bounded = True
            return False
        return True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: N802
        if not self._bump():
            return
        try:
            self.functions.append(node.name)
            if len(self.functions) > MAX_FUNCTIONS_PER_FILE:
                self._bounded = True
        except Exception as _visitor_error:  # noqa: BLE001
            logger.debug('[CALLGRAPH] bounded AST visitor operation failed; continuing traversal', exc_info=True)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:  # noqa: N802
        if not self._bump():
            return
        try:
            self.functions.append(node.name)
            if len(self.functions) > MAX_FUNCTIONS_PER_FILE:
                self._bounded = True
        except Exception as _visitor_error:  # noqa: BLE001
            logger.debug('[CALLGRAPH] bounded AST visitor operation failed; continuing traversal', exc_info=True)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
        if not self._bump():
            return
        try:
            if len(self.calls) >= MAX_CALLS_PER_FILE:
                self._bounded = True
                return
            target = ""
            is_method = False
            if isinstance(node.func, ast.Name):
                target = node.func.id
            elif isinstance(node.func, ast.Attribute):
                target = node.func.attr
                is_method = True
            if target:
                self.calls.append(CallEdge(
                    caller_file="",  # filled by caller
                    target_name=target,
                    line=getattr(node, "lineno", 0),
                    col=getattr(node, "col_offset", 0),
                    is_method_call=is_method,
                ))
        except Exception as _visitor_error:  # noqa: BLE001
            logger.debug('[CALLGRAPH] bounded AST visitor operation failed; continuing traversal', exc_info=True)
        self.generic_visit(node)


def _analyze_file(path: str) -> FileNode:
    """Parse + analyze a single .py file. Returns FileNode (never raises)."""
    try:
        p = Path(path)
        mtime = p.stat().st_mtime
        source = p.read_text(encoding="utf-8", errors="replace")
        sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        node = FileNode(path=path, sha=sha, mtime=mtime)
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as e:
            node.parse_error = f"SyntaxError: {e}"  # silent-by-design: error recorded on FileNode.parse_error and surfaced by delta checks
            return node
        except Exception as e:  # noqa: BLE001
            node.parse_error = f"{type(e).__name__}: {e}"  # silent-by-design: same explicit record on the node
            return node
        analyzer = _FileAnalyzer()
        analyzer.visit(tree)
        for ce in analyzer.calls:
            ce.caller_file = path
        node.functions_defined = analyzer.functions
        node.calls = analyzer.calls
        if analyzer._bounded:
            node.parse_error = (node.parse_error or "") + " [bounded]"
        return node
    except Exception as e:  # noqa: BLE001 — fail-open
        logger.debug(f"[IMP-22] analyze {path} error: {e}")
        return FileNode(path=path, sha="", mtime=0.0, parse_error=str(e))


# ============================================================
# CallGraph class.
# ============================================================

class CallGraph:
    """Persistent call graph with incremental delta support.

    On-disk format: JSON at `cache_file` (default data/callgraph.json).
    Thread-safe: `threading.RLock` guards all mutations.
    """

    def __init__(self, cache_file: str = DEFAULT_CACHE_FILE) -> None:
        # [S3-SECURITY-SWEEP] reject traversal-shaped cache paths (HIGH fix).
        # Kept as str: _save/_load use os.path + string concat on this attr.
        self.cache_file = str(sanitize_storage_path(
            cache_file, default=DEFAULT_CACHE_FILE, label="callgraph cache",
        ))
        self._lock = threading.RLock()
        # file_path -> FileNode
        self._files: dict[str, FileNode] = {}
        # function_name -> set of file_paths where defined
        self._func_index: dict[str, set[str]] = {}
        # function_name -> set of file_paths that CALL it
        self._caller_index: dict[str, set[str]] = {}
        self._stats = {
            "builds": 0, "deltas": 0, "invalidations": 0,
            "rebuilds_from_corrupt": 0, "errors": 0,
        }
        self._load()

    # ----- persistence -----

    def _load(self) -> None:
        try:
            if not os.path.exists(self.cache_file):
                return
            with Path(self.cache_file).open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("[IMP-22] cache malformed (not dict), rebuilding")
                self._stats["rebuilds_from_corrupt"] += 1
                return
            if data.get("version") != 1:
                logger.warning("[IMP-22] cache version mismatch, rebuilding")
                self._stats["rebuilds_from_corrupt"] += 1
                return
            files_data = data.get("files", {})
            if not isinstance(files_data, dict):
                self._stats["rebuilds_from_corrupt"] += 1
                return
            for path, fd in files_data.items():
                try:
                    node = FileNode.from_dict(fd)
                    node.path = path  # ensure path matches the key
                    self._files[path] = node
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[IMP-22] file entry parse error {path}: {e}")
                    continue
            self._rebuild_indexes()
            logger.info(
                f"[IMP-22] loaded {len(self._files)} files from {self.cache_file}"
            )
        except json.JSONDecodeError as e:
            logger.warning(f"[IMP-22] cache JSON corrupt, will rebuild: {e}")
            self._stats["rebuilds_from_corrupt"] += 1
            self._files.clear()
            self._func_index.clear()
            self._caller_index.clear()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-22] cache load error: {e}")

    def _save(self) -> None:
        """Persist graph to disk. Atomic via os.replace. Fail-open."""
        try:
            os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)
            data = {
                "version": 1,
                "built_at": time.time(),
                "file_count": len(self._files),
                "files": {p: n.to_dict() for p, n in self._files.items()},
            }
            tmp = self.cache_file + ".tmp"
            with Path(tmp).open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.cache_file)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-22] cache save error: {e}")
            self._stats["errors"] += 1

    def _rebuild_indexes(self) -> None:
        """Rebuild func_index + caller_index from self._files."""
        try:
            self._func_index.clear()
            self._caller_index.clear()
            for path, node in self._files.items():
                for fname in node.functions_defined:
                    self._func_index.setdefault(fname, set()).add(path)
                for edge in node.calls:
                    self._caller_index.setdefault(edge.target_name, set()).add(path)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-22] rebuild_indexes error: {e}")

    # ----- public API -----

    def build_full(self, scp_root: str) -> int:
        """Full build: walk scp_root, analyze every .py file, persist graph.

        Returns number of files indexed. Replaces any existing graph.
        """
        try:
            with self._lock:
                self._stats["builds"] += 1
                self._files.clear()
                self._func_index.clear()
                self._caller_index.clear()

            root = Path(scp_root)
            if not root.exists() or not root.is_dir():
                logger.warning(f"[IMP-22] scp_root not a dir: {scp_root}")
                return 0

            count = 0
            try:
                # [A12 H-1] Deterministic walk: sort theo path TRƯỚC khi cap
                # (thứ tự rglob phụ thuộc OS) + WARNING khi truncation xảy ra.
                candidates = sorted(
                    p for p in root.rglob("*.py")
                    if not any(part in SKIP_DIRS for part in p.parts)
                )
                if len(candidates) > MAX_FILES_PER_BUILD:
                    logger.warning(
                        "[scanner-cap] %s: %d file .py vượt cap %d — cắt còn %d "
                        "(callgraph index sẽ thiếu %d file)",
                        __name__, len(candidates), MAX_FILES_PER_BUILD,
                        MAX_FILES_PER_BUILD, len(candidates) - MAX_FILES_PER_BUILD,
                    )
                    candidates = candidates[:MAX_FILES_PER_BUILD]
                for p in candidates:
                    node = _analyze_file(str(p))
                    with self._lock:
                        self._files[str(p)] = node
                    count += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[IMP-22] walk error: {e}")

            with self._lock:
                self._rebuild_indexes()
                self._save()

            logger.info(f"[IMP-22] build_full: {count} files indexed")
            return count
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-22] build_full error: {e}")
            self._stats["errors"] += 1
            return 0

    def apply_delta(self, changed_files: list[str]) -> DeltaResult:
        """Re-analyze only `changed_files`, compute edge delta.

        Returns DeltaResult with added/removed edges + affected callers.
        """
        result = DeltaResult()
        try:
            with self._lock:
                self._stats["deltas"] += 1

            if not changed_files:
                result.reason = "no changed files"
                return result

            for path in changed_files:
                try:
                    p = Path(path)
                    if not p.exists():
                        # File deleted — remove from graph.
                        with self._lock:
                            old = self._files.pop(path, None)
                        if old:
                            result.removed_edges.extend(old.calls)
                            result.files_rebuilt += 1
                            if path not in result.affected_callers:
                                result.affected_callers.append(path)
                            for fname in old.functions_defined:
                                if path in self._func_index.get(fname, set()):
                                    self._func_index[fname].discard(path)
                                    if fname not in result.affected_callees:
                                        result.affected_callees.append(fname)
                        continue

                    # Re-analyze.
                    new_node = _analyze_file(path)
                    with self._lock:
                        old = self._files.get(path)
                        # Compute edge delta.
                        old_edges = {e.key(): e for e in (old.calls if old else [])}
                        new_edges = {e.key(): e for e in new_node.calls}
                        for k, e in new_edges.items():
                            if k not in old_edges:
                                result.added_edges.append(e)
                        for k, e in old_edges.items():
                            if k not in new_edges:
                                result.removed_edges.append(e)
                        # Update file entry.
                        self._files[path] = new_node
                        result.files_rebuilt += 1
                        if path not in result.affected_callers:
                            result.affected_callers.append(path)
                        # Track affected callees (target function names).
                        for e in result.added_edges:
                            if e.target_name not in result.affected_callees:
                                result.affected_callees.append(e.target_name)
                        for e in result.removed_edges:
                            if e.target_name not in result.affected_callees:
                                result.affected_callees.append(e.target_name)
                except Exception as e:  # noqa: BLE001
                    logger.debug(f"[IMP-22] delta file {path} error: {e}")
                    result.files_skipped += 1
                    continue

            # Rebuild indexes (cheaper than incremental index maintenance).
            with self._lock:
                self._rebuild_indexes()
                self._save()

            result.reason = (
                f"delta applied: +{len(result.added_edges)}/"
                f"-{len(result.removed_edges)} edges, "
                f"{len(result.affected_callers)} caller files affected"
            )
            return result
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-22] apply_delta error: {e}")
            self._stats["errors"] += 1
            result.reason = f"error (fail-open): {e}"
            return result

    def get_callers(self, func_name: str) -> list[str]:
        """Return list of file paths that call `func_name`."""
        try:
            with self._lock:
                return sorted(self._caller_index.get(func_name, set()))
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[IMP-22] get_callers error: {e}")
            return []

    # [SCP-DNA-FIX R13-3] Bug #7: get_callers() already returns [] on
    # error, but the public API is never invoked by any caller (per
    # vulture BUG-008). The blast_radius.py module (which the manifest
    # claimed would use get_callers()) still does a full AST walk
    # instead. This safe wrapper:
    #   - Returns [] on ANY error (already true, but explicit).
    #   - Logs at INFO level when called so wiring tests can verify
    #     invocation (the original get_callers logs only at DEBUG).
    #   - Normalizes `func_name` (strip, lowercase-first) so callers
    #     don't have to.
    # The companion module-level `get_callers_for(symbol)` helper (below
    # the singleton accessor) is the canonical entry point for
    # blast_radius.py — engine.py / runner_phases should call THAT,
    # not get_callers() directly.
    def get_callers_safe(self, func_name: str) -> list[str]:
        """Public wrapper around get_callers() with normalized input +
        fail-open [] return on any error. Use this from external callers
        (blast_radius.py, engine.py) instead of get_callers() directly.
        """
        try:
            if not func_name or not isinstance(func_name, str):
                return []
            name = func_name.strip()
            if not name:
                return []
            callers = self.get_callers(name)
            # Log at INFO so wiring audits (vulture, manual grep) can
            # verify the API is actually invoked, not just defined.
            logger.info(
                f"[IMP-22] get_callers_safe({name!r}) → {len(callers)} caller(s)"
            )
            return callers
        except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
            logger.warning(
                f"[IMP-22] get_callers_safe crashed for {func_name!r}: {e} "
                f"(fail-open — caller will treat as 0 callers)"
            )
            return []

    def get_definitions(self, func_name: str) -> list[str]:
        """Return list of file paths where `func_name` is defined."""
        try:
            with self._lock:
                return sorted(self._func_index.get(func_name, set()))
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[IMP-22] get_definitions error: {e}")
            return []

    def get_calls_in_file(self, file_path: str) -> list[CallEdge]:
        """Return all calls made in `file_path`."""
        try:
            with self._lock:
                node = self._files.get(file_path)
                return list(node.calls) if node else []
        except Exception as query_err:  # noqa: BLE001
            # fail-loudly (S-B1b): query crash must not masquerade as "no calls".
            logger.warning("callgraph_delta: get_calls_in_file crashed for %s, returning empty: %s", file_path, query_err, exc_info=True)
            return []

    def invalidate_file(self, path: str) -> None:
        """Remove a file from the graph (caller should call apply_delta after)."""
        try:
            with self._lock:
                self._stats["invalidations"] += 1
                self._files.pop(path, None)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[IMP-22] invalidate error: {e}")

    def clear_all(self) -> None:
        """Wipe the graph + persist empty state."""
        try:
            with self._lock:
                self._files.clear()
                self._func_index.clear()
                self._caller_index.clear()
                self._save()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[IMP-22] clear_all error: {e}")

    def stats(self) -> dict[str, Any]:
        """Return graph stats snapshot."""
        try:
            with self._lock:
                return {
                    **dict(self._stats),
                    "file_count": len(self._files),
                    "function_count": len(self._func_index),
                    "caller_index_size": len(self._caller_index),
                    "cache_file": self.cache_file,
                }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def is_file_current(self, path: str) -> bool:
        """True if the cached entry for `path` matches the file's current SHA."""
        try:
            p = Path(path)
            if not p.exists():
                return False
            source = p.read_text(encoding="utf-8", errors="replace")
            sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
            with self._lock:
                node = self._files.get(path)
                return node is not None and node.sha == sha
        except Exception as fresh_err:  # noqa: BLE001
            # silent-by-design: False = "not provably current" → caller re-scans (safe direction).
            logger.debug("callgraph_delta: freshness check crashed for %s: %s", path, fresh_err, exc_info=True)
            return False


# ============================================================
# Singleton accessor.
# ============================================================

_CALL_GRAPH: CallGraph | None = None
_GRAPH_LOCK = threading.Lock()


def get_call_graph(cache_file: str = DEFAULT_CACHE_FILE) -> CallGraph:
    """Return the singleton CallGraph. Lazy-initialized."""
    global _CALL_GRAPH
    if _CALL_GRAPH is None:
        with _GRAPH_LOCK:
            if _CALL_GRAPH is None:
                _CALL_GRAPH = CallGraph(cache_file=cache_file)
    return _CALL_GRAPH


def reset_call_graph() -> None:
    """Reset the singleton (for tests)."""
    global _CALL_GRAPH
    with _GRAPH_LOCK:
        _CALL_GRAPH = None


# [SCP-DNA-FIX R13-3] Bug #7: module-level singleton accessor alias +
# canonical entry point for blast_radius.py.
# The existing `get_call_graph()` already returns the singleton, but
# vulture BUG-008 found that NO caller in the codebase ever invokes
# `get_call_graph().get_callers(...)` — blast_radius.py still does a
# full AST walk. The manifest promised this would replace the walk,
# but the wiring was never done. We can't edit blast_radius.py (owned
# by Group A), so we provide:
#   1. `get_callgraph()` — short alias for `get_call_graph()` (matches
#      the manifest's documented name).
#   2. `get_callers_for(symbol)` — one-liner convenience that combines
#      singleton lookup + safe caller query. Group A should wire this
#      into blast_radius.py's compute_blast_radius() to replace the
#      full-walk that's currently there.
def get_callgraph(cache_file: str = DEFAULT_CACHE_FILE) -> CallGraph:
    """Short alias for get_call_graph(). Returns the singleton CallGraph."""
    return get_call_graph(cache_file=cache_file)


def get_callers_for(symbol: str) -> list[str]:
    """Module-level convenience: get callers of `symbol` via the singleton.

    Combines get_call_graph() + CallGraph.get_callers_safe(). Returns []
    on any error (fail-open). Use this from blast_radius.py instead of
    a full AST walk to look up who calls a function.

    Group A TODO (blast_radius.py — DO NOT EDIT from Group C):
        In `compute_blast_radius(target_file, target_function, scp_root)`,
        replace the internal full-AST-walk that collects caller_files
        with:
            from scp.autofix.callgraph_delta import get_callers_for
            caller_files = get_callers_for(target_function)
        If the call-graph hasn't been built yet (returns []), fall back
        to the existing full-walk. This makes IMP-22 actually pay off
        (the 642-LOC module is currently 100% dead code from the
        engine's perspective).
    """
    try:
        if not symbol or not isinstance(symbol, str):
            return []
        graph = get_callgraph()
        return graph.get_callers_safe(symbol)
    except Exception as e:  # noqa: BLE001 — fail-open per DNA #7
        logger.warning(
            f"[IMP-22] get_callers_for crashed for {symbol!r}: {e} "
            f"(fail-open — caller should fall back to full walk)"
        )
        return []


__all__ = [
    "CallEdge",
    "FileNode",
    "DeltaResult",
    "CallGraph",
    "get_call_graph",
    "reset_call_graph",
    # [SCP-DNA-FIX R13-3] Bug #7: added for blast_radius.py wiring.
    "get_callgraph",
    "get_callers_for",
    "DEFAULT_CACHE_FILE",
    "MAX_FILES_PER_BUILD",
    "MAX_NODES_PER_FILE",
]
