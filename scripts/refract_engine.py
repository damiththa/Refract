#!/usr/bin/env python3
"""Refract — Context & Prompt Trajectory Engine for Google Antigravity.

Operates in two modes:
1. PreInvocation Lifecycle Hook (stdin JSON -> stdout injectSteps JSON)
2. CLI Utility (--analyze, --html-widget, --set-mode, --set-threshold, --status) for /refract skills.
"""

from __future__ import annotations

import argparse
from collections import deque
import html
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PLUGIN_ROOT / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "mode": "auto-intercept",  # "auto-intercept" | "coach" | "slash-only"
    "scoreThreshold": 72,
    "rescueFailureSpirals": True,
    "maxTranscriptTurns": 12,
    "alwaysIncludeRules": [],
}

# Short conversational confirmations that should NEVER be intercepted
BYPASS_EXACT_PHRASES = {
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
}

ACTION_VERBS = {
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
}

VAGUE_PHRASES = [
    r"\bfix\s+it\b",
    r"\bmake\s+it\s+(?:work|better|faster|good|clean)\b",
    r"\bdo\s+the\s+same\b",
    r"\btry\s+again\b",
    r"\bnot\s+working\b",
    r"\bstill\s+(?:broken|failing|fails|wrong|doesn'?t\s+work)\b",
    r"\bsame\s+(?:error|issue|bug|problem)\b",
    r"\bchange\s+this\b",
    r"\bupdate\s+it\b",
    r"\bfix\s+this\b",
    r"\bhelp\s+me\b",
    r"\bwhat'?s\s+wrong\b",
]

DEICTIC_REFERENCES = [
    (r"\b(?:this|that)\s+(?:file|module|component|class|function|method|handler|endpoint|script|test)\b", "file_or_symbol"),
    (r"\b(?:the\s+other|the\s+second|the\s+first|the\s+previous)\s+(?:one|file|function|endpoint|handler|approach|option)\b", "prior_turn_entity"),
    (r"\b(?:this|that|the)\s+(?:error|bug|exception|crash|failure|issue|warning)\b", "recent_error"),
    (r"\bdo\s+the\s+same\b", "prior_action_pattern"),
    (r"\b(?:fix|update|refactor|change|run|test)\s+(?:it|this|that|them)\b", "implicit_target"),
]

FRUSTRATION_PATTERNS = [
    r"\bstill\s+(?:not\s+working|broken|failing|fails|wrong|same|getting)\b",
    r"\bsame\s+(?:error|issue|bug|problem|output|failure)\b",
    r"\bdidn'?t\s+(?:work|fix\s+it|help|solve)\b",
    r"\bdoesn'?t\s+work\b",
    r"\bwhy\s+is\s+it\s+still\b",
    r"\byou\s+broke\b",
    r"\bthat\s+broke\b",
    r"\btry\s+(?:something\s+else|again|another\s+way)\b",
]

ARCHITECTURAL_FORK_PATTERNS = [
    (
        r"\badd\s+(?:caching|cache)\b",
        "Caching Strategy Fork",
        ["In-memory LRU / local cache", "Distributed cache (Redis / Memcached)", "HTTP / CDN Cache-Control headers"],
    ),
    (
        r"\badd\s+(?:auth|authentication|login)\b",
        "Authentication Architecture Fork",
        ["Stateless JWT / Bearer tokens", "Server-side session cookies", "OAuth2 / OIDC provider integration"],
    ),
    (
        r"\badd\s+(?:rate\s+limit|rate-limit|throttl\w+)\b",
        "Rate Limiting Scope Fork",
        ["In-process memory limiter (per-instance)", "Redis-backed distributed sliding window", "API Gateway / reverse-proxy middleware"],
    ),
    (
        r"\b(?:add|setup|use)\s+(?:a\s+)?database\b",
        "Database Storage Fork",
        ["PostgreSQL / relational schema", "SQLite / embedded local file", "NoSQL / document store"],
    ),
    (
        r"\bstate\s+management\b",
        "State Architecture Fork",
        ["Local component / hook state", "Lightweight store (Zustand / Signals / Context)", "Global state machine / Redux pattern"],
    ),
]


def load_config(config_path: Path = CONFIG_PATH, workspace_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """Loads global plugin config and merges optional workspace .agents/refract.json overrides."""
    cfg = dict(DEFAULT_CONFIG)
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except Exception:
            pass

    if workspace_paths:
        for wp in workspace_paths:
            ws_cfg_path = Path(wp).expanduser() / ".agents" / "refract.json"
            if ws_cfg_path.exists():
                try:
                    ws_loaded = json.loads(ws_cfg_path.read_text(encoding="utf-8"))
                    if isinstance(ws_loaded, dict):
                        cfg.update(ws_loaded)
                except Exception:
                    pass
    return cfg


def save_config(updates: Dict[str, Any], config_path: Path = CONFIG_PATH) -> Dict[str, Any]:
    cfg = load_config(config_path)
    cfg.update(updates)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return cfg


def clean_json_arg(val: Any) -> str:
    """Strips extra JSON string quoting found in transcript tool_calls args."""
    if not isinstance(val, str):
        return str(val)
    s = val.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try:
            unquoted = json.loads(s)
            if isinstance(unquoted, str):
                return unquoted
        except Exception:
            return s[1:-1]
    return s


def extract_user_request(raw_content: str) -> str:
    """Extracts the core prompt inside <USER_REQUEST>...</USER_REQUEST> if present."""
    if not raw_content:
        return ""
    match = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", raw_content, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw_content.strip()


def is_internal_artifact_path(file_path: str) -> bool:
    """Filters out Antigravity internal brain/system/builtin files from workspace file binding."""
    if not file_path:
        return True
    ignored_segments = (
        "/.system_generated/",
        "/.gemini/antigravity/brain/",
        "/.gemini/antigravity/builtin/",
    )
    return any(seg in file_path for seg in ignored_segments)


def parse_transcript(transcript_path: Optional[str], max_turns: int = 12) -> Dict[str, Any]:
    """Parses the tail of Antigravity's transcript.jsonl for trajectory intelligence."""
    trajectory: Dict[str, Any] = {
        "latest_user_prompt": "",
        "prior_user_prompts": [],
        "recent_files": [],
        "recent_commands": [],
        "recent_errors": [],
        "active_errors": [],
        "consecutive_errors": 0,
        "turn_count": 0,
        "last_step_type": "",
    }
    if not transcript_path:
        return trajectory

    path = Path(transcript_path).expanduser()
    if not path.exists():
        return trajectory

    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            recent_lines = deque(f, maxlen=250)
    except Exception:
        return trajectory

    user_prompts: List[str] = []
    files_seen: List[str] = []
    commands_seen: List[str] = []
    all_errors_seen: List[str] = []
    active_errors: List[str] = []
    consecutive_errors = 0

    for line in recent_lines:
        line = line.strip()
        if not line:
            continue
        try:
            step = json.loads(line)
        except Exception:
            continue

        step_type = step.get("type", "")
        status = step.get("status", "")
        content = step.get("content", "") or ""
        trajectory["last_step_type"] = step_type

        if step_type == "USER_INPUT":
            extracted = extract_user_request(content)
            if extracted:
                user_prompts.append(extracted)

        elif step_type == "PLANNER_RESPONSE":
            tool_calls = step.get("tool_calls") or []
            for tc in tool_calls:
                tc_name = tc.get("name", "")
                args = tc.get("args") or {}
                if tc_name in {"view_file", "replace_file_content", "write_to_file", "multi_replace_file_content"}:
                    raw_path = args.get("AbsolutePath") or args.get("TargetFile") or ""
                    cleaned_path = clean_json_arg(raw_path)
                    if cleaned_path and not is_internal_artifact_path(cleaned_path):
                        if cleaned_path in files_seen:
                            files_seen.remove(cleaned_path)
                        files_seen.append(cleaned_path)
                elif tc_name == "run_command":
                    cmd = clean_json_arg(args.get("CommandLine", ""))
                    if cmd and "refract_engine.py" not in cmd:
                        if cmd in commands_seen:
                            commands_seen.remove(cmd)
                        commands_seen.append(cmd)

        elif step_type == "GENERIC":
            is_err = (
                status == "ERROR"
                or "Encountered error in tool execution:" in content
                or bool(re.search(r"The command exited with code [1-9]\d*", content))
            )
            if is_err:
                consecutive_errors += 1
                snippet = content.strip().splitlines()[-1][:160] if content.strip() else "Tool execution failed"
                all_errors_seen.append(snippet)
                active_errors.append(snippet)
            elif "The command exited with code 0" in content:
                # A subsequent command succeeded, clearing resolved error state
                consecutive_errors = 0
                active_errors.clear()

    trajectory["turn_count"] = len(user_prompts)
    if user_prompts:
        trajectory["latest_user_prompt"] = user_prompts[-1]
        trajectory["prior_user_prompts"] = user_prompts[:-1][-max_turns:]

    trajectory["recent_files"] = files_seen[-6:]
    trajectory["recent_commands"] = commands_seen[-4:]
    trajectory["recent_errors"] = all_errors_seen[-3:]
    trajectory["active_errors"] = active_errors[-2:]
    trajectory["consecutive_errors"] = consecutive_errors
    return trajectory


def should_bypass_hook(
    hook_input: Dict[str, Any],
    prompt_text: str,
    config: Dict[str, Any],
    trajectory: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Determines if PreInvocation should immediately return {} without interfering."""
    if config.get("mode") == "slash-only":
        return True, "Mode is slash-only"

    invocation_num = hook_input.get("invocationNum", 1)
    if isinstance(invocation_num, int) and invocation_num > 1:
        return True, "Mid-turn tool loop (invocationNum > 1)"

    if trajectory:
        last_step = trajectory.get("last_step_type", "")
        if last_step and last_step != "USER_INPUT":
            return True, f"Mid-turn tool continuation (last_step_type={last_step})"

    cleaned = prompt_text.strip()
    if not cleaned:
        return True, "Empty prompt"

    # Never intercept explicit slash commands
    if cleaned.startswith("/"):
        return True, "Explicit slash command"

    # Never intercept short conversational confirmations
    normalized = re.sub(r"[^\w\s]", "", cleaned.lower()).strip()
    if normalized in BYPASS_EXACT_PHRASES:
        return True, "Short confirmation phrase"

    return False, ""


def evaluate_prompt(prompt_text: str, trajectory: Dict[str, Any]) -> Dict[str, Any]:
    """Scores a prompt across the 5-Dimension Trajectory Rubric (0-100)."""
    text = prompt_text.strip()
    lower = text.lower()
    words = re.findall(r"\b\w+\b", lower)
    word_count = len(words)

    recent_files: List[str] = trajectory.get("recent_files", [])
    active_errors: List[str] = trajectory.get("active_errors", [])
    recent_errors: List[str] = trajectory.get("recent_errors", [])
    prior_prompts: List[str] = trajectory.get("prior_user_prompts", [])
    consecutive_errors: int = trajectory.get("consecutive_errors", 0)

    gaps: List[str] = []
    bound_context: Dict[str, Any] = {
        "files": [],
        "errors": [],
        "prior_intent": prior_prompts[-1] if prior_prompts else "",
    }

    # --- 1. Intent Clarity (0 - 25) ---
    has_action_verb = any(w in ACTION_VERBS for w in words)
    has_vague_phrase = any(re.search(pat, lower) for pat in VAGUE_PHRASES)
    has_code_ident = bool(
        re.search(
            r"[`][\w./-]+[`]|\b\w+\.(?:ts|tsx|js|jsx|py|go|rs|java|json|md|css|html|sh|yml|yaml)\b|\b[a-z]+[A-Z]\w+\b|\b\w+_\w+\b",
            text,
        )
    )

    clarity = 13
    if has_action_verb:
        clarity += 6
    if has_code_ident:
        clarity += 6
    if word_count < 5:
        clarity -= 6
    elif word_count >= 12:
        clarity += 3
    if has_vague_phrase:
        clarity -= 6
        gaps.append("Uses vague phrasing instead of specifying the exact behavior or target symbol.")
    clarity = max(3, min(25, clarity))

    # --- 2. Context Grounding (0 - 25) ---
    ungrounded_refs: List[str] = []
    for pat, ref_kind in DEICTIC_REFERENCES:
        m = re.search(pat, lower)
        if m:
            ungrounded_refs.append(f"'{m.group(0)}' ({ref_kind})")

    context_score = 17
    if has_code_ident or "@" in text or "#" in text:
        context_score += 7
    if ungrounded_refs and not has_code_ident:
        context_score -= 11
        if recent_files:
            bound_names = [Path(f).name for f in recent_files[-3:]]
            bound_context["files"] = recent_files[-3:]
            gaps.append(
                f"Contains ungrounded reference ({', '.join(ungrounded_refs[:2])}); auto-bound to recent project files: {', '.join(bound_names)}."
            )
        else:
            gaps.append(
                f"Contains ambiguous reference ({', '.join(ungrounded_refs[:2])}) without naming a file, function, or component."
            )
    elif recent_files and ungrounded_refs:
        bound_context["files"] = recent_files[-2:]

    # Only bind errors when there is an active unresolved error OR the user explicitly mentions an error/bug/failure
    mentions_error = bool(re.search(r"\b(?:error|bug|exception|fail\w*|broken|crash\w*|issue)\b", lower))
    if active_errors:
        bound_context["errors"] = active_errors[-2:]
    elif mentions_error and recent_errors:
        bound_context["errors"] = recent_errors[-1:]

    context_score = max(4, min(25, context_score))

    # --- 3. Trajectory Continuity & Failure Spiral Detection (0 - 20) ---
    frustration_match = any(re.search(pat, lower) for pat in FRUSTRATION_PATTERNS)
    is_failure_spiral = frustration_match or (consecutive_errors >= 2 and word_count < 25)

    continuity = 16
    if is_failure_spiral:
        continuity = 5
        gaps.append(
            "Vibe-Coding Failure Spiral detected (repeated error or frustration follow-up). Needs root-cause isolation instead of another blind edit."
        )
    elif prior_prompts and ungrounded_refs and not bound_context["files"]:
        continuity = 10
    elif word_count >= 10:
        continuity = 19
    continuity = max(4, min(20, continuity))

    # --- 4. Scope, Constraints & Architectural Forks (0 - 15) ---
    detected_fork: Optional[Dict[str, Any]] = None
    for pat, fork_title, fork_options in ARCHITECTURAL_FORK_PATTERNS:
        if re.search(pat, lower) and word_count < 25:
            detected_fork = {"title": fork_title, "options": fork_options}
            gaps.append(f"Unresolved {fork_title}: {', '.join(fork_options)}.")
            break

    has_constraints = bool(
        re.search(r"\b(?:without|do\s+not|don'?t|must|only|preserve|keep|ensure|avoid|strictly|compatibility|branch)\b", lower)
    )
    constraints_score = 9
    if has_constraints:
        constraints_score += 5
    if word_count >= 18:
        constraints_score += 3
    if detected_fork:
        constraints_score -= 6
    constraints_score = max(3, min(15, constraints_score))

    # --- 5. Verification / Definition of Done (0 - 15) ---
    has_verification = bool(
        re.search(r"\b(?:test|tests|unit\s+test|verify|check|assert|compile|build|lint|expect|output|return|push|commit|readme)\b", lower)
    )
    verification_score = 8
    if has_verification:
        verification_score += 6
    elif word_count >= 22:
        verification_score += 3
    else:
        gaps.append("No explicit verification or Definition-of-Done criteria specified.")
    verification_score = max(3, min(15, verification_score))

    overall = clarity + context_score + continuity + constraints_score + verification_score

    if overall >= 80 and not is_failure_spiral and not detected_fork:
        verdict = "Focused & Execution-Ready"
        badge = "🟢"
    elif overall >= 60 and not is_failure_spiral and not detected_fork:
        verdict = "Diffuse — Benefits from Context Grounding"
        badge = "🟡"
    else:
        verdict = "High Drift / Ambiguity Risk — Refraction Needed"
        badge = "🔴"

    return {
        "overallScore": overall,
        "verdict": verdict,
        "badge": badge,
        "isFailureSpiral": is_failure_spiral,
        "architecturalFork": detected_fork,
        "dimensions": {
            "clarity": {"score": clarity, "max": 25, "label": "Intent Clarity"},
            "context": {"score": context_score, "max": 25, "label": "Context Grounding"},
            "continuity": {"score": continuity, "max": 20, "label": "Trajectory Continuity"},
            "constraints": {"score": constraints_score, "max": 15, "label": "Scope & Constraints"},
            "verification": {"score": verification_score, "max": 15, "label": "Verification Criteria"},
        },
        "gaps": gaps,
        "boundContext": bound_context,
    }


def synthesize_spectrums(
    prompt_text: str,
    evaluation: Dict[str, Any],
    trajectory: Dict[str, Any],
    custom_rules: Optional[List[str]] = None,
) -> Dict[str, Dict[str, str]]:
    """Refracts the user's raw prompt into 3 actionable, non-fluffy engineering spectrums."""
    raw = prompt_text.strip()
    bound_files: List[str] = evaluation.get("boundContext", {}).get("files", [])
    recent_files: List[str] = bound_files or trajectory.get("recent_files", [])
    recent_commands: List[str] = trajectory.get("recent_commands", [])
    bound_errors: List[str] = evaluation.get("boundContext", {}).get("errors", [])
    prior_prompts: List[str] = trajectory.get("prior_user_prompts", [])

    file_clause = ""
    if recent_files:
        short_files = ", ".join(f"`{Path(p).name}` ({p})" for p in recent_files[-3:])
        file_clause = f" Focus on {short_files}."

    prior_clause = ""
    if prior_prompts and len(raw.split()) < 14:
        last_goal = prior_prompts[-1].replace("\n", " ")[:120]
        prior_clause = f"Building directly on our previous step (\"{last_goal}\"), "

    error_clause = ""
    if bound_errors:
        err_snip = bound_errors[-1]
        error_clause = f" Resolve the active error (`{err_snip}`)."

    rules_clause = ""
    if custom_rules:
        joined_rules = "; ".join(r.strip() for r in custom_rules if r.strip())
        if joined_rules:
            rules_clause = f" Adhere to project rules: {joined_rules}."

    test_cmd = "the project's test suite"
    for cmd in reversed(recent_commands):
        if any(k in cmd for k in ("test", "pytest", "unittest", "npm", "cargo", "go test", "tsc")):
            test_cmd = cmd
            break

    # Spectrum 1: Precision (Direct, Context-Grounded)
    precision_prompt = (
        f"{prior_clause}{raw}.{file_clause}{error_clause}{rules_clause} "
        f"Preserve existing public interfaces and unrelated logic, and summarize the exact changes made."
    ).strip()
    precision_prompt = re.sub(r"\s+", " ", precision_prompt).replace("..", ".")

    # Spectrum 2: Root-Cause & Hypothesis (Ideal for debugging / unstucking failure spirals)
    root_cause_prompt = (
        f"Before making any code edits for \"{raw}\",{file_clause}{error_clause} "
        f"1) Identify the top 2 root-cause hypotheses based on our conversation history and current file state, "
        f"2) Verify which hypothesis is actually occurring by inspecting the relevant code/logs, and "
        f"3) Apply a targeted fix and verify it.{rules_clause}"
    ).strip()
    root_cause_prompt = re.sub(r"\s+", " ", root_cause_prompt)

    # Spectrum 3: Strict Spec & Verification-Driven (TDD / Guardrailed)
    fork = evaluation.get("architecturalFork")
    fork_note = (
        f" First confirm or select the preferred approach among: {', '.join(fork['options'])}."
        if fork
        else ""
    )
    strict_prompt = (
        f"Execute task: \"{raw}\".{file_clause}{fork_note}{rules_clause} "
        f"Constraints: Keep the diff minimal and well-typed, handle edge/error cases explicitly, "
        f"and verify the implementation by running `{test_cmd}` before concluding."
    ).strip()
    strict_prompt = re.sub(r"\s+", " ", strict_prompt)

    recommended = "root_cause" if evaluation.get("isFailureSpiral") else "precision"

    return {
        "recommended": {
            "key": recommended,
            "reason": (
                "Failure spiral / debugging loop detected — Root-Cause Isolation prevents blind guessing."
                if recommended == "root_cause"
                else "Direct context-bound execution grounded in active workspace files."
            ),
        },
        "precision": {
            "title": "⚡ Precision Spectrum (Context-Grounded)",
            "prompt": precision_prompt,
            "when": "Best for fast, unambiguous execution bound to recent files.",
        },
        "root_cause": {
            "title": "🔬 Root-Cause Spectrum (Hypothesis-First)",
            "prompt": root_cause_prompt,
            "when": "Best when debugging stubborn errors or breaking a 'still not working' loop.",
        },
        "strict_spec": {
            "title": "🛡️ Strict Spec Spectrum (Guardrailed + Verified)",
            "prompt": strict_prompt,
            "when": "Best for production changes requiring minimal diff scope and test verification.",
        },
    }


def build_ephemeral_injection(
    prompt_text: str,
    evaluation: Dict[str, Any],
    spectrums: Dict[str, Any],
    trajectory: Dict[str, Any],
    mode: str,
) -> str:
    """Formats the transient PreInvocation ephemeralMessage injected for the current turn."""
    score = evaluation["overallScore"]
    verdict = evaluation["verdict"]
    rec_key = spectrums["recommended"]["key"]
    rec_spectrum = spectrums[rec_key]
    gaps_text = "\n".join(f"  - {g}" for g in evaluation["gaps"]) or "  - None"

    recent_files = trajectory.get("recent_files", [])
    files_line = ", ".join(recent_files[-3:]) if recent_files else "None in recent transcript"

    if mode == "coach" or evaluation.get("architecturalFork"):
        return (
            f"[REFRACT_INTERCEPT mode=\"coach\" score=\"{score}/100\" verdict=\"{verdict}\"]\n"
            f"The user submitted a prompt that scored {score}/100 on the Refract Trajectory Rubric.\n"
            f"Detected Context & Trajectory Gaps:\n{gaps_text}\n"
            f"Active Session Files: {files_line}\n\n"
            f"Refracted Spectrum Options:\n"
            f"1. {spectrums['precision']['title']}: {spectrums['precision']['prompt']}\n"
            f"2. {spectrums['root_cause']['title']}: {spectrums['root_cause']['prompt']}\n"
            f"3. {spectrums['strict_spec']['title']}: {spectrums['strict_spec']['prompt']}\n\n"
            f"INSTRUCTION FOR AGENT (Coach Mode): Use the `ask_question` tool to briefly show the user their Refract Score ({score}/100) "
            f"and let them pick which Refracted Spectrum (or their original prompt) to execute with 1 click."
        )

    # Default: auto-intercept mode
    return (
        f"[REFRACT_INTERCEPT mode=\"auto-intercept\" score=\"{score}/100\" verdict=\"{verdict}\"]\n"
        f"Refract automatically grounded the user's prompt using the conversation trajectory.\n"
        f"- Original Prompt: {prompt_text.strip()}\n"
        f"- Active Session Files: {files_line}\n"
        f"- Detected Gaps Resolved:\n{gaps_text}\n"
        f"- Upgraded Prompt ({rec_spectrum['title']}): {rec_spectrum['prompt']}\n\n"
        f"INSTRUCTION FOR AGENT (Auto-Intercept Mode):\n"
        f"1. At the very top of your response, include a single compact collapsible block:\n"
        f"   <details><summary>💠 <b>Refracted Prompt</b> (Score: {score}/100 → Grounded via {rec_spectrum['title']})</summary>\n\n"
        f"   > {rec_spectrum['prompt']}\n"
        f"   </details>\n"
        f"2. Immediately execute the Upgraded Prompt thoroughly without asking unnecessary meta-questions."
    )


def generate_html_scorecard(
    prompt_text: str,
    evaluation: Dict[str, Any],
    spectrums: Dict[str, Any],
    trajectory: Dict[str, Any],
    output_path: Path,
    mode: str,
) -> Path:
    """Generates a compact (<480px) interactive Generative UI HTML widget for /refract-check."""
    score = evaluation["overallScore"]
    verdict = html.escape(evaluation["verdict"])
    escaped_prompt = html.escape(prompt_text.strip() or "(Auditing recent conversation trajectory)")
    is_spiral = evaluation.get("isFailureSpiral", False)

    dims_html = []
    for key, dim in evaluation["dimensions"].items():
        pct = int(round((dim["score"] / dim["max"]) * 100))
        bar_color = "#10B981" if pct >= 75 else ("#F59E0B" if pct >= 55 else "#EF4444")
        dims_html.append(
            f"""
            <div class="space-y-1">
              <div class="flex justify-between text-xs">
                <span class="font-medium text-[var(--foreground)]">{html.escape(dim['label'])}</span>
                <span class="text-[var(--muted-foreground)] font-mono">{dim['score']}/{dim['max']}</span>
              </div>
              <div class="w-full h-1.5 bg-[var(--secondary)] rounded-full overflow-hidden">
                <div class="h-full rounded-full" style="width: {pct}%; background: {bar_color};"></div>
              </div>
            </div>
            """
        )

    gaps_items = "".join(
        f'<li class="text-xs text-[var(--muted-foreground)] flex items-start gap-1.5"><span class="text-amber-400">▸</span><span>{html.escape(g)}</span></li>'
        for g in (evaluation["gaps"] or ["Prompt is well-grounded in current conversation context."])
    )

    spec_data = {
        "precision": spectrums["precision"]["prompt"],
        "root_cause": spectrums["root_cause"]["prompt"],
        "strict_spec": spectrums["strict_spec"]["prompt"],
    }
    spec_json = json.dumps(spec_data)

    score_color = "#10B981" if score >= 80 else ("#F59E0B" if score >= 60 else "#EF4444")
    spiral_badge = (
        '<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/15 text-red-400 border border-red-500/30">⚠️ Failure Spiral Rescue Active</span>'
        if is_spiral
        else '<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">✓ Trajectory Healthy</span>'
    )

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-3">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl p-4 shadow-sm space-y-3">
    <!-- Header -->
    <div class="flex items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
      <div class="flex items-center gap-2.5">
        <div class="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-sm border border-[var(--border)]" style="color: {score_color};">
          {score}
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h2 class="font-semibold text-sm text-[var(--foreground)]">💠 Refract Trajectory Scorecard</h2>
            <span class="text-xs px-2 py-0.5 rounded bg-[var(--secondary)] text-[var(--muted-foreground)] font-mono">mode: {html.escape(mode)}</span>
          </div>
          <p class="text-xs text-[var(--muted-foreground)]">{verdict}</p>
        </div>
      </div>
      <div>{spiral_badge}</div>
    </div>

    <!-- 2-Column Grid: 5-Dimension Rubric + Diagnostic Gaps -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div class="space-y-2 bg-[var(--background)]/40 border border-[var(--border)] rounded-lg p-2.5">
        <div class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">5-Dimension Rubric</div>
        {''.join(dims_html)}
      </div>

      <div class="space-y-2 bg-[var(--background)]/40 border border-[var(--border)] rounded-lg p-2.5 flex flex-col justify-between">
        <div class="space-y-1.5">
          <div class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">Analyzed Draft & Trajectory Gaps</div>
          <div class="text-xs font-mono bg-[var(--secondary)]/60 rounded px-2 py-1 truncate" title="{escaped_prompt}">{escaped_prompt}</div>
          <ul class="space-y-1 pt-1">{gaps_items}</ul>
        </div>
        <div class="text-xs text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)] flex justify-between">
          <span>Session Turns: <b>{trajectory.get('turn_count', 0)}</b></span>
          <span>Bound Files: <b>{len(trajectory.get('recent_files', []))}</b></span>
        </div>
      </div>
    </div>

    <!-- Interactive Refracted Spectrum Switcher -->
    <div class="space-y-2 pt-1">
      <div class="flex items-center justify-between gap-2">
        <div class="flex gap-1.5">
          <button onclick="selectSpec('precision')" id="btn-precision" class="px-2.5 py-1 rounded-md text-xs font-medium border border-[var(--border)] bg-[var(--primary)] text-[var(--primary-foreground)]">⚡ Precision</button>
          <button onclick="selectSpec('root_cause')" id="btn-root_cause" class="px-2.5 py-1 rounded-md text-xs font-medium border border-[var(--border)] bg-[var(--secondary)] text-[var(--secondary-foreground)]">🔬 Root-Cause</button>
          <button onclick="selectSpec('strict_spec')" id="btn-strict_spec" class="px-2.5 py-1 rounded-md text-xs font-medium border border-[var(--border)] bg-[var(--secondary)] text-[var(--secondary-foreground)]">🛡️ Strict Spec</button>
        </div>
        <button onclick="copyPrompt()" id="copy-btn" class="px-2.5 py-1 rounded-md text-xs font-medium border border-[var(--border)] bg-[var(--secondary)] text-[var(--foreground)] hover:opacity-90">📋 Copy Spectrum</button>
      </div>
      <div id="spec-box" class="text-xs font-mono bg-[var(--background)]/60 border border-[var(--border)] rounded-lg p-2.5 leading-relaxed select-all"></div>
    </div>
  </div>

  <script>
    const SPECS = {spec_json};
    let activeKey = {json.dumps(spectrums['recommended']['key'])};

    function selectSpec(key) {{
      activeKey = key;
      document.getElementById('spec-box').textContent = SPECS[key] || '';
      ['precision', 'root_cause', 'strict_spec'].forEach(k => {{
        const btn = document.getElementById('btn-' + k);
        if (k === key) {{
          btn.className = 'px-2.5 py-1 rounded-md text-xs font-medium border border-[var(--border)] bg-[var(--primary)] text-[var(--primary-foreground)]';
        }} else {{
          btn.className = 'px-2.5 py-1 rounded-md text-xs font-medium border border-[var(--border)] bg-[var(--secondary)] text-[var(--secondary-foreground)]';
        }}
      }});
    }}

    function copyPrompt() {{
      const text = SPECS[activeKey] || '';
      navigator.clipboard.writeText(text).then(() => {{
        const btn = document.getElementById('copy-btn');
        btn.textContent = '✓ Copied!';
        setTimeout(() => {{ btn.textContent = '📋 Copy Spectrum'; }}, 1500);
      }});
    }}

    selectSpec(activeKey);
  </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def check_environment() -> Dict[str, Any]:
    """Verifies Python runtime version, required bundle files, and configuration."""
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 8)
    plugin_json_ok = (PLUGIN_ROOT / "plugin.json").exists()
    hooks_json_ok = (PLUGIN_ROOT / "hooks.json").exists()
    logo_ok = (PLUGIN_ROOT / "assets" / "logo.svg").exists()
    rules_ok = (PLUGIN_ROOT / "rules" / "AGENTS.md").exists()
    skills_ok = all(
        (PLUGIN_ROOT / "skills" / s / "SKILL.md").exists()
        for s in ("refract", "refract-check", "refract-mode")
    )
    all_ok = py_ok and plugin_json_ok and hooks_json_ok and logo_ok and rules_ok and skills_ok
    return {
        "status": "healthy" if all_ok else "error",
        "pythonVersion": py_ver,
        "pythonRequirementMet": py_ok,
        "requiredMinimumPython": "3.8.0",
        "externalPipDependencies": "None (Python standard library only)",
        "nodeJsRequiredForAntigravity": False,
        "nodeJsRequiredForVSCodePhase2": "Node.js >= 18.0.0 (only when building Phase 2 VS Code extension)",
        "bundleIntegrity": {
            "pluginJson": plugin_json_ok,
            "hooksJson": hooks_json_ok,
            "logoSvg": logo_ok,
            "rulesAgentsMd": rules_ok,
            "skills": skills_ok,
        },
        "pluginRoot": str(PLUGIN_ROOT),
        "config": load_config(),
    }


def run_hook_from_stdin() -> int:
    """Entrypoint when invoked by Antigravity's PreInvocation lifecycle hook."""
    raw_stdin = sys.stdin.read().strip()
    if not raw_stdin:
        print("{}")
        return 0

    try:
        hook_input = json.loads(raw_stdin)
    except Exception:
        print("{}")
        return 0

    workspace_paths = hook_input.get("workspacePaths") or []
    config = load_config(workspace_paths=workspace_paths)
    transcript_path = hook_input.get("transcriptPath")
    trajectory = parse_transcript(transcript_path, max_turns=int(config.get("maxTranscriptTurns", 12)))
    prompt_text = trajectory.get("latest_user_prompt", "")

    bypass, _ = should_bypass_hook(hook_input, prompt_text, config, trajectory)
    if bypass:
        print("{}")
        return 0

    evaluation = evaluate_prompt(prompt_text, trajectory)
    threshold = int(config.get("scoreThreshold", 72))
    rescue_spirals = bool(config.get("rescueFailureSpirals", True))

    needs_refraction = bool(evaluation["gaps"]) and (
        evaluation["overallScore"] < threshold
        or (rescue_spirals and evaluation["isFailureSpiral"])
        or bool(evaluation.get("architecturalFork"))
    )

    if not needs_refraction:
        print("{}")
        return 0

    spectrums = synthesize_spectrums(
        prompt_text,
        evaluation,
        trajectory,
        custom_rules=config.get("alwaysIncludeRules") or [],
    )
    ephemeral = build_ephemeral_injection(
        prompt_text=prompt_text,
        evaluation=evaluation,
        spectrums=spectrums,
        trajectory=trajectory,
        mode=str(config.get("mode", "auto-intercept")),
    )
    output = {
        "injectSteps": [
            {
                "ephemeralMessage": ephemeral,
            }
        ]
    }
    print(json.dumps(output))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Refract — Context & Prompt Trajectory Engine")
    parser.add_argument("--analyze", type=str, help="Analyze and refract a specific draft prompt string")
    parser.add_argument("--transcript", type=str, default="", help="Optional path to transcript.jsonl")
    parser.add_argument("--html-widget", type=str, default="", help="Optional output path for Generative UI HTML scorecard")
    parser.add_argument("--set-mode", choices=["auto-intercept", "coach", "slash-only"], help="Update Refract operating mode")
    parser.add_argument("--set-threshold", type=int, help="Update Refract score threshold (0-100)")
    parser.add_argument("--status", action="store_true", help="Print current Refract configuration and status")
    parser.add_argument("--doctor", action="store_true", help="Check system requirements and bundle integrity")

    args = parser.parse_args(argv)

    if args.doctor:
        report = check_environment()
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "healthy" else 1

    if args.set_mode or args.set_threshold is not None:
        updates: Dict[str, Any] = {}
        if args.set_mode:
            updates["mode"] = args.set_mode
        if args.set_threshold is not None:
            updates["scoreThreshold"] = max(0, min(100, args.set_threshold))
        cfg = save_config(updates)
        print(json.dumps({"status": "updated", "config": cfg}, indent=2))
        return 0

    if args.status:
        cfg = load_config()
        print(json.dumps({"plugin": "refract", "config": cfg}, indent=2))
        return 0

    if args.analyze is not None or args.html_widget:
        cfg = load_config()
        trajectory = parse_transcript(args.transcript or None, max_turns=int(cfg.get("maxTranscriptTurns", 12)))
        draft = args.analyze if args.analyze else trajectory.get("latest_user_prompt", "")
        if not draft:
            draft = "Refactor the current module and fix any failing cases"
        evaluation = evaluate_prompt(draft, trajectory)
        spectrums = synthesize_spectrums(
            draft,
            evaluation,
            trajectory,
            custom_rules=cfg.get("alwaysIncludeRules") or [],
        )

        result: Dict[str, Any] = {
            "draft": draft,
            "config": cfg,
            "trajectorySummary": {
                "turnCount": trajectory.get("turn_count", 0),
                "recentFiles": trajectory.get("recent_files", []),
                "recentCommands": trajectory.get("recent_commands", []),
                "recentErrors": trajectory.get("recent_errors", []),
                "activeErrors": trajectory.get("active_errors", []),
                "consecutiveErrors": trajectory.get("consecutive_errors", 0),
            },
            "evaluation": evaluation,
            "spectrums": spectrums,
        }

        if args.html_widget:
            widget_path = generate_html_scorecard(
                prompt_text=draft,
                evaluation=evaluation,
                spectrums=spectrums,
                trajectory=trajectory,
                output_path=Path(args.html_widget).expanduser(),
                mode=str(cfg.get("mode", "auto-intercept")),
            )
            result["htmlWidgetPath"] = str(widget_path)

        print(json.dumps(result, indent=2))
        return 0

    return run_hook_from_stdin()


if __name__ == "__main__":
    sys.exit(main())
