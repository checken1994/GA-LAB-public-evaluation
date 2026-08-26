# PC folder archive index

**Created:** 2026-08-26
**Canonical code commit at sync:** `fb629aead5c3332422980ab4facfc2b31900f466`

## Purpose

This index records the two auxiliary workspaces that were removed from `C:\Users\check\Downloads` only after a complete tar.gz archive was created and validated. The archives remain outside the Git repository at `C:\Users\check\Downloads\scp-folder-archives-20260826\` and are not copied into GitHub because they contain full `.git` directories, logs, caches and generated files.

| Removed folder | Repository/HEAD observed | Archive | Original file count | Status |
|---|---|---|---:|---|
| `scp-agent-structure-debt` | `checken1994/scp-agent.git`, `master`, `cb132a5af9f0dbcc6293b939ab32136cef22593c` | `scp-agent-structure-debt_cb132a5a.tar.gz` | 5,789 | Archived, then removed from Downloads |
| `scp-structure-debt-worktree` | `checken1994/GA-LAB.git`, `structure-debt-pc-merge`, `23f41b7efae89b3b1e2a96c50cae51021ac9098d` | `scp-structure-debt-worktree_23f41b7e.tar.gz` | 49,677 | Archived, then removed from Downloads |

The PC archive directory contains `manifest.json`, which records source path, HEAD, remote, file count, byte count, archive path and archive SHA-256. The two tarballs were checked for existence before deletion. The archive is the exact recovery copy; this GitHub index is only the provenance pointer.

## What was synchronized into canonical root

The committed GA-LAB content already in `origin/main` was pulled into `C:\Users\check\Downloads\scp`. The untracked six-file comparison artifact from `scp-structure-debt-worktree` was copied under `reports/archived_workspaces_20260826/scp-structure-debt-worktree/` without overwriting tracked root files. Its copy has its own manifest and file hashes.

The separate `scp-agent` repository was **not blindly merged**. The existing core-repository matrix records 475 common paths, 435 identical blobs, 40 differing common blobs, 214 paths only in `scp-agent` and 697 only in GA-LAB. Different implementation files require review; an archive is not proof that those changes belong in GA-LAB.

## Deletion postcondition

At the time of this index, both old Downloads folders were confirmed absent, `C:\Users\check\Downloads\scp` remained present, and the external archive directory remained present. No root code, GitHub branch, raw archive or unrelated untracked file was deleted.
