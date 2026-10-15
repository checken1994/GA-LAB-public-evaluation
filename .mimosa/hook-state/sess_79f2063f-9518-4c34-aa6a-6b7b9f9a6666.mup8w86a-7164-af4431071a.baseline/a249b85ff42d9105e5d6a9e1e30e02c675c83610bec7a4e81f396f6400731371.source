#!/usr/bin/env python3
"""SCP T00 Meta-Audit & Test-Integrity Authority (L2/L3)

This script enforces SCP's test integrity policies by strictly monitoring
test modifications, skips, deletions, and manufactured evidence against
a trusted baseline.

Violations already existing in the baseline are tracked as BASELINE_DEBT.
New violations added by the candidate branch are REJECTED.
Delta is computed using a finding-set (Counter) to prevent spoofing.
"""
import sys
import yaml
import subprocess
import ast
import re
import tempfile
import shutil
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = PROJECT_ROOT / "spec" / "guardrail_policy.yaml"

def fail_closed(msg):
    print(f"\n[T00 FAIL-CLOSED] {msg}")
    sys.exit(1)

def load_policy():
    if not POLICY_FILE.exists():
        fail_closed("Policy file spec/guardrail_policy.yaml is missing.")
    try:
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            policy = yaml.safe_load(f)
            if not policy:
                fail_closed("Policy file is empty or invalid YAML.")
            if "enforcement_context" not in policy:
                fail_closed("Policy missing 'enforcement_context'.")
            return policy
    except Exception as e:
        fail_closed(f"Failed to parse policy: {e}")

def run_git_cmd(args, check=False):
    try:
        res = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if check and res.returncode != 0:
            fail_closed(f"Git command failed: {' '.join(args)}\n{res.stderr}")
        return res.stdout.strip()
    except Exception as e:
        if check:
            fail_closed(f"Git execution error: {e}")
        return ""

def get_git_content(ref, path):
    try:
        out = subprocess.check_output(
            ["git", "show", f"{ref}:{path}"], 
            stderr=subprocess.DEVNULL, cwd=PROJECT_ROOT
        )
        return out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return None

def get_local_content(path):
    p = PROJECT_ROOT / path
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None

SKIP_MARKS = ('skip', 'xfail', 'skipif')

class AuditVisitor(ast.NodeVisitor):
    def __init__(self):
        self.findings = Counter()
        self.current_func = "<module>"
        
    def visit_FunctionDef(self, node):
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._handle_function(node)

    def _handle_function(self, node):
        old = self.current_func
        self.current_func = node.name
            
        for dec in node.decorator_list:
            attr_name = None
            if isinstance(dec, ast.Attribute):
                attr_name = dec.attr
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Attribute):
                    attr_name = dec.func.attr
                elif isinstance(dec.func, ast.Name):
                    attr_name = dec.func.id
                    
            if attr_name in ('skip', 'xfail', 'skipif'):
                self.findings[f"{attr_name} in {self.current_func}"] += 1
                
        self.generic_visit(node)
        self.current_func = old

    def _skip_mark_names(self, value):
        """Names of pytest.mark.{skip,xfail,skipif} referenced in a pytestmark value."""
        marks = set()
        if value is None:
            return marks
        for node in ast.walk(value):
            attr_node = node.func if isinstance(node, ast.Call) else node
            if (
                isinstance(attr_node, ast.Attribute)
                and attr_node.attr in SKIP_MARKS
                and isinstance(attr_node.value, ast.Attribute)
                and attr_node.value.attr == 'mark'
                and isinstance(attr_node.value.value, ast.Name)
                and attr_node.value.value.id == 'pytest'
            ):
                marks.add(attr_node.attr)
        return marks

    def _check_pytestmark_target(self, target, value):
        # A module- or class-level `pytestmark = pytest.mark.skip(...)` silently
        # skips whole files/classes without any skip call or function decorator.
        if isinstance(target, ast.Name) and target.id == 'pytestmark':
            for mark in sorted(self._skip_mark_names(value)):
                self.findings[f"pytestmark {mark} in {self.current_func}"] += 1

    def visit_Assign(self, node):
        for target in node.targets:
            self._check_pytestmark_target(target, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        self._check_pytestmark_target(node.target, node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._check_pytestmark_target(node.target, node.value)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if getattr(node.func.value, 'id', '') == 'pytest' and node.func.attr in ('skip', 'xfail', 'importorskip'):
                self.findings[f"pytest.{node.func.attr}() in {self.current_func}"] += 1
        self.generic_visit(node)

def get_fa01_signatures(code: str):
    if not code: return Counter()
    try:
        tree = ast.parse(code)
        visitor = AuditVisitor()
        visitor.visit(tree)
        return visitor.findings
    except SyntaxError:
        return Counter()

def get_fa04_signatures(code: str) -> Counter:
    findings = Counter()
    if not code: return findings
    for i, line in enumerate(code.splitlines()):
        content = line.strip()
        if re.search(r'["\']simulated\s+verifi(ed|cation)["\']', content, re.IGNORECASE):
            findings[f"simulated verification: {content}"] += 1
        if re.search(r'return\s*\{.*["\']status["\'].*["\']VERIFIED["\']', content, re.IGNORECASE):
            findings[f"hardcoded VERIFIED: {content}"] += 1
    return findings

def audit_content(candidate_code: str, baseline_code: str, path: str):
    new_violations = []
    debts = []
    
    # FA-01
    if (path.startswith("tests/") or path.startswith("scp/tests/")) and path.endswith(".py"):
        c_fa01 = get_fa01_signatures(candidate_code)
        b_fa01 = get_fa01_signatures(baseline_code)
        
        delta = c_fa01 - b_fa01
        for sig, count in delta.items():
            new_violations.append(f"FA-01: {path} -> {sig} ({count} new instances)")
            
        debt = c_fa01 & b_fa01
        for sig, count in debt.items():
            debts.append(f"FA-01: {path} -> {sig} ({count} historical instances)")
            
    # FA-04
    if path.startswith("scp/") and path.endswith(".py"):
        c_fa04 = get_fa04_signatures(candidate_code)
        b_fa04 = get_fa04_signatures(baseline_code)
        
        delta = c_fa04 - b_fa04
        for sig, count in delta.items():
            new_violations.append(f"FA-04: {path} -> {sig} ({count} new instances)")
            
        debt = c_fa04 & b_fa04
        for sig, count in debt.items():
            debts.append(f"FA-04: {path} -> {sig} ({count} historical instances)")
            
    return new_violations, debts

def parse_nodeids(output: str) -> set:
    nodeids = set()
    for line in output.splitlines():
        line = line.strip()
        if (line.startswith("tests/") or line.startswith("scp/tests/")) and "::" in line:
            nodeids.add(line)
    return nodeids

def get_real_nodeids(cwd: Path) -> set:
    targets = []
    if (cwd / "tests").exists(): targets.append("tests/")
    if (cwd / "scp" / "tests").exists(): targets.append("scp/tests/")
    if (cwd / "tests" / "internal").exists(): targets.append("tests/internal/")
    if not targets: return set()
    
    cmd = [sys.executable, "-m", "pytest"] + targets + ["--collect-only", "-q"]
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode not in (0, 5): # 0 is success, 5 is no tests collected
        fail_closed(f"Pytest collection failed in {cwd}:\n{res.stdout}\n{res.stderr}")
    return parse_nodeids(res.stdout)

def get_baseline_nodeids(trusted_base: str) -> set:
    tmpdir = tempfile.mkdtemp()
    try:
        run_git_cmd(["worktree", "add", "-d", tmpdir, trusted_base], check=True)
        # Neutralize historical module-level network call during pytest collection if present in baseline
        hist_test_api = Path(tmpdir) / "tests" / "test_api.py"
        if hist_test_api.exists():
            try:
                content = hist_test_api.read_text(encoding="utf-8", errors="ignore")
                if "_url_open(req).getcode()" in content and "def test_api_status():" not in content:
                    hist_test_api.write_text("def test_api_status(): pass\n", encoding="utf-8")
            except Exception:
                pass
        return get_real_nodeids(Path(tmpdir))
    finally:
        run_git_cmd(["worktree", "remove", "-f", tmpdir], check=False)
        shutil.rmtree(tmpdir, ignore_errors=True)

def check_real_test_deletion(trusted_base: str):
    print(f"[T00 Meta-Audit] Collecting baseline pytest nodeids ({trusted_base})...")
    b_nodeids = get_baseline_nodeids(trusted_base)
    # Map scp/tests/ to tests/internal/ in baseline nodeids to support moving the directory
    mapped_b_nodeids = set()
    for n in b_nodeids:
        if n.startswith("scp/tests/"):
            mapped_b_nodeids.add(n.replace("scp/tests/", "tests/internal/", 1))
        else:
            mapped_b_nodeids.add(n)
    
    print(f"[T00 Meta-Audit] Collecting candidate pytest nodeids...")
    c_nodeids = get_real_nodeids(PROJECT_ROOT)
    
    missing = mapped_b_nodeids - c_nodeids
    violations = []
    for m in sorted(missing):
        violations.append(f"FA-02: Deleted test nodeid: {m}")
    return violations

def check_code_owner_violations(policy):
    changed_files = run_git_cmd(["diff", "--cached", "--name-only"]).splitlines()
    if not changed_files:
        changed_files = run_git_cmd(["diff", "--name-only"]).splitlines()

    protected = policy.get("protected_paths", [])
    violations = []
    for f in changed_files:
        if not f: continue
        for p in protected:
            if f.startswith(p.strip('/')):
                violations.append(f"L4 Protected Path Modified: {f}")
                break
    return violations

def run_stale_code_tripwire_check():
    """T00-extension (S25, 2026): stale-code tripwire.

    Detects code-drifted-from-reality automatically: blueprint modules
    missing/unimportable, imports of non-existent symbols/modules, duplicated
    judge prompts, and metric drift (print()/silent-except > +5% vs baseline).

    Fail-closed: a tripwire tool crash is itself a violation. First run seeds
    data/governance/tripwire_baseline.json (metrics + known findings as
    BASELINE_DEBT, same philosophy as FA-01/FA-04 above); later runs reject
    only NEW findings, so pre-existing debt never turns the current tree red
    while genuine new drift does.
    """
    try:
        import importlib.util
        tool_path = PROJECT_ROOT / "tools" / "stale_code_tripwire.py"
        if not tool_path.exists():
            return [f"TRIPWIRE: tool file missing: {tool_path}"]
        spec = importlib.util.spec_from_file_location("stale_code_tripwire", tool_path)
        mod = importlib.util.module_from_spec(spec)
        # Register before exec_module: @dataclass in the tool resolves
        # annotations through sys.modules[cls.__module__].
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod.run_for_t00(PROJECT_ROOT)
    except Exception as e:  # fail-closed: a broken gate must block, never pass
        return [f"TRIPWIRE: tool failed to run (fail-closed): {type(e).__name__}: {e}"]

def main():
    policy = load_policy()
    trusted_base = policy["enforcement_context"].get("trusted_base", "origin/main")
    
    res = run_git_cmd(["rev-parse", "--verify", trusted_base])
    if not res and not trusted_base.startswith("origin/"):
        remote_base = f"origin/{trusted_base}"
        if run_git_cmd(["rev-parse", "--verify", remote_base]):
            trusted_base = remote_base
            res = True
    if not res:
        fail_closed(f"Trusted base '{trusted_base}' is invalid or missing. Run 'git fetch'.")
        
    print(f"[T00 Meta-Audit] Starting Test-Integrity Regression Authority...")
    print(f"[T00 Meta-Audit] Trusted Base: {trusted_base}")
    print("\n--- SCOPE & LIMITATIONS ---")
    print(" * FA-01 (Semantic Weakening): Partial (skip/xfail checked, incl. module-level pytestmark). Logic weakening requires L4 human review.")
    print(" * FA-02: ENFORCED for regressions in collected pytest nodeids")
    print(" * FA-03 (Same-SHA Evidence): NOT ENFORCED by T00 (Requires dedicated evidence tool).")
    print(" * FA-04 (Manufactured Green): Regex-based. Complex AST tracking requires L4 human review.")
    print(" * FA-05 (Self-Granting Auth): NOT ENFORCED by T00 (Requires capability scanner).")
    print(" * T00-extension stale-code tripwire: blueprint-vs-code, unresolved imports, duplicated prompt logic, metric drift (delta vs data/governance/tripwire_baseline.json).")
    
    all_new_violations = []
    all_debts = []
    
    # FA-02 Real nodeid check
    all_new_violations.extend(check_real_test_deletion(trusted_base))
    
    # FA-01 and FA-04
    all_paths = set()
    for p in PROJECT_ROOT.rglob("*.py"):
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        if rel.startswith("tests/") or rel.startswith("scp/"):
            all_paths.add(rel)
            
    out = run_git_cmd(["ls-tree", "-r", "--name-only", trusted_base])
    for line in out.splitlines():
        if line.endswith(".py") and (line.startswith("tests/") or line.startswith("scp/")):
            all_paths.add(line)
            
    # Normalize all paths to tests/internal/ for deduplication
    normalized_paths = set()
    for p in all_paths:
        if p.startswith("scp/tests/"):
            normalized_paths.add(p.replace("scp/tests/", "tests/internal/", 1))
        else:
            normalized_paths.add(p)
            
    for norm_path in normalized_paths:
        base_path = norm_path
            
        c_code = get_local_content(norm_path)
        b_code = get_git_content(trusted_base, base_path)
        new_v, debts = audit_content(c_code, b_code or "", norm_path)
        all_new_violations.extend(new_v)
        all_debts.extend(debts)
        
    l4_violations = check_code_owner_violations(policy)

    # --- T00-extension: stale-code tripwire (S25) ---
    all_new_violations.extend(run_stale_code_tripwire_check())

    if all_debts:
        print("\n--- BASELINE_DEBT (Tracked, Not Blocking) ---")
        for debt in sorted(all_debts):
            print(f" [DEBT] {debt}")
            
    if l4_violations:
        print("\n--- L4 CODEOWNERS (Warning) ---")
        for v in l4_violations:
            print(f" [L4] {v}")
        print("Note: L4 is VERIFIED only by GitHub Server-Side Ruleset. This is a local warning.")

    if all_new_violations:
        print("\n" + "="*60)
        print("T00 META-AUDIT FAILED - NEW REGRESSIONS DETECTED")
        print("="*60)
        for v in sorted(all_new_violations):
            print(f" [FAIL] {v}")
        print("\nFix violations before proceeding.")
        sys.exit(1)
        
    print("\n[T00 Meta-Audit] All integrity checks passed (0 new regressions).")
    sys.exit(0)

if __name__ == "__main__":
    main()
