from pathlib import Path
from datetime import datetime
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'bridge-provider-secrets-before-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
p=root/'mini-services/llm-bridge/index.ts'; (backup/p.name).write_bytes(p.read_bytes())
s=p.read_text(encoding='utf-8-sig')
if 'from "node:fs"' not in s and "from 'node:fs'" not in s:
    s='import { readFileSync } from "node:fs";\n'+s
old='''const OPENROUTER_API_KEYS: string[] = [\n  process.env.OPENROUTER_API_KEY,\n  process.env.OPENROUTER_API_KEY_2,\n  process.env.OPENROUTER_API_KEY_3,\n].filter((k): k is string => typeof k === "string" && k.length > 0);'''
new='''function readOptionalSecret(envName: string, fileEnvName: string): string {\n  const direct = (process.env[envName] ?? "").trim();\n  if (direct) return direct;\n  const file = (process.env[fileEnvName] ?? "").trim();\n  if (!file) return "";\n  const value = readFileSync(file, "utf8").trim();\n  if (!value) throw new Error(`${fileEnvName} is empty`);\n  return value;\n}\n\nconst OPENROUTER_API_KEYS: string[] = [\n  readOptionalSecret("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_FILE"),\n  readOptionalSecret("OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_2_FILE"),\n  readOptionalSecret("OPENROUTER_API_KEY_3", "OPENROUTER_API_KEY_3_FILE"),\n].filter((k): k is string => k.length > 0);'''
if old not in s: raise SystemExit('provider array marker missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8',newline='\n')
test=root/'tests/reality-tests/reality_4-d-029.py'
test.write_text('''#!/usr/bin/env python3\n"""Reality test: bridge source supports file-backed provider key references."""\nfrom pathlib import Path\np=Path(__file__).resolve().parents[2]/"mini-services/llm-bridge/index.ts"\ns=p.read_text(encoding="utf-8")\nfor marker in ["OPENROUTER_API_KEY_FILE","OPENROUTER_API_KEY_2_FILE","OPENROUTER_API_KEY_3_FILE","readFileSync"]:\n    assert marker in s, marker\nprint("PASS [1]: bridge supports file-backed provider secret references")\nprint("✓ Reality test 4-d-029 PASSED")\n''',encoding='utf-8',newline='\n')
print(f'backup={backup}')
