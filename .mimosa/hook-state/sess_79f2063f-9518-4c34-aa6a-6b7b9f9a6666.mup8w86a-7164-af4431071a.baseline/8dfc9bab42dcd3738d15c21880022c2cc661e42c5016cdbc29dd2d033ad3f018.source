"""Create a first-run .env without shipping weak required secrets.

The script is intentionally create-only: an existing .env is never modified.
It copies the documented root template, generates the required JWT/admin
secrets, and creates the production auth-password secret outside tracked
source under `.private-secrets/`.
"""
from __future__ import annotations

import argparse
import secrets
from pathlib import Path


def _set_key(lines: list[str], key: str, value: str) -> None:
    active = f"{key}="
    commented = f"# {key}="
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(active) or stripped.startswith(commented):
            lines[i] = f"{key}={value}"
            return
    lines.append(f"{key}={value}")


def bootstrap(template: Path, output: Path, secret_dir: Path) -> bool:
    if output.exists():
        print(f"[bootstrap] keep existing {output}")
        return False
    if not template.is_file():
        raise FileNotFoundError(f"missing env template: {template}")

    secret_dir.mkdir(parents=True, exist_ok=True)
    auth_password_path = secret_dir / "scp-auth-password"
    if not auth_password_path.exists():
        auth_password_path.write_text(secrets.token_urlsafe(32), encoding="utf-8")

    lines = template.read_text(encoding="utf-8-sig").splitlines()
    jwt_secret = secrets.token_hex(32)
    admin_key = secrets.token_urlsafe(32)
    try:
        auth_ref = auth_password_path.relative_to(output.parent).as_posix()
    except ValueError:
        auth_ref = str(auth_password_path.resolve())

    _set_key(lines, "SCP_JWT_SECRET", jwt_secret)
    _set_key(lines, "SCP_ADMIN_KEY", admin_key)
    _set_key(lines, "SCP_AUTH_PASSWORD_FILE", auth_ref)

    if len(jwt_secret) < 32 or len(admin_key) < 8:
        raise RuntimeError("generated required secrets violate config contract")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[bootstrap] created {output}")
    print(f"[bootstrap] created auth secret {auth_password_path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=".env.example")
    parser.add_argument("--output", default=".env")
    parser.add_argument("--secret-dir", default=".private-secrets")
    args = parser.parse_args()

    bootstrap(Path(args.template), Path(args.output), Path(args.secret_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
