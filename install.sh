#!/usr/bin/env bash
set -euo pipefail

# Refract — 1-Command Installer for Google Antigravity
# Usage:
#   ./install.sh              -> Installs globally to ~/.gemini/config/plugins/refract
#   ./install.sh --workspace /path/to/repo -> Installs to /path/to/repo/.agents/plugins/refract

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.gemini/config/plugins/refract"

if [[ "${1:-}" == "--workspace" && -n "${2:-}" ]]; then
  TARGET_DIR="$2/.agents/plugins/refract"
fi

echo "💎 Installing Refract plugin to: ${TARGET_DIR}"
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

echo "✅ Refract installed successfully!"
echo "   • Slash commands registered: /refract, /refract-check, /refract-mode"
echo "   • Lifecycle hook registered: PreInvocation (transcript-aware interceptor)"
