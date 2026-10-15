"""Partition package — extracted from `core/data_partitioner.py` in Task 10-B.

Sub-modules:
  - shard:    DataPartitioner + domain/keyword constants + helpers
  - rotate:   ThreeTierCache (HOT RAM + WARM SQLite + COLD pipeline)
  - archive:  BypassLessonsStore + TTLExpirer + migrate_old_to_new

All public symbols re-exported here — backward compatible.
"""
from scp.core.partition.archive import (
    BypassLessonsStore,
    TTLExpirer,
    migrate_old_to_new,
)
from scp.core.partition.rotate import ThreeTierCache
from scp.core.partition.shard import (
    _BYPASS_ENCRYPTOR_LOCK,
    _BYPASS_ENCRYPTOR_SINGLETON,
    DATA_DIR,
    DB_PATH,
    DOMAIN_KEYWORDS,
    DOMAIN_TABLES,
    TTL_BYPASS_LOG_DAILY,
    TTL_ERROR_STORE_DAILY,
    TTL_PENDING_RESOLUTIONS,
    TTL_QUESTION_LOG,
    TTL_VERDICT_CACHE,
    TTL_VERDICT_CACHE_DB,
    DataPartitioner,
    _get_bypass_encryptor,
    detect_domain,
    hash_question,
)

__all__ = [
    # shard
    "DataPartitioner",
    "DATA_DIR",
    "DB_PATH",
    "DOMAIN_KEYWORDS",
    "DOMAIN_TABLES",
    "TTL_BYPASS_LOG_DAILY",
    "TTL_ERROR_STORE_DAILY",
    "TTL_PENDING_RESOLUTIONS",
    "TTL_QUESTION_LOG",
    "TTL_VERDICT_CACHE",
    "TTL_VERDICT_CACHE_DB",
    "detect_domain",
    "hash_question",
    "_get_bypass_encryptor",
    "_BYPASS_ENCRYPTOR_SINGLETON",
    "_BYPASS_ENCRYPTOR_LOCK",
    # rotate
    "ThreeTierCache",
    # archive
    "BypassLessonsStore",
    "TTLExpirer",
    "migrate_old_to_new",
]
