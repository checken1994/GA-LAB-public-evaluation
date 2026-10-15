from pathlib import Path

def rep(path, old, new, count=1):
    p = Path(path)
    src = p.read_text(encoding='utf-8')
    found = src.count(old)
    assert found == count, f"{path}: anchor x{found} (want {count}): {old[:70]!r}"
    p.write_text(src.replace(old, new), encoding='utf-8')
    print(f"OK {path} x{count}")

# ---- _number_utils.py (3 parse probes) ----
rep('scp/meta/_number_utils.py',
    "    try:\n        value = float(raw_num.replace(\",\", \"\"))\n    except ValueError:",
    "    try:\n        value = float(raw_num.replace(\",\", \"\"))\n"
    "    except ValueError as exc:\n"
    "        # silent-by-design: probe order — next probe swaps the last separator to a dot.\n"
    "        logger.debug(\"_number_utils: comma-strip parse failed, trying dot-swap: %s\", exc, exc_info=True)")
rep('scp/meta/_number_utils.py',
    "        try:\n            value = float(raw_num.replace(\",\", \".\"))\n        except ValueError:\n            return None",
    "        try:\n            value = float(raw_num.replace(\",\", \".\"))\n"
    "        except ValueError as exc:\n"
    "            # silent-by-design: both probes failed; None means \"no number\" by contract.\n"
    "            logger.debug(\"_number_utils: number parse failed: %s\", exc, exc_info=True)\n"
    "            return None")
rep('scp/meta/_number_utils.py',
    "        except (TypeError, ValueError):\n            return None",
    "        except (TypeError, ValueError) as exc:\n"
    "            # silent-by-design: coerce probe; None means \"not a finite number\" by contract.\n"
    "            logger.debug(\"_number_utils: float coercion failed: %s\", exc, exc_info=True)\n"
    "            return None")

# ---- behavior_monitor.py ----
rep('scp/meta/behavior_monitor.py',
    "    try:\n        f = float(v)\n    except (TypeError, ValueError):\n        return default",
    "    try:\n        f = float(v)\n"
    "    except (TypeError, ValueError) as exc:\n"
    "        # silent-by-design: coerce probe; caller default is the documented fallback.\n"
    "        logger.debug(\"behavior_monitor: float coercion failed, using default: %s\", exc, exc_info=True)\n"
    "        return default")
rep('scp/meta/behavior_monitor.py',
    "                    try:\n                        event = json.loads(line)\n                    except (json.JSONDecodeError, ValueError):\n                        continue",
    "                    try:\n                        event = json.loads(line)\n"
    "                    except (json.JSONDecodeError, ValueError) as exc:\n"
    "                        # Corrupt event line must be visible, not silently dropped.\n"
    "                        logger.warning(\"behavior_monitor: corrupt event line skipped: %s\", exc, exc_info=True)\n"
    "                        continue")

# ---- calibration_engine.py ----
rep('scp/meta/calibration_engine.py',
    "        except Exception:\n            factor = 1.0",
    "        except Exception as exc:\n"
    "            # Calibration silently degrading to 1.0 would bias downstream verdicts — must be visible.\n"
    "            logger.warning(\"calibration_engine: factor lookup failed, using neutral 1.0: %s\", exc, exc_info=True)\n"
    "            factor = 1.0")

# ---- capability_levels.py ----
rep('scp/meta/capability_levels.py',
    "    try:\n        return CapabilityLevel[name]\n    except KeyError:\n        return CapabilityLevel.FULL_PRODUCTION",
    "    try:\n        return CapabilityLevel[name]\n"
    "    except KeyError as exc:\n"
    "        # Fail-open to FULL_PRODUCTION is the current contract — but an unknown\n"
    "        # level name silently widening capability must be visible.\n"
    "        logger.warning(\"capability_levels: unknown SCP_CAPABILITY_LEVEL %r, falling back to FULL_PRODUCTION\", name, exc_info=True)\n"
    "        return CapabilityLevel.FULL_PRODUCTION")

# ---- cognitive_gate.py ----
rep('scp/meta/cognitive_gate.py',
    "except Exception:\n    _DB_AVAILABLE = False",
    "except Exception as exc:\n"
    "    # silent-by-design: db_manager import is optional at module load; the flag drives the fallback.\n"
    "    logger.debug(\"cognitive_gate: db_manager unavailable: %s\", exc, exc_info=True)\n"
    "    _DB_AVAILABLE = False")

# ---- external_trust.py ----
rep('scp/meta/external_trust.py',
    "            try:\n                datetime.strptime(m.group(2), \"%Y-%m-%d\")\n            except ValueError:\n                return False",
    "            try:\n                datetime.strptime(m.group(2), \"%Y-%m-%d\")\n"
    "            except ValueError as exc:\n"
    "                # silent-by-design: unparseable date means the candidate does not validate, by contract.\n"
    "                logger.debug(\"external_trust: date validation failed: %s\", exc, exc_info=True)\n"
    "                return False")

# ---- falsification_engine.py ----
rep('scp/meta/falsification_engine.py',
    "        except (TypeError, ValueError):\n            conf = 0.0\n            reasons.append(\"confidence unparseable \u2014 treating as 0%\")",
    "        except (TypeError, ValueError) as exc:\n"
    "            # silent-by-design: the 0% treatment is recorded in reasons and returned to the caller.\n"
    "            logger.debug(\"falsification_engine: confidence unparseable, treating as 0: %s\", exc, exc_info=True)\n"
    "            conf = 0.0\n            reasons.append(\"confidence unparseable \u2014 treating as 0%\")")
rep('scp/meta/falsification_engine.py',
    "            try:\n                value = float(raw_num.replace(\",\", \"\"))\n            except ValueError:",
    "            try:\n                value = float(raw_num.replace(\",\", \"\"))\n"
    "            except ValueError as exc:\n"
    "                # silent-by-design: probe order — next probe swaps the separator to a dot.\n"
    "                logger.debug(\"falsification_engine: comma-strip parse failed, trying dot-swap: %s\", exc, exc_info=True)")
rep('scp/meta/falsification_engine.py',
    "                except ValueError:\n                    continue",
    "                except ValueError as exc:\n"
    "                    # silent-by-design: both parse probes failed; the token is not a number by contract.\n"
    "                    logger.debug(\"falsification_engine: number parse failed, skipping token: %s\", exc, exc_info=True)\n"
    "                    continue")

# ---- kb_evolve.py ----
rep('scp/meta/kb_evolve.py',
    "            except re.error:\n                continue  # Skip invalid regex",
    "            except re.error as exc:\n"
    "                # silent-by-design: invalid regex patterns are skipped so one bad KB entry cannot abort matching.\n"
    "                logger.debug(\"kb_evolve: invalid regex skipped: %s\", exc, exc_info=True)\n"
    "                continue  # Skip invalid regex")

# ---- meta.py ----
rep('scp/meta/meta.py',
    "            return {\"total\": total, \"active\": active, \"completed\": completed,\n                    \"avg_progress\": round(avg_progress, 2)}\n        except Exception:\n            return {\"total\": 0, \"active\": 0, \"completed\": 0, \"avg_progress\": 0}",
    "            return {\"total\": total, \"active\": active, \"completed\": completed,\n                    \"avg_progress\": round(avg_progress, 2)}\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"meta: goal stats query failed, reporting zeros: %s\", exc, exc_info=True)\n"
    "            return {\"total\": 0, \"active\": 0, \"completed\": 0, \"avg_progress\": 0}")
rep('scp/meta/meta.py',
    "            return {\"total_questions\": total, \"asked\": asked, \"by_type\": by_type}\n        except Exception:\n            return {\"total_questions\": 0, \"asked\": 0, \"by_type\": {}}",
    "            return {\"total_questions\": total, \"asked\": asked, \"by_type\": by_type}\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"meta: curiosity stats query failed, reporting zeros: %s\", exc, exc_info=True)\n"
    "            return {\"total_questions\": 0, \"asked\": 0, \"by_type\": {}}")
rep('scp/meta/meta.py',
    "            return {\"total_relations\": total, \"by_relation\": by_relation}\n        except Exception:\n            return {\"total_relations\": 0, \"by_relation\": {}}",
    "            return {\"total_relations\": total, \"by_relation\": by_relation}\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"meta: world-model stats query failed, reporting zeros: %s\", exc, exc_info=True)\n"
    "            return {\"total_relations\": 0, \"by_relation\": {}}")
rep('scp/meta/meta.py',
    "                    if abs(existing_count - sample_count) <= 10:\n                        return True  # Too similar, skip\n            return False\n        except Exception:\n            return False",
    "                    if abs(existing_count - sample_count) <= 10:\n                        return True  # Too similar, skip\n            return False\n"
    "        except Exception as exc:\n"
    "            # Fail-open (return False = not similar) is the current dedup contract; visible now.\n"
    "            logger.warning(\"meta: question dedup check failed, treating as dissimilar: %s\", exc, exc_info=True)\n"
    "            return False")
rep('scp/meta/meta.py',
    "            return {\"total_principles\": total, \"avg_confidence\": round(avg_conf, 2)}\n        except Exception:\n            return {\"total_principles\": 0, \"avg_confidence\": 0}",
    "            return {\"total_principles\": total, \"avg_confidence\": round(avg_conf, 2)}\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"meta: principles stats query failed, reporting zeros: %s\", exc, exc_info=True)\n"
    "            return {\"total_principles\": 0, \"avg_confidence\": 0}")
rep('scp/meta/meta.py',
    "            except Exception as e:\n                print(f\"     Error: {e}\")",
    "            except Exception as e:\n"
    "                logger.warning(\"meta: principle verification step failed: %s\", e, exc_info=True)\n"
    "                print(f\"     Error: {e}\")")

# ---- principle_rules.py ----
rep('scp/meta/principle_rules.py',
    "            return [dict(r) for r in rows] if rows else []\n        except Exception:\n            return []",
    "            return [dict(r) for r in rows] if rows else []\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"principle_rules: active rules query failed, returning empty: %s\", exc, exc_info=True)\n"
    "            return []")

# ---- question_tracker.py ----
rep('scp/meta/question_tracker.py',
    "            except Exception:\n                qtype = \"INTERNAL\" if is_internal else \"NEW\"",
    "            except Exception as exc:\n"
    "                # silent-by-design: classification falls back to the documented default type.\n"
    "                logger.debug(\"question_tracker: question classification failed, using default type: %s\", exc, exc_info=True)\n"
    "                qtype = \"INTERNAL\" if is_internal else \"NEW\"")

# ---- why_sources/wikipedia.py ----
rep('scp/meta/why_sources/wikipedia.py',
    "        except Exception as exc:\n            # Parse error or unexpected \u2014 register failure.\n            _wiki_register_failure(f\"unexpected: {exc}\")",
    "        except Exception as exc:\n"
    "            # silent-by-design: the failure is registered via _wiki_register_failure (source health) and surfaced via last_err.\n"
    "            # Parse error or unexpected \u2014 register failure.\n            _wiki_register_failure(f\"unexpected: {exc}\")")

# ---- why_v80_modes.py (4 documented-default fallbacks; confidence x3 + sanitize x1) ----
rep('scp/meta/why_v80_modes.py',
    "    try:\n        confidence = float(parsed.get(\"confidence\", 0.0))\n        confidence = max(0.0, min(1.0, confidence))\n    except (TypeError, ValueError):\n        confidence = 0.0",
    "    try:\n        confidence = float(parsed.get(\"confidence\", 0.0))\n        confidence = max(0.0, min(1.0, confidence))\n"
    "    except (TypeError, ValueError) as exc:\n"
    "        # silent-by-design: unparseable LLM confidence falls back to the documented 0.0 default.\n"
    "        logger.debug(\"why_v80_modes: confidence unparseable, using 0.0: %s\", exc, exc_info=True)\n"
    "        confidence = 0.0",
    3)
rep('scp/meta/why_v80_modes.py',
    "    try:\n        sanitize_missing = bool(parsed.get(\"sanitize_missing\", True))\n    except (TypeError, ValueError):\n        sanitize_missing = True",
    "    try:\n        sanitize_missing = bool(parsed.get(\"sanitize_missing\", True))\n"
    "    except (TypeError, ValueError) as exc:\n"
    "        # silent-by-design: unparseable flag falls back to the documented True default.\n"
    "        logger.debug(\"why_v80_modes: sanitize_missing unparseable, using True: %s\", exc, exc_info=True)\n"
    "        sanitize_missing = True")

print("meta batch done")
