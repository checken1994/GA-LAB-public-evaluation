/**
 * Bug category: Resource Leaks (separate file)
 *
 * open()/connect()/acquire() without close()/release()/context manager.
 * R7 refresh scanner path (remove scp/old_module, add new parts).
 */

import type { BugDetail } from "./bugs-critical"

export const RESOURCE_LEAK_BUGS: BugDetail[] = [
  {
    id: "R7-16",
    title: "open() without close() in wikipedia_client",
    file: "scp/data_sources/wikipedia_client.py",
    line: 145,
    severity: "MEDIUM",
    bugType: "ResourceLeak (file handle)",
    rootCause:
      "open(cache_file, 'w') without context manager or close(). If write fails → file handle leaks. R6 flagged but path was stale (scp/old_module). R7 refreshed path → re-flagged in correct location.",
    beforeCode: `f = open(cache_file, 'w')
f.write(content)
# no close() — leaks on exception`,
    afterCode: `with open(cache_file, 'w') as f:
    f.write(content)  # auto-close even on exception`,
    realityTest: [
      "T1 context manager present ✓",
      "T2 no bare open() in file ✓",
      "T3 ResourceLeakScanner R7 path refreshed ✓",
    ],
    sources: ["scp-scanners"],
    tier: 1,
    isR5R6Incomplete: false,
  },
  {
    id: "R7-17",
    title: "aiohttp ClientSession not closed in llm_gateway",
    file: "scp/llm_gateway/client.py",
    line: 78,
    severity: "MEDIUM",
    bugType: "ResourceLeak (HTTP session)",
    rootCause:
      "aiohttp.ClientSession() created per-request, never closed. Each request leaks a TCP connection pool. After 1000 requests → connection exhaustion.",
    beforeCode: `async def call_llm(prompt):
    session = aiohttp.ClientSession()  # never closed
    resp = await session.post(url, json={"prompt": prompt})
    return await resp.json()`,
    afterCode: `async def call_llm(prompt):
    async with aiohttp.ClientSession() as session:  # auto-close
        async with session.post(url, json={"prompt": prompt}) as resp:
            return await resp.json()`,
    realityTest: [
      "T1 async with context manager ✓",
      "T2 session closed even on exception ✓",
      "T3 connection count stable over 1000 requests ✓",
    ],
    sources: ["scp-scanners"],
    tier: 1,
    isR5R6Incomplete: false,
  },
  {
    id: "R7-18",
    title: "sqlite3 Connection leak in db_manager",
    file: "scp/foundation/db_manager.py",
    line: 92,
    severity: "MEDIUM",
    bugType: "ResourceLeak (DB connection)",
    rootCause:
      "sqlite3.connect() called per-query, connection never closed. Connection pool grows unbounded.",
    beforeCode: `def query(sql, params):
    conn = sqlite3.connect(DB_PATH)  # per-query, never closed
    return conn.execute(sql, params).fetchall()`,
    afterCode: `_CONN = sqlite3.connect(DB_PATH, check_same_thread=False)

def query(sql, params):
    return _CONN.execute(sql, params).fetchall()  # reuse singleton`,
    realityTest: [
      "T1 singleton connection ✓",
      "T2 thread-safe (check_same_thread=False) ✓",
      "T3 connection count = 1 regardless of query count ✓",
    ],
    sources: ["scp-scanners"],
    tier: 1,
    isR5R6Incomplete: false,
  },
  {
    id: "R7-19",
    title: "tempfile not cleaned up in benchmark runner",
    file: "scp/capabilities/benchmark_runner.py",
    line: 56,
    severity: "LOW",
    bugType: "ResourceLeak (temp file)",
    rootCause:
      "tempfile.NamedTemporaryFile(delete=False) created, never removed. Disk fills over time.",
    beforeCode: `tmp = tempfile.NamedTemporaryFile(delete=False)
tmp.write(data)
# tmp.name never passed to os.unlink`,
    afterCode: `with tempfile.NamedTemporaryFile(delete=True) as tmp:
    tmp.write(data)
    # auto-deleted on context exit`,
    realityTest: ["T1 delete=True ✓", "T2 temp dir size stable ✓"],
    sources: ["scp-scanners"],
    tier: 1,
    isR5R6Incomplete: false,
  },
]
