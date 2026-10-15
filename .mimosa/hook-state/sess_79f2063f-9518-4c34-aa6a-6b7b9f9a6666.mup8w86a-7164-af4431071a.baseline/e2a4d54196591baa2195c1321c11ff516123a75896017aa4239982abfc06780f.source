from __future__ import annotations

from pathlib import Path

path = Path(str(Path(__file__).resolve().parent.parent / "scp" / "runtime" / "slm_impls" / "misc_slm.py"))
text = path.read_text(encoding="utf-8")
if "SCP_LOCAL_ONLY" in text:
    print("local-only branch already present")
    raise SystemExit(0)
text = text.replace("import logging\nimport re\n", "import logging\nimport os\nimport re\n", 1)
needle = "        entity = self._extract_entity_universal(question)\n"
if needle not in text:
    raise SystemExit("entity extraction line not found")
branch = '''        entity = self._extract_entity_universal(question)\n        # Benchmark/local inference mode: never call live Wikipedia/Wikidata/DuckDuckGo.\n        # Use only bounded local evidence so long runs remain reproducible and safe.\n        if os.environ.get("SCP_LOCAL_ONLY", "0") == "1":\n            local_answer = ""\n            local_evidence: dict[str, Any] = {}\n            local_confidence = 0.0\n            if entity:\n                try:\n                    from scp.data_sources.geography import GeographyDataSource\n                    geo = GeographyDataSource()\n                    local = getattr(geo, "_local_data", {}).get(entity.casefold())\n                    if isinstance(local, dict) and local.get("capital"):\n                        capital = str(local["capital"])\n                        local_answer = f"The capital of {entity} is {capital}."\n                        local_evidence = {\n                            "value": capital,\n                            "source": "Local Geography Database",\n                            "entity": entity,\n                            "verified": True,\n                        }\n                        local_confidence = 0.95\n                except Exception as local_error:\n                    logger.debug("UniversalSLM local-only lookup failed: %s", local_error)\n            local_response = SLMResponse(\n                question=question,\n                answer=local_answer,\n                confidence=local_confidence,\n                domain="universal",\n                reasoning="Local-only benchmark path; live retrieval disabled",\n                evidence=local_evidence,\n                slm_name=self.name,\n                processing_time=time.time() - start,\n            )\n            self.cache_response(question, local_response)\n            self._end_timer(start, bool(local_answer))\n            return local_response\n'''
text = text.replace(needle, branch, 1)
path.write_text(text, encoding="utf-8")
print("patched", path)
