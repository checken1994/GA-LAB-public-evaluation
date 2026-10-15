from pathlib import Path

def rep(path, old, new, count=1):
    p = Path(path)
    src = p.read_text(encoding='utf-8')
    found = src.count(old)
    assert found == count, f"{path}: anchor x{found} (want {count}): {old[:70]!r}"
    p.write_text(src.replace(old, new), encoding='utf-8')
    print(f"OK {path} x{count}")

# ---- bounded_evolution.py ----
rep('scp/core/bounded_evolution.py',
    "    except (OSError, ValueError, TypeError):\n        return {}",
    "    except (OSError, ValueError, TypeError) as exc:\n"
    "        logger.warning(\"bounded_evolution: stage file read failed for %s: %s\", stage_file, exc, exc_info=True)\n"
    "        return {}")
rep('scp/core/bounded_evolution.py',
    "    except BaseException as exc:  # propagate sanitized failure to parent\n        result_queue.put(",
    "    except BaseException as exc:  # silent-by-design: sanitized failure is propagated to the parent via the queue.\n"
    "        logger.debug(\"bounded_evolution: child cycle failed (%s), propagated via queue\", type(exc).__name__, exc_info=True)\n"
    "        result_queue.put(")
rep('scp/core/bounded_evolution.py',
    "    except ValueError:\n        configured_provider_timeout = 30.0",
    "    except ValueError as exc:\n"
    "        # silent-by-design: malformed env value falls back to the documented 30s default.\n"
    "        logger.debug(\"bounded_evolution: SCP_EVOLUTION_PROVIDER_TIMEOUT_SECONDS unparseable, using 30.0: %s\", exc, exc_info=True)\n"
    "        configured_provider_timeout = 30.0")

# ---- ai_threat_scanner.py ----
rep('scp/core/ai_threat_scanner.py',
    "                except Exception:  # noqa: S112\n                    continue",
    "                except Exception as exc:  # noqa: S112\n"
    "                    # silent-by-design: one bad historical record must not abort source aggregation.\n"
    "                    logger.debug(\"ai_threat_scanner: record aggregation skipped a bad record: %s\", exc, exc_info=True)\n"
    "                    continue")

# ---- audit_fetcher.py ----
rep('scp/core/audit_fetcher.py',
    "                except json.JSONDecodeError:\n                    continue",
    "                except json.JSONDecodeError as exc:\n"
    "                    # Corrupt historical record must be visible; skipping keeps aggregation resilient.\n"
    "                    logger.warning(\"audit_fetcher: corrupt record skipped in aggregation: %s\", exc, exc_info=True)\n"
    "                    continue")

# ---- circuit_breaker.py ----
rep('scp/core/circuit_breaker.py',
    "    except (TypeError, ValueError):\n        return default",
    "    except (TypeError, ValueError) as exc:\n"
    "        # silent-by-design: malformed env value falls back to the documented default.\n"
    "        logger.debug(\"circuit_breaker: env %s unparseable, using default %s: %s\", name, default, exc, exc_info=True)\n"
    "        return default")

# ---- data_partitioner.py (self-test already loud: traceback + sys.exit(1)) ----
rep('scp/core/data_partitioner.py',
    "    except Exception:\n        import traceback\n        traceback.print_exc()",
    "    except Exception:  # silent-by-design: failure is loud already (traceback print + sys.exit(1)).\n        import traceback\n        traceback.print_exc()")

# ---- db_manager.py ----
rep('scp/core/db_manager.py',
    "    except Exception:\n        return 0.0",
    "    except Exception as exc:\n"
    "        logger.warning(\"db_manager: get_db_size failed for %s, reporting 0.0: %s\", DB_PATH, exc, exc_info=True)\n"
    "        return 0.0")

# ---- dependency_resolver.py ----
rep('scp/core/dependency_resolver.py',
    "    except SyntaxError:\n        return names",
    "    except SyntaxError as exc:\n"
    "        # silent-by-design: probing arbitrary source; unparseable input yields the empty set by contract.\n"
    "        logger.debug(\"dependency_resolver: source not parseable, no imports extracted: %s\", exc, exc_info=True)\n"
    "        return names")
rep('scp/core/dependency_resolver.py',
    "        except ImportError:\n            pass\n        report.missing_imports.append(name)",
    "        except ImportError:  # silent-by-design: absence is explicitly recorded in report.missing_imports.\n            pass\n        report.missing_imports.append(name)")

# ---- doubt_cron.py ----
rep('scp/core/doubt_cron.py',
    "        except Exception as exc:\n            checks.append({\"check\": display, \"ok\": False, \"detail\": f\"{type(exc).__name__}: {str(exc)[:150]}\"})",
    "        except Exception as exc:\n"
    "            # silent-by-design: the failure is carried in the report entry below (ok=False + detail).\n"
    "            logger.debug(\"doubt_cron: check %s failed: %s\", display, exc, exc_info=True)\n"
    "            checks.append({\"check\": display, \"ok\": False, \"detail\": f\"{type(exc).__name__}: {str(exc)[:150]}\"})")

# ---- fast_learning_engine_parts/fastlearningengine.py ----
rep('scp/core/fast_learning_engine_parts/fastlearningengine.py',
    "        except Exception:\n            return False",
    "        except Exception as exc:\n"
    "            logger.warning(\"fast_learning_engine: knowledge existence check failed (treating as unknown): %s\", exc, exc_info=True)\n"
    "            return False")
rep('scp/core/fast_learning_engine_parts/fastlearningengine.py',
    "            return known\n        except Exception:\n            return set()",
    "            return known\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"fast_learning_engine: known-entity scan failed, returning empty set: %s\", exc, exc_info=True)\n"
    "            return set()")

# ---- file_mutex.py ----
rep('scp/core/file_mutex.py',
    "                except FileExistsError:\n                    # Stale lock: holder ch\u1ebft m\u00e0 kh\u00f4ng release (>holder_ttl) \u2192 l\u1ea5y quy\u1ec1n",
    "                except FileExistsError:  # silent-by-design: lock contention is the normal retry path.\n                    # Stale lock: holder ch\u1ebft m\u00e0 kh\u00f4ng release (>holder_ttl) \u2192 l\u1ea5y quy\u1ec1n")
rep('scp/core/file_mutex.py',
    "                    except OSError:\n                        continue\n                    if age > 60.0:",
    "                    except OSError as exc:\n"
    "                        # silent-by-design: stale-lock probe raced with removal; retry continues by design.\n"
    "                        logger.debug(\"file_mutex: stale-lock age probe failed, retrying: %s\", exc, exc_info=True)\n"
    "                        continue\n                    if age > 60.0:")

# ---- fitness_engine.py ----
rep('scp/core/fitness_engine.py',
    "    try:\n        return _eval(ast.parse(expr.strip(), mode=\"eval\"))\n    except (ValueError, SyntaxError):\n        return None",
    "    try:\n        return _eval(ast.parse(expr.strip(), mode=\"eval\"))\n"
    "    except (ValueError, SyntaxError) as exc:\n"
    "        # silent-by-design: parse/eval probe; None means \"not a deterministic expression\" by contract.\n"
    "        logger.debug(\"fitness_engine: expression eval probe failed: %s\", exc, exc_info=True)\n"
    "        return None")
rep('scp/core/fitness_engine.py',
    "    try:\n        return float(str(value).strip().replace(\",\", \".\"))\n    except (TypeError, ValueError):\n        return None",
    "    try:\n        return float(str(value).strip().replace(\",\", \".\"))\n"
    "    except (TypeError, ValueError) as exc:\n"
    "        # silent-by-design: parse probe; None means \"not a number\" by contract.\n"
    "        logger.debug(\"fitness_engine: numeric parse failed: %s\", exc, exc_info=True)\n"
    "        return None")
rep('scp/core/fitness_engine.py',
    "        try:\n            last = json.loads(line)\n        except (TypeError, ValueError):\n            continue",
    "        try:\n            last = json.loads(line)\n"
    "        except (TypeError, ValueError) as exc:\n"
    "            # Corrupt ledger line must be visible, not silently dropped.\n"
    "            logger.warning(\"fitness_engine: corrupt ledger line in %s: %s\", path, exc, exc_info=True)\n"
    "            continue")

# ---- harm_detector.py ----
rep('scp/core/harm_detector.py',
    "                except Exception:  # noqa: S112\n                    continue",
    "                except Exception as exc:  # noqa: S112\n"
    "                    # silent-by-design: one bad historical record must not abort type aggregation.\n"
    "                    logger.debug(\"harm_detector: record aggregation skipped a bad record: %s\", exc, exc_info=True)\n"
    "                    continue")

# ---- healing_engine.py ----
rep('scp/core/healing_engine.py',
    "        except Exception: return None",
    "        except Exception as exc:\n"
    "            logger.warning(\"healing_engine: recovery issue insert failed, issue id None: %s\", exc, exc_info=True)\n"
    "            return None")
rep('scp/core/healing_engine.py',
    "        except Exception: return []",
    "        except Exception as exc:\n"
    "            logger.warning(\"healing_engine: error_history query failed, returning empty: %s\", exc, exc_info=True)\n"
    "            return []")

# ---- kham_pha_logger.py ----
rep('scp/core/kham_pha_logger.py',
    "except ImportError:\n    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), \"data\")",
    "except ImportError as exc:\n"
    "    # silent-by-design: db_manager import is optional; the documented repo-relative data dir is used.\n"
    "    logger.debug(\"kham_pha_logger: DATA_DIR import failed, using repo-relative default: %s\", exc, exc_info=True)\n"
    "    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), \"data\")")

# ---- learning_run_ledger.py ----
rep('scp/core/learning_run_ledger.py',
    "    except (TypeError, ValueError):\n        return None",
    "    except (TypeError, ValueError) as exc:\n"
    "        # silent-by-design: coerce probe; None means \"not an int\" by contract.\n"
    "        logger.debug(\"learning_run_ledger: int coercion failed: %s\", exc, exc_info=True)\n"
    "        return None")

# ---- policy_materializer.py ----
rep('scp/core/policy_materializer.py',
    "        except OSError:\n            pass\n        raise",
    "        except OSError as exc:\n"
    "            # silent-by-design: best-effort temp cleanup before re-raising the real error.\n"
    "            logger.debug(\"policy_materializer: temp file cleanup failed (non-fatal): %s\", exc, exc_info=True)\n"
    "        raise")

# ---- reality_engine.py ----
rep('scp/core/reality_engine.py',
    "        except Exception: return None",
    "        except Exception as exc:\n"
    "            # silent-by-design: external fetch is best-effort; None means \"unverifiable here\".\n"
    "            logger.debug(\"reality_engine: external fetch failed: %s\", exc, exc_info=True)\n"
    "            return None")

# ---- smart_cache.py ----
rep('scp/core/smart_cache.py',
    "            from scp.runtime.slm_base import SLMResponse\n            return SLMResponse(**value)\n        except Exception:\n            return None",
    "            from scp.runtime.slm_base import SLMResponse\n            return SLMResponse(**value)\n"
    "        except Exception as exc:\n"
    "            # silent-by-design: invalid cached payload degrades to a cache miss by design.\n"
    "            logger.debug(\"smart_cache: cached SLMResponse reconstruction failed, cache miss: %s\", exc, exc_info=True)\n"
    "            return None")
rep('scp/core/smart_cache.py',
    "        return _dict_to_slm_response(cached)\n    except Exception:\n        return None",
    "        return _dict_to_slm_response(cached)\n"
    "    except Exception as exc:\n"
    "        # silent-by-design: cache read failure degrades to a cache miss, never to a wrong answer.\n"
    "        logger.debug(\"smart_cache: cache read failed, treating as miss: %s\", exc, exc_info=True)\n"
    "        return None")

# ---- speculative.py ----
rep('scp/core/speculative.py',
    "            except Exception as exc:\n                meta[\"verdict\"] = f\"ERROR: {type(exc).__name__}: {str(exc)[:100]}\"",
    "            except Exception as exc:\n"
    "                # silent-by-design: the error is recorded in meta[verdict] and returned to the caller.\n"
    "                logger.debug(\"speculative: attempt failed, verdict=ERROR recorded: %s\", exc, exc_info=True)\n"
    "                meta[\"verdict\"] = f\"ERROR: {type(exc).__name__}: {str(exc)[:100]}\"")
rep('scp/core/speculative.py',
    "            try:\n                self.cleanup_extra(base)\n            except Exception:\n                pass",
    "            try:\n                self.cleanup_extra(base)\n"
    "            except Exception as exc:\n"
    "                # silent-by-design: user-provided cleanup is best-effort; it must not mask the main result.\n"
    "                logger.debug(\"speculative: cleanup_extra failed (non-fatal): %s\", exc, exc_info=True)")

# ---- streaming_factcheck.py ----
rep('scp/core/streaming_factcheck.py',
    "            return None\n        except Exception:\n            return None",
    "            return None\n"
    "        except Exception as exc:\n"
    "            # silent-by-design: fact-check lookup is best-effort; None means \"unverified\" by contract.\n"
    "            logger.debug(\"streaming_factcheck: lookup failed, returning None: %s\", exc, exc_info=True)\n"
    "            return None")

# ---- subsystem_telemetry.py ----
rep('scp/core/subsystem_telemetry.py',
    "        except OSError:\n            return False",
    "        except OSError as exc:\n"
    "            logger.warning(\"subsystem_telemetry: ledger append failed for %s: %s\", self.ledger_path, exc, exc_info=True)\n"
    "            return False")
rep('scp/core/subsystem_telemetry.py',
    "        except (TypeError, ValueError):\n            age = float(\"inf\")",
    "        except (TypeError, ValueError) as exc:\n"
    "            # silent-by-design: unparseable tick timestamp reports infinite age (never a fake fresh age).\n"
    "            logger.debug(\"subsystem_telemetry: last_tick timestamp unparseable, age=inf: %s\", exc, exc_info=True)\n"
    "            age = float(\"inf\")")
rep('scp/core/subsystem_telemetry.py',
    "            except asyncio.CancelledError:\n                pass",
    "            except asyncio.CancelledError as exc:\n"
    "                # silent-by-design: awaiting an already-cancelled ticker is the expected shutdown path.\n"
    "                logger.debug(\"subsystem_telemetry: ticker cancellation observed: %s\", exc, exc_info=True)")

print("core batch 2 done")
