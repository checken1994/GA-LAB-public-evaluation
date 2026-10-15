from pathlib import Path
from datetime import datetime
import re
root=Path.cwd(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); backup=root/'.private-secrets'/f'escalation-write-lock-before-{stamp}'; backup.mkdir(parents=True,exist_ok=True)
p=root/'scp/security/escalation.py'; (backup/p.name).write_bytes(p.read_bytes())
s=p.read_text(encoding='utf-8-sig')
old='        self._timers: dict[str, threading.Timer] = {}\n'
new=old+'        # Dedicated append lock: protects JSONL write atomicity without holding\n        # the escalation state lock. This closes concurrent lost-write races.\n        self._write_lock = threading.Lock()\n'
if old not in s: raise SystemExit('timer marker missing')
if 'self._write_lock = threading.Lock()' not in s: s=s.replace(old,new,1)
old2='        with self.escalation_log_path.open("a") as log_file:\n            json.dump(log_entry, log_file)\n            log_file.write("\\n")\n'
new2='        with self._write_lock:\n            with self.escalation_log_path.open("a") as log_file:\n                json.dump(log_entry, log_file)\n                log_file.write("\\n")\n'
if old2 not in s: raise SystemExit('log write marker missing')
s=s.replace(old2,new2,1)
p.write_text(s,encoding='utf-8',newline='\n')
print(f'backup={backup}')
print('patched dedicated write lock')
