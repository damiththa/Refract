---
name: refract
description: >-
  Refract a rough or underspecified prompt through the full conversation history and
  workspace context into 3 actionable engineering spectrums (Precision, Root-Cause,
  Strict Spec), and let the user execute their preferred spectrum with one click.
  Triggered by the /refract slash command.
---

# Refract (`/refract`) — Context & Trajectory Prompt Refiner

When the user invokes `/refract` (with or without a draft prompt), follow these steps:

## Step 1: Locate the Active Transcript & Run the Refract Engine

1. Identify the current conversation's `transcript.jsonl` path (`<appDataDir>/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`).
2. Extract the draft prompt provided after `/refract` (if the user invoked `/refract` bare with no text, ask them what task they want to refract, or analyze their previous prompt turn).
3. Run the Refract Engine CLI to score the draft against the conversation trajectory:

```bash
python3 ~/.gemini/config/plugins/refract/scripts/refract_engine.py \
  --analyze "<USER_DRAFT_PROMPT>" \
  --transcript "<TRANSCRIPT_JSONL_PATH>"
```
*(If running from a workspace copy before global install, use `/Users/madushan/.gemini/antigravity/scratch/refract/scripts/refract_engine.py`.)*

## Step 2: Enrich with Live Workspace Context

Using the `trajectorySummary` and `evaluation` returned by `refract_engine.py` plus your own awareness of the workspace and conversation:
- Refine the 3 spectrum prompts so they reference the **exact file basenames, symbols, and error messages** from our current session (never use generic "Act as a senior engineer" filler):
  1. **⚡ Precision Spectrum (Context-Grounded)**: Direct, unambiguous instructions bound to the exact files/functions from our conversation.
  2. **🔬 Root-Cause Spectrum (Hypothesis-First)**: Step-by-step diagnostic verification before editing code (recommend this first if `isFailureSpiral` is `true`).
  3. **🛡️ Strict Spec Spectrum (Guardrailed + Verified)**: Explicit constraints, minimal diff scope, edge-case coverage, and exact test/build verification command.

## Step 3: Present Score & 1-Click Execution Modal (`ask_question`)

1. Output a brief, high-signal summary of the **Refract Score (`overallScore/100`)** and the key **Context/Trajectory Gaps** resolved.
2. Call `ask_question` presenting the 3 Refracted Spectrums (putting the recommended spectrum first with `(Recommended)`), so the user can **click once to immediately execute** their preferred prompt in the next step.
3. As soon as the user selects an option, **immediately execute that refracted prompt** as your primary task.
