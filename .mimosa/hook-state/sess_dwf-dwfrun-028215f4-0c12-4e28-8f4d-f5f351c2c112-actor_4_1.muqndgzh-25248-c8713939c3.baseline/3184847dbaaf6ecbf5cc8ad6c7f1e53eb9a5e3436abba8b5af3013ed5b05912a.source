from pathlib import Path

def rep(path, old, new, count=1):
    p = Path(path)
    src = p.read_text(encoding='utf-8')
    found = src.count(old)
    assert found == count, f"{path}: anchor x{found} (want {count}): {old[:70]!r}"
    p.write_text(src.replace(old, new), encoding='utf-8')
    print(f"OK {path} x{count}")

# ============ logger setup where missing ============
rep('scp/core/antibody.py',
    "import os\nimport re\n",
    "import logging\nimport os\nimport re\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/call_session_hub.py',
    "import asyncio\nimport json\nimport secrets\nimport time\nimport uuid\n",
    "import asyncio\nimport json\nimport logging\nimport secrets\nimport time\nimport uuid\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/context_pruner.py',
    "import ast\nimport re\nfrom typing import Any\n",
    "import ast\nimport logging\nimport re\nfrom typing import Any\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/hypothesis_zone.py',
    "import os\nimport sqlite3\nfrom datetime import datetime\n",
    "import logging\nimport os\nimport sqlite3\nfrom datetime import datetime\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/policy_materializer.py',
    "import hashlib\nimport json\nimport os\nimport shutil\n",
    "import hashlib\nimport json\nimport logging\nimport os\nimport shutil\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/file_mutex.py',
    "import contextlib\nimport os\nimport time\n",
    "import contextlib\nimport logging\nimport os\nimport time\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/fitness_engine.py',
    "import ast\nimport hashlib\nimport json\nimport operator\n",
    "import ast\nimport hashlib\nimport json\nimport logging\nimport operator\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/subsystem_telemetry.py',
    "import asyncio\nimport hashlib\nimport json\nimport os\nimport sqlite3\nimport threading\nimport time\nimport uuid\n",
    "import asyncio\nimport hashlib\nimport json\nimport logging\nimport os\nimport sqlite3\nimport threading\nimport time\nimport uuid\n\nlogger = logging.getLogger(__name__)\n")

rep('scp/core/fast_learning_engine_parts/fastlearningengine.py',
    "import asyncio\nimport json\nimport logging\nimport os\nimport random\nimport re\nimport sqlite3\nimport threading\nimport time\n",
    "import asyncio\nimport json\nimport logging\nimport os\nimport random\nimport re\nimport sqlite3\nimport threading\nimport time\n\nlogger = logging.getLogger(__name__)\n")

print("logger setup done")
