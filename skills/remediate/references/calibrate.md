# Calibrate — Full Procedure

`/remediate calibrate` reads `plans/CALIBRATION.md` and **rewrites sections of the skill file** based on the learnings.

Steps:
1. Read `plans/CALIBRATION.md` — extract the RULES section and HISTORY section. If the file doesn't exist, report that there is nothing to calibrate and stop — do not edit the skill.
2. Read the skill file at `~/.claude/skills/remediate/SKILL.md`
3. **Filter**: only take learnings that improve the remediation **process** — how to analyze, plan, batch, execute, or audit. Discard codebase-specific implementation rules (e.g., "use canonicalJson for signing", "clear epoch accumulators at midnight"). Those belong in CALIBRATION.md where they're injected at runtime via `{additional rules from CALIBRATION.md}` in the prompt template.
4. For each process-level learning, determine which section of the skill it applies to:
   - Analysis quality → Phase 1 (e.g., "verify math direction with concrete values before implementing")
   - Batch coordination → batch formation rules (e.g., "when adding a required field to a shared type, include constructor updates in same agent")
   - Multi-agent failure patterns → `references/audit-checklist.md` (e.g., "check that new methods actually replaced old callers")
   - Model assignment → COMPLEXITY table
5. Present the diff to the user for approval before writing.

**What belongs in the skill vs CALIBRATION.md**:
- **Skill**: process rules that apply to ANY codebase. "Verify direction with concrete values." "Audit for unwired replacement methods." "Group shared-type field additions with constructor updates."
- **CALIBRATION.md**: project-specific implementation rules. "Use canonicalJson for signing." "Clear epochImpacts on rollover." "Register PIDs before sandbox completes." These are injected into agent prompts at runtime and don't need to be in the skill.

**What this means**: The skill stays lean and portable. CALIBRATION.md captures project-specific knowledge that agents need at runtime. Both evolve, but through different channels.

After calibration, CALIBRATION.md's RULES section can note "baked into skill on YYYY-MM-DD" for each rule that was applied, so future runs don't re-apply the same rule.
