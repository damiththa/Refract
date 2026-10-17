---
name: refract-check
description: >-
  Audit a prompt draft or the current conversation's trajectory health across the
  5-Dimension Refract Rubric, and render an interactive Generative UI Scorecard
  widget inline in chat. Triggered by the /refract-check slash command.
---

# Refract Check (`/refract-check`) — Interactive Scorecard & Trajectory Audit

When the user invokes `/refract-check` (with a draft prompt or bare to audit the conversation trajectory), follow these steps:

## Step 1: Run the Refract Engine & Generate the HTML Scorecard

1. Determine the current conversation's `transcript.jsonl` path (`<appDataDir>/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`) and artifact directory (`<appDataDir>/brain/<conversation-id>`).
2. Run `refract_engine.py` with `--analyze` and `--html-widget`:

```bash
python3 ~/.gemini/config/plugins/refract/scripts/refract_engine.py \
  --analyze "<USER_DRAFT_OR_EMPTY>" \
  --transcript "<TRANSCRIPT_JSONL_PATH>" \
  --html-widget "<ARTIFACT_DIR>/refract_scorecard.html"
```

3. Use `write_to_file` (with `Overwrite: true` and `ArtifactMetadata: { UserFacing: true, RequestFeedback: false, Summary: "Interactive Refract Trajectory Scorecard" }`) or touch the generated `<ARTIFACT_DIR>/refract_scorecard.html` file so Antigravity registers it as a user-facing artifact.

## Step 2: Embed the Interactive Scorecard Inline in Chat

Include the `<agent-embed>` tag directly in your response so the interactive scorecard renders inline in the conversation:

```markdown
<agent-embed src="file:///<ARTIFACT_DIR>/refract_scorecard.html"></agent-embed>
```

## Step 3: Provide Concise SME Coaching Notes

Below the embedded widget, provide a concise summary:
- Highlight any **Unbound Pronouns / Missing Context** or **Failure Spiral Risks** detected in the transcript.
- Remind the user they can click between **⚡ Precision**, **🔬 Root-Cause**, and **🛡️ Strict Spec** inside the widget (or run `/refract` to execute one with 1 click).
