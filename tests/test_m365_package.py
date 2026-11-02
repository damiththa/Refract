#!/usr/bin/env python3
"""Unit tests for Microsoft 365 Copilot Declarative Agent packaging."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys_path_added = False
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))
    sys_path_added = True

from scripts import build_m365_package  # noqa: E402


class TestM365Package(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="refract_m365_test_")
        self.tmp_path = Path(self.tmp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_app_manifest_schema(self) -> None:
        manifest_path = PROJECT_ROOT / "appPackage" / "manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifestVersion"], "1.19")
        self.assertEqual(manifest["name"]["short"], "Refract")
        self.assertIn("copilotAgents", manifest)
        self.assertIn("declarativeAgents", manifest["copilotAgents"])
        self.assertEqual(len(manifest["copilotAgents"]["declarativeAgents"]), 1)
        self.assertEqual(
            manifest["copilotAgents"]["declarativeAgents"][0]["file"],
            "declarativeAgent.json",
        )

    def test_declarative_agent_schema(self) -> None:
        agent_path = PROJECT_ROOT / "appPackage" / "declarativeAgent.json"
        self.assertTrue(agent_path.exists())
        agent = json.loads(agent_path.read_text(encoding="utf-8"))
        self.assertEqual(agent["version"], "v1.6")
        self.assertEqual(agent["name"], "Refract")
        self.assertEqual(len(agent["conversation_starters"]), 3)
        cap_names = [c["name"] for c in agent["capabilities"]]
        self.assertIn("OneDriveAndSharePoint", cap_names)
        self.assertIn("GraphConnectors", cap_names)
        self.assertIn("WebSearch", cap_names)

    def test_icon_dimensions(self) -> None:
        color_path = PROJECT_ROOT / "appPackage" / "color.png"
        outline_path = PROJECT_ROOT / "appPackage" / "outline.png"
        build_m365_package.verify_png_dimensions(color_path, 192, 192, "color")
        build_m365_package.verify_png_dimensions(outline_path, 32, 32, "outline")

    def test_m365_zip_packaging_integrity(self) -> None:
        zip_path = build_m365_package.package_m365_agent(output_dir=self.tmp_path)
        self.assertTrue(zip_path.exists())
        self.assertEqual(zip_path.name, "refract-m365-copilot.zip")

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("declarativeAgent.json", names)
            self.assertIn("instructions.txt", names)
            self.assertIn("color.png", names)
            self.assertIn("outline.png", names)

    def test_instructions_content_and_rubric(self) -> None:
        instructions_path = PROJECT_ROOT / "appPackage" / "instructions.txt"
        self.assertTrue(instructions_path.exists())
        text = instructions_path.read_text(encoding="utf-8")
        self.assertIn("5-DIMENSION ENTERPRISE RUBRIC", text)
        self.assertIn("INTENT & DELIVERABLE SPECIFICITY", text)
        self.assertIn("DEICTIC CONTEXT GROUNDING", text)
        self.assertIn("FAILURE SPIRAL RESCUE", text)
        self.assertIn("Precision Spectrum", text)
        self.assertIn("Root-Cause / Diagnostic Spectrum", text)
        self.assertIn("Strict Executive Spec", text)
        self.assertGreater(len(text), 1000)

    def test_documentation_and_examples_exist(self) -> None:
        readme_path = PROJECT_ROOT / "README.md"
        examples_path = PROJECT_ROOT / "examples" / "ENTERPRISE_EXAMPLES.md"
        guide_path = PROJECT_ROOT / "docs" / "M365_SETUP_GUIDE.md"
        self.assertTrue(readme_path.exists())
        self.assertTrue(examples_path.exists())
        self.assertTrue(guide_path.exists())
        self.assertIn("Example 1", examples_path.read_text(encoding="utf-8"))
        self.assertIn("Method 1: Web Agent Builder", guide_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
