#!/usr/bin/env python3
"""Zero-dependency Microsoft 365 Copilot Declarative Agent Packager & Validator.

Generates a standards-compliant Microsoft 365 App package zip archive
(`refract-m365-copilot.zip`) ready for direct upload/sideloading into
Microsoft Teams, Microsoft 365 Copilot, or the Microsoft 365 Admin Center.
Uses only the Python 3.8+ standard library (zipfile, json, struct, pathlib).
"""

from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
from typing import Dict, List, Tuple
import zipfile


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_PKG_DIR = ROOT_DIR / "appPackage"


def verify_png_dimensions(png_path: Path, expected_w: int, expected_h: int, label: str) -> None:
    if not png_path.exists():
        raise FileNotFoundError(f"Missing required M365 {label} icon: {png_path}")
    data = png_path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG signature in {png_path}")
    width, height = struct.unpack(">II", data[16:24])
    if width != expected_w or height != expected_h:
        raise ValueError(
            f"M365 {label} icon must be exactly {expected_w}x{expected_h} (got {width}x{height})"
        )


def validate_manifests() -> Tuple[Dict, Dict]:
    manifest_path = APP_PKG_DIR / "manifest.json"
    agent_path = APP_PKG_DIR / "declarativeAgent.json"
    instructions_path = APP_PKG_DIR / "instructions.txt"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing appPackage/manifest.json at {manifest_path}")
    if not agent_path.exists():
        raise FileNotFoundError(f"Missing appPackage/declarativeAgent.json at {agent_path}")
    if not instructions_path.exists():
        raise FileNotFoundError(f"Missing appPackage/instructions.txt at {instructions_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    agent = json.loads(agent_path.read_text(encoding="utf-8"))

    # Validate M365 App Manifest
    for field in ("manifestVersion", "version", "id", "developer", "icons", "name", "description", "copilotAgents"):
        if field not in manifest:
            raise ValueError(f"appPackage/manifest.json missing required field: '{field}'")

    # Validate Declarative Agent Manifest
    for field in ("version", "name", "description", "instructions", "conversation_starters", "capabilities"):
        if field not in agent:
            raise ValueError(f"appPackage/declarativeAgent.json missing required field: '{field}'")

    # Validate Icons
    verify_png_dimensions(APP_PKG_DIR / "color.png", 192, 192, "color")
    verify_png_dimensions(APP_PKG_DIR / "outline.png", 32, 32, "outline")

    return manifest, agent


def package_m365_agent(output_dir: Path = ROOT_DIR) -> Path:
    manifest, agent = validate_manifests()

    zip_filename = "refract-m365-copilot.zip"
    zip_path = output_dir / zip_filename

    files_to_bundle: List[Tuple[Path, str]] = [
        (APP_PKG_DIR / "manifest.json", "manifest.json"),
        (APP_PKG_DIR / "declarativeAgent.json", "declarativeAgent.json"),
        (APP_PKG_DIR / "instructions.txt", "instructions.txt"),
        (APP_PKG_DIR / "color.png", "color.png"),
        (APP_PKG_DIR / "outline.png", "outline.png"),
    ]

    for src_path, _ in files_to_bundle:
        if not src_path.exists():
            raise FileNotFoundError(f"Required package file missing: {src_path}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src_path, arc_name in files_to_bundle:
            zf.write(src_path, arcname=arc_name)

    print("💠 Refract — Microsoft 365 Copilot Declarative Agent Packager")
    print("────────────────────────────────────────────────────────────")
    print(f"✅ App Manifest: {manifest['name']['full']} v{manifest['version']}")
    print(f"✅ Declarative Agent: {agent['name']} (version {agent['version']})")
    print("✅ Icons verified: color.png (192x192) & outline.png (32x32)")
    print(f"✅ Conversation Starters: {len(agent['conversation_starters'])} configured")
    print(f"✅ Capabilities: {', '.join(c['name'] for c in agent['capabilities'])}")
    print(f"✅ Packaged zip: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    print("────────────────────────────────────────────────────────────")
    print("👉 Ready to upload: Microsoft Teams -> Apps -> Manage your apps -> Upload a customized app")
    print("   Or deploy tenant-wide: admin.microsoft.com -> Settings -> Integrated apps")
    print("────────────────────────────────────────────────────────────")
    return zip_path


if __name__ == "__main__":
    try:
        package_m365_agent()
    except Exception as exc:
        print(f"❌ M365 Agent packaging failed: {exc}", file=sys.stderr)
        sys.exit(1)
