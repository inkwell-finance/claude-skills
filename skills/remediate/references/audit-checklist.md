# Cross-Batch Audit Checklist

Paste this full checklist into the Phase 4b audit agent's prompt (see SKILL.md Phase 4b).

**Multi-agent conflicts**: fields added but not used by another agent, duplicate definitions, inconsistent imports

**Incomplete wiring**: `new X()` not passed to consumer, async methods with sync call sites, modules created but not imported

**Protocol/type drift**: test files using old type shapes, validation schemas out of sync with interfaces, IDL/proto field name mismatches with application code

**SQL mismatches**: application code assuming constraints migrations didn't create, missing indexes for query patterns

**Security**: template injection, `as any` casts, non-null assertions on optional fields, unhandled promise rejections

**Cross-repo consistency**: canonicalization functions producing different output, signing/verification algorithm mismatches

**Identity key confusion**: components using different keys for the same entity (pubkey vs peerId vs proposalId). Check that Maps, lookups, and stores all use the same key type for a given entity.

**Metrics double-counting**: metrics incremented on intermediate events (every partial result) instead of only on state transitions (actual finalization). Check that counters inside loops or callback handlers fire at the right granularity.

**Dead imports**: one agent imports a metric/function, another agent moves the actual usage to a different file. Grep for unused imports in modified files.

**Duplicate timers/sweeps**: two agents both add setInterval for the same resource (e.g., queue processing). Check for multiple timers targeting the same Redis key or data structure.

**Async call-site drift**: functions changed from sync to async (`Promise<` return type) but callers not updated with `await`. Grep modified files for new `async` keywords and verify all call sites use `await`. Run 3's only critical audit finding was this exact pattern.

**New required field propagation**: if a shared type gained a new required field, grep for all object literals / constructors that build that type across all repos. Verify each includes the new field. Run 4 found sandbox.ts constructing BacktestResult without a newly-added `winRate` field — broke all job submissions.

**Replacement method wiring**: if a new method was added to replace an old pattern (e.g., atomic LPOP replacing peek+remove), grep for the OLD method name and verify zero callers remain. Run 4 found `dequeueNextProposal()` added but `processQueuedProposals()` still calling the old `getNextQueuedProposal()` + `dequeueProposal()` pair.

**Schema optionality drift**: when a new field is added to a protocol schema as required, verify ALL producers (broadcast, publish, construct) include it — not just consumers that read it. If any producer doesn't include the field, the schema will reject messages at the consumer side, silently breaking inter-service communication. Run 13 found a required `signature` field that the coordinator's broadcast function didn't include.

**Auditor trace depth**: when verifying a fix exists, trace into private methods and call chains — don't just grep for the function name at the top level. Run 13's audit had 2 false positives (29%) because the auditor found `pendingJobsCount.set()` inside a private method that WAS called from `init()`, and `updateStoredUnrealizedPnl` inside a helper that WAS called from the price update path. Pattern: for any "this function is never called" finding, grep for the function name AND its containing method's name.
