# Refract — Trajectory & Context Interception Rules

When the `refract` plugin is enabled, its `PreInvocation` hook (`scripts/refract_engine.py`) evaluates incoming prompts against the conversation transcript (`transcript.jsonl`) and workspace trajectory.

## Handling `[REFRACT_INTERCEPT]` Ephemeral Messages

When you receive an ephemeral message starting with `[REFRACT_INTERCEPT ...]`:

1. **In `auto-intercept` mode (`[REFRACT_INTERCEPT mode="auto-intercept" ...]`)**:
   - Render the compact collapsible header at the very start of your final user-facing response:
     ```markdown
     <details><summary>💠 <b>Refracted Prompt</b> (Score: X/100 → Grounded via Spectrum)</summary>

     > [Upgraded context-grounded prompt]
     </details>
     ```
   - Execute the **Upgraded Prompt** directly, using the bound session files and error context identified from the transcript.
   - If a **Failure Spiral** was flagged (`🔬 Root-Cause Spectrum`), stop making blind edits: state your top root-cause hypotheses, verify the actual state using read/diagnostic tools first, and then apply the fix.

2. **In `coach` mode (`[REFRACT_INTERCEPT mode="coach" ...]`)**:
   - Briefly display the Refract Score and the detected trajectory/context gaps.
   - Immediately call `ask_question` with the 3 Refracted Spectrums (`⚡ Precision`, `🔬 Root-Cause`, `🛡️ Strict Spec`) so the user can choose how to proceed with 1 click.

3. **When NO `[REFRACT_INTERCEPT]` tag is present**:
   - The user's prompt passed the Refract Trajectory Rubric threshold (or was an explicit slash command / confirmation). Respond normally with zero extra meta-commentary.
