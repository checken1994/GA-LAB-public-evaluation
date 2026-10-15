"""[F-05 audit-r2 2026-10-01] __main__ env loader fallback must survive a
missing python-dotenv.

Causal chain (audit probe ``probe2_main_logger_nameerror``, OBSERVED):
  scp/__main__.py::_load_env_at_startup catches ImportError from
  ``from dotenv import load_dotenv`` but its except body called
  ``logger.debug(...)`` — while ``logger`` is only bound AFTER the function
  runs (module level, line ~95). On an environment without python-dotenv the
  loader therefore died with ``NameError: name 'logger' is not defined``
  instead of running the built-in manual parser fallback.

Pinned contract (executed in a SUBPROCESS against the REAL working-tree
``scp/__main__.py``, via a sandbox fake repo root so the loader's
``Path(__file__).parent.parent/.env`` fallback branch is reachable without
touching the real repo .env):
  1. No NameError when dotenv is missing (process exits 0).
  2. The fallback parser actually RUNS: keys from the sandbox .env land in
     os.environ.
  3. The fallback is visible (stderr notice) — fail-loudly, not silent.
  4. Control: with the explicit SCP_ENV_FILE boundary, keys still apply.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_FALLBACK_PROBE = """
import sys
# Simulate a deployment WITHOUT python-dotenv: any `import dotenv` /
# `from dotenv import ...` now raises ImportError (None in sys.modules).
sys.modules['dotenv'] = None
import os
os.environ.pop('SCP_ENV_FILE', None)
sys.path.insert(0, r'{sandbox}')
# Importing the entry module executes _load_env_at_startup() at module scope;
# __file__ of the sandboxed copy resolves the sandbox root -> sandbox/.env.
import scp.__main__
loaded = os.environ.get('SCP_MAIN_FALLBACK_PROBE')
assert loaded == 'ok-f05', f'fallback parser did not run: SCP_MAIN_FALLBACK_PROBE={{loaded!r}}'
print('F05-FALLBACK-OK')
"""

_EXPLICIT_PROBE = """
import os
import sys
os.environ['SCP_ENV_FILE'] = r'{env_file}'
sys.path.insert(0, r'{repo_root}')
import scp.__main__
assert os.environ.get('SCP_MAIN_EXPLICIT_PROBE') == 'ok-explicit', (
    'explicit env file keys must apply')
print('F05-EXPLICIT-OK')
"""


def _make_sandbox(tmp_path: Path) -> Path:
    """Fake repo root whose scp/__main__.py is the REAL working-tree file."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "scp").mkdir()
    shutil.copy2(_REPO_ROOT / "scp" / "__main__.py", sandbox / "scp" / "__main__.py")
    # Package shim: keep the SANDBOX package dir FIRST in __path__ (so
    # scp.__main__ resolves to the sandboxed copy whose parent.parent is the
    # sandbox root), then extend with the REAL repo scp/ dir for every other
    # submodule (production_guard, release_identity, ...).
    real_pkg_dir = str((_REPO_ROOT / "scp")).replace("\\", "\\\\")
    sandbox_pkg_dir = str((sandbox / "scp")).replace("\\", "\\\\")
    (sandbox / "scp" / "__init__.py").write_text(
        f"__path__ = [r'{sandbox_pkg_dir}', r'{real_pkg_dir}']\n"
        "from scp.core.release_identity import RELEASE_VERSION\n"
        "__version__ = RELEASE_VERSION\n",
        encoding="utf-8",
    )
    return sandbox


def test_env_loader_fallback_runs_without_dotenv(tmp_path):
    sandbox = _make_sandbox(tmp_path)
    (sandbox / ".env").write_text("SCP_MAIN_FALLBACK_PROBE=ok-f05\n", encoding="utf-8")
    probe = _FALLBACK_PROBE.format(sandbox=str(sandbox).replace("\\", "\\\\"))
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=110,
    )
    assert proc.returncode == 0, (
        "env loader crashed without dotenv (F-05 regression)\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    assert "F05-FALLBACK-OK" in proc.stdout
    assert "NameError" not in proc.stderr, (
        "F-05 regression: logger referenced before binding in the "
        f"dotenv-missing branch\nstderr={proc.stderr!r}"
    )
    # Fail-loudly contract: the fallback must be observable on stderr.
    assert "python-dotenv unavailable" in proc.stderr


def test_env_loader_explicit_file_applies_keys_with_dotenv_present(tmp_path):
    """Control: with the explicit SCP_ENV_FILE boundary, keys still apply."""
    env_file = tmp_path / "explicit.env"
    env_file.write_text("SCP_MAIN_EXPLICIT_PROBE=ok-explicit\n", encoding="utf-8")
    probe = _EXPLICIT_PROBE.format(
        env_file=str(env_file).replace("\\", "\\\\"),
        repo_root=str(_REPO_ROOT).replace("\\", "\\\\"),
    )
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=110,
    )
    assert proc.returncode == 0, proc.stderr
    assert "F05-EXPLICIT-OK" in proc.stdout
