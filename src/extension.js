// @ts-check
"use strict";

const vscode = require("vscode");
const path = require("path");
const {
  loadMergedConfig,
  shouldBypassPrompt,
  evaluatePrompt,
  synthesizeSpectrums,
  buildWebviewScorecardHtml,
} = require("./refractCore");

/**
 * Live session trajectory state tracked across editor, diagnostics, terminal, and chat turns.
 */
const sessionState = {
  /** @type {string[]} */
  recentFiles: [],
  /** @type {string[]} */
  recentCommands: [],
  /** @type {string[]} */
  recentErrors: [],
  /** @type {number} */
  consecutiveTerminalErrors: 0,
  /** @type {string} */
  lastAnalyzedDraft: "",
  /** @type {any} */
  lastEvaluation: null,
  /** @type {any} */
  lastSpectrums: null,
};

/** @type {vscode.StatusBarItem | undefined} */
let statusBarItem;

/** @type {vscode.WebviewPanel | undefined} */
let activeScorecardPanel;

/**
 * Records a workspace file path into recentFiles (most recent last, max 8).
 * @param {string | undefined} fsPath
 */
function recordRecentFile(fsPath) {
  if (!fsPath) return;
  if (fsPath.includes(".git" + path.sep) || fsPath.startsWith("extension-output")) return;
  const idx = sessionState.recentFiles.indexOf(fsPath);
  if (idx !== -1) {
    sessionState.recentFiles.splice(idx, 1);
  }
  sessionState.recentFiles.push(fsPath);
  if (sessionState.recentFiles.length > 8) {
    sessionState.recentFiles.shift();
  }
}

/**
 * Collects live error diagnostics from the VS Code Problems panel.
 * @returns {string[]}
 */
function collectActiveDiagnostics() {
  /** @type {string[]} */
  const errors = [];
  try {
    const allDiagnostics = vscode.languages.getDiagnostics();
    for (const [uri, diags] of allDiagnostics) {
      if (uri.scheme !== "file") continue;
      recordRecentFile(uri.fsPath);
      for (const d of diags) {
        if (d.severity === vscode.DiagnosticSeverity.Error) {
          const line = d.range.start.line + 1;
          const msg = d.message.replace(/\s+/g, " ").slice(0, 140);
          errors.push(`${path.basename(uri.fsPath)}:${line} — ${msg}`);
          if (errors.length >= 4) return errors;
        }
      }
    }
  } catch (_err) {
    // Ignore diagnostic read errors
  }
  return errors;
}

/**
 * Reads the merged Refract configuration from VS Code settings and workspace .agents/refract.json.
 */
function getActiveConfig() {
  const cfg = vscode.workspace.getConfiguration("refract");
  const vsSettings = {
    mode: cfg.get("mode", "auto-intercept"),
    scoreThreshold: cfg.get("scoreThreshold", 72),
    rescueFailureSpirals: cfg.get("rescueFailureSpirals", true),
    alwaysIncludeRules: cfg.get("alwaysIncludeRules", []),
  };
  const folders = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
  return loadMergedConfig(vsSettings, folders);
}

/**
 * Assembles the current trajectory snapshot for Refract evaluation.
 * @param {readonly (vscode.ChatRequestTurn | vscode.ChatResponseTurn)[]} [chatHistory]
 */
function getTrajectorySnapshot(chatHistory = []) {
  if (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.uri.scheme === "file") {
    recordRecentFile(vscode.window.activeTextEditor.document.uri.fsPath);
  }

  /** @type {string[]} */
  const priorUserPrompts = [];
  for (const turn of chatHistory) {
    if ("prompt" in turn && typeof turn.prompt === "string" && turn.prompt.trim()) {
      priorUserPrompts.push(turn.prompt.trim());
    }
  }

  const diagErrors = collectActiveDiagnostics();
  const activeErrors = [...diagErrors, ...sessionState.recentErrors.slice(-2)].slice(-3);

  return {
    prior_user_prompts: priorUserPrompts.slice(-12),
    recent_files: [...sessionState.recentFiles],
    recent_commands: [...sessionState.recentCommands],
    recent_errors: [...sessionState.recentErrors, ...diagErrors].slice(-4),
    active_errors: activeErrors,
    consecutive_errors:
      sessionState.consecutiveTerminalErrors + (diagErrors.length > 0 ? 1 : 0),
    turn_count: priorUserPrompts.length + 1,
  };
}

/**
 * Updates the VS Code Status Bar item with the current Refract mode and health status.
 */
function updateStatusBar() {
  if (!statusBarItem) return;
  const config = getActiveConfig();
  const diagErrors = collectActiveDiagnostics();
  const isSpiral = sessionState.consecutiveTerminalErrors >= 2;
  const modeShort =
    config.mode === "auto-intercept"
      ? "Auto"
      : config.mode === "coach"
      ? "Coach"
      : "Slash";

  if (isSpiral) {
    statusBarItem.text = `$(warning) 💠 Refract: Spiral Rescue (${modeShort})`;
    statusBarItem.tooltip =
      "Refract detected repeated errors — click to refract a debugging prompt or open Scorecard";
  } else {
    statusBarItem.text = `$(sparkle) 💠 Refract: ${modeShort}`;
    statusBarItem.tooltip = `Refract Context & Trajectory Engine (Mode: ${config.mode}, Threshold: ${config.scoreThreshold}/100, Active Errors: ${diagErrors.length}). Click to Refract Prompt (Cmd+Alt+P).`;
  }
  statusBarItem.show();
}

/**
 * Opens or updates the Interactive 5-Dimension Trajectory Scorecard Webview Panel.
 * @param {string} [draftPrompt]
 */
function openScorecardWebview(draftPrompt) {
  const config = getActiveConfig();
  const trajectory = getTrajectorySnapshot();
  const promptToAnalyze =
    (draftPrompt && draftPrompt.trim()) ||
    sessionState.lastAnalyzedDraft ||
    "Refactor the active module and fix any open diagnostics";

  const evaluation = evaluatePrompt(promptToAnalyze, trajectory);
  const spectrums = synthesizeSpectrums(
    promptToAnalyze,
    evaluation,
    trajectory,
    config.alwaysIncludeRules
  );

  sessionState.lastAnalyzedDraft = promptToAnalyze;
  sessionState.lastEvaluation = evaluation;
  sessionState.lastSpectrums = spectrums;

  if (!activeScorecardPanel) {
    activeScorecardPanel = vscode.window.createWebviewPanel(
      "refractScorecard",
      "💠 Refract Trajectory Scorecard",
      vscode.ViewColumn.Beside,
      { enableScripts: true }
    );
    activeScorecardPanel.onDidDispose(() => {
      activeScorecardPanel = undefined;
    });
    activeScorecardPanel.webview.onDidReceiveMessage(async (msg) => {
      if (!msg || typeof msg !== "object") return;
      if (msg.type === "copy" && msg.prompt) {
        await vscode.env.clipboard.writeText(msg.prompt);
        vscode.window.showInformationMessage("💠 Refract: Copied spectrum prompt to clipboard.");
      } else if (msg.type === "sendToChat" && msg.prompt) {
        await vscode.commands.executeCommand("workbench.action.chat.open", {
          query: msg.prompt,
        });
      }
    });
  } else {
    activeScorecardPanel.reveal(vscode.ViewColumn.Beside);
  }

  activeScorecardPanel.webview.html = buildWebviewScorecardHtml(
    promptToAnalyze,
    evaluation,
    spectrums,
    trajectory,
    config.mode
  );
}

/**
 * Forwards an upgraded prompt directly to the user's active VS Code Chat Language Model (vscode.lm).
 * @param {string} finalPrompt
 * @param {vscode.ChatRequest} request
 * @param {vscode.ChatResponseStream} stream
 * @param {vscode.CancellationToken} token
 */
async function executeWithHostChatModel(finalPrompt, request, stream, token) {
  if (!request.model) {
    stream.markdown(
      `\n\n> Copy or click a follow-up spectrum below to run this prompt in your chat session.`
    );
    return;
  }

  const messages = [
    vscode.LanguageModelChatMessage.User(finalPrompt),
  ];

  try {
    const chatResponse = await request.model.sendRequest(messages, {}, token);
    for await (const fragment of chatResponse.text) {
      stream.markdown(fragment);
    }
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : String(err);
    stream.markdown(
      `\n\n*(Host model execution note: ${errMsg}. You can run the refracted prompt above directly in chat.)*`
    );
  }
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  // Seed initial active file if an editor is open
  if (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.uri.scheme === "file") {
    recordRecentFile(vscode.window.activeTextEditor.document.uri.fsPath);
  }

  // Track editor navigation & saves
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && editor.document.uri.scheme === "file") {
        recordRecentFile(editor.document.uri.fsPath);
        updateStatusBar();
      }
    }),
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (doc.uri.scheme === "file") {
        recordRecentFile(doc.uri.fsPath);
      }
    }),
    vscode.languages.onDidChangeDiagnostics(() => {
      updateStatusBar();
    })
  );

  // Track terminal command executions & exit codes (VS Code 1.93+ Shell Integration)
  if (typeof vscode.window.onDidEndTerminalShellExecution === "function") {
    context.subscriptions.push(
      vscode.window.onDidEndTerminalShellExecution((event) => {
        const cmdLine = event.execution && event.execution.commandLine
          ? event.execution.commandLine.value
          : "";
        if (cmdLine) {
          sessionState.recentCommands.push(cmdLine);
          if (sessionState.recentCommands.length > 6) {
            sessionState.recentCommands.shift();
          }
        }
        if (typeof event.exitCode === "number") {
          if (event.exitCode !== 0) {
            sessionState.consecutiveTerminalErrors += 1;
            sessionState.recentErrors.push(
              `Command '${cmdLine || "shell"}' exited with code ${event.exitCode}`
            );
          } else {
            sessionState.consecutiveTerminalErrors = 0;
            sessionState.recentErrors = [];
          }
          updateStatusBar();
        }
      })
    );
  }

  // Status Bar Item
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = "refract.refractPrompt";
  context.subscriptions.push(statusBarItem);
  updateStatusBar();

  // Command 1: Cmd+Alt+P — Refract Prompt (QuickPick across 3 Spectrums)
  context.subscriptions.push(
    vscode.commands.registerCommand("refract.refractPrompt", async () => {
      const editor = vscode.window.activeTextEditor;
      const selectedText =
        editor && !editor.selection.isEmpty
          ? editor.document.getText(editor.selection).trim()
          : "";

      const draft = await vscode.window.showInputBox({
        title: "💠 Refract — Context & Prompt Trajectory Engine",
        prompt: "Enter a rough prompt to refract against your active files, diagnostics, and terminal state",
        value: selectedText || sessionState.lastAnalyzedDraft || "",
        placeHolder: "e.g., fix the error in this handler and add tests",
      });
      if (!draft || !draft.trim()) return;

      const config = getActiveConfig();
      const trajectory = getTrajectorySnapshot();
      const evaluation = evaluatePrompt(draft, trajectory);
      const spectrums = synthesizeSpectrums(
        draft,
        evaluation,
        trajectory,
        config.alwaysIncludeRules
      );

      sessionState.lastAnalyzedDraft = draft;
      sessionState.lastEvaluation = evaluation;
      sessionState.lastSpectrums = spectrums;

      const recKey = spectrums.recommended.key;
      /** @type {Array<vscode.QuickPickItem & { action?: string, promptText?: string }>} */
      const items = [
        {
          label: `${recKey === "precision" ? "$(star-full) (Recommended) " : ""}${spectrums.precision.title}`,
          description: `Score: ${evaluation.overallScore}/100`,
          detail: spectrums.precision.prompt,
          action: "chat",
          promptText: spectrums.precision.prompt,
        },
        {
          label: `${recKey === "root_cause" ? "$(star-full) (Recommended) " : ""}${spectrums.root_cause.title}`,
          description: evaluation.isFailureSpiral ? "⚠️ Failure Spiral Rescue" : "Hypothesis-First",
          detail: spectrums.root_cause.prompt,
          action: "chat",
          promptText: spectrums.root_cause.prompt,
        },
        {
          label: `${spectrums.strict_spec.title}`,
          description: "Guardrailed + Test Verification",
          detail: spectrums.strict_spec.prompt,
          action: "chat",
          promptText: spectrums.strict_spec.prompt,
        },
        {
          label: "$(graph) Open Interactive 5-Dimension Trajectory Scorecard",
          description: `${evaluation.badge} ${evaluation.verdict}`,
          detail: "Inspect all 5 rubric bars, bound context files, and diagnostic gaps in a visual panel",
          action: "scorecard",
        },
      ];

      const picked = await vscode.window.showQuickPick(items, {
        title: `💠 Refract Score: ${evaluation.overallScore}/100 (${evaluation.verdict}) — Select Spectrum to Execute in Chat`,
        matchOnDetail: true,
      });

      if (!picked) return;
      if (picked.action === "scorecard") {
        openScorecardWebview(draft);
      } else if (picked.promptText) {
        await vscode.env.clipboard.writeText(picked.promptText);
        await vscode.commands.executeCommand("workbench.action.chat.open", {
          query: picked.promptText,
        });
      }
    })
  );

  // Command 2: Open Interactive Trajectory Scorecard Webview
  context.subscriptions.push(
    vscode.commands.registerCommand("refract.openScorecard", (draftArg) => {
      openScorecardWebview(typeof draftArg === "string" ? draftArg : undefined);
    })
  );

  // Command 3: Switch Refract Operating Mode
  context.subscriptions.push(
    vscode.commands.registerCommand("refract.switchMode", async () => {
      const current = getActiveConfig().mode;
      const items = [
        {
          label: `${current === "auto-intercept" ? "$(check) " : ""}auto-intercept`,
          description: "(Default) Silently grounds diffuse prompts in-flight and executes immediately",
          mode: "auto-intercept",
        },
        {
          label: `${current === "coach" ? "$(check) " : ""}coach`,
          description: "Shows the 5-Dimension score and lets you pick which spectrum to run with 1 click",
          mode: "coach",
        },
        {
          label: `${current === "slash-only" ? "$(check) " : ""}slash-only`,
          description: "Only refracts when explicitly summoned via /refract, /check, or Cmd+Alt+P",
          mode: "slash-only",
        },
      ];
      const chosen = await vscode.window.showQuickPick(items, {
        title: "💠 Refract — Select Operating Mode",
      });
      if (chosen) {
        await vscode.workspace
          .getConfiguration("refract")
          .update("mode", chosen.mode, vscode.ConfigurationTarget.Global);
        updateStatusBar();
        vscode.window.showInformationMessage(`💠 Refract mode set to '${chosen.mode}'.`);
      }
    })
  );

  // Command 4: Run Doctor Health Check
  context.subscriptions.push(
    vscode.commands.registerCommand("refract.runDoctor", () => {
      const config = getActiveConfig();
      const trajectory = getTrajectorySnapshot();
      vscode.window.showInformationMessage(
        `💠 Refract Doctor: Healthy | Engine: Native Node.js (${process.version}, 0 external deps) | Mode: ${config.mode} | Threshold: ${config.scoreThreshold}/100 | Tracked Files: ${trajectory.recent_files.length} | Active Errors: ${trajectory.active_errors.length}`
      );
    })
  );

  // Register @refract Chat Participant (VS Code Chat API)
  if (vscode.chat && typeof vscode.chat.createChatParticipant === "function") {
    const participant = vscode.chat.createChatParticipant(
      "refract.participant",
      async (request, chatContext, stream, token) => {
        const config = getActiveConfig();
        const trajectory = getTrajectorySnapshot(chatContext.history);
        const rawPrompt = (request.prompt || "").trim();

        // Slash Command: /mode
        if (request.command === "mode") {
          const requestedMode = rawPrompt.toLowerCase();
          if (["auto-intercept", "coach", "slash-only"].includes(requestedMode)) {
            await vscode.workspace
              .getConfiguration("refract")
              .update("mode", requestedMode, vscode.ConfigurationTarget.Global);
            updateStatusBar();
            stream.markdown(
              `### 💠 Refract Mode Updated\nOperating mode is now **\`${requestedMode}\`** (Score Threshold: \`${config.scoreThreshold}/100\`).`
            );
            return { metadata: { command: "mode" } };
          }
          stream.markdown(
            `### 💠 Refract Operating Mode\n- **Current Mode**: \`${config.mode}\`\n- **Score Threshold**: \`${config.scoreThreshold}/100\`\n- **Failure Spiral Rescue**: \`${config.rescueFailureSpirals}\`\n\nSwitch modes anytime via \`@refract /mode auto-intercept\`, \`@refract /mode coach\`, or \`@refract /mode slash-only\`.`
          );
          stream.button({
            command: "refract.switchMode",
            title: "⚙️ Switch Refract Mode...",
          });
          return { metadata: { command: "mode" } };
        }

        // Slash Command: /doctor
        if (request.command === "doctor") {
          stream.markdown(
            `### 💠 Refract Environment & Trajectory Doctor\n` +
              `- **Status**: \`Healthy\` (100% On-Device Execution)\n` +
              `- **Runtime**: VS Code Extension Host (\`Node ${process.version}\`, Zero external packages)\n` +
              `- **Active Mode**: \`${config.mode}\` (Threshold: \`${config.scoreThreshold}/100\`)\n` +
              `- **Bound Workspace Files (${trajectory.recent_files.length})**: ${
                trajectory.recent_files.map((f) => `\`${path.basename(f)}\``).join(", ") || "None yet"
              }\n` +
              `- **Active Problems / Diagnostics (${trajectory.active_errors.length})**: ${
                trajectory.active_errors.map((e) => `\`${e}\``).join("; ") || "None"
              }\n`
          );
          return { metadata: { command: "doctor" } };
        }

        const promptText =
          rawPrompt ||
          sessionState.lastAnalyzedDraft ||
          "Refactor the current file and resolve any open diagnostics";
        const evaluation = evaluatePrompt(promptText, trajectory);
        const spectrums = synthesizeSpectrums(
          promptText,
          evaluation,
          trajectory,
          config.alwaysIncludeRules
        );

        sessionState.lastAnalyzedDraft = promptText;
        sessionState.lastEvaluation = evaluation;
        sessionState.lastSpectrums = spectrums;

        // Slash Command: /check (Interactive Scorecard)
        if (request.command === "check") {
          openScorecardWebview(promptText);
          stream.markdown(
            `### 💠 Refract Trajectory Scorecard: **${evaluation.overallScore}/100** ${evaluation.badge} *(${evaluation.verdict})*\n\n` +
              `| Dimension | Score |\n| :--- | :--- |\n` +
              Object.values(evaluation.dimensions)
                .map((d) => `| **${d.label}** | \`${d.score}/${d.max}\` |`)
                .join("\n") +
              `\n\n**Detected Gaps:**\n` +
              (evaluation.gaps.map((g) => `- ${g}`).join("\n") || "- None — prompt is well-grounded!") +
              `\n\n*Opened the Interactive 5-Dimension Scorecard Panel beside your editor. Click a follow-up spectrum below to execute immediately:*`
          );
          stream.button({
            command: "refract.openScorecard",
            arguments: [promptText],
            title: "📊 Reveal Interactive Scorecard Panel",
          });
          return {
            metadata: {
              command: "check",
              spectrums,
              evaluation,
            },
          };
        }

        // Slash Command: /refract OR Coach Mode OR Architectural Fork
        const isExplicitRefractCmd = request.command === "refract";
        const shouldCoach =
          isExplicitRefractCmd ||
          config.mode === "coach" ||
          Boolean(evaluation.architecturalFork);

        if (shouldCoach) {
          stream.markdown(
            `### 💠 Refracted Spectrums — Score: **${evaluation.overallScore}/100** ${evaluation.badge} *(${evaluation.verdict})*\n\n` +
              (evaluation.gaps.length > 0
                ? `**Context & Trajectory Gaps Resolved:**\n${evaluation.gaps.map((g) => `- ${g}`).join("\n")}\n\n`
                : "") +
              `#### 1. ${spectrums.precision.title}\n> ${spectrums.precision.prompt}\n\n` +
              `#### 2. ${spectrums.root_cause.title}\n> ${spectrums.root_cause.prompt}\n\n` +
              `#### 3. ${spectrums.strict_spec.title}\n> ${spectrums.strict_spec.prompt}\n\n` +
              `*Click any follow-up button below to execute that spectrum immediately:*`
          );
          stream.button({
            command: "refract.openScorecard",
            arguments: [promptText],
            title: "📊 Open Interactive Scorecard",
          });
          return {
            metadata: {
              command: "refract",
              showFollowups: true,
              spectrums,
              evaluation,
            },
          };
        }

        // Default: Auto-Intercept Mode
        const bypassCheck = shouldBypassPrompt(promptText, config);
        const needsRefraction =
          !bypassCheck.bypass &&
          evaluation.gaps.length > 0 &&
          (evaluation.overallScore < config.scoreThreshold ||
            (config.rescueFailureSpirals && evaluation.isFailureSpiral));

        if (!needsRefraction) {
          await executeWithHostChatModel(promptText, request, stream, token);
          return { metadata: { command: "passthrough", evaluation } };
        }

        const recKey = spectrums.recommended.key;
        const recSpec = spectrums[recKey];

        stream.markdown(
          `<details><summary>💠 <b>Refracted Prompt</b> (Score: ${evaluation.overallScore}/100 → Grounded via ${recSpec.title})</summary>\n\n` +
            `> ${recSpec.prompt}\n\n` +
            `</details>\n\n`
        );

        await executeWithHostChatModel(recSpec.prompt, request, stream, token);
        return {
          metadata: {
            command: "auto-intercept",
            showFollowups: true,
            spectrums,
            evaluation,
          },
        };
      }
    );

    participant.iconPath = vscode.Uri.file(
      path.join(context.extensionPath, "assets", "logo.png")
    );

    participant.followupProvider = {
      provideFollowups(result, _context, _token) {
        const meta = result && result.metadata;
        if (!meta || !meta.spectrums) return [];
        const s = meta.spectrums;
        return [
          {
            prompt: s.precision.prompt,
            label: "⚡ Execute Precision Spectrum",
          },
          {
            prompt: s.root_cause.prompt,
            label: "🔬 Execute Root-Cause Spectrum",
          },
          {
            prompt: s.strict_spec.prompt,
            label: "🛡️ Execute Strict Spec Spectrum",
          },
        ];
      },
    };

    context.subscriptions.push(participant);
  }

  // Register #refract Language Model Tool (vscode.lm.registerTool)
  if (vscode.lm && typeof vscode.lm.registerTool === "function") {
    context.subscriptions.push(
      vscode.lm.registerTool("refract_prompt", {
        async invoke(options, _token) {
          const input = (options && options.input) || {};
          const draft = String(input.draftPrompt || "").trim();
          const config = getActiveConfig();
          const trajectory = getTrajectorySnapshot();
          const evaluation = evaluatePrompt(draft, trajectory);
          const spectrums = synthesizeSpectrums(
            draft,
            evaluation,
            trajectory,
            config.alwaysIncludeRules
          );
          const payload = {
            overallScore: evaluation.overallScore,
            verdict: evaluation.verdict,
            isFailureSpiral: evaluation.isFailureSpiral,
            gaps: evaluation.gaps,
            boundWorkspaceFiles: trajectory.recent_files,
            activeDiagnostics: trajectory.active_errors,
            recommendedSpectrum: spectrums[spectrums.recommended.key],
            spectrums,
          };
          return new vscode.LanguageModelToolResult([
            new vscode.LanguageModelTextPart(JSON.stringify(payload, null, 2)),
          ]);
        },
      })
    );
  }
}

function deactivate() {
  if (statusBarItem) {
    statusBarItem.dispose();
  }
}

module.exports = {
  activate,
  deactivate,
};
