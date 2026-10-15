# Auto-extracted from llm_fix.py
from __future__ import annotations

import re


def _extract_search_replace_block(llm_response: str) -> str | None:
    """Extract the SEARCH/REPLACE (or legacy OLD/NEW) block from LLM response.

    [OPT-30] Updated to accept BOTH formats:
      - New canonical: <<<<<<< SEARCH / ======= / >>>>>>> REPLACE
      - Legacy:        <<<<<<< OLD    / ======= / >>>>>>> NEW  (backward compat)

    Both forms are normalized to the canonical `<<<<<<< SEARCH ... >>>>>>> REPLACE`
    output so downstream _apply_fix() only needs to handle one format.

    [FIX #25] TẠI SAO: LLMs sometimes forget the closing marker suffix
    (output `>>>>>>>` instead of `>>>>>>> REPLACE` or `>>>>>>> NEW`).
    Also sometimes use `======` (5 equals) instead of `=======` (7 equals).
    Reality > Model: tested Bug #3 → LLM output `>>>>>>>` (no NEW), regex
    didn't match → patched=False. After fix: regex accepts `>>>>>>>` with
    or without a trailing identifier suffix, and 5-7 equals.
    """
    if not llm_response:
        return None
    sr_pattern = re.compile('<<<<<<<\\s*SEARCH\\s*\\n(.*?)\\n={5,7}\\s*\\n(.*?)\\n>>>>>>>\\s*(?:REPLACE)?\\s*', re.DOTALL)
    m = sr_pattern.search(llm_response)
    if m:
        return f'<<<<<<< SEARCH\n{m.group(1)}\n=======\n{m.group(2)}\n>>>>>>> REPLACE'
    old_pattern = re.compile('<<<<<<<\\s*OLD\\s*\\n(.*?)\\n={5,7}\\s*\\n(.*?)\\n>>>>>>>\\s*(?:NEW)?\\s*', re.DOTALL)
    m = old_pattern.search(llm_response)
    if m:
        return f'<<<<<<< SEARCH\n{m.group(1)}\n=======\n{m.group(2)}\n>>>>>>> REPLACE'
    fenced = re.search('```(?:python)?\\s*\\n(.*?)\\n```', llm_response, re.DOTALL)
    if fenced:
        return None
    return None
