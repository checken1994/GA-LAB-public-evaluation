import hashlib


class ImmutableSourceSnapshot:
    def __init__(self, source_files: dict[str, str]):
        self._files = {k: v for k, v in source_files.items()}

    def get_file(self, path: str) -> str | None:
        return self._files.get(path)

    def manifest_hash(self) -> str:
        keys = sorted(self._files.keys())
        content = "".join([f"{k}:{self._files[k]}" for k in keys])
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

class MutableExecutionOverlay:
    def __init__(self, base_snapshot: ImmutableSourceSnapshot):
        self._base = base_snapshot
        self._overlay: dict[str, str] = {}

    def write_file(self, path: str, content: str) -> None:
        if path is None or content is None:
            raise ValueError("Path and content must be valid")
        self._overlay[path] = content

    def read_file(self, path: str) -> str | None:
        if path in self._overlay:
            return self._overlay[path]
        return self._base.get_file(path)

class SnapshotAuthority:
    """
    Separates immutable source snapshot from mutable hermetic execution overlay.
    """
    def __init__(self, source_files: dict[str, str]):
        self._immutable_snapshot = ImmutableSourceSnapshot(source_files)
        self._expected_hash = self._immutable_snapshot.manifest_hash()
        self._tampered = False

    def get_immutable_snapshot(self) -> ImmutableSourceSnapshot:
        return self._immutable_snapshot

    def create_execution_overlay(self) -> MutableExecutionOverlay:
        return MutableExecutionOverlay(self._immutable_snapshot)

    def verify_integrity(self) -> bool:
        if self._tampered:
            return False
        return self._immutable_snapshot.manifest_hash() == self._expected_hash

    def tamper(self) -> None:
        """Simulate tampering with the snapshot boundary."""
        self._tampered = True
        self._immutable_snapshot._files["tampered"] = "yes"
