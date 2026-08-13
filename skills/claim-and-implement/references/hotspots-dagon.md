# Privacy-model hotspots — dagon enumeration

Moved verbatim from SKILL.md Phase 4 (IMPLEMENT). Source of truth is `packages/dagon/CLAUDE.md` §"MANDATORY: Privacy-model discipline".

Any TOUCHES path under ANY of the following triggers the full privacy-model chain — do not narrow this list without updating CLAUDE.md first:

1. ANY file under `programs/dagon-pool/anchor/src/processor/` (new or modified Anchor instruction).
2. ANY file under `services/mock-executor/src/session/` or `services/mock-executor/src/privacy/` (new or modified HTTP handler, session logic, privacy primitive).
3. ANY file under `services/mock-executor/src/solana/` that adds a new ix builder or new signing path.
4. ANY new `.route(...)` call in the mock-executor router.
5. ANY new public gRPC method or new proto message that carries user data.
6. ANY field / PDA / ciphertext handle added to `programs/dagon-pool/anchor/src/state.rs`.
7. ANY new `documentation/adrs/NNN-*.md` that makes a privacy or compliance claim.
8. ANY file under `crates/dagon-fhe/src/` that changes a graph's input/output shape.

When any of the above is touched, the VERIFY chain MUST include:

```
pnpm check:privacy-model && pnpm test:privacy-model
```

A skipped privacy-model step counts as a verification failure, regardless of what the original Tier-2 gate said. A new data flow across a trust boundary additionally requires a row in `documentation/privacy-model/flows.yaml` + an arrow in `documentation/privacy-model/DFD.mmd` — paired in the SAME commit (the pre-commit hook enforces this). Narration does not satisfy enumeration; a `flows.yaml` row with all 7 LINDDUN cells filled is the evidence.
