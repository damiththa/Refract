# 💎 Refract — AI Context & Prompt Trajectory Engine

**Refract** is a trajectory-aware prompt interceptor and coaching plugin for **Google Antigravity** (Antigravity 2.0, Antigravity IDE, and `agy` CLI).

Unlike traditional prompt enhancers that inflate short prompts with generic boilerplate (*"Act as a 10x senior engineer..."*), **Refract** reads your live conversation history (`transcript.jsonl`) and workspace context to solve the real reasons coding prompts fail:

1. **Multi-Turn Pronoun & Context Binding**: Binds shorthand follow-ups (*"do the same for the other handler"*, *"fix that error"*) to the exact files, symbols, and tool outputs from earlier turns.
2. **Vibe-Coding Failure Spiral Rescue**: Detects when recent turns have consecutive tool/test errors or frustration prompts (*"still broken"*, *"same error"*) and automatically pivots the agent into a **Root-Cause Isolation & Hypothesis Check** instead of blind guessing.
3. **Architectural Fork Detection**: Distinguishes between missing file context (auto-filled) and genuine design forks (e.g., caching, auth, rate limiting) that require a quick decision.
4. **Update-Safe & Collision-Free**: Lives in `~/.gemini/config/plugins/refract` (or `.agents/plugins/refract`) with namespaced `/refract`, `/refract-check`, and `/refract-mode` commands that never collide with built-in Antigravity commands.

---

## Features & Slash Commands

| Feature / Command | How It Works |
| :--- | :--- |
| **Passive `PreInvocation` Hook** | Evaluates every prompt in $<5\text{ms}$ before the model runs. Strong prompts pass through invisibly; diffuse prompts or failure spirals are grounded via transient `ephemeralMessage` injection. |
| **`/refract [draft]`** | Scores your prompt on the 5-Dimension Trajectory Rubric and lets you execute 1 of 3 Refracted Spectrums (**⚡ Precision**, **🔬 Root-Cause**, **🛡️ Strict Spec**) with 1 click. |
| **`/refract-check [draft]`** | Renders an **Interactive Generative UI Scorecard Widget** inline in chat showing dimension bars, trajectory health, and copyable spectrum tabs. |
| **`/refract-mode`** | Switches between `auto-intercept` (default), `coach` (1-click confirmation modal), and `slash-only` modes. |

---

## Installation

### Global Install (All Antigravity Workspaces)
```bash
./install.sh
```

### Workspace / Team Install (Committed to Git)
```bash
./install.sh --workspace /path/to/your/repo
```

---

## Running Tests
```bash
python3 -m unittest discover -s tests -v
```
