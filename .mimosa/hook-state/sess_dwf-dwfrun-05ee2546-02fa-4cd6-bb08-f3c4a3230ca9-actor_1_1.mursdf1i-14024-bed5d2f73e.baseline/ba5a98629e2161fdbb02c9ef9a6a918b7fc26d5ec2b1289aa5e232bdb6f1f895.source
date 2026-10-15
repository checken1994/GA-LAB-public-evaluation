import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTES = ROOT / "dashboard" / "src" / "app" / "api"
ROUTE_LISTING = ROUTES / "scp" / "routes" / "route.ts"


_ALLOWED_EXPORTS = re.compile(
    r"^\s*export\s+(?:async\s+)?(?:function\s+"
    r"(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)|"
    r"const\s+(?:dynamic|revalidate|runtime|preferredRegion|fetchCache|"
    r"maxDuration|dynamicParams|generateStaticParams))\b"
)


def test_route_listing_does_not_export_non_route_symbols():
    source = ROUTE_LISTING.read_text(encoding="utf-8")
    assert "export const SCP_ROUTES" not in source
    assert "export interface ScpRoute" not in source


def test_api_routes_have_only_next_allowed_runtime_exports():
    violations = []
    for path in sorted(ROUTES.rglob("route.ts")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("export ") and not _ALLOWED_EXPORTS.match(line):
                violations.append(f"{path.relative_to(ROOT)}:{number}:{line.strip()}")
    assert not violations, "non-Next route exports: " + "; ".join(violations)


def test_route_listing_gateway_hint_matches_isolated_runtime_contract():
    source = ROUTE_LISTING.read_text(encoding="utf-8")
    assert 'gatewayPattern: "Append ?XTransformPort=8000' in source
