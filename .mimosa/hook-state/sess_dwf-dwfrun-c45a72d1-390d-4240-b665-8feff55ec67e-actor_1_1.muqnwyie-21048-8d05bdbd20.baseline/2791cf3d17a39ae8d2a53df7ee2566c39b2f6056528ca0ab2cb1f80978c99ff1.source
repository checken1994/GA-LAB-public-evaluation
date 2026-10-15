from pathlib import Path

def rep(path, old, new, count=1):
    p = Path(path)
    src = p.read_text(encoding='utf-8')
    found = src.count(old)
    assert found == count, f"{path}: anchor x{found} (want {count}): {old[:60]!r}"
    p.write_text(src.replace(old, new), encoding='utf-8')
    print(f"OK {path} x{count}")

# ---------- math_evaluator.py (add logger) ----------
rep('scp/core/math_evaluator.py',
    "import ast\nimport math\nimport operator\nimport re\nfrom typing import Any",
    "import ast\nimport logging\nimport math\nimport operator\nimport re\nfrom typing import Any\n\nlogger = logging.getLogger(__name__)")

# 335: evaluate probe -> substring extraction fallback
rep('scp/core/math_evaluator.py',
    "        try:\n            evaluate_expression(q2)\n            return q2\n        except MathEvalError:",
    "        try:\n            evaluate_expression(q2)\n            return q2\n"
    "        except MathEvalError as exc:\n"
    "            # silent-by-design: probe failure triggers the documented substring-extraction fallback.\n"
    "            logger.debug(\"math_evaluator: direct evaluate failed, extracting substring: %s\", exc, exc_info=True)")

# 350: candidate trim loop probe (anchor: comment line follows at deeper indent)
rep('scp/core/math_evaluator.py',
    "                    except MathEvalError:\n",
    "                    except MathEvalError as exc:\n"
    "                        # silent-by-design: trim-probe failure drives the documented cut-from-end loop.\n"
    "                        logger.debug(\"math_evaluator: candidate evaluate failed, trimming: %s\", exc, exc_info=True)\n",
    count=1)

# 381: last-number float parse probe
rep('scp/core/math_evaluator.py',
    "    try:\n        return float(nums[-1])\n    except ValueError:\n        return None",
    "    try:\n        return float(nums[-1])\n"
    "    except ValueError as exc:\n"
    "        # silent-by-design: parse probe on free text; None means \"no number found\".\n"
    "        logger.debug(\"math_evaluator: last-number parse failed: %s\", exc, exc_info=True)\n"
    "        return None")

# 493: CLI self-test already prints the error — mirror to logs
rep('scp/core/math_evaluator.py',
    "        except Exception as e:\n            print(f\"  [ERR ] {expr:30s} \u2192 {e}\")",
    "        except Exception as e:\n"
    "            # silent-by-design: CLI self-test prints the error directly; mirrored to logs.\n"
    "            logger.debug(\"math_evaluator self-test: %s \u2192 %s\", expr, e, exc_info=True)\n"
    "            print(f\"  [ERR ] {expr:30s} \u2192 {e}\")")

# ---------- partition/shard.py ----------
rep('scp/core/partition/shard.py',
    "                            try:\n                                with open(_path, encoding=\"utf-8\", errors=\"replace\") as f:\n                                    _day_lines = f.readlines()\n                            except Exception:  # noqa: S112\n                                continue",
    "                            try:\n                                with open(_path, encoding=\"utf-8\", errors=\"replace\") as f:\n                                    _day_lines = f.readlines()\n"
    "                            except Exception as _dup_err:  # noqa: S112\n"
    "                                # silent-by-design: unreadable day file only weakens dedup; never blocks the write path.\n"
    "                                logger.debug(\"shard: bypass day-file read failed for %s (non-fatal): %s\", _path, _dup_err, exc_info=True)\n"
    "                                continue")

rep('scp/core/partition/shard.py',
    "                                except Exception:  # noqa: S112\n                                    continue",
    "                                except Exception as _line_err:  # noqa: S112\n"
    "                                    # silent-by-design: unparseable historical line only weakens dedup; never blocks writes.\n"
    "                                    logger.debug(\"shard: bypass line parse failed in dedup scan (non-fatal): %s\", _line_err, exc_info=True)\n"
    "                                    continue")

rep('scp/core/partition/shard.py',
    "            try:\n                file_date = datetime.strptime(f.stem, \"%Y-%m-%d\")\n            except ValueError:\n                continue",
    "            try:\n                file_date = datetime.strptime(f.stem, \"%Y-%m-%d\")\n"
    "            except ValueError as exc:\n"
    "                # silent-by-design: non-date files in the archive dir are skipped by design.\n"
    "                logger.debug(\"shard: skipped non-date file %s: %s\", f, exc, exc_info=True)\n"
    "                continue")

# ---------- partition/archive.py ----------
rep('scp/core/partition/archive.py',
    "            return count or 0\n        except Exception:\n            return 0",
    "            return count or 0\n"
    "        except Exception as exc:\n"
    "            # silent-by-design: TTL cleanup is best-effort maintenance; stale rows are harmless.\n"
    "            logger.debug(\"archive: pending_reverification TTL cleanup failed (non-fatal): %s\", exc, exc_info=True)\n"
    "            return 0")

# ---------- top_systems_learning.py (4x corrupt ledger line) ----------
rep('scp/core/top_systems_learning.py',
    "                try:\n                    digest = json.loads(line).get(\"content_sha256\")\n                except (TypeError, ValueError):\n                    continue",
    "                try:\n                    digest = json.loads(line).get(\"content_sha256\")\n"
    "                except (TypeError, ValueError) as exc:\n"
    "                    # Corrupt ledger line must be visible, not silently dropped.\n"
    "                    logger.warning(\"top_systems_learning: corrupt ledger line in %s: %s\", self.ledger_path, exc, exc_info=True)\n"
    "                    continue")

rep('scp/core/top_systems_learning.py',
    "            for line in reversed(lines[-2000:]):\n                try:\n                    record = json.loads(line)\n                except (TypeError, ValueError):\n                    continue",
    "            for line in reversed(lines[-2000:]):\n                try:\n                    record = json.loads(line)\n"
    "                except (TypeError, ValueError) as exc:\n"
    "                    # Corrupt ledger line must be visible, not silently dropped.\n"
    "                    logger.warning(\"top_systems_learning: corrupt ledger line in %s: %s\", self.ledger_path, exc, exc_info=True)\n"
    "                    continue")

rep('scp/core/top_systems_learning.py',
    "            try:\n                record = json.loads(line)\n            except (TypeError, ValueError):\n                kept_lines.append(line)\n                continue",
    "            try:\n                record = json.loads(line)\n"
    "            except (TypeError, ValueError) as exc:\n"
    "                # Corrupt line is kept verbatim (no data loss) but must be visible.\n"
    "                logger.warning(\"top_systems_learning: corrupt ledger line kept in %s: %s\", self.ledger_path, exc, exc_info=True)\n"
    "                kept_lines.append(line)\n                continue")

rep('scp/core/top_systems_learning.py',
    "            for line in self.ledger_path.read_text(encoding=\"utf-8\").splitlines():\n                try:\n                    record = json.loads(line)\n                except (TypeError, ValueError):\n                    continue\n                count += 1",
    "            for line in self.ledger_path.read_text(encoding=\"utf-8\").splitlines():\n                try:\n                    record = json.loads(line)\n"
    "                except (TypeError, ValueError) as exc:\n"
    "                    # Corrupt ledger line must be visible, not silently dropped.\n"
    "                    logger.warning(\"top_systems_learning: corrupt ledger line in %s: %s\", self.ledger_path, exc, exc_info=True)\n"
    "                    continue\n"
    "                count += 1")

print("cluster B done")
