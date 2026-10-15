"""Compat helpers for FastAPI route introspection (AUDIT-R2 2026-10-01).

FastAPI 0.142 wraps ``include_router`` results in ``_IncludedRouter``
containers instead of flattening APIRoutes onto ``app.routes``. The
helpers here collect route paths recursively so the same assertions
hold on both the old (flattened) and the new (nested) layout.

Strictness is unchanged: a prefix only shows up here if its router is
actually mounted on the app — an unmounted router contributes nothing
to the collected paths, exactly like the previous flatten-based scan.
"""

from __future__ import annotations

from typing import Iterable, Iterator


def iter_route_paths(routes: Iterable) -> Iterator[str]:
    """Yield every concrete route path from a route table, recursing into
    nested ``_IncludedRouter`` containers (fastapi>=0.142) transparently."""
    for route in routes:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            yield path
        # fastapi>=0.142: _IncludedRouter keeps the original APIRouter and
        # has no top-level .path; older FastAPI already flattens, so this
        # attribute is simply absent there.
        nested = getattr(route, "original_router", None)
        if nested is not None:
            yield from iter_route_paths(getattr(nested, "routes", []))
