"""Generate SBOM (Software Bill of Materials) cho supply-chain audit."""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

def generate():
    root = Path(__file__).resolve().parents[1]
    req_file = root / "scp" / "requirements.txt"
    packages = []
    for line in req_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        if "==" in line:
            name, version = line.split("==", 1)
            packages.append({"name": name.strip(), "version": f"={version.strip()}", "type": "pinned"})
        elif ">=" in line:
            name, version = line.split(">=", 1)
            packages.append({"name": name.strip(), "version": f">={version.strip()}", "type": "minimum"})
        else:
            packages.append({"name": line.strip(), "version": "unspecified", "type": "unpinned"})

    # Get installed versions
    result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    installed = {}
    for line in result.stdout.splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            installed[name.lower().replace("-", "_")] = version

    for pkg in packages:
        key = pkg["name"].lower().replace("-", "_")
        pkg["installed_version"] = installed.get(key, "NOT INSTALLED")

    sbom = {
        "spdx_version": "SPDX-2.3",
        "spdx_id": "SPDXRef-DOCUMENT",
        "name": "SCP-Agent-Runtime",
        "created": datetime.now(timezone.utc).isoformat(),
        "packages": packages,
        "total": len(packages),
    }
    out = root / "reports" / "sbom.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sbom, indent=1), encoding="utf-8")
    print(f"SBOM written: {out} ({len(packages)} packages)")

if __name__ == "__main__":
    generate()
