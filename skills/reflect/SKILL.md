---
name: reflect
description: Session retrospective — analyze what happened, find friction, auto-implement quick wins, publish report. Use when the user says "reflect", "retro", "post-mortem", "what went wrong this session", or "what should we improve".
---

You are performing a session retrospective to extract learnings and suggest system improvements.

**This is NOT `/eod` or `/pause`.** Those handle day-ending and session-saving mechanics. `/reflect` is a learning loop that analyzes the current session for ways to improve your Claude Code setup itself.

## What This Does

1. Reads the current session transcript
2. Identifies friction points, struggles, workarounds, repeated patterns, and discoveries
3. Produces a report with specific, actionable improvement suggestions
4. Auto-implements quick wins (memory updates, one-liner SOP additions) with your approval
5. Presents the full report in readable format

## Architecture: Subagent Delegation

The analysis phase (Step 2) runs in a subagent that **inherits the session model** (omit the `model` parameter on the Agent call; opus fallback if fable rate-limits) for pattern recognition, synthesis, and memory drafts. The main session handles transcript loading (Step 1) and implementation (Steps 3-4).

```
Main session:       Load transcripts → delegate analysis → implement quick wins → publish
Analysis subagent:  Analyze patterns → check overlap → generate report
```

---

### Step 1: Load Session Transcript

Get the current session transcript from disk. Claude Code stores sessions in `~/.claude/projects/<project-slug>/`, where the slug is the project path with `/` replaced by `-` (e.g. `/home/lars/sui/omp-squad` → `-home-lars-sui-omp-squad`). Derive it at runtime:

```bash
# Slug = absolute project path with '/' replaced by '-'
PROJECT_DIR=$(pwd)
SLUG=$(echo "$PROJECT_DIR" | tr '/' '-')
SESSION_DIR="$HOME/.claude/projects/$SLUG"

# Find the main session (most recently modified)
LATEST_JSONL=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1)
echo "Main session: $LATEST_JSONL"
wc -l "$LATEST_JSONL"
```

Read the session file, extracting user messages and assistant text (skip raw tool results):

```bash
extract_session() {
  local FILE="$1"
  echo "=== $(basename $FILE) ==="
  # User messages
  jq -r 'select(.type == "user") | select(.message.content | type == "string") | "USER: " + .message.content' "$FILE" 2>/dev/null
  # Assistant text blocks only
  jq -r 'select(.type == "assistant") | .message.content[]? | select(.type == "text") | "ASSISTANT: " + .text' "$FILE" 2>/dev/null
}

extract_session "$LATEST_JSONL"
```

**If a JSONL is very large (1000+ lines),** focus on:
- All user messages (these are the primary signal)
- Assistant text that contains reasoning, decisions, or corrections
- Tool use results that show errors or retries

---

### Step 2: Spawn Analysis Subagent

Delegate the heavy analysis work to a subagent that inherits the session model. Pass it:
1. The extracted transcript content from Step 1
2. The analysis framework and report template — both live in [references/report-template.md](references/report-template.md); read that file and paste both sections into the prompt
3. Existing system context (commands, skills, memory files)

**Before spawning**, gather the overlap context the agent will need:

```bash
# Existing commands
ls .claude/commands/*.md 2>/dev/null | head -30
# Existing skills (if using skill directories)
ls .claude/skills/*/SKILL.md 2>/dev/null | head -30
# Memory files (if using auto-memory)
ls ~/.claude/projects/$SLUG/memory/ 2>/dev/null
```

**Spawn the Agent** with `subagent_type: "general-purpose"` and NO `model` parameter (it inherits the session model; opus fallback if fable rate-limits):

```
Agent({
  description: "Reflect analysis",
  prompt: `You are performing a session retrospective analysis. Your job is to analyze transcripts, identify patterns and friction, and produce a structured improvement report.

DO NOT implement any changes. DO NOT write any files. Only produce the report as text output.

## Transcript Data
{paste extracted user messages and assistant text from Step 1}

## Existing System Context
Commands: {list}
Skills: {list}
Memory files: {list}

{paste the Analysis Framework and Report Template sections from references/report-template.md}
`
})
```

The subagent returns the full report as text. Save it for the next steps.

---

### Step 3: Auto-Implement Quick Wins

Using the analysis report, implement any items marked `Auto-implement? Yes`:
- Memory file additions or updates (no breaking changes, purely additive)
- One-liner SOP additions (appending a note to an existing file)
- Fixing an obviously wrong reference in a doc

**Rules for auto-implementation:**
- Only implement if confidence is high (the need is unambiguous from the transcript)
- Write the change, then append it to the "Quick Wins Auto-Implemented" section of the report
- Do NOT auto-implement: new skills, new commands, changes to core system files, anything that could break existing behavior

For each auto-implemented item, apply the change and note it in the report.

---

### Step 4: Save Report + Present Summary

1. **Save the full report** to `~/.claude/reflections/`:
   ```bash
   mkdir -p ~/.claude/reflections
   DATE=$(date +"%Y-%m-%d")
   TOPIC_SLUG="<1-3-word-description>"  # e.g. "email-triage", "auth-refactor"
   OUTFILE="$HOME/.claude/reflections/${DATE}-${TOPIC_SLUG}.md"
   ```

2. **Present the report** — render as markdown, open in browser, or use your preferred viewer.

3. **Show a summary** with:
   - What the session accomplished
   - How many improvements found
   - What was auto-implemented
   - What needs approval

---

## What This Command Does NOT Do

- Does not commit or push (that's `/pause` or manual)
- Does not update task status (that's `/eod`)
- Does not save session state for resumption (that's `/pause`)
- Does not auto-implement anything with breaking changes or meaningful risk

## Guidelines

- **Minimum viable report.** If the session was straightforward with no friction, say so. Don't invent problems. A report that says "Clean session, no improvements needed" is a valid outcome.
