---
name: stop-slop
description: Remove AI writing tells from prose while preserving meaning. Use when drafting, editing, or reviewing any written deliverable — docs, ADRs, READMEs, marketing copy, scripts, emails, reports — or when the user says "slop", "de-slop", "sounds like AI", "humanize this", "make it less robotic", or "punch this up". Not for code, commit messages, quoted material, or structured config text.
metadata:
  author: Hardik Pandya (https://hvpandya.com)
  upstream: github.com/hardikpandya/stop-slop @ 8da1f03
---

# Stop Slop

Eliminate predictable AI writing patterns from prose.

Two constraints govern every edit:

**Preserve meaning.** Never strengthen, weaken, or drop a claim while restyling it. Quantifiers ("most", "some", "usually") are content, not hedges. Keep uncertainty that reflects real uncertainty, and reasoning the reader needs to evaluate a claim. Never alter direct quotes, code, numbers, or citations. If removing a pattern would change what the text asserts, keep the pattern or flag it.

**Match the register.** These rules target narrative and persuasive prose. In technical writing, software components are legitimate actors ("the validator rejects the flow" is correct), passive voice is fine when the actor is unknown or irrelevant, and precision adverbs ("only", "atomically", "weekly") carry information. The tells to hunt are repetition and performance, not grammar.

## Core Rules

1. **Cut filler phrases.** Remove throat-clearing openers, emphasis crutches, and all adverbs. See [references/phrases.md](references/phrases.md).

2. **Break formulaic structures.** Avoid binary contrasts, negative listings, dramatic fragmentation, rhetorical setups, false agency. See [references/structures.md](references/structures.md).

3. **Use active voice.** Prefer a concrete actor as the subject — a person where one exists, the component itself in technical prose. Never let an abstraction perform a human's action ("the complaint becomes a fix", "the decision emerges"). Keep passive voice only when the actor is unknown or genuinely irrelevant.

4. **Be specific.** No vague declaratives ("The reasons are structural"). Name the specific thing. No lazy extremes ("every," "always," "never") doing vague work.

5. **Put the reader in the room.** No narrator-from-a-distance voice. "You" beats "People." Specifics beat abstractions.

6. **Vary rhythm.** Mix sentence lengths. Two items beat three. End paragraphs differently. No em dashes.

7. **Trust readers.** State facts directly. Skip reassurance, hand-holding, and re-justifying what the reader already accepts. Keep load-bearing reasoning and real caveats.

8. **Cut quotables.** If a line performs profundity while only restating the previous point, rewrite it as a plain statement.

## Quick Checks

Before delivering prose:

- Empty intensifiers or hedge adverbs ("really", "very", "just", "actually")? Kill them. Keep adverbs that carry information.
- Passive voice hiding a known actor? Make the actor the subject.
- Inanimate thing doing a human verb ("the decision emerges")? Name the person.
- Rhetorical Wh- opener ("What makes this hard is...")? Restructure it. A plain subordinate clause ("When the build fails, ...") is fine.
- Any "here's what/this/that" throat-clearing? Cut to the point.
- Any "not X, it's Y" contrasts? State Y directly.
- Three consecutive sentences match length? Break one.
- Paragraph ends with punchy one-liner? Vary it.
- Em-dash anywhere? Remove it.
- Vague declarative ("The implications are significant")? Name the specific implication.
- Narrator-from-a-distance ("Nobody designed this")? Put the reader in the scene.
- Meta-joiners ("The rest of this essay...")? Delete. Let the essay move.

## Final Gate

Before delivering, confirm:

- Every Quick Check passes.
- Meaning survived: no claim strengthened, weakened, or dropped; quantifiers, numbers, quotes, and attributions intact.
- Nothing cuttable remains.

If a check fails, revise the failing sentences and re-check once. Deliver after that single revision pass; note anything that still reads as a tell rather than looping.

## Examples

See [references/examples.md](references/examples.md) for before/after transformations.
