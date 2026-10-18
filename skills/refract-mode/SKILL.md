---
name: refract-mode
description: >-
  View or switch Refract's operating mode between Auto-Intercept Mode, Coach Mode,
  and Slash-Only Mode, or adjust the interception score threshold. Triggered by
  the /refract-mode slash command.
---

# Refract Mode (`/refract-mode`) — Configure Interception Behavior

When the user invokes `/refract-mode`, help them inspect or switch how Refract intercepts chat messages:

## Operating Modes

1. **`auto-intercept` (Default)**:
   - Passively inspects every turn via the `PreInvocation` hook.
   - Strong prompts (Score $\ge$ threshold) pass through invisibly with zero overhead.
   - Diffuse follow-ups or failure spirals are automatically grounded using `transcript.jsonl`, shown in a compact `<details><summary>💠 Refracted Prompt...</summary></details>` block at the top of the response, and executed immediately.
2. **`coach`**:
   - When a prompt scores below the threshold or hits an architectural fork, Refract pauses and presents a 1-click `ask_question` modal with the 3 Refracted Spectrums before executing.
3. **`slash-only`**:
   - Disables automatic turn interception; Refract only activates when summoned explicitly via `/refract` or `/refract-check`.

## Steps

1. If the user didn't specify a target mode in `/refract-mode`, check current status first:
   ```bash
   python3 ~/.gemini/config/plugins/refract/scripts/refract_engine.py --status
   ```
   Then use `ask_question` to let them pick **`auto-intercept`**, **`coach`**, or **`slash-only`**.
2. Update the configuration using the CLI:
   ```bash
   python3 ~/.gemini/config/plugins/refract/scripts/refract_engine.py --set-mode <MODE>
   ```
3. Confirm the active mode and threshold to the user.
