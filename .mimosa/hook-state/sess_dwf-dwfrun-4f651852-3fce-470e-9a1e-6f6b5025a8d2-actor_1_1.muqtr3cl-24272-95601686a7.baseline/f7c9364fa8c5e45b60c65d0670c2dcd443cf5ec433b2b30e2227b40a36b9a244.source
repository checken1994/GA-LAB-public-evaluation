# Auto-extracted from llm_fix.py
from __future__ import annotations

import logging
import re as _re_module
from pathlib import Path

logger = logging.getLogger(__name__)

def _generate_bare_except_fix(bug) -> str | None:
    """Generate fix for BareExceptPass bugs WITHOUT calling LLM.

    Pattern: `except Exception as e: pass` → `except Exception as e: logger.exception("...")`

    Returns search-replace block, or None if not a BareExceptPass bug.
    """
    if bug.bug_type != 'BareExceptPass':
        return None
    filepath = Path(bug.file)
    if not filepath.exists():
        return None
    try:
        source = filepath.read_text(encoding='utf-8')
        lines = source.splitlines()
        bug_line_idx = bug.line - 1
        if bug_line_idx >= len(lines):
            return None
        except_line = lines[bug_line_idx].rstrip()
        except_match = _re_module.match('^(\\s*)(except\\s+)(\\w+)(\\s+as\\s+\\w+)?\\s*:(\\s*#.*)?$', except_line)
        if not except_match:
            single_match = _re_module.match('^(\\s*)(except\\s+)(\\w+)(\\s+as\\s+\\w+)?\\s*:\\s*pass\\s*(?:#.*)?$', except_line)
            if single_match:
                indent = single_match.group(1)
                except_kw = single_match.group(2)
                exc_type = single_match.group(3)
                old_block = f'{indent}{except_kw}{exc_type}: pass'
                new_block = f'{indent}{except_kw}{exc_type} as e:\n{indent}    logger.exception(f"[{filepath.name}:{bug.line}] silenced exception")'
                return f'<<<<<<< SEARCH\n{old_block}\n=======\n{new_block}\n>>>>>>> REPLACE'
            return None
        indent = except_match.group(1)
        except_kw = except_match.group(2)
        exc_type = except_match.group(3)
        as_clause = except_match.group(4) or ''
        except_comment = except_match.group(5) or ''
        pass_line_idx = bug_line_idx + 1
        while pass_line_idx < len(lines):
            pass_line = lines[pass_line_idx].rstrip()
            if pass_line.strip() == '':
                pass_line_idx += 1
                continue
            if pass_line.strip() == 'pass' or _re_module.match('^\\s*pass\\s*#', pass_line):
                pass_indent = _re_module.match('^(\\s*)', pass_line).group(1)
                old_block = f'{except_line}\n{pass_line.rstrip()}'
                if not as_clause:
                    new_except = f'{except_kw}{exc_type} as e:'
                    new_pass = f'logger.debug(f"[{filepath.name}:{bug.line}] silenced: {{e}}")'
                else:
                    new_except = f'{except_kw}{exc_type}{as_clause}:'
                    var_name = as_clause.strip().split()[-1] if as_clause.strip() else 'e'
                    new_pass = f'logger.debug(f"[{filepath.name}:{bug.line}] silenced: {{{var_name}}}")'
                new_except = f'{new_except}{except_comment}'
                new_block = f'{indent}{new_except}\n{pass_indent}{new_pass}'
                return f'<<<<<<< SEARCH\n{old_block}\n=======\n{new_block}\n>>>>>>> REPLACE'
            else:
                return None
        return None
    except Exception as e:
        logger.warning(f'[llm_fix] BareExceptPass fix generation failed: {e}', exc_info=True)
        return None
