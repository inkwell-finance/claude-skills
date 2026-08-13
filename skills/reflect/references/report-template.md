# /reflect — Analysis Framework and Report Template

Paste both sections below into the analysis subagent's prompt (or instruct it
to read this file).

## Analysis Framework

Review the transcripts looking for these categories. DEDUP RULE: Each issue belongs in exactly one section — the most relevant one.

### A. Friction Points
- Tool failures or retries
- Wrong approaches that had to be corrected
- Missing information that required extra lookups
- Commands or skills that didn't exist but should have
- Manual steps that could be automated

### B. Struggles and Corrections
- Misunderstandings of intent
- Wrong file paths or API usage
- Incorrect assumptions
- "No, I meant..." moments

### C. Repeated Patterns
- Similar queries run in different contexts
- Workflows that follow the same structure
- Lookups that could be cached

### D. Discoveries
- How a system actually works vs. assumption
- New capabilities found
- Edge cases or gotchas

### E. Skill/Command Gaps
- Requests that required long ad-hoc workflows
- Multi-step processes that could be a /command

### F. Documentation Gaps
- Outdated or incomplete SOPs
- Missing cross-references
- Tribal knowledge that should be written down

## Report Template

Produce the report in EXACTLY this format:

# Session Retrospective - {DATE}

**Session focus:** {1-sentence summary}\
**Duration:** {approximate}\
**Key files touched:** {list}

---

## Friction Points Found

### {Friction Point 1}
- **What happened:** {Specific description}
- **Impact:** {How much time/effort was wasted}
- **Suggested fix:** {Concrete improvement}
- **Type:** {memory | skill | command | sop | agent | code}
- **Breaking change?** {Yes/No}
- **Effort:** {Small | Medium | Large}
- **Auto-implement?** {Yes — memory/sop update | No — needs review}

---

## Corrections Made (Learning Opportunities)

### {Correction 1}
- **User said:** "{Quote or paraphrase}"
- **What was wrong:** {What was incorrect}
- **Root cause:** {Why}
- **Prevention:** {How to avoid}
- **Type:** {memory | sop | skill | prompt-update}
- **Auto-implement?** {Yes | No}

---

## New Patterns Worth Capturing

### {Pattern 1}
- **Pattern:** {Description}
- **Frequency this session:** {count}
- **Suggested action:** {Add to memory | Create skill | Update SOP | Create command}
- **Draft content:** {Exact text/code to add}
- **Auto-implement?** {Yes | No}

---

## Skill/Command Suggestions

### {Suggestion 1}: /command-name
- **Trigger:** {When invoked}
- **What it does:** {Brief description}
- **Based on:** {Session evidence}
- **Effort:** {Small | Medium | Large}
- **Priority:** {Should exist now | Nice to have | Someday}

---

## Memory Updates

### {Memory 1}
- **File:** {filename.md}
- **Content:** {Exact frontmatter + body to write}
- **Replaces:** {Existing entry, if any}
- **Auto-implement?** Yes

---

## Documentation Gaps

### {Gap 1}
- **What's missing:** {Description}
- **Where it should go:** {File path}
- **Draft content:** {Content}
- **Auto-implement?** {Yes | No}

---

## Summary

**COUNTING RULE:** Count distinct actionable items only. A memory that fixes a friction point is ONE item. Auto-implemented + Needs approval must sum to total.

**Total actionable improvements:** {count} ({count} auto-implemented + {count} needs approval)

Breakdown by type:
- Memory/SOP updates: {count} (auto-implemented)
- New skills/commands: {count} (needs approval if non-trivial)
- Documentation fixes: {count}

**Top 3 highest-impact improvements:**
1. {Most impactful}
2. {Second}
3. {Third}
