<div align="center">
  <img src="https://raw.githubusercontent.com/damiththa/Refract/vscode-extension/assets/logo.png" alt="Refract Logo" width="100" height="100" />
  <h1>💠 Refract</h1>
  <p><strong>Stop Copilot from guessing blindly. Ground your prompts in your active files and compiler errors in &lt;2ms.</strong></p>
  
  <p>
    <a href="#-quick-start-30-seconds"><img src="https://img.shields.io/badge/Quick_Start-30_Seconds-2563EB?style=flat-square" alt="Quick Start" /></a>
    <img src="https://img.shields.io/badge/Latency-%3C2ms_Local-10B981?style=flat-square" alt="Latency" />
    <img src="https://img.shields.io/badge/Extra_Tokens-%240_(Zero)-8B5CF6?style=flat-square" alt="Zero Tokens" />
    <img src="https://img.shields.io/badge/Privacy-100%25_On--Device-059669?style=flat-square" alt="Privacy" />
    <img src="https://img.shields.io/badge/License-MIT-gray?style=flat-square" alt="License" />
  </p>
</div>

---

## 🎯 Why Refract?

When you ask AI: *"Fix the error in this file"* or *"Why isn't this working?"*, standard AI assistants have a blind spot:
* They don't know which file you're looking at.
* They don't see the red squiggly error in your editor.
* They don't know your last terminal command failed with exit code 1.

So they guess. They hallucinate imports, edit the wrong lines, and when you reply *"still broken!"*, they apologize and dig the hole deeper.

**Refract fixes this in `<2ms` before your prompt ever reaches the AI.**

Like an optical prism (`💠`), Refract inspects your **active editor tab**, **compiler errors from the Problems pane**, and **terminal failures**, binding them directly into your prompt so your AI gets it right on **Turn 1**.

---

## ⚡ The Difference (Before vs. After)

| When You Type... | Without Refract ❌ | With Refract 💠 |
| :--- | :--- | :--- |
| **`"fix the error in this file"`** | Copilot guesses the file, hallucinates missing imports, and breaks working code. | **Auto-Grounding**: Refract binds `auth.ts:42` and the exact TypeScript error from your Problems pane. Clean fix on Turn 1. |
| **`"it still doesn't work"`** *(Turn 3)* | **Failure Spiral**: Copilot apologizes, repeats the same broken snippet, and wastes your time. | **Spiral Rescue**: Refract detects repeated failures, stops blind guessing, and pivots Copilot into **Root-Cause Isolation** to verify logs first. |
| **`"add caching"`** | Copilot arbitrarily installs Redis when all you wanted was an in-memory dictionary. | **Fork Detection**: Flags that caching has 3 architectural options (In-memory, Redis, HTTP) and asks for 1-click confirmation before writing 50 lines. |

---

## 🖼️ How Refract Works in 3 Simple Steps

<p align="center">
  <a href="https://github.com/damiththa/Refract">
    <img src="https://raw.githubusercontent.com/damiththa/Refract/vscode-extension/assets/how-it-works-diagram.png" alt="How Refract Works Diagram" width="800" />
  </a>
</p>

1. **You write naturally**: Type a quick prompt in chat (`@refract fix this`) or press `Cmd+Alt+P`.
2. **Refract grounds it in &lt;2ms**: Silently attaches your active file, compiler errors, and terminal state (100% on-device, zero API calls).
3. **Your active model executes**: Forwards the grounded prompt to whichever model you already use in VS Code (Copilot GPT-4o, Claude 3.5 Sonnet, etc.)—or lets you choose one of 3 focused spectrums.

---

## 🚀 Quick Start (30 Seconds)

You can use Refract in whichever way fits your workflow:

### Workflow 1: Direct in VS Code Chat (`@refract`)
1. Open any file in your editor (e.g., `server.ts`).
2. Open the Chat panel (`Cmd+Alt+I` / `Ctrl+Alt+I`) and type:
   ```text
   @refract fix the error in this file
   ```
3. Refract automatically binds `server.ts` and your open compiler errors, streams the fix directly, and provides 1-click follow-up spectrum buttons.

### Workflow 2: Global Editor Shortcut (`Cmd+Alt+P`)
1. Highlight any code (or just keep your cursor anywhere in an editor).
2. Press **`Cmd + Alt + P`** (macOS) or **`Ctrl + Alt + P`** (Windows / Linux).
3. Type a rough thought (e.g. `make this async and handle timeouts`).
4. An instant QuickPick appears showing your prompt score and 3 execution spectrums. Pick one to copy or send straight to Chat!

### Workflow 3: Interactive Visual Scorecard (`/check`)
1. In Chat, type:
   ```text
   @refract /check add caching to the user endpoint
   ```
2. Refract opens the **Interactive 5-Dimension Scorecard** panel beside your code, displaying rubric score bars, bound files, and live tabs to preview each spectrum.

---

## 💠 The 3 Spectrums Explained

Whenever Refract enhances a prompt, it synthesizes 3 tailored engineering spectrums:

* ⚡ **Precision Spectrum (Context-Grounded — Default)**
  * *Best for*: Everyday bug fixes, refactors, and fast implementation.
  * *What it does*: Binds your active file and compiler error, instructs the AI to preserve existing interfaces and unrelated code, and asks for a clear summary of changes.

* 🔬 **Root-Cause Spectrum (Hypothesis-First)**
  * *Best for*: Stubborn errors, "it still doesn't work" loops, and breaking out of failure spirals.
  * *What it does*: Prevents blind edits. Instructs the AI to state its top 2 root-cause hypotheses, inspect relevant code/logs to verify which is occurring, and apply a targeted fix.

* 🛡️ **Strict Spec Spectrum (Guardrailed + Test-Verified)**
  * *Best for*: Production pull requests, architectural changes, and mission-critical code.
  * *What it does*: Enforces minimal diff scope, strict error handling, and requires running your project's test command (`npm test`, `pytest`, etc.) before concluding.

---

## 🔒 100% On-Device Privacy & Zero Cost

<p align="center">
  <a href="https://github.com/damiththa/Refract">
    <img src="https://raw.githubusercontent.com/damiththa/Refract/vscode-extension/assets/privacy-diagram.png" alt="Refract Architecture & Data Privacy Diagram" width="800" />
  </a>
</p>

| Guarantee | How It Works | Why It Matters |
| :--- | :--- | :--- |
| **0 External Network Calls** | Refract contains **zero networking code**. No telemetry, no external server, no data leaving your machine. | 100% safe for proprietary, enterprise, and NDA codebases. |
| **$0 Extra Token Cost** | Trajectory scoring and file binding happen in local JavaScript in **&lt;2ms**. It does not call an external LLM to refine your prompt. | Fast response time (&lt;2ms) and zero added API charges. |
| **Your Choice of LLM** | `@refract` forwards directly to whichever model you already selected in VS Code Chat (Copilot GPT-4o, Claude 3.5 Sonnet, etc.). | No separate OpenAI, Anthropic, or Gemini API keys to configure. |

---

## ⌨️ Cheat Sheet & Shortcuts

| Action | Shortcut (macOS) | Shortcut (Windows/Linux) | In Chat |
| :--- | :--- | :--- | :--- |
| **Refract a Prompt** | `Cmd + Alt + P` | `Ctrl + Alt + P` | `@refract <prompt>` |
| **Pick from 3 Spectrums** | — | — | `@refract /refract <prompt>` |
| **Open Visual Scorecard** | `Cmd + Alt + Shift + P` | `Ctrl + Alt + Shift + P` | `@refract /check <prompt>` |
| **Health & Diagnostic Check**| — | — | `@refract /doctor` |
| **Switch Mode (Auto/Coach)** | Click Status Bar | Click Status Bar | `@refract /mode` |

---

## ⚙️ Configuration & Custom Team Rules

### VS Code Settings (`settings.json`)
```json
{
  "refract.mode": "auto-intercept",
  "refract.scoreThreshold": 72,
  "refract.rescueFailureSpirals": true,
  "refract.alwaysIncludeRules": [
    "Preserve public TypeScript interfaces",
    "Run unit tests after modifying handlers"
  ]
}
```

### Shared Team Config (`.agents/refract.json` or `.vscode/refract.json`)
Commit `.agents/refract.json` or `.vscode/refract.json` to your repository so both **VS Code** and **Google Antigravity** teammates automatically share the same project rules and score thresholds!

---

## 📄 License
MIT
