#!/usr/bin/env bash
set -euo pipefail

# 💠 Refract — 1-Command Installer & Pre-Flight Checker
# Usage:
#   ./install.sh                           -> Checks requirements & installs globally to ~/.gemini/config/plugins/refract
#   ./install.sh --workspace /path/to/repo -> Checks requirements & installs to /path/to/repo/.agents/plugins/refract
#   ./install.sh --check                   -> Runs pre-flight requirement check only (Antigravity / Python 3.8+)
#   ./install.sh --check-vscode            -> Runs pre-flight requirement check for Phase 2 VS Code extension (Node 18+, npm, Python 3.8+)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.gemini/config/plugins/refract"
MODE="install"

if [[ "${1:-}" == "--check" ]]; then
  MODE="check-only"
elif [[ "${1:-}" == "--check-vscode" ]]; then
  MODE="check-vscode"
elif [[ "${1:-}" == "--workspace" && -n "${2:-}" ]]; then
  TARGET_DIR="$2/.agents/plugins/refract"
fi

echo "💠 Refract — Pre-Flight System & Requirement Check"
echo "────────────────────────────────────────────────────────────"

MISSING_REQS=0

# 1. Check Python 3 (Required for Antigravity PreInvocation Hook & CLI Engine)
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ MISSING REQUIREMENT: 'python3' was not found in your PATH."
  echo "   Refract requires Python 3.8+ (standard library only, zero pip packages)."
  echo "   How to install Python 3:"
  echo "     • macOS:   xcode-select --install   OR   brew install python"
  echo "     • Ubuntu:  sudo apt update && sudo apt install -y python3"
  echo "     • Windows: winget install Python.Python.3.12"
  MISSING_REQS=1
else
  PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "❌ OUTDATED REQUIREMENT: Python ${PY_VERSION} detected, but Python 3.8+ is required."
    echo "   Please upgrade Python 3 (e.g., 'brew upgrade python' on macOS)."
    MISSING_REQS=1
  else
    echo "✅ Python 3 requirement met: Python ${PY_VERSION} (>= 3.8, zero pip packages needed)"
  fi
fi

# 2. Check Python Standard Library Modules
if [[ "${MISSING_REQS}" -eq 0 ]]; then
  if ! python3 -c 'import argparse, collections, html, json, os, pathlib, re, sys' >/dev/null 2>&1; then
    echo "❌ BROKEN PYTHON STDLIB: One or more standard library modules failed to import."
    MISSING_REQS=1
  else
    echo "✅ Python standard library modules verified"
  fi
fi

# 3. Check Git (Recommended for updates & workspace branch tracking)
if command -v git >/dev/null 2>&1; then
  GIT_VER="$(git --version | awk '{print $3}')"
  echo "✅ Git detected: v${GIT_VER}"
else
  echo "⚠️  OPTIONAL: 'git' not found in PATH (only needed for cloning/updating the repo)."
fi

# 4. Check Node.js & npm (ONLY required if --check-vscode is passed for Phase 2 VS Code Extension dev)
if [[ "${MODE}" == "check-vscode" ]]; then
  echo "────────────────────────────────────────────────────────────"
  echo "🔍 Checking Phase 2 VS Code Extension Build Requirements (Node.js 18+ & npm)..."
  if ! command -v node >/dev/null 2>&1; then
    echo "❌ MISSING REQUIREMENT (VS Code Extension): 'node' was not found in your PATH."
    echo "   Building the Phase 2 VS Code extension requires Node.js 18+ and npm."
    echo "   Install via: brew install node   OR   https://nodejs.org/"
    MISSING_REQS=1
  else
    NODE_VER="$(node -v)"
    NODE_MAJOR="$(node -e 'console.log(process.versions.node.split(".")[0])')"
    if [[ "${NODE_MAJOR}" -lt 18 ]]; then
      echo "❌ OUTDATED REQUIREMENT (VS Code Extension): Node ${NODE_VER} detected, but Node.js 18+ is required."
      MISSING_REQS=1
    else
      echo "✅ Node.js requirement met: ${NODE_VER} (>= v18)"
    fi
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "❌ MISSING REQUIREMENT (VS Code Extension): 'npm' was not found in your PATH."
    MISSING_REQS=1
  else
    NPM_VER="$(npm -v)"
    echo "✅ npm requirement met: v${NPM_VER}"
  fi
else
  echo "ℹ️  Note: Node.js / npm is NOT required for the Google Antigravity plugin."
fi

echo "────────────────────────────────────────────────────────────"

if [[ "${MISSING_REQS}" -ne 0 ]]; then
  echo "🛑 Pre-flight check failed. Please install the missing requirement(s) listed above and re-run ./install.sh."
  exit 1
fi

if [[ "${MODE}" == "check-only" || "${MODE}" == "check-vscode" ]]; then
  echo "✅ All checked requirements are satisfied!"
  exit 0
fi

# 5. Install Plugin Bundle
echo "💠 Installing Refract plugin to: ${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"

cp -R "${SCRIPT_DIR}/plugin.json" "${TARGET_DIR}/"
cp -R "${SCRIPT_DIR}/hooks.json" "${TARGET_DIR}/"
cp -R "${SCRIPT_DIR}/README.md" "${TARGET_DIR}/"
cp -R "${SCRIPT_DIR}/assets" "${TARGET_DIR}/"
cp -R "${SCRIPT_DIR}/rules" "${TARGET_DIR}/"
cp -R "${SCRIPT_DIR}/scripts" "${TARGET_DIR}/"
cp -R "${SCRIPT_DIR}/skills" "${TARGET_DIR}/"

# Preserve existing user config.json if already customized
if [[ ! -f "${TARGET_DIR}/config.json" ]]; then
  cp "${SCRIPT_DIR}/config.json" "${TARGET_DIR}/config.json"
fi

chmod +x "${TARGET_DIR}/scripts/refract_engine.py"

# 6. Post-Install Health Verification (--doctor)
if python3 "${TARGET_DIR}/scripts/refract_engine.py" --doctor >/dev/null 2>&1; then
  echo "✅ Post-install health check (--doctor) passed!"
else
  echo "⚠️  Warning: Post-install health check reported an issue. Run:"
  echo "   python3 ${TARGET_DIR}/scripts/refract_engine.py --doctor"
  exit 1
fi

echo "✅ Refract installed successfully!"
echo "   • Slash commands registered: /refract, /refract-check, /refract-mode"
echo "   • Lifecycle hook registered: PreInvocation (transcript-aware interceptor)"
echo "   • Next step: Restart Google Antigravity once if this is your first install."
