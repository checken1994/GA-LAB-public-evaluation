from __future__ import annotations

from pathlib import Path

ROOT = Path(str(Path(__file__).resolve().parent.parent))


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    backup = path.with_suffix(path.suffix + ".pre_web_fallback.bak")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {label}")


helpers = ROOT / "scp" / "api_server_parts" / "helpers.py"
replace_once(
    helpers,
    "    speculative_mode: dict[str, Any] | None = None\n",
    "    speculative_mode: dict[str, Any] | None = None\n"
    "    web_fallback_used: bool = False\n"
    "    web_fallback: dict[str, Any] | None = None\n",
    "AskResponse web fallback fields",
)

api = ROOT / "scp" / "api_server.py"
replace_once(
    api,
    "logger = logging.getLogger(\"scp.api\")\n",
    "logger = logging.getLogger(\"scp.api\")\n\n"
    "from scp.web_control.internet_search import InternetSearch\n",
    "InternetSearch import",
)
replace_once(
    api,
    "    v98_context = _extract_v98_context(request)\n",
    "    v98_context = _extract_v98_context(request)\n"
    "    _web_fallback_used = False\n"
    "    _web_fallback: dict = {}\n",
    "web fallback initialization",
)
replace_once(
    api,
    "        except Exception as _ollama_err:\n            logger.warning(f\"[CHATBOT] Ollama call failed: {_ollama_err}\")\n",
    "        except Exception as _ollama_err:\n"
    "            logger.warning(f\"[CHATBOT] Ollama call failed: {_ollama_err}\")\n"
    "            # A model/API timeout is not a reason to stop evidence retrieval.\n"
    "            # This fallback is retrieval-only: public snippets are untrusted\n"
    "            # data, never executable instructions and never treated as truth.\n"
    "            if os.environ.get(\"SCP_WEB_FALLBACK\", \"1\") == \"1\":\n"
    "                try:\n"
    "                    _web_timeout = min(float(os.environ.get(\"SCP_WEB_FALLBACK_TIMEOUT\", \"8\")), 12.0)\n"
    "                    _web_search = InternetSearch(timeout=min(_web_timeout / 2.0, 4.0))\n"
    "                    _web_fallback = await asyncio.wait_for(\n"
    "                        _web_search.search(req.question, max_results=6),\n"
    "                        timeout=_web_timeout,\n"
    "                    )\n"
    "                    _web_fallback_used = bool(_web_fallback.get(\"success\"))\n"
    "                    _web_fallback[\"trigger\"] = \"llm_timeout_or_error\"\n"
    "                    _web_fallback[\"llm_error\"] = str(_ollama_err)[:240]\n"
    "                    if _web_fallback_used:\n"
    "                        _snippets = []\n"
    "                        for _item in _web_fallback.get(\"results\", [])[:6]:\n"
    "                            _title = str(_item.get(\"title\", \"\")).strip()\n"
    "                            _snippet = str(_item.get(\"snippet\", \"\")).strip()\n"
    "                            _url = str(_item.get(\"url\", \"\")).strip()\n"
    "                            _snippets.append(f\"- {_title}: {_snippet} ({_url})\")\n"
    "                        _ai_answer = (\n"
    "                            \"[SCP public-web evidence; untrusted, requires verification]\\n\"\n"
    "                            + \"\\n\".join(_snippets)\n"
    "                        )\n"
    "                        v98_context[\"web_fallback\"] = _web_fallback\n"
    "                    else:\n"
    "                        logger.warning(\"[CHATBOT] Public web fallback returned no result: %s\", _web_fallback.get(\"errors\"))\n"
    "                except Exception as _web_err:\n"
    "                    _web_fallback = {\"success\": False, \"method\": \"public-search\", \"error\": str(_web_err)[:240]}\n"
    "                    logger.warning(\"[CHATBOT] Public web fallback failed: %s\", _web_err)\n",
    "LLM timeout public web fallback",
)
replace_once(
    api,
    "    return AskResponse(\n        verdict=v.verdict,\n",
    "    if _web_fallback_used:\n"
    "        _api_slm_trace.append({\n"
    "            \"domain\": v.domain,\n"
    "            \"slm_name\": \"public_web_search\",\n"
    "            \"answer\": \"retrieved public snippets\",\n"
    "            \"time_ms\": None,\n"
    "            \"source\": \"public-search\",\n"
    "            \"evidence\": _web_fallback,\n"
    "        })\n"
    "    return AskResponse(\n        verdict=v.verdict,\n",
    "slm_trace public web record",
)
replace_once(
    api,
    "        speculative_mode=_api_speculative_mode,\n    )\n",
    "        speculative_mode=_api_speculative_mode,\n"
    "        web_fallback_used=_web_fallback_used,\n"
    "        web_fallback=(_web_fallback or None),\n"
    "    )\n",
    "AskResponse web fallback response metadata",
)

judgecore = ROOT / "scp" / "runtime" / "judge_parts" / "judgecore_mixin.py"
replace_once(
    judgecore,
    "from scp.core.db_manager import (\n    db_exec,\n)\n",
    "from scp.core.db_manager import (\n    db_exec,\n)\n"
    "from scp.core.evidence_filter import filter_slm_responses\n",
    "JudgeCore evidence filter import",
)
replace_once(
    judgecore,
    "        ground_truth = {}\n",
    "        _filtered_slm_responses, _evidence_filter_report = filter_slm_responses(\n"
    "            question, slm_responses or []\n"
    "        )\n"
    "        if _evidence_filter_report.get(\"droppedCount\"):\n"
    "            slm_responses = _filtered_slm_responses\n"
    "            verdict.slm_responses = _filtered_slm_responses\n"
    "        verdict.evidence[\"evidence_consistency\"] = _evidence_filter_report\n"
    "        ground_truth = {}\n",
    "JudgeCore evidence consistency gate",
)

print("all patches applied")
