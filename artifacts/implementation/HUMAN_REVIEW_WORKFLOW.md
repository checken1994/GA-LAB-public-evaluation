# Human review workflow included in SCP main

The private canonical repository now includes a reviewer-friendly queue generator and a fail-closed decision validator. The queue can be rendered as CSV and HTML. Each row shows the question, candidate answer, canonical source URL/title, source excerpt, source hash, current/high-stakes flag, and blank decision fields.

A reviewer may choose `VERIFIED`, `REJECTED`, or `NEEDS_MORE_EVIDENCE`. A `VERIFIED` record must include reviewer identity, a timezone-aware UTC timestamp, a source URL matching the candidate, an evidence quote, a decision hash, and an HMAC signature when the reviewing organization requires signed records. Missing or inconsistent fields result in `BLOCKED`.

The workflow does not auto-promote data. Independent model triage remains model triage; it cannot be relabeled as human verification. The queue also does not itself prove that a source is correct or current. A second reviewer or adjudicator is still required when decisions conflict.

The public evidence repository contains only this implementation summary and the previously exported sanitized evidence. It does not include private source history, secret keys, local caches, raw archives, or unreviewed private artifacts. The full source-level implementation is in the private GA-LAB repository at the commit recorded in the public update.
