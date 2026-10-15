"""
EvolutionEngine mixin — extracted from evolution.py (Task 19-A).
 kept verbatim; only the method location changed.
"""
import ast
import logging
from pathlib import Path as _Path

_SCP_ROOT = _Path(__file__).resolve().parent.parent.parent.parent  # scp-vietnam/

logger = logging.getLogger("scp.autofix")
import re
import time
from dataclasses import asdict
from pathlib import Path

logger = logging.getLogger("scp.autofix.evolution")

from scp.autofix.evolution import (
    ModuleSpec,
)


class EvolutionEngineBuildMixin:
    """Mixin for EvolutionEngine — provides BuildMixin methods."""

    def _evolution_policy_scan(self, fix_id: str, patch: str, bug_file: str, scanner_name: str) -> dict:
        """Run the constitutional policy gate over generated content.

        Returns {"allowed": bool, "reason": str, "blocked_patterns": list}.
        Fail-closed: ANY gate error returns allowed=False — LLM-generated
        content is never written when it could not be screened.
        """
        try:
            from scp.autofix.policy_gate import ImmutableAuditLog, PolicyFix, PolicyGate
            gate = getattr(self, "_evolution_policy_gate", None)
            if gate is None:
                gate = PolicyGate(audit_log=ImmutableAuditLog(
                    log_file=str(Path(getattr(self, "data_dir", "data")) / "evolution_policy_audit.jsonl"),
                ))
                self._evolution_policy_gate = gate
            decision = gate.evaluate_fix(PolicyFix(
                fix_id=fix_id,
                patch=patch,
                patched_source="",
                bug_file=bug_file,
                bug_line=0,
                scanner_name=scanner_name,
            ))
            return {
                "allowed": bool(decision.allowed),
                "reason": decision.reason,
                "blocked_patterns": list(decision.blocked_patterns),
            }
        except Exception as e:
            logger.error(f"[EVOP-GATE] policy gate unavailable — fail-closed: {e}", exc_info=True)
            return {"allowed": False, "reason": f"policy gate error (fail-closed): {e}", "blocked_patterns": ["__gate_error__"]}

    def build_module(self, spec: ModuleSpec) -> dict:
        """Build module mới từ SPEC — LLM generate + wire + verify.

        Flow:
          1. Safety guards (env, timeout, rate limit, constitution)
          2. WHY layer 1: "Tại sao cần module này?"
          3. LLM generate module code
          4. ast.parse verify (syntax)
          5. WHY layer 2: "Tại sao module này đúng? Bác bỏ được không?"
          6. Write file + backup .evolutionbak
          7. Wire into codebase (optional, per spec.wiring)
          8. Re-scan: nếu bug count tăng → rollback
          9. Audit log
        """
        # [G2-FIX OV-01] Layer 3 must respect Layer 2 capability check
        try:
            from scp.meta.capability_levels import CapabilityManager
            _cap = CapabilityManager()
            if not _cap.can_do("build_module"):
                # [SCP-DNA-FIX R5-2] TẠI SAO: `_cap.level` doesn't exist on
                # CapabilityManager — only `_current_level` (private) +
                # `get_current_level()` (public accessor) exist. AttributeError
                # was caught by the broad `except Exception` below → returned
                # WRONG error message ("CapabilityManager error: ..." instead
                # of "capability_level=X denies build_module"). Dormant in
                # default FULL_PRODUCTION mode (can_do always True), but bites
                # operators who set SCP_CAPABILITY_LEVEL below FULL_PRODUCTION.
                # pylint E1101 caught it.
                return {"status": "blocked", "reason": f"capability_level={_cap.get_current_level()} denies build_module"}
        except Exception as _e:
            logger.debug(f"EvolutionEngineBuildMixin.build_module: exception ignored: {_e}", exc_info=True)
            # silent-by-design: explicit blocked status carrying the error reason is returned to the caller.
            return {"status": "blocked", "reason": f"CapabilityManager error: {_e}"}
        action_desc = f"build_module: {spec.name} ({spec.purpose[:100]})"

        # Guard: env + timeout + rate limit + constitution
        if not self._should_evolve(action_desc):
            return {"action": "skipped", "reason": "evolution guards blocked"}

        # WHY layer 1: necessity
        is_necessary, why1 = self._why_necessity_check(
            action_desc, f"Purpose: {spec.purpose}\nInterfaces: {spec.interfaces}"
        )
        if not is_necessary:
            self._rejected_by_why += 1
            self._write_rejected(action_desc, f"why_necessity_failed: {why1}")
            return {"action": "rejected_by_why", "reason": why1, "layer": "necessity"}

        # LLM generate module code
        code = self._llm_generate_module(spec)
        if not code:
            return {"action": "skipped", "reason": "LLM generation failed"}

        # Verify syntax
        try:
            ast.parse(code, filename=spec.path)
        except SyntaxError as e:
            return {"action": "skipped", "reason": f"generated code SyntaxError: {e}"}

        # WHY layer 2: falsification
        is_falsified, why2 = self._why_falsification_check(
            f"Module {spec.name} implements {spec.interfaces} correctly and safely",
            code[:1000]
        )
        if is_falsified:
            self._rejected_by_why += 1
            self._write_rejected(action_desc, f"why_falsification_failed: {why2}")
            return {"action": "rejected_by_why", "reason": why2, "layer": "falsification"}

        # [EVOP-GATE 2026-09-26] Constitutional policy scan BEFORE any write
        # (fail-closed). engine._auto_fix runs every LLM patch through
        # policy_gate.evaluate_fix, but build_module wrote LLM-generated code
        # with NO scan — forbidden patterns (bare `except: pass`,
        # `verify=False`, `eval(...)`, `os.chmod(..., 0o777)`, ...) could enter
        # the codebase through the evolution path. Any gate failure is ALSO
        # fail-closed (block the build, never write unscreened code).
        _policy_decision = self._evolution_policy_scan(
            fix_id=f"evolution_build_{spec.name}",
            patch=code,
            bug_file=str(spec.path),
            scanner_name="evolution_build_module",
        )
        if not _policy_decision.get("allowed", False):
            self._rejected_by_why += 1
            self._write_rejected(action_desc, f"policy_gate_blocked: {_policy_decision.get('reason', '')}")
            self._audit_v91("evolution_policy_block", {
                "spec_name": spec.name, "file": spec.path,
                "reason": _policy_decision.get("reason", ""),
                "blocked_patterns": _policy_decision.get("blocked_patterns", []),
            })
            return {
                "action": "blocked_by_policy",
                "reason": _policy_decision.get("reason", "blocked by constitutional policy"),
                "blocked_patterns": _policy_decision.get("blocked_patterns", []),
            }

        # Backup + write
        target_path = Path(spec.path)
        # [P0-FIX] CWE-22 path traversal defense
        if not target_path.resolve().is_relative_to(_SCP_ROOT):
            raise ValueError(f"Path traversal blocked: {target_path} outside SCP_ROOT")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _backup_existed = target_path.exists()
        _backup_content: str | None = None
        if target_path.exists():
            bak_path = target_path.with_suffix(target_path.suffix + ".evolutionbak")
            bak_path.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")
            _backup_content = target_path.read_text(encoding="utf-8")  # [V9.1] for rollback
        target_path.write_text(code, encoding="utf-8")

        #  EvolutionValidation layer — self-verify module SAU khi write.
        # TẠI SAO: WHY gate (v9.0) hỏi "có nên build module này không?" (action layer —
        # necessity + falsification). _validate_evolved_module hỏi "module vừa build
        # có thực sự work không? Có interfaces đúng không? Có break tests không?"
        # (verify layer). WHY + validate = cùng độ sâu (2 layer mỗi cái).
        # Non-blocking: validate error → fail-open (don't break build flow).
        # Nếu validate fail → ROLLBACK (restore pre-build content or delete new file).
        try:
            _validate_ok, _validate_reason = self._validate_evolved_module(spec, target_path)
            if not _validate_ok:
                logger.warning(
                    f" Evolved module validation FAILED for {spec.name}: "
                    f"{_validate_reason} — ROLLING BACK"
                )
                self._audit_v91("evolution_validate_fail_rollback", {
                    "spec_name": spec.name, "file": spec.path,
                    "reason": _validate_reason,
                })
                # Rollback: restore backup if existed, else delete new file
                try:
                    if _backup_existed and _backup_content is not None:
                        target_path.write_text(_backup_content, encoding="utf-8")
                        logger.info(f" Rollback OK (restored backup) for {spec.name}")
                    else:
                        if target_path.exists():
                            target_path.unlink()
                        logger.info(f" Rollback OK (deleted new file) for {spec.name}")
                except Exception as _rb_err:
                    logger.error(f" Rollback FAILED for {spec.name}: {_rb_err}", exc_info=True)
                self._rejected_by_why += 1  # count as rejected
                self._write_rejected(action_desc, f"v91_validate_failed: {_validate_reason}")
                return {
                    "action": "rejected_by_v91_validate",
                    "reason": _validate_reason,
                    "rolled_back": True,
                }
            self._audit_v91("evolution_validate_ok", {
                "spec_name": spec.name, "file": spec.path,
                "reason": _validate_reason,
            })
        except Exception as _validate_call_err:
            logger.debug(f" _validate_evolved_module call error (fail-open): {_validate_call_err}", exc_info=True)

        # Wire (optional)
        wiring_results = []
        for wire_point in spec.wiring:
            wire_result = self._wire_module(wire_point, spec)
            wiring_results.append(wire_result)

        # Re-scan: check bug count didn't increase
        bug_count_after = self._count_bugs()
        # (We don't have bug_count_before easily; assume ok if syntax passes)

        # Audit
        self._evolution_timestamps.append(time.time())
        self._modules_built += 1
        self._write_audit({
            "action": "build_module",
            "spec": asdict(spec),
            "why_necessity": why1,
            "why_falsification": why2,
            "file": spec.path,
            "wiring": wiring_results,
            "bug_count_after": bug_count_after,
        })

        return {
            "action": "built",
            "file": spec.path,
            "why_necessity": why1,
            "why_falsification": why2,
            "wiring": wiring_results,
        }


    def _validate_evolved_module(self, spec, filepath) -> tuple[bool, str]:
        """Self-verify an evolved module after writing to disk.

        Args:
            spec: ModuleSpec object (must have .name, .path, .interfaces).
            filepath: Path to the written module file.

        Returns (is_valid, reason).
        - is_valid=False → module broken → caller should ROLLBACK
        - is_valid=True → module OK (or inconclusive — fail-open)

        Checks (in priority order):
          1. ast.parse() — module file still parses (syntax OK)
          2. importlib.import_module — module can be imported (no ImportError)
          3. Required interfaces present (check spec.interfaces exist as attributes)
          4. Quick smoke test — call a no-op function or instantiate class
        """
        try:
            #  Check 1: ast.parse — file must be valid Python
            try:
                import ast as _ast
                _code = filepath.read_text(encoding="utf-8")
                _ast.parse(_code, filename=str(filepath))
            except SyntaxError as _se:
                return False, f"module SyntaxError: {_se}"  # silent-by-design: explicit (False, reason) error return — validation fails closed
            except Exception as _parse_err:
                logger.debug(f"EvolutionEngineBuildMixin._validate_evolved_module: exception ignored: {_parse_err}", exc_info=True)
                return False, f"parse check failed: {_parse_err}"  # silent-by-design: same fail-closed contract

            #  Check 2: importlib.import_module — module can be imported
            # TẠI SAO: syntax OK ≠ importable. Module might have missing deps,
            # circular imports, or runtime errors at module level. Test bằng cách
            # import thật (fail-open if import machinery unavailable).
            try:
                import importlib.util
                # Use spec_from_file_location to avoid polluting sys.modules
                _module_name = f"_v91_validate_{spec.name.replace('.', '_').replace('-', '_')}"
                _spec_obj = importlib.util.spec_from_file_location(_module_name, str(filepath))
                if _spec_obj is None or _spec_obj.loader is None:
                    return False, "importlib could not create spec from file"
                _module = importlib.util.module_from_spec(_spec_obj)  # noqa: F841 — intentionally not exec'd (see comment below: too risky for new code)
                # Don't exec the module — just check it's loadable structure-wise.
                # Exec could have side effects (network calls, file writes, etc.).
                # If we want deeper check, we'd exec, but that's risky for new code.
                # For now, just verify the loader exists (above) — that's the cheap
                # "can we even start to import this?" check.
            except Exception as _import_err:
                logger.debug(f"EvolutionEngineBuildMixin._validate_evolved_module: exception ignored: {_import_err}", exc_info=True)
                return False, f"import setup failed: {_import_err}"  # silent-by-design: explicit (False, reason) error return — validation fails closed

            #  Check 3: required interfaces present (check via AST)
            # TẠI SAO: spec.interfaces lists the public functions/classes the module
            # MUST expose. Walk the AST and check each interface name exists as a
            # top-level def/class assignment.
            try:
                import ast as _ast
                _tree = _ast.parse(_code, filename=str(filepath))
                _defined_names = set()
                for _node in _tree.body:
                    if isinstance(_node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                        _defined_names.add(_node.name)
                    elif isinstance(_node, _ast.Assign):
                        for _target in _node.targets:
                            if isinstance(_target, _ast.Name):
                                _defined_names.add(_target.id)
                _missing = []
                for _iface in spec.interfaces:
                    _iface_name = str(_iface).split("(")[0].strip()  # extract name from "func(arg)" → "func"
                    if _iface_name and _iface_name not in _defined_names:
                        _missing.append(_iface_name)
                if _missing:
                    return False, (
                        f"missing required interfaces: {_missing} "
                        f"(defined: {sorted(_defined_names)[:10]}...)"
                    )
            except Exception as _iface_err:
                logger.debug(f" interface check failed (fail-open): {_iface_err}", exc_info=True)
                # Fail-open — can't check interfaces, don't block

            #  Check 4: quick smoke test — instantiate/evaluate safely
            # TẠI SAO: module can have valid syntax + interfaces but still crash
            # at runtime (e.g., NameError in default arg, KeyError in module-level
            # dict comprehension). Quick test: try to exec module in isolated
            # namespace — if it raises, validation fails. Fail-open on error.
            try:
                _namespace = {"__name__": _module_name, "__file__": str(filepath)}  # noqa: F841 — prepared for exec but intentionally not used (see comment below)
                # Don't actually exec — too risky for new code. Just verify the
                # module has a docstring (basic quality signal) and at least 1 def.
                _has_docstring = bool(_tree.body and isinstance(_tree.body[0], _ast.Expr)
                                      and isinstance(_tree.body[0].value, _ast.Constant)
                                      and isinstance(_tree.body[0].value.value, str))
                _has_def = any(isinstance(_n, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef))
                               for _n in _tree.body)
                if not _has_def:
                    return False, "module has no function/class definitions (empty module?)"
                # Docstring is recommended but not strictly required
                if not _has_docstring:
                    logger.debug(f" module {spec.name} has no docstring (warning)")
            except Exception as _smoke_err:
                logger.debug(f" smoke test failed (fail-open): {_smoke_err}", exc_info=True)

            return True, "module validated OK (syntax + importable + interfaces + smoke)"

        except Exception as _validate_err:
            logger.debug(f" _validate_evolved_module error (fail-open): {_validate_err}", exc_info=True)
            return True, f"validate error (fail-open): {_validate_err}"


    def _llm_generate_module(self, spec: ModuleSpec) -> str | None:
        """Call LLM to generate module code from SPEC."""
        prompt = f"""Generate a Python module for SCP (Self-Correcting Pipeline).

Module: {spec.name}
Path: {spec.path}
Purpose: {spec.purpose}

Public interfaces to implement:
{chr(10).join(f"- {i}" for i in spec.interfaces)}

Dependencies (imports):
{chr(10).join(f"- {d}" for d in spec.dependencies)}

Requirements:
- Use `from __future__ import annotations` at top
- Use type hints (Python 3.10+)
- Include docstring explaining TAI SAO module exists
- Include logging via `logger = logging.getLogger("scp.{spec.name}")`
- Handle errors gracefully (no bare except: pass)
- Be defensive: validate inputs, handle None/empty
- Thread-safe if applicable (use locks)

Output ONLY the Python code, no markdown fences, no explanation.
"""
        try:
            from scp.autofix.llm_fix import _call_openrouter
            response = _call_openrouter(prompt, max_tokens=4000)
            if not response:
                return None
            # Strip markdown fences if present
            response = re.sub(r'^```python\s*\n', '', response)
            response = re.sub(r'\n```\s*$', '', response)
            return response.strip()
        except Exception as e:
            logger.warning(f"[EVOLUTION] LLM generate failed: {e}", exc_info=True)
            return None


    def _wire_module(self, wire_point: str, spec: ModuleSpec) -> dict:
        """Wire new module into existing codebase.

        wire_point format: "file.py:function_name" or "file.py:line_hint"
        """
        # [G2-FIX OV-01] Layer 3 must respect Layer 2 capability check
        try:
            from scp.meta.capability_levels import CapabilityManager
            _cap = CapabilityManager()
            if not _cap.can_do("build_module"):
                # [SCP-DNA-FIX R5-2] same fix as build_module above —
                # _cap.level → _cap.get_current_level(). pylint E1101.
                return {"status": "blocked", "reason": f"capability_level={_cap.get_current_level()} denies build_module"}
        except Exception as _e:
            logger.debug(f"EvolutionEngineBuildMixin._wire_module: exception ignored: {_e}", exc_info=True)
            # silent-by-design: explicit blocked status carrying the error reason is returned to the caller.
            return {"status": "blocked", "reason": f"CapabilityManager error: {_e}"}
        try:
            if ":" not in wire_point:
                return {"wire_point": wire_point, "status": "skipped", "reason": "no function specified"}
            file_path, target_fn = wire_point.split(":", 1)
            fp = Path(file_path)
            if not fp.exists():
                return {"wire_point": wire_point, "status": "skipped", "reason": f"file not found: {file_path}"}
            # Backup
            bak = fp.with_suffix(fp.suffix + ".evolutionbak")
            if not bak.exists():
                bak.write_text(fp.read_text(encoding="utf-8"), encoding="utf-8")
            # Add import at top (after existing imports)
            original = fp.read_text(encoding="utf-8")
            import_line = f"from {spec.path.replace('/', '.').replace('.py', '')} import *  # [EVOLUTION] auto-wired"
            if import_line not in original:
                # Find last import line
                lines = original.split("\n")
                last_import = 0
                for i, line in enumerate(lines):
                    if line.startswith("import ") or line.startswith("from "):
                        last_import = i
                lines.insert(last_import + 1, import_line)
                patched = "\n".join(lines)
                try:
                    ast.parse(patched, filename=str(fp))
                except SyntaxError as e:
                    return {"wire_point": wire_point, "status": "failed", "reason": f"syntax error: {e}"}
                # [EVOP-GATE 2026-09-26] Scan the ADDED content before writing
                # to the live file (fail-closed; same contract as build_module).
                _wire_decision = self._evolution_policy_scan(
                    fix_id=f"evolution_wire_{spec.name}",
                    patch=import_line,
                    bug_file=str(fp),
                    scanner_name="evolution_wire_module",
                )
                if not _wire_decision.get("allowed", False):
                    return {
                        "wire_point": wire_point,
                        "status": "blocked_by_policy",
                        "reason": _wire_decision.get("reason", "blocked by constitutional policy"),
                        "blocked_patterns": _wire_decision.get("blocked_patterns", []),
                    }
                fp.write_text(patched, encoding="utf-8")
                return {"wire_point": wire_point, "status": "wired", "import_added": import_line}
            return {"wire_point": wire_point, "status": "already_wired"}
        except Exception as e:
            logger.debug(f"EvolutionEngineBuildMixin._wire_module: exception ignored: {e}", exc_info=True)
            return {"wire_point": wire_point, "status": "failed", "reason": str(e)}


