# Progress: worker_m2_p1_boundary

- **Current Status**: Investigating codebase and upstream analysis (explorer_m1_3/handoff.md)
- **Last visited**: 2026-09-27T08:40:20Z

## Checklist
- [ ] 1. Read ORIGINAL_REQUEST.md and explorer_m1_3/handoff.md (Sections 1.3 & 2.3)
- [ ] 2. Inspect target files:
  - [ ] dashboard/src/app/api/scp/ask/route.ts (and any other files with extractCallerAuth)
  - [ ] dashboard/src/middleware.ts
  - [ ] dashboard/src/lib/probe-allowlist.ts
  - [ ] mini-services/llm-bridge/core.ts
  - [ ] scp/web_control/web_navigator.py & scp/web_control/browser_session.py
- [ ] 3. Plan changes according to requirements & specifications
- [ ] 4. Implement Fix 1: extractCallerAuth real authentication (token/secret, 401 on invalid/missing)
- [ ] 5. Implement Fix 2: middleware.ts IP spoofing defense & probe-allowlist tightening
- [ ] 6. Implement Fix 3: mini-services/llm-bridge/core.ts timing-safe Bearer auth & fail-closed check
- [ ] 7. Implement Fix 4: scp/web_control/web_navigator.py & browser_session.py egress policy and DNS rebinding prevention
- [ ] 8. Verify all changes (syntax, type checks, unit tests)
- [ ] 9. Final self-critique, update BRIEFING.md, and write handoff.md
- [ ] 10. Send completion message to parent
