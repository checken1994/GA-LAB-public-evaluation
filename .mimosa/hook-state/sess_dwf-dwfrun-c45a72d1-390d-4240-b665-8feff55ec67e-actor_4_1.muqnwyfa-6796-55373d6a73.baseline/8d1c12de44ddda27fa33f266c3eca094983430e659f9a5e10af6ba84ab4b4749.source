from __future__ import annotations
import hashlib
import json
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
test_dir = root / '.private-secrets' / 'release-audit' / 'r43c-policy-loader-test'
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir(parents=True)

sys.path.insert(0, str(root))
from scp.runtime.judge import RealityJudge

obj = RealityJudge.__new__(RealityJudge)
obj._exp_policies = {'stale': True}
obj._exp_policies_ts = 0.0
obj._exp_policies_ttl = 0.0
obj._exp_policies_path = str(test_dir / 'active_policies.json')

checks = {}
checks['missing_clears'] = obj._get_exp_policies() == {}

Path(obj._exp_policies_path).write_text('{bad', encoding='utf-8')
obj._exp_policies = {'stale': True}; obj._exp_policies_ts = 0.0
checks['corrupt_clears'] = obj._get_exp_policies() == {}

payload = {
    'source_priorities': {}, 'domain_tolerances': {}, 'kb_priorities': [],
    'recurring_errors': [], 'confidence_adjustments': {},
    '_meta': {'schema_version': 1, 'eligible_lesson_count': 1},
}
canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
payload['_meta']['policy_sha256'] = hashlib.sha256(canonical).hexdigest()
Path(obj._exp_policies_path).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
obj._exp_policies = {'stale': True}; obj._exp_policies_ts = 0.0
checks['valid_loads'] = obj._get_exp_policies().get('_meta', {}).get('eligible_lesson_count') == 1

payload['_meta']['policy_sha256'] = '0' * 64
Path(obj._exp_policies_path).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
obj._exp_policies = {'stale': True}; obj._exp_policies_ts = 0.0
checks['hash_mismatch_clears'] = obj._get_exp_policies() == {}

result = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks, 'test_dir': str(test_dir)}
(test_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
raise SystemExit(0 if result['status'] == 'PASS' else 1)
