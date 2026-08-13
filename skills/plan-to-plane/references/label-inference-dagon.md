# Label inference — dagon path/topic table

Moved verbatim from SKILL.md Phase 2 (dagon-specific heuristics; the general rule — only attach a label if the signal is strong, `LABELS: [...]` frontmatter overrides — lives in SKILL.md).

Component-inferred (from TOUCHES paths — if any path matches, add the label):
- `programs/` or `*/anchor/src/` → `on-chain`
- `services/mock-executor/` or `crates/` or `*/backend/` → `backend`
- `ui-start/` or `frontend/` or `src/dapp/` → `frontend`
- `documentation/` or `plans/` only → no component label (it's a doc task)

Topic-inferred (from concern title or body):
- Title or body contains "security", "auth", "key" → `security`
- Title or body contains "OFAC", "MiCA", "FINRA", "KYT", "GDPR", "counsel" → `compliance`
- Body has "engineering-ready" / "ships independently" → `engineering-ready`
- Body has "blocked on Encrypt" / "queue item A\d+" → `external-dep`
- Title starts with "ADR-" or body references ADR → `ADR`
- Title contains "concern-\d+" → `concern`
