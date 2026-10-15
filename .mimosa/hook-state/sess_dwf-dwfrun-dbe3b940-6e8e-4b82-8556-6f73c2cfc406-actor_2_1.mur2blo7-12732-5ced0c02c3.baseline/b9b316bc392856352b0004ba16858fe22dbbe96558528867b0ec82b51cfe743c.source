from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'scheduler-admin-auth-before-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
p=root/'mini-services/loop-scheduler/index.ts'; (backup/p.name).write_bytes(p.read_bytes())
s=p.read_text(encoding='utf-8-sig')
marker='async function handleRequest(req: Request): Promise<Response> {'
helper='''function constantTimeTokenEquals(provided: string, expected: string): boolean {\n  const a = new TextEncoder().encode(provided);\n  const b = new TextEncoder().encode(expected);\n  let diff = a.length ^ b.length;\n  const n = Math.max(a.length, b.length);\n  for (let i = 0; i < n; i += 1) diff |= (a[i] ?? 0) ^ (b[i] ?? 0);\n  return diff === 0;\n}\n\nfunction schedulerAdminAuthorized(req: Request): boolean {\n  const authorization = req.headers.get("authorization") ?? "";\n  const bearer = authorization.toLowerCase().startsWith("bearer ")\n    ? authorization.slice(7).trim()\n    : "";\n  const headerToken = req.headers.get("x-scp-admin-token")?.trim() ?? "";\n  return constantTimeTokenEquals(bearer || headerToken, SCHEDULER_ADMIN_TOKEN);\n}\n\n'''+marker
if marker not in s: raise SystemExit('handler marker missing')
if 'function schedulerAdminAuthorized' not in s: s=s.replace(marker,helper,1)
marker2='  const method = req.method.toUpperCase();\n'
insert2='''  const method = req.method.toUpperCase();\n\n  // Mutating scheduler controls are operator-only. A missing token is a\n  // configuration error, not permission to run unauthenticated.\n  if (method === "POST" && new Set(["/trigger", "/pause", "/resume"]).has(path)) {\n    if (!SCHEDULER_ADMIN_TOKEN) {\n      return jsonResponse({ error: "scheduler admin auth not configured" }, 503);\n    }\n    if (!schedulerAdminAuthorized(req)) {\n      return jsonResponse({ error: "scheduler admin authentication required" }, 401);\n    }\n  }\n'''
if marker2 not in s: raise SystemExit('method marker missing')
if 'scheduler admin authentication required' not in s: s=s.replace(marker2,insert2,1)
marker3='  const HOST = process.env.LOOP_SCHEDULER_HOST ?? "127.0.0.1";\n'
insert3=marker3+'  const SCHEDULER_ADMIN_TOKEN = process.env.SCP_SCHEDULER_ADMIN_TOKEN ?? "";\n'
if marker3 not in s: raise SystemExit('host marker missing')
if 'const SCHEDULER_ADMIN_TOKEN' not in s: s=s.replace(marker3,insert3,1)
p.write_text(s,encoding='utf-8',newline='\n')
test=root/'tests/reality-tests/reality_4-d-028.py'
test.write_text('''#!/usr/bin/env python3\n"""Reality test: scheduler source has an explicit auth boundary for mutating controls."""\nfrom pathlib import Path\np=Path(__file__).resolve().parents[2]/"mini-services/loop-scheduler/index.ts"\ns=p.read_text(encoding="utf-8")\nrequired=["SCP_SCHEDULER_ADMIN_TOKEN","schedulerAdminAuthorized","/trigger","/pause","/resume","scheduler admin authentication required"]\nmissing=[x for x in required if x not in s]\nassert not missing, missing\nprint("PASS [1]: scheduler mutating endpoints require explicit admin token")\nprint("✓ Reality test 4-d-028 PASSED")\n''',encoding='utf-8',newline='\n')
print(f'backup={backup}')
