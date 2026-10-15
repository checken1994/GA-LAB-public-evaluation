import os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
for line in (root/'.env.test').read_text(encoding='utf-8-sig').splitlines():
 s=line.strip()
 if s and not s.startswith('#') and '=' in s:
  k,v=s.split('=',1);os.environ[k.strip()]=v.strip()
from scp.llm_gateway import get_gateway
x=get_gateway()
try: status=x.stats()
except Exception as e: status={'stats_error':type(e).__name__+': '+str(e)[:200]}
print({'ollama_default_enabled':getattr(getattr(x,'ollama_default',None),'enabled',None),'openrouter_enabled':getattr(getattr(x,'openrouter',None),'enabled',None),'stats':status})
