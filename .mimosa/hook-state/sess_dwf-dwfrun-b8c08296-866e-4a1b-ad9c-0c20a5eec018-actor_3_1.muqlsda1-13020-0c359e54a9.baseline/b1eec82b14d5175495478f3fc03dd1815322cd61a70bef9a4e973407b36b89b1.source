# Auto-extracted from llm_fix.py
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("scp.autofix.llm_fix.deterministic")

def _generate_deterministic_fix(bug) -> str | None:
    """Generate fix cho lỗi đơn giản KHÔNG cần LLM.

    DNA #7: AutoFix safe — có cấp bậc.
    Lỗi đơn giản = Tier 1 (auto-fix no log) → deterministic, không LLM.
    Lỗi phức tạp = Tier 2+ → gọi LLM.

    Returns search-replace block, or None if not a simple bug.
    """
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        source = filepath.read_text(encoding='utf-8')
        lines = source.splitlines()
        bug_line_idx = bug.line - 1
        if bug_line_idx >= len(lines):
            return None
        bug_line = lines[bug_line_idx]
        bug_type = bug.bug_type
        if bug_type == 'RuffSecurity_S101' or bug_type == 'S101':
            import re
            m = re.match('^(\\s*)assert\\s+(.+)$', bug_line)
            if m:
                indent = m.group(1)
                condition = m.group(2).strip()
                old = bug_line.rstrip()
                new = f"{indent}if not ({condition}):\n{indent}    raise AssertionError(f'Assertion failed: {condition}')"
                return f'<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE'
        if bug_type in ('RuffSecurity_S110', 'S110', 'RuffSecurity_S112', 'S112'):
            import re
            next_line_raw = lines[bug_line_idx + 1] if bug_line_idx + 1 < len(lines) else ''
            next_line_stripped = next_line_raw.strip()
            if next_line_stripped in ('continue', 'pass'):
                m = re.match('^(\\s*)(except\\s+.*)$', bug_line)
                if m:
                    indent = m.group(1)
                    except_clause = m.group(2).rstrip().rstrip(':')
                    next_indent = next_line_raw[:len(next_line_raw) - len(next_line_raw.lstrip())]
                    old = f'{bug_line.rstrip()}\n{next_line_raw.rstrip()}'
                    new = f"{indent}{except_clause} as _e:\n{next_indent}logger.warning(f'Silent except: {{_e!r}}')\n{next_line_raw.rstrip()}"
                    return f'<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE'
        if bug_type in ('F401', 'UnusedImport'):
            old = bug_line.rstrip()
            return f'<<<<<<< SEARCH\n{old}\n=======\n>>>>>>> REPLACE'
        if bug_type in ('F841', 'UnusedVariable'):
            import re
            m = re.match('^(\\s*)(\\w+)\\s*=', bug_line)
            if m:
                indent = m.group(1)
                var_name = m.group(2)
                old = bug_line.rstrip()
                new = bug_line.rstrip().replace(var_name, f'_{var_name}', 1)
                return f'<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE'
        if bug_type in ('E702',):
            import re
            m = re.match('^(\\s*)(.+);(.+)$', bug_line)
            if m:
                indent = m.group(1)
                first = m.group(2).strip()
                second = m.group(3).strip()
                old = bug_line.rstrip()
                new = f'{indent}{first}\n{indent}{second}'
                return f'<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE'
        if bug_type in ('B007',):
            import re
            m = re.match('^(\\s*)for\\s+(\\w+)\\s+in\\s+', bug_line)
            if m:
                var_name = m.group(2)
                old = bug_line.rstrip()
                new = bug_line.rstrip().replace(f' {var_name} ', f' _{var_name} ', 1)
                return f'<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE'
        return None
    except Exception as recipe_err:
        # silent-by-design: documented default — no deterministic recipe applies,
        # caller falls back to the LLM path.
        logger.debug("deterministic fix recipe crashed, falling back to LLM: %s", recipe_err, exc_info=True)
        return None
