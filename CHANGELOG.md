# Change Log — 💠 Refract

All notable changes to the **Refract** extension will be documented in this file.

## [1.0.1] - 2026-10-23

### Enhanced
- **New Instructional Marketplace Overview & Quick Start**:
  - Clear 30-second workflow guides for `@refract` Chat, `Cmd+Alt+P` QuickPick, and `#refract` Copilot Agent Mode.
  - Side-by-side **Before vs. After** comparison table highlighting auto-grounding, failure-spiral rescue, and architectural fork detection.
  - Plain-English breakdown of the 3 Execution Spectrums (⚡ Precision, 🔬 Root-Cause, 🛡️ Strict Spec).
- **New Visual 3-Step Workflow Diagram**:
  - Bundled high-resolution 1600x640 workflow graphic (`assets/how-it-works-diagram.png`) illustrating prompt auto-grounding in &lt;2ms.
  - Dedicated Enterprise Privacy & Data Security section with architecture diagram.
- **Improved Display & Marketplace Discoverability**:
  - Updated title to *Refract — Instant Context Grounding for VS Code Chat & Copilot*.

## [1.0.0] - 2026-10-18

### Added
- **VS Code Chat Participant (`@refract`)**:
  - Passive in-flight prompt refraction (`auto-intercept` mode) using the 5-Dimension Trajectory Rubric (`<5ms` local execution).
  - `/refract` command with 1-click follow-up buttons for **⚡ Precision**, **🔬 Root-Cause**, and **🛡️ Strict Spec** spectrums.
  - `/check` command that launches the **Interactive 5-Dimension Trajectory Scorecard** Webview panel beside your editor.
  - `/mode` command to toggle between `auto-intercept`, `coach`, and `slash-only`.
  - `/doctor` command for instant runtime and trajectory health verification.
- **Language Model Tool (`#refract` / `refract_prompt`)**:
  - Reference `#refract` inside any VS Code Chat or Copilot Agent Mode turn.
- **Live IDE Context & Failure Spiral Detection**:
  - Automatically binds active editor files, live VS Code **Problems** panel errors (`vscode.languages.getDiagnostics()`), and terminal shell execution exit codes (`onDidEndTerminalShellExecution`).
- **Keyboard Shortcuts & Status Bar**:
  - `Cmd+Alt+P` (`Ctrl+Alt+P` on Windows/Linux) for instant QuickPick prompt refraction from anywhere in the editor.
  - Live `💠 Refract` status bar indicator with Failure Spiral rescue alerts.
- **100% On-Device Privacy & Zero External Runtime Dependencies**:
  - Executes 100% locally inside VS Code's built-in Node.js Extension Host with zero external network calls and zero extra token cost.
