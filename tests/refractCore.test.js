// Parity tests for the VS Code Node engine (src/refractCore.js).
// Run with: node tests/refractCore.test.js   (no npm packages required)
"use strict";

const assert = require("node:assert/strict");
const core = require("../src/refractCore");

let passed = 0;
function test(name, fn) {
  fn();
  passed += 1;
  console.log(`ok - ${name}`);
}

test("bypasses slash commands, confirmations, and slash-only mode", () => {
  const cfg = { ...core.DEFAULT_CONFIG };
  assert.equal(core.shouldBypassPrompt("/plan build a service", cfg).bypass, true);
  assert.equal(core.shouldBypassPrompt("Looks good!", cfg).bypass, true);
  assert.equal(core.shouldBypassPrompt("fix this", { ...cfg, mode: "slash-only" }).bypass, true);
  assert.equal(core.shouldBypassPrompt("fix the bug in this file", cfg).bypass, false);
});

test("binds deictic references to recent files and scores below threshold", () => {
  const traj = {
    prior_user_prompts: ["Refactor the authentication middleware in auth_handler.py"],
    recent_files: ["/workspace/src/auth_handler.py"],
    recent_commands: ["pytest tests/test_auth.py"],
  };
  const prompt = "now do the same for this file and make it async";
  const ev = core.evaluatePrompt(prompt, traj);
  assert.ok(ev.boundContext.files.includes("/workspace/src/auth_handler.py"));
  assert.ok(ev.overallScore < 75);

  const specs = core.synthesizeSpectrums(prompt, ev, traj, ["Use strict type annotations"]);
  assert.match(specs.precision.prompt, /auth_handler\.py/);
  assert.match(specs.precision.prompt, /Use strict type annotations/);
  assert.match(specs.strict_spec.prompt, /pytest tests\/test_auth\.py/);
});

test("detects failure spirals and recommends Root-Cause", () => {
  const traj = {
    recent_files: ["/workspace/src/db_pool.py"],
    active_errors: ["db_pool.py:88 — PoolTimeout"],
    consecutive_errors: 1,
  };
  const prompt = "it still doesn't work, same error";
  const ev = core.evaluatePrompt(prompt, traj);
  assert.equal(ev.isFailureSpiral, true);
  const specs = core.synthesizeSpectrums(prompt, ev, traj);
  assert.equal(specs.recommended.key, "root_cause");
  assert.match(specs.root_cause.prompt, /PoolTimeout/);
});

test("flags architectural forks", () => {
  const ev = core.evaluatePrompt("add caching to the user endpoint", {});
  assert.ok(ev.architecturalFork);
  assert.equal(ev.architecturalFork.title, "Caching Strategy Fork");
});

test("strong, specific prompt scores as execution-ready", () => {
  const prompt =
    "Refactor `parse_transcript` in `scripts/refract_engine.py` to cap `recent_files` at 6 items while preserving existing return types, and verify by running `python3 -m unittest`.";
  const ev = core.evaluatePrompt(prompt, {});
  assert.ok(ev.overallScore >= core.DEFAULT_CONFIG.scoreThreshold, `score was ${ev.overallScore}`);
  assert.equal(ev.isFailureSpiral, false);
});

test("webview scorecard HTML escapes input and embeds spectrums", () => {
  const prompt = "fix <script>alert(1)</script> in this file";
  const traj = { recent_files: ["/workspace/src/app.ts"], turn_count: 2 };
  const ev = core.evaluatePrompt(prompt, traj);
  const specs = core.synthesizeSpectrums(prompt, ev, traj);
  const html = core.buildWebviewScorecardHtml(prompt, ev, specs, traj, "auto-intercept");
  assert.match(html, /Refract Trajectory Scorecard/);
  assert.ok(html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));
  assert.match(html, /Send to VS Code Chat/);
});

console.log(`\n${passed} JS tests passed`);
