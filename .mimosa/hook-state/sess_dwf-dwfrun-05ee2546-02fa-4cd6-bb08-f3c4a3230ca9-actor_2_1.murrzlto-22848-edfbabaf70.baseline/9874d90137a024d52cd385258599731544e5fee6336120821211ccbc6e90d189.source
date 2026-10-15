"""Source Identity authority (26-P0.06).

Source identity is deliberately conservative: normalization may remove syntax
that cannot affect identity (URL fragments, default ports, host case) but never
sorts/drops arbitrary query parameters or assumes two publishers are the same.

A source_id identifies the logical source; evidence_id remains an occurrence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

from scp.contracts.ids import new_id
from scp.contracts.time import now_utc_iso
from scp.persistence import FoundationDB


class SourceKind(str, Enum):
    WEB_DOCUMENT = "WEB_DOCUMENT"
    API_ENDPOINT = "API_ENDPOINT"
    REPOSITORY = "REPOSITORY"
    FILE = "FILE"
    SERVICE = "SERVICE"
    RUNTIME = "RUNTIME"
    HUMAN_ATTESTATION = "HUMAN_ATTESTATION"


def _idna_host(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError(f"invalid hostname: {host!r}") from exc


def canonicalize_url(value: str) -> str:
    """Conservative URL identity normalization.

    - http/https only for web identities;
    - lower-case/IDNA host;
    - strip fragment;
    - drop only default :80/:443 ports;
    - preserve path AND query byte ordering/semantics.
    """
    raw = str(value or "").strip()
    parts = urlsplit(raw)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("web source identity requires http/https URL")
    if not parts.hostname:
        raise ValueError("URL must contain a hostname")
    host = _idna_host(parts.hostname)
    port = parts.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    _userinfo = ""
    if parts.username is not None or parts.password is not None:
        # Credentials are not a valid part of a persisted source identity.
        raise ValueError("URL source identity must not contain credentials")
    netloc = host if port is None else f"{host}:{port}"
    path = parts.path or "/"
    return urlunsplit(SplitResult(scheme, netloc, path, parts.query, ""))


def canonicalize_repository(*, repository: str, path: str | None = None, commit_sha: str | None = None) -> str:
    repo = str(repository or "").strip().strip("/")
    if repo.count("/") != 1:
        raise ValueError("repository identity must be owner/name")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise ValueError("repository identity must be owner/name")
    normalized_path = (path or "").strip().lstrip("/")
    sha = (commit_sha or "").strip().lower()
    if sha and (len(sha) < 7 or any(ch not in "0123456789abcdef" for ch in sha)):
        raise ValueError("commit_sha must be hexadecimal when supplied")
    suffix = f"@{sha}" if sha else "@UNPINNED"
    path_suffix = f":{normalized_path}" if normalized_path else ""
    return f"github:{owner.lower()}/{name.lower()}{suffix}{path_suffix}"


def canonicalize_source(kind: SourceKind | str, identity: str, *, metadata: dict | None = None) -> str:
    k = kind if isinstance(kind, SourceKind) else SourceKind(str(kind).strip().upper())
    meta = metadata or {}
    if k in {SourceKind.WEB_DOCUMENT, SourceKind.API_ENDPOINT}:
        return canonicalize_url(identity)
    if k is SourceKind.REPOSITORY:
        return canonicalize_repository(
            repository=identity,
            path=meta.get("path"),
            commit_sha=meta.get("commit_sha"),
        )
    value = str(identity or "").strip()
    if not value:
        raise ValueError("source identity cannot be empty")
    return f"{k.value.lower()}:{value}"


_SOURCE_MIGRATIONS = [
    (
        "0002_source_identity",
        [
            """CREATE TABLE IF NOT EXISTS sources (
                   source_id TEXT PRIMARY KEY,
                   kind TEXT NOT NULL,
                   original_identity TEXT NOT NULL,
                   canonical_identity TEXT NOT NULL,
                   publisher TEXT,
                   domain TEXT,
                   canonicalization_version INTEGER NOT NULL DEFAULT 1,
                   metadata_json TEXT NOT NULL,
                   first_observed_at TEXT NOT NULL,
                   last_observed_at TEXT NOT NULL,
                   UNIQUE(kind, canonical_identity))""",
            "CREATE INDEX IF NOT EXISTS idx_sources_canonical ON sources(kind, canonical_identity)",
        ],
    ),
]


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    kind: str
    original_identity: str
    canonical_identity: str
    publisher: str | None
    domain: str | None
    canonicalization_version: int
    metadata: dict
    first_observed_at: str
    last_observed_at: str


class SourceStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db = FoundationDB(db_path, _SOURCE_MIGRATIONS)

    def register(
        self,
        *,
        kind: SourceKind | str,
        identity: str,
        publisher: str | None = None,
        metadata: dict | None = None,
        observed_at: str | None = None,
    ) -> SourceRecord:
        k = kind if isinstance(kind, SourceKind) else SourceKind(str(kind).strip().upper())
        meta = dict(metadata or {})
        canonical = canonicalize_source(k, identity, metadata=meta)
        ts = observed_at or now_utc_iso()
        domain = None
        if k in {SourceKind.WEB_DOCUMENT, SourceKind.API_ENDPOINT}:
            domain = urlsplit(canonical).hostname
        existing = self.db.query(
            "SELECT * FROM sources WHERE kind=? AND canonical_identity=?",
            (k.value, canonical),
        )
        if existing:
            # Identity is stable. Only the observed-at projection advances; the
            # original identity/provenance is not silently rewritten.
            self.db.execute(
                "UPDATE sources SET last_observed_at=? WHERE source_id=?",
                (ts, existing[0]["source_id"]),
            )
            self.db._conn.commit()
            return self.get(existing[0]["source_id"])
        source_id = new_id("src")
        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO sources
                   (source_id,kind,original_identity,canonical_identity,publisher,domain,
                    canonicalization_version,metadata_json,first_observed_at,last_observed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    source_id,
                    k.value,
                    str(identity).strip(),
                    canonical,
                    publisher,
                    domain,
                    1,
                    json.dumps(meta, ensure_ascii=False, sort_keys=True),
                    ts,
                    ts,
                ),
            )
        return self.get(source_id)

    def get(self, source_id: str) -> SourceRecord:
        rows = self.db.query("SELECT * FROM sources WHERE source_id=?", (source_id,))
        if not rows:
            raise KeyError(source_id)
        row = rows[0]
        return SourceRecord(
            source_id=row["source_id"],
            kind=row["kind"],
            original_identity=row["original_identity"],
            canonical_identity=row["canonical_identity"],
            publisher=row["publisher"],
            domain=row["domain"],
            canonicalization_version=int(row["canonicalization_version"]),
            metadata=json.loads(row["metadata_json"] or "{}"),
            first_observed_at=row["first_observed_at"],
            last_observed_at=row["last_observed_at"],
        )

    def close(self) -> None:
        self.db.close()
