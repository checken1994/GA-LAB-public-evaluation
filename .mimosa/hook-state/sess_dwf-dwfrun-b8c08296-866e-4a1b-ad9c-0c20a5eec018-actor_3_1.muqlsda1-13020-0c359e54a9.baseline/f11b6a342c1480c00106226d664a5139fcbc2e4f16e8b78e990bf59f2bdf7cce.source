# Auto-extracted from cross_func_taint_scanner.py
from __future__ import annotations

import ast
import logging
from collections import defaultdict
from pathlib import Path

from scp.autofix.classifier import BugReport, BugTier
from scp.autofix.scanners.taint_flow_scanner import (
    _CWE_TITLES,
)

logger = logging.getLogger(__name__)

class _CrossFuncScanner:
    """Encapsulates the whole-program call graph + detection logic."""

    def __init__(self):
        self.funcs_by_qualname: dict[str, FunctionInfo] = {}  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        self.funcs_by_name: dict[str, list[FunctionInfo]] = defaultdict(list)  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        self._fixpoint_done: bool = False

    def add_file(self, path: Path) -> None:
        """Parse a file and add its functions to the call graph."""
        path = Path(path)
        try:
            source = path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.warning(f'Could not read {path}: {e}', exc_info=True)
            return
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            logger.debug(f'SyntaxError in {path}: {e}')
            return
        try:
            relpath = str(path.relative_to(_SCP_ROOT.parent))  # noqa: F821  # [hygiene-keep] _SCP_ROOT injected by cross_func_taint_scanner.py rebind/wire
        except ValueError:
            # silent-by-design: relative_to probe — absolute path is the
            # documented fallback for files outside the scp root.
            logger.debug('crossfunc: %s not under scp root, using absolute path', path, exc_info=True)
            relpath = str(path)
        builder = _CallGraphBuilder(path, relpath)  # noqa: F821  # [hygiene-keep] _CallGraphBuilder injected by cross_func_taint_scanner.py rebind/wire
        builder.visit(tree)
        for info in builder.funcs:
            if info.qualname in self.funcs_by_qualname:
                continue
            self.funcs_by_qualname[info.qualname] = info
            self.funcs_by_name[info.name].append(info)
        self._fixpoint_done = False

    def run_fixpoint(self) -> None:
        if self._fixpoint_done:
            return
        _run_fixpoint(self.funcs_by_qualname)  # noqa: F821  # [hygiene-keep] _run_fixpoint injected by cross_func_taint_scanner.py rebind/wire
        self._fixpoint_done = True

    def detect_bugs(self, only_in_files: set[str] | None=None) -> list[BugReport]:
        """Walk each function with cross-function awareness; return bugs.

        If `only_in_files` is set, only report bugs whose CALLER is in one of
        those files (used by scan_file to limit reports to the target file).
        """
        if not self._fixpoint_done:
            self.run_fixpoint()
        bugs: list[BugReport] = []
        seen_keys: set[tuple[str, int, str, int, int]] = set()
        for _qualname, info in self.funcs_by_qualname.items():
            if only_in_files is not None and info.file not in only_in_files:
                continue
            detector = _FunctionDetector(info, self.funcs_by_name)  # noqa: F821  # [hygiene-keep] _FunctionDetector injected by cross_func_taint_scanner.py rebind/wire
            detector.analyze()
            for f in detector.findings:
                key = (info.file, f['call_line'], f['callee_qualname'], f['sink_line'], f['source_line'])
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                bugs.append(self._build_bug_report(info, f))
        return bugs

    @staticmethod
    def _build_bug_report(caller_info: FunctionInfo, finding: dict) -> BugReport:  # noqa: F821  # [hygiene-keep] FunctionInfo injected by cross_func_taint_scanner.py rebind/wire
        """Construct a BugReport from a detector finding."""
        cwe = finding['cwe']
        cwe_title = _CWE_TITLES.get(cwe, 'Cross-Function Taint')
        sink_name = finding['sink_name']
        sink_line = finding['sink_line']
        callee_name = finding['callee_name']
        callee_file = finding['callee_file']
        callee_param = finding['callee_param']
        tainted_var = finding['tainted_var']
        src_line = finding['source_line']
        src_desc = finding['source_desc']
        call_line = finding['call_line']
        via_callee = finding['via_callee']
        via_callee_file = finding.get('via_callee_file')
        caller_short = Path(caller_info.file).name
        callee_short = Path(callee_file).name
        via_callee_name: str | None = None
        if via_callee and '::' in via_callee:
            via_callee_name = via_callee.split('::', 1)[1]
        if via_callee_name is not None:
            sink_file_short = Path(via_callee_file or callee_file).name
            chain = f'source@{caller_short}:{src_line} → call@{caller_short}:{call_line} ({caller_info.name} → {callee_name}) → {callee_name} calls {via_callee_name} → sink@{sink_file_short}:{sink_line} ({sink_name})'
            desc = f'CrossFuncTaint [{cwe} — {cwe_title}]: tainted variable `{tainted_var}` flows from source {src_desc} at line {src_line} through call `{callee_name}({tainted_var})` at line {call_line} (param `{callee_param}`), which transitively passes it to `{via_callee_name}` where it reaches sink `{sink_name}(...)` at line {sink_line}. Call chain: {chain}. This is a CROSS-FUNCTION taint flow (source and sink in different functions); the intra-function taint scanner (taint_flow_scanner.py) would miss this.'
        else:
            chain = f'source@{caller_short}:{src_line} → call@{caller_short}:{call_line} ({caller_info.name} → {callee_name}) → sink@{callee_short}:{sink_line} ({sink_name})'
            desc = f'CrossFuncTaint [{cwe} — {cwe_title}]: tainted variable `{tainted_var}` flows from source {src_desc} at line {src_line} through call `{callee_name}({tainted_var})` at line {call_line} to sink `{sink_name}(...)` at line {sink_line} in callee `{callee_name}` (param `{callee_param}`). Call chain: {chain}. This is a CROSS-FUNCTION taint flow (source and sink in different functions); the intra-function taint scanner (taint_flow_scanner.py) would miss this.'
        fix = f'Sanitize `{tainted_var}` before passing to `{callee_name}` at line {call_line}. '
        if cwe == 'CWE-78':
            fix += 'Use shlex.quote() per arg, or pass an argument list with shell=False. For SCP, prefer scp.core.safe_process.'
        elif cwe == 'CWE-89':
            fix += "Use parameterized SQL inside the callee: cursor.execute('... WHERE id=?', (var,)). If the callee cannot be changed, validate/sanitize the input at the call site (e.g., regex-whitelist)."
        elif cwe == 'CWE-79':
            fix += 'Use markupsafe.escape() on the input before passing it in, or rely on Jinja2 autoescape inside the callee.'
        elif cwe == 'CWE-502':
            fix += 'Avoid passing untrusted data to a function that deserializes it. Use yaml.safe_load() / json.loads() inside the callee, or validate the input at the call site.'
        elif cwe == 'CWE-94':
            fix += 'Avoid passing untrusted data to a function that eval/execs it. Use ast.literal_eval() inside the callee, or refactor to a real parser.'
        return BugReport(file=caller_info.file, line=call_line, bug_type=f'CrossFuncTaint_{cwe}', description=desc, suggested_fix=fix, tier=BugTier.TIER_3_PERMISSION, affects_logic=True)
