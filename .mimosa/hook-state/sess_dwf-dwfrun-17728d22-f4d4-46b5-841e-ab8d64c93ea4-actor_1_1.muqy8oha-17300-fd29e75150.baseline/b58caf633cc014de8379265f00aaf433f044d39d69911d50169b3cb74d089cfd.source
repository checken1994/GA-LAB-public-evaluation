from pathlib import Path

def rep(path, old, new, count=1):
    p = Path(path)
    src = p.read_text(encoding='utf-8')
    found = src.count(old)
    assert found == count, f"{path}: anchor x{found} (want {count}): {old[:70]!r}"
    p.write_text(src.replace(old, new), encoding='utf-8')
    print(f"OK {path} x{count}")

# ---- anchor.py ----
rep('scp/core/anchor.py',
    "            except (ValueError, TypeError):\n                is_match = str(anchor_value).strip().lower() == str(value).strip().lower()",
    "            except (ValueError, TypeError) as exc:\n"
    "                # silent-by-design: non-numeric values fall back to documented string comparison.\n"
    "                logger.debug(\"anchor: numeric compare failed, using string compare: %s\", exc, exc_info=True)\n"
    "                is_match = str(anchor_value).strip().lower() == str(value).strip().lower()")
rep('scp/core/anchor.py',
    "            return db_query_all(\"SELECT * FROM reality_anchor ORDER BY entity\")\n        except Exception:\n            return []",
    "            return db_query_all(\"SELECT * FROM reality_anchor ORDER BY entity\")\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"anchor: get_all_anchors query failed: %s\", exc, exc_info=True)\n"
    "            return []")
rep('scp/core/anchor.py',
    "            return {\"total_anchors\": cnt[\"cnt\"] if cnt else 0}\n        except Exception:\n            return {\"total_anchors\": 0}",
    "            return {\"total_anchors\": cnt[\"cnt\"] if cnt else 0}\n"
    "        except Exception as exc:\n"
    "            logger.warning(\"anchor: get_stats query failed: %s\", exc, exc_info=True)\n"
    "            return {\"total_anchors\": 0}")
rep('scp/core/anchor.py',
    "except Exception as e:\n    print(f\"[WARN] RealityAnchor init failed: {e}\")\n    _anchor = None",
    "except Exception as e:\n    logger.warning(\"RealityAnchor init failed: %s\", e, exc_info=True)\n    print(f\"[WARN] RealityAnchor init failed: {e}\")\n    _anchor = None")

# ---- antibody.py ----
rep('scp/core/antibody.py',
    "except Exception as e:\n    print(f\"[WARN] AntibodyEngine init failed: {e}\")\n    _antibody = None",
    "except Exception as e:\n    logger.warning(\"AntibodyEngine init failed: %s\", e, exc_info=True)\n    print(f\"[WARN] AntibodyEngine init failed: {e}\")\n    _antibody = None")

# ---- call_session_hub.py ----
rep('scp/core/call_session_hub.py',
    "                except json.JSONDecodeError:\n                    await websocket.send_json({\"type\": \"error\", \"code\": \"SIGNAL_INVALID_JSON\"})\n                    continue",
    "                except json.JSONDecodeError as exc:\n"
    "                    # silent-by-design: the peer is notified via an error frame; connection continues.\n"
    "                    logger.debug(\"call_session_hub: invalid signaling JSON rejected: %s\", exc, exc_info=True)\n"
    "                    await websocket.send_json({\"type\": \"error\", \"code\": \"SIGNAL_INVALID_JSON\"})\n"
    "                    continue")
rep('scp/core/call_session_hub.py',
    "        except WebSocketDisconnect:\n            pass",
    "        except WebSocketDisconnect as exc:\n"
    "            # silent-by-design: peer disconnect is the expected end of the receive loop.\n"
    "            logger.debug(\"call_session_hub: peer disconnected: %s\", exc, exc_info=True)")
rep('scp/core/call_session_hub.py',
    "        except Exception:\n            return",
    "        except Exception as exc:\n"
    "            # silent-by-design: sender task ends when the peer socket breaks; cleanup runs in caller.\n"
    "            logger.debug(\"call_session_hub: sender loop ended: %s\", exc, exc_info=True)\n            return")
rep('scp/core/call_session_hub.py',
    "                except asyncio.QueueFull:\n                    continue",
    "                except asyncio.QueueFull as exc:\n"
    "                    logger.warning(\"call_session_hub: signal message dropped for slow peer %s: %s\", peer_id, exc, exc_info=True)\n"
    "                    continue")

# ---- context_pruner.py ----
rep('scp/core/context_pruner.py',
    "    try:\n        tree = ast.parse(source)\n    except SyntaxError:\n        return []",
    "    try:\n        tree = ast.parse(source)\n"
    "    except SyntaxError as exc:\n"
    "        # silent-by-design: source may legitimately be non-Python; hotspots cannot be computed.\n"
    "        logger.debug(\"context_pruner: source not parseable, no hotspots: %s\", exc, exc_info=True)\n"
    "        return []")
rep('scp/core/context_pruner.py',
    "    try:\n        tree = ast.parse(source)\n    except SyntaxError:\n        return source",
    "    try:\n        tree = ast.parse(source)\n"
    "    except SyntaxError as exc:\n"
    "        # silent-by-design: unparseable source is returned unchanged by design.\n"
    "        logger.debug(\"context_pruner: source not parseable, returned unchanged: %s\", exc, exc_info=True)\n"
    "        return source")
rep('scp/core/context_pruner.py',
    "        if pruned.strip():\n            return pruned\n    except Exception:\n        pass",
    "        if pruned.strip():\n            return pruned\n"
    "    except Exception as exc:\n"
    "        # silent-by-design: pruning is an optional refinement; the line-window fallback below is documented.\n"
    "        logger.debug(\"context_pruner: prune failed, using raw line window: %s\", exc, exc_info=True)")
rep('scp/core/context_pruner.py',
    "        return \"\\n\".join(f\"{n}: {lines[n - 1]}\" for n in range(start, end + 1))\n    except Exception:\n        return \"\"",
    "        return \"\\n\".join(f\"{n}: {lines[n - 1]}\" for n in range(start, end + 1))\n"
    "    except Exception as exc:\n"
    "        logger.warning(\"context_pruner: context build failed, returning empty context: %s\", exc, exc_info=True)\n"
    "        return \"\"")

# ---- cross_verify.py ----
rep('scp/core/cross_verify.py',
    "        except TypeError:\n            # Python <3.9 fallback: cancel_futures kwarg not supported.",
    "        except TypeError as exc:\n"
    "            # silent-by-design: Python <3.9 fallback; wait=False below still avoids blocking.\n"
    "            logger.debug(\"cross_verify: cancel_futures unsupported (%s), using shutdown(wait=False)\", exc, exc_info=True)\n"
    "            # Python <3.9 fallback: cancel_futures kwarg not supported.")
rep('scp/core/cross_verify.py',
    "        try:\n            data = fetch_with_retry(url, {\"User-Agent\": \"SCP-V91/1.0\"}, timeout=5, max_retries=1)\n        except Exception:\n            data = None",
    "        try:\n            data = fetch_with_retry(url, {\"User-Agent\": \"SCP-V91/1.0\"}, timeout=5, max_retries=1)\n"
    "        except Exception as exc:\n"
    "            # silent-by-design: REST summary is best-effort; later strategies still run.\n"
    "            logger.debug(\"cross_verify: wikipedia REST fetch failed: %s\", exc, exc_info=True)\n"
    "            data = None")
rep('scp/core/cross_verify.py',
    "                except Exception:  # noqa: S112\n                    continue",
    "                except Exception as exc:  # noqa: S112\n"
    "                    # silent-by-design: one bad page title must not abort the remaining candidates.\n"
    "                    logger.debug(\"cross_verify: page summary fetch failed, skipping: %s\", exc, exc_info=True)\n"
    "                    continue")
rep('scp/core/cross_verify.py',
    "        except Exception:\n            # Fallback: use q= with \"book\" appended\n            url = f\"https://openlibrary.org/search.json?q={urllib.parse.quote(title)}",
    "        except Exception as exc:\n"
    "            # silent-by-design: title= failure falls back to the documented q= query.\n"
    "            logger.debug(\"cross_verify: openlibrary title= failed, using q= fallback: %s\", exc, exc_info=True)\n"
    "            # Fallback: use q= with \"book\" appended\n            url = f\"https://openlibrary.org/search.json?q={urllib.parse.quote(title)}")

# ---- hypothesis_zone.py ----
rep('scp/core/hypothesis_zone.py',
    "            except (ValueError, TypeError):\n                is_match = str(entry[\"value\"]).strip().lower() == str(pass_value).strip().lower()",
    "            except (ValueError, TypeError) as exc:\n"
    "                # silent-by-design: non-numeric entries fall back to documented string comparison.\n"
    "                logger.debug(\"hypothesis_zone: numeric compare failed, using string compare: %s\", exc, exc_info=True)\n"
    "                is_match = str(entry[\"value\"]).strip().lower() == str(pass_value).strip().lower()")
rep('scp/core/hypothesis_zone.py',
    "        except Exception as e:\n            print(f\"HypothesisStore add_partial error: {e}\")\n            return -1",
    "        except Exception as e:\n            logger.warning(\"HypothesisStore add_partial failed: %s\", e, exc_info=True)\n            print(f\"HypothesisStore add_partial error: {e}\")\n            return -1")
rep('scp/core/hypothesis_zone.py',
    "            ) or 0\n        except Exception:\n            return 0",
    "            ) or 0\n"
    "        except Exception as exc:\n"
    "            # silent-by-design: cleanup is best-effort maintenance; stale pending entries are harmless.\n"
    "            logger.debug(\"hypothesis_zone: partial_entries cleanup failed (non-fatal): %s\", exc, exc_info=True)\n"
    "            return 0")
rep('scp/core/hypothesis_zone.py',
    "except Exception as e:\n    print(f\"[WARN] Hypothesis Zone init failed: {e}\")",
    "except Exception as e:\n    logger.warning(\"Hypothesis Zone init failed: %s\", e, exc_info=True)\n    print(f\"[WARN] Hypothesis Zone init failed: {e}\")")

# ---- conflict_resolver.py ----
rep('scp/core/conflict_resolver.py',
    "    try:\n        return float(v)\n    except (ValueError, TypeError):\n        return None",
    "    try:\n        return float(v)\n"
    "    except (ValueError, TypeError) as exc:\n"
    "        # silent-by-design: parse probe; None means \"not numeric\" by contract.\n"
    "        logger.debug(\"conflict_resolver: value not numeric: %s\", exc, exc_info=True)\n"
    "        return None")
rep('scp/core/conflict_resolver.py',
    "            except (TypeError, ValueError):\n                pass  # fail-open: keep multiplier at 1.0",
    "            except (TypeError, ValueError) as exc:\n"
    "                # silent-by-design: fail-open keeps multiplier at 1.0; made observable.\n"
    "                logger.debug(\"conflict_resolver: effective-weight clamp failed, multiplier=1.0: %s\", exc, exc_info=True)")
rep('scp/core/conflict_resolver.py',
    "            try:\n                normalized = str(float(val))\n            except (ValueError, TypeError):\n                normalized = str(val)\n            distinct.add(normalized)",
    "            try:\n                normalized = str(float(val))\n            except (ValueError, TypeError) as exc:\n"
    "                # silent-by-design: non-numeric values normalize to their string form by design.\n"
    "                logger.debug(\"conflict_resolver: value normalize fallback: %s\", exc, exc_info=True)\n"
    "                normalized = str(val)\n            distinct.add(normalized)")
rep('scp/core/conflict_resolver.py',
    "            try:\n                normalized = str(float(val))\n            except (ValueError, TypeError):\n                normalized = str(val)\n            by_value[normalized].append(v)",
    "            try:\n                normalized = str(float(val))\n            except (ValueError, TypeError) as exc:\n"
    "                # silent-by-design: non-numeric values normalize to their string form by design.\n"
    "                logger.debug(\"conflict_resolver: value normalize fallback: %s\", exc, exc_info=True)\n"
    "                normalized = str(val)\n            by_value[normalized].append(v)")

print("core batch 1 done")
