# Fully-worked promotion body — dagon example

Moved verbatim from SKILL.md Phase 4 (WRITE BACK). SKILL.md keeps the anchor-heading skeleton; this is the complete dagon-flavored example.

```html
<hr />
<h2>Tier-1 origin &amp; research context</h2>
<p><em>Emitted by /promote-issue on YYYY-MM-DD. Source plan: <code>path/to/plan.md</code>. Reviewer-facing narrative; agents can skip to Tier-2 below.</em></p>

<h3>Discovery</h3>
<p>...</p>

<h3>Severity rationale</h3>
<p>...</p>

<h3>Why the fix is non-trivial</h3>
<p>...</p>

<h3>Options considered</h3>
<ul><li><strong>Option A — ...:</strong> ...</li><li><strong>Option B — ...:</strong> ...</li></ul>

<h3>Why-now recommendation</h3>
<p>...</p>

<h3>Interim mitigation</h3>
<ul><li>...</li></ul>

<h3>Owner &amp; timing</h3>
<ul><li><strong>Engineering:</strong> ...</li><li><strong>Gate:</strong> ...</li><li><strong>Ship target:</strong> ...</li></ul>

<hr />
<h2>Tier-2 implementation context</h2>
<p><em>Promoted by /promote-issue on YYYY-MM-DD. Source plan: <code>path/to/plan.md</code></em></p>

<h3>Touches (files + lines)</h3>
<ul><li>...</li></ul>

<h3>Acceptance test</h3>
<pre><code>cargo test -p dagon-pool --test concern_30_binding -- --exact</code></pre>
<p>Must fail before the change; must pass after.</p>

<h3>Verification gate</h3>
<pre><code>cargo check -p dagon-pool &amp;&amp; cargo test --workspace --lib &amp;&amp; pnpm check:privacy-model</code></pre>

<h3>Scope</h3>
<p><strong>Allowed:</strong> <code>programs/dagon-pool/anchor/src/processor/</code>, <code>programs/dagon-pool/anchor/src/state.rs</code>, <code>documentation/privacy-model/</code>, <code>tests/</code></p>
<p><strong>Denied:</strong> <code>programs/archive/</code>, <code>ui-start/</code>, anything not named above</p>

<h3>Expected vs. actual</h3>
<p><strong>Actual:</strong> ...</p>
<p><strong>Expected:</strong> ...</p>

<h3>Reference implementation</h3>
<p>See sibling closure: <code>PRIVACY-COMPLIANCE-AUDIT.md</code> §P0-6 closure trail — same shape of fix applied to <code>submit_schedule.rs</code>.</p>

<h3>Hotspot / gate reminders</h3>
<ul>
  <li>TOUCHES <code>state.rs</code> → adding a field shifts vector offsets; update SchedulePool BASE_SIZE constant and add a canary test pinning the new size.</li>
  <li>TOUCHES <code>flows.yaml</code> → must add/update at least one flow row + DFD arrow; <code>pnpm check:privacy-model</code> will block PR merge otherwise.</li>
  <li>2-strike rule: if the verification gate fails twice on the same failure, stop and escalate — don't loop.</li>
</ul>
```
