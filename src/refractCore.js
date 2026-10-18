// @ts-check
"use strict";

/**
 * Refract — Isomorphic Core Context & Prompt Trajectory Engine (Node.js / VS Code Extension Host).
 *
 * Runs 100% locally in <2ms inside VS Code's built-in Extension Host with ZERO external npm or Python
 * runtime dependencies required for Marketplace end-users.
 */

const fs = require("fs");
const path = require("path");

const DEFAULT_CONFIG = {
  mode: "auto-intercept", // "auto-intercept" | "coach" | "slash-only"
  scoreThreshold: 72,
  rescueFailureSpirals: true,
  maxTranscriptTurns: 12,
  alwaysIncludeRules: [],
};

const BYPASS_EXACT_PHRASES = new Set([
  "y",
  "yes",
  "n",
  "no",
  "ok",
  "okay",
  "sure",
  "proceed",
  "continue",
  "go ahead",
  "looks good",
  "lgtm",
  "thanks",
  "thank you",
  "done",
  "ship it",
  "approved",
  "approve",
]);

const ACTION_VERBS = new Set([
  "implement",
  "refactor",
  "debug",
  "fix",
  "create",
  "build",
  "add",
  "update",
  "remove",
  "delete",
  "optimize",
  "test",
  "verify",
  "migrate",
  "extract",
  "analyze",
  "explain",
  "configure",
  "wire",
  "expose",
  "validate",
  "benchmark",
  "trace",
  "isolate",
  "rename",
  "convert",
  "replace",
  "design",
  "push",
  "commit",
  "branch",
  "document",
  "summarize",
]);

const VAGUE_PHRASES = [
  /\bfix\s+it\b/i,
  /\bmake\s+it\s+(?:work|better|faster|good|clean)\b/i,
  /\bdo\s+the\s+same\b/i,
  /\btry\s+again\b/i,
  /\bnot\s+working\b/i,
  /\bstill\s+(?:broken|failing|fails|wrong|doesn'?t\s+work)\b/i,
  /\bsame\s+(?:error|issue|bug|problem)\b/i,
  /\bchange\s+this\b/i,
  /\bupdate\s+it\b/i,
  /\bfix\s+this\b/i,
  /\bhelp\s+me\b/i,
  /\bwhat'?s\s+wrong\b/i,
];

/** @type {Array<[RegExp, string]>} */
const DEICTIC_REFERENCES = [
  [/\b(?:this|that)\s+(?:file|module|component|class|function|method|handler|endpoint|script|test)\b/i, "file_or_symbol"],
  [/\b(?:the\s+other|the\s+second|the\s+first|the\s+previous)\s+(?:one|file|function|endpoint|handler|approach|option)\b/i, "prior_turn_entity"],
  [/\b(?:this|that|the)\s+(?:error|bug|exception|crash|failure|issue|warning)\b/i, "recent_error"],
  [/\bdo\s+the\s+same\b/i, "prior_action_pattern"],
  [/\b(?:fix|update|refactor|change|run|test)\s+(?:it|this|that|them)\b/i, "implicit_target"],
];

const FRUSTRATION_PATTERNS = [
  /\bstill\s+(?:not\s+working|broken|failing|fails|wrong|same|getting)\b/i,
  /\bsame\s+(?:error|issue|bug|problem|output|failure)\b/i,
  /\bdidn'?t\s+(?:work|fix\s+it|help|solve)\b/i,
  /\bdoesn'?t\s+work\b/i,
  /\bwhy\s+is\s+it\s+still\b/i,
  /\byou\s+broke\b/i,
  /\bthat\s+broke\b/i,
  /\btry\s+(?:something\s+else|again|another\s+way)\b/i,
];

/** @type {Array<[RegExp, string, string[]]>} */
const ARCHITECTURAL_FORK_PATTERNS = [
  [
    /\badd\s+(?:caching|cache)\b/i,
    "Caching Strategy Fork",
    ["In-memory LRU / local cache", "Distributed cache (Redis / Memcached)", "HTTP / CDN Cache-Control headers"],
  ],
  [
    /\badd\s+(?:auth|authentication|login)\b/i,
    "Authentication Architecture Fork",
    ["Stateless JWT / Bearer tokens", "Server-side session cookies", "OAuth2 / OIDC provider integration"],
  ],
  [
    /\badd\s+(?:rate\s+limit|rate-limit|throttl\w+)\b/i,
    "Rate Limiting Scope Fork",
    ["In-process memory limiter (per-instance)", "Redis-backed distributed sliding window", "API Gateway / reverse-proxy middleware"],
  ],
  [
    /\b(?:add|setup|use)\s+(?:a\s+)?database\b/i,
    "Database Storage Fork",
    ["PostgreSQL / relational schema", "SQLite / embedded local file", "NoSQL / document store"],
  ],
  [
    /\bstate\s+management\b/i,
    "State Architecture Fork",
    ["Local component / hook state", "Lightweight store (Zustand / Signals / Context)", "Global state machine / Redux pattern"],
  ],
];

/**
 * Escapes HTML special characters safely.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Loads workspace .agents/refract.json or .vscode/refract.json overrides and merges with VS Code settings.
 * @param {Partial<typeof DEFAULT_CONFIG>} vscodeSettings
 * @param {string[]} workspaceFolders
 */
function loadMergedConfig(vscodeSettings = {}, workspaceFolders = []) {
  const cfg = {
    ...DEFAULT_CONFIG,
    ...vscodeSettings,
    alwaysIncludeRules: Array.isArray(vscodeSettings.alwaysIncludeRules)
      ? [...vscodeSettings.alwaysIncludeRules]
      : [],
  };

  for (const folder of workspaceFolders) {
    for (const rel of [".agents/refract.json", ".vscode/refract.json"]) {
      const candidate = path.join(folder, rel);
      try {
        if (fs.existsSync(candidate)) {
          const parsed = JSON.parse(fs.readFileSync(candidate, "utf8"));
          if (parsed && typeof parsed === "object") {
            if (typeof parsed.mode === "string") cfg.mode = parsed.mode;
            if (typeof parsed.scoreThreshold === "number") cfg.scoreThreshold = parsed.scoreThreshold;
            if (typeof parsed.rescueFailureSpirals === "boolean") {
              cfg.rescueFailureSpirals = parsed.rescueFailureSpirals;
            }
            if (Array.isArray(parsed.alwaysIncludeRules)) {
              for (const r of parsed.alwaysIncludeRules) {
                if (typeof r === "string" && !cfg.alwaysIncludeRules.includes(r)) {
                  cfg.alwaysIncludeRules.push(r);
                }
              }
            }
          }
        }
      } catch (_err) {
        // Ignore malformed workspace config
      }
    }
  }
  return cfg;
}

/**
 * Checks whether a prompt should bypass interception immediately.
 * @param {string} promptText
 * @param {typeof DEFAULT_CONFIG} config
 * @returns {{ bypass: boolean, reason: string }}
 */
function shouldBypassPrompt(promptText, config) {
  if (config.mode === "slash-only") {
    return { bypass: true, reason: "Mode is slash-only" };
  }
  const cleaned = String(promptText || "").trim();
  if (!cleaned) {
    return { bypass: true, reason: "Empty prompt" };
  }
  if (cleaned.startsWith("/")) {
    return { bypass: true, reason: "Explicit slash command" };
  }
  const normalized = cleaned.toLowerCase().replace(/[^\w\s]/g, "").trim();
  if (BYPASS_EXACT_PHRASES.has(normalized)) {
    return { bypass: true, reason: "Short confirmation phrase" };
  }
  return { bypass: false, reason: "" };
}

/**
 * Evaluates a developer prompt across the 5-Dimension Trajectory Rubric (0-100).
 * @param {string} promptText
 * @param {{
 *   prior_user_prompts?: string[],
 *   recent_files?: string[],
 *   recent_commands?: string[],
 *   recent_errors?: string[],
 *   active_errors?: string[],
 *   consecutive_errors?: number,
 *   turn_count?: number
 * }} trajectory
 */
function evaluatePrompt(promptText, trajectory = {}) {
  const text = String(promptText || "").trim();
  const lower = text.toLowerCase();
  const words = lower.match(/\b\w+\b/g) || [];
  const wordCount = words.length;

  const recentFiles = trajectory.recent_files || [];
  const activeErrors = trajectory.active_errors || [];
  const recentErrors = trajectory.recent_errors || [];
  const priorPrompts = trajectory.prior_user_prompts || [];
  const consecutiveErrors = trajectory.consecutive_errors || 0;

  /** @type {string[]} */
  const gaps = [];
  const boundContext = {
    files: /** @type {string[]} */ ([]),
    errors: /** @type {string[]} */ ([]),
    prior_intent: priorPrompts.length > 0 ? priorPrompts[priorPrompts.length - 1] : "",
  };

  // --- 1. Intent Clarity (0 - 25) ---
  const hasActionVerb = words.some((w) => ACTION_VERBS.has(w));
  const hasVaguePhrase = VAGUE_PHRASES.some((pat) => pat.test(lower));
  const hasCodeIdent =
    /[`][\w./-]+[`]|\b\w+\.(?:ts|tsx|js|jsx|py|go|rs|java|json|md|css|html|sh|yml|yaml)\b|\b[a-z]+[A-Z]\w+\b|\b\w+_\w+\b/.test(
      text
    );

  let clarity = 13;
  if (hasActionVerb) clarity += 6;
  if (hasCodeIdent) clarity += 6;
  if (wordCount < 5) clarity -= 6;
  else if (wordCount >= 12) clarity += 3;
  if (hasVaguePhrase) {
    clarity -= 6;
    gaps.push("Uses vague phrasing instead of specifying the exact behavior or target symbol.");
  }
  clarity = Math.max(3, Math.min(25, clarity));

  // --- 2. Context Grounding (0 - 25) ---
  /** @type {string[]} */
  const ungroundedRefs = [];
  for (const [pat, refKind] of DEICTIC_REFERENCES) {
    const m = lower.match(pat);
    if (m) {
      ungroundedRefs.push(`'${m[0]}' (${refKind})`);
    }
  }

  let contextScore = 17;
  if (hasCodeIdent || text.includes("@") || text.includes("#")) {
    contextScore += 7;
  }
  if (ungroundedRefs.length > 0 && !hasCodeIdent) {
    contextScore -= 11;
    if (recentFiles.length > 0) {
      const boundSlice = recentFiles.slice(-3);
      const boundNames = boundSlice.map((f) => path.basename(f));
      boundContext.files = boundSlice;
      gaps.push(
        `Contains ungrounded reference (${ungroundedRefs.slice(0, 2).join(", ")}); auto-bound to active workspace files: ${boundNames.join(", ")}.`
      );
    } else {
      gaps.push(
        `Contains ambiguous reference (${ungroundedRefs.slice(0, 2).join(", ")}) without naming a file, function, or component.`
      );
    }
  } else if (recentFiles.length > 0 && ungroundedRefs.length > 0) {
    boundContext.files = recentFiles.slice(-2);
  }

  const mentionsError = /\b(?:error|bug|exception|fail\w*|broken|crash\w*|issue|problem|diagnostic)\b/i.test(lower);
  if (activeErrors.length > 0) {
    boundContext.errors = activeErrors.slice(-2);
  } else if (mentionsError && recentErrors.length > 0) {
    boundContext.errors = recentErrors.slice(-1);
  }
  contextScore = Math.max(4, Math.min(25, contextScore));

  // --- 3. Trajectory Continuity & Failure Spiral Detection (0 - 20) ---
  const frustrationMatch = FRUSTRATION_PATTERNS.some((pat) => pat.test(lower));
  const isFailureSpiral = frustrationMatch || (consecutiveErrors >= 2 && wordCount < 25);

  let continuity = 16;
  if (isFailureSpiral) {
    continuity = 5;
    gaps.push(
      "Vibe-Coding Failure Spiral detected (repeated error or frustration follow-up). Needs root-cause isolation instead of another blind edit."
    );
  } else if (priorPrompts.length > 0 && ungroundedRefs.length > 0 && boundContext.files.length === 0) {
    continuity = 10;
  } else if (wordCount >= 10) {
    continuity = 19;
  }
  continuity = Math.max(4, Math.min(20, continuity));

  // --- 4. Scope, Constraints & Architectural Forks (0 - 15) ---
  /** @type {{ title: string, options: string[] } | null} */
  let detectedFork = null;
  for (const [pat, forkTitle, forkOptions] of ARCHITECTURAL_FORK_PATTERNS) {
    if (pat.test(lower) && wordCount < 25) {
      detectedFork = { title: forkTitle, options: forkOptions };
      gaps.push(`Unresolved ${forkTitle}: ${forkOptions.join(", ")}.`);
      break;
    }
  }

  const hasConstraints =
    /\b(?:without|do\s+not|don'?t|must|only|preserve|keep|ensure|avoid|strictly|compatibility|branch)\b/i.test(lower);
  let constraintsScore = 9;
  if (hasConstraints) constraintsScore += 5;
  if (wordCount >= 18) constraintsScore += 3;
  if (detectedFork) constraintsScore -= 6;
  constraintsScore = Math.max(3, Math.min(15, constraintsScore));

  // --- 5. Verification / Definition of Done (0 - 15) ---
  const hasVerification =
    /\b(?:test|tests|unit\s+test|verify|check|assert|compile|build|lint|expect|output|return|push|commit|readme)\b/i.test(
      lower
    );
  let verificationScore = 8;
  if (hasVerification) {
    verificationScore += 6;
  } else if (wordCount >= 22) {
    verificationScore += 3;
  } else {
    gaps.push("No explicit verification or Definition-of-Done criteria specified.");
  }
  verificationScore = Math.max(3, Math.min(15, verificationScore));

  const overall = clarity + contextScore + continuity + constraintsScore + verificationScore;

  let verdict = "High Drift / Ambiguity Risk — Refraction Needed";
  let badge = "🔴";
  if (overall >= 80 && !isFailureSpiral && !detectedFork) {
    verdict = "Focused & Execution-Ready";
    badge = "🟢";
  } else if (overall >= 60 && !isFailureSpiral && !detectedFork) {
    verdict = "Diffuse — Benefits from Context Grounding";
    badge = "🟡";
  }

  return {
    overallScore: overall,
    verdict,
    badge,
    isFailureSpiral,
    architecturalFork: detectedFork,
    dimensions: {
      clarity: { score: clarity, max: 25, label: "Intent Clarity" },
      context: { score: contextScore, max: 25, label: "Context Grounding" },
      continuity: { score: continuity, max: 20, label: "Trajectory Continuity" },
      constraints: { score: constraintsScore, max: 15, label: "Scope & Constraints" },
      verification: { score: verificationScore, max: 15, label: "Verification Criteria" },
    },
    gaps,
    boundContext,
  };
}

/**
 * Refracts a raw developer prompt into 3 actionable engineering spectrums.
 * @param {string} promptText
 * @param {ReturnType<typeof evaluatePrompt>} evaluation
 * @param {any} trajectory
 * @param {string[]} customRules
 */
function synthesizeSpectrums(promptText, evaluation, trajectory = {}, customRules = []) {
  const raw = String(promptText || "").trim();
  const boundFiles = (evaluation.boundContext && evaluation.boundContext.files) || [];
  const recentFiles = boundFiles.length > 0 ? boundFiles : trajectory.recent_files || [];
  const recentCommands = trajectory.recent_commands || [];
  const boundErrors = (evaluation.boundContext && evaluation.boundContext.errors) || [];
  const priorPrompts = trajectory.prior_user_prompts || [];

  let fileClause = "";
  if (recentFiles.length > 0) {
    const shortFiles = recentFiles
      .slice(-3)
      .map((p) => `\`${path.basename(p)}\` (${p})`)
      .join(", ");
    fileClause = ` Focus on ${shortFiles}.`;
  }

  let priorClause = "";
  if (priorPrompts.length > 0 && raw.split(/\s+/).length < 14) {
    const lastGoal = String(priorPrompts[priorPrompts.length - 1]).replace(/\n/g, " ").slice(0, 120);
    priorClause = `Building directly on our previous step ("${lastGoal}"), `;
  }

  let errorClause = "";
  if (boundErrors.length > 0) {
    const errSnip = boundErrors[boundErrors.length - 1];
    errorClause = ` Resolve the active diagnostic/error (\`${errSnip}\`).`;
  }

  let rulesClause = "";
  if (Array.isArray(customRules) && customRules.length > 0) {
    const joined = customRules.map((r) => String(r).trim()).filter(Boolean).join("; ");
    if (joined) {
      rulesClause = ` Adhere to project rules: ${joined}.`;
    }
  }

  let testCmd = "the project's test suite";
  for (let i = recentCommands.length - 1; i >= 0; i--) {
    const cmd = recentCommands[i];
    if (/(?:test|pytest|unittest|npm|cargo|go test|tsc)/i.test(cmd)) {
      testCmd = cmd;
      break;
    }
  }

  const precisionPrompt = `${priorClause}${raw}.${fileClause}${errorClause}${rulesClause} Preserve existing public interfaces and unrelated logic, and summarize the exact changes made.`
    .replace(/\s+/g, " ")
    .replace(/\.\./g, ".")
    .trim();

  const rootCausePrompt = `Before making any code edits for "${raw}",${fileClause}${errorClause} 1) Identify the top 2 root-cause hypotheses based on our conversation history and current file/diagnostic state, 2) Verify which hypothesis is actually occurring by inspecting the relevant code/logs, and 3) Apply a targeted fix and verify it.${rulesClause}`
    .replace(/\s+/g, " ")
    .trim();

  const fork = evaluation.architecturalFork;
  const forkNote = fork ? ` First confirm or select the preferred approach among: ${fork.options.join(", ")}.` : "";
  const strictPrompt = `Execute task: "${raw}".${fileClause}${forkNote}${rulesClause} Constraints: Keep the diff minimal and well-typed, handle edge/error cases explicitly, and verify the implementation by running \`${testCmd}\` before concluding.`
    .replace(/\s+/g, " ")
    .trim();

  const recommended = evaluation.isFailureSpiral ? "root_cause" : "precision";

  return {
    recommended: {
      key: recommended,
      reason:
        recommended === "root_cause"
          ? "Failure spiral / active diagnostic errors detected — Root-Cause Isolation prevents blind guessing."
          : "Direct context-bound execution grounded in active VS Code workspace files and diagnostics.",
    },
    precision: {
      title: "⚡ Precision Spectrum (Context-Grounded)",
      prompt: precisionPrompt,
      when: "Best for fast, unambiguous execution bound to active files and diagnostics.",
    },
    root_cause: {
      title: "🔬 Root-Cause Spectrum (Hypothesis-First)",
      prompt: rootCausePrompt,
      when: "Best when debugging stubborn errors or breaking a 'still not working' loop.",
    },
    strict_spec: {
      title: "🛡️ Strict Spec Spectrum (Guardrailed + Verified)",
      prompt: strictPrompt,
      when: "Best for production changes requiring minimal diff scope and test verification.",
    },
  };
}

/**
 * Generates the interactive HTML Scorecard for the VS Code Webview Panel.
 * Uses VS Code theme CSS variables (--vscode-*) with seamless fallback variables.
 * @param {string} promptText
 * @param {ReturnType<typeof evaluatePrompt>} evaluation
 * @param {ReturnType<typeof synthesizeSpectrums>} spectrums
 * @param {any} trajectory
 * @param {string} mode
 */
function buildWebviewScorecardHtml(promptText, evaluation, spectrums, trajectory, mode) {
  const score = evaluation.overallScore;
  const verdict = escapeHtml(evaluation.verdict);
  const escapedPrompt = escapeHtml(promptText.trim() || "(Auditing active VS Code workspace trajectory)");
  const isSpiral = Boolean(evaluation.isFailureSpiral);

  const dimsHtml = Object.values(evaluation.dimensions)
    .map((dim) => {
      const pct = Math.round((dim.score / dim.max) * 100);
      const barColor = pct >= 75 ? "#10B981" : pct >= 55 ? "#F59E0B" : "#EF4444";
      return `
      <div class="dim-row">
        <div class="dim-label">
          <span>${escapeHtml(dim.label)}</span>
          <span class="mono">${dim.score}/${dim.max}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width: ${pct}%; background: ${barColor};"></div>
        </div>
      </div>`;
    })
    .join("\n");

  const gapsList =
    evaluation.gaps && evaluation.gaps.length > 0
      ? evaluation.gaps
      : ["Prompt is well-grounded in current workspace files and diagnostics."];
  const gapsHtml = gapsList
    .map((g) => `<li class="gap-item"><span class="bullet">▸</span><span>${escapeHtml(g)}</span></li>`)
    .join("\n");

  const specData = {
    precision: spectrums.precision.prompt,
    root_cause: spectrums.root_cause.prompt,
    strict_spec: spectrums.strict_spec.prompt,
  };
  const scoreColor = score >= 80 ? "#10B981" : score >= 60 ? "#F59E0B" : "#EF4444";
  const spiralBadge = isSpiral
    ? `<span class="badge badge-danger">⚠️ Failure Spiral Rescue Active</span>`
    : `<span class="badge badge-ok">✓ Trajectory Healthy</span>`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>💠 Refract Trajectory Scorecard</title>
  <style>
    :root {
      --bg: var(--vscode-editor-background, #0f172a);
      --card: var(--vscode-sideBar-background, #1e293b);
      --fg: var(--vscode-editor-foreground, #f8fafc);
      --muted: var(--vscode-descriptionForeground, #94a3b8);
      --border: var(--vscode-panel-border, #334155);
      --accent: var(--vscode-button-background, #2563eb);
      --accent-fg: var(--vscode-button-foreground, #ffffff);
      --sec-bg: var(--vscode-button-secondaryBackground, #334155);
      --sec-fg: var(--vscode-button-secondaryForeground, #e2e8f0);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 16px;
      background: var(--bg);
      color: var(--fg);
      font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
      font-size: 13px;
      line-height: 1.5;
    }
    .container {
      max-width: 820px;
      margin: 0 auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
      margin-bottom: 14px;
      gap: 12px;
      flex-wrap: wrap;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .score-box {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      border: 2px solid ${scoreColor};
      color: ${scoreColor};
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 16px;
    }
    .title-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    h2 {
      margin: 0;
      font-size: 15px;
    }
    .mode-pill {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 6px;
      background: var(--sec-bg);
      color: var(--sec-fg);
      font-family: monospace;
    }
    .subtitle {
      margin: 2px 0 0 0;
      font-size: 12px;
      color: var(--muted);
    }
    .badge {
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: 600;
    }
    .badge-danger {
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.35);
    }
    .badge-ok {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-bottom: 16px;
    }
    .panel {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
    }
    .panel-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 10px;
    }
    .dim-row { margin-bottom: 8px; }
    .dim-label {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      margin-bottom: 3px;
    }
    .bar-track {
      width: 100%;
      height: 6px;
      background: var(--sec-bg);
      border-radius: 999px;
      overflow: hidden;
    }
    .bar-fill { height: 100%; border-radius: 999px; }
    .draft-box {
      font-family: monospace;
      font-size: 12px;
      background: var(--sec-bg);
      padding: 6px 8px;
      border-radius: 6px;
      margin-bottom: 8px;
      word-break: break-word;
    }
    .gaps-list {
      list-style: none;
      padding: 0;
      margin: 0 0 10px 0;
    }
    .gap-item {
      display: flex;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 5px;
    }
    .bullet { color: #f59e0b; }
    .meta-footer {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: var(--muted);
      border-top: 1px solid var(--border);
      padding-top: 8px;
    }
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }
    .tabs, .actions {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    button {
      cursor: pointer;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 500;
      background: var(--sec-bg);
      color: var(--sec-fg);
    }
    button.active {
      background: var(--accent);
      color: var(--accent-fg);
      border-color: var(--accent);
    }
    button.primary-action {
      background: #10b981;
      color: #052e16;
      border-color: #10b981;
      font-weight: 600;
    }
    .spec-box {
      font-family: monospace;
      font-size: 12px;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      line-height: 1.6;
      white-space: pre-wrap;
    }
    .mono { font-family: monospace; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="header-left">
        <div class="score-box">${score}</div>
        <div>
          <div class="title-row">
            <h2>💠 Refract Trajectory Scorecard</h2>
            <span class="mode-pill">mode: ${escapeHtml(mode)}</span>
          </div>
          <p class="subtitle">${verdict}</p>
        </div>
      </div>
      <div>${spiralBadge}</div>
    </div>

    <div class="grid">
      <div class="panel">
        <div class="panel-title">5-Dimension Rubric</div>
        ${dimsHtml}
      </div>
      <div class="panel">
        <div class="panel-title">Analyzed Draft &amp; Trajectory Gaps</div>
        <div class="draft-box">${escapedPrompt}</div>
        <ul class="gaps-list">${gapsHtml}</ul>
        <div class="meta-footer">
          <span>Chat Turns: <b>${trajectory.turn_count || 0}</b></span>
          <span>Bound Files: <b>${(trajectory.recent_files || []).length}</b></span>
          <span>Active Diagnostics: <b>${(trajectory.active_errors || []).length}</b></span>
        </div>
      </div>
    </div>

    <div class="toolbar">
      <div class="tabs">
        <button id="btn-precision" onclick="selectSpec('precision')">⚡ Precision</button>
        <button id="btn-root_cause" onclick="selectSpec('root_cause')">🔬 Root-Cause</button>
        <button id="btn-strict_spec" onclick="selectSpec('strict_spec')">🛡️ Strict Spec</button>
      </div>
      <div class="actions">
        <button onclick="copySpectrum()" id="copy-btn">📋 Copy Spectrum</button>
        <button class="primary-action" onclick="sendToChat()">🚀 Send to VS Code Chat</button>
      </div>
    </div>
    <div id="spec-box" class="spec-box"></div>
  </div>

  <script>
    const vscode = typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null;
    const SPECS = ${JSON.stringify(specData)};
    let activeKey = ${JSON.stringify(spectrums.recommended.key)};

    function selectSpec(key) {
      activeKey = key;
      document.getElementById('spec-box').textContent = SPECS[key] || '';
      ['precision', 'root_cause', 'strict_spec'].forEach(k => {
        const btn = document.getElementById('btn-' + k);
        btn.className = (k === key) ? 'active' : '';
      });
    }

    function copySpectrum() {
      const text = SPECS[activeKey] || '';
      if (vscode) {
        vscode.postMessage({ type: 'copy', prompt: text });
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
      }
      const btn = document.getElementById('copy-btn');
      btn.textContent = '✓ Copied!';
      setTimeout(() => { btn.textContent = '📋 Copy Spectrum'; }, 1500);
    }

    function sendToChat() {
      const text = SPECS[activeKey] || '';
      if (vscode) {
        vscode.postMessage({ type: 'sendToChat', prompt: text });
      }
    }

    selectSpec(activeKey);
  </script>
</body>
</html>`;
}

module.exports = {
  DEFAULT_CONFIG,
  loadMergedConfig,
  shouldBypassPrompt,
  evaluatePrompt,
  synthesizeSpectrums,
  buildWebviewScorecardHtml,
};
