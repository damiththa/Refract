<div align="center">
  <img src="https://raw.githubusercontent.com/damiththa/Refract/vscode-extension/assets/logo.png" alt="Refract Logo" width="100" height="100" />
  <h1>💠 Refract for Microsoft 365 Copilot</h1>
  <p><strong>Stop Copilot from guessing blindly. Ground your prompts in your files, emails, and meetings in &lt;2ms.</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/Platform-Microsoft_365_Copilot-0078D4?style=flat-square" alt="Platform" />
    <img src="https://img.shields.io/badge/Type-Declarative_Agent_(v1.6)-2563EB?style=flat-square" alt="Type" />
    <img src="https://img.shields.io/badge/Manifest-Teams_App_v1.19-10B981?style=flat-square" alt="Manifest" />
    <img src="https://img.shields.io/badge/Cloud_Hosting-%240_(Zero)-8B5CF6?style=flat-square" alt="Zero Hosting" />
    <img src="https://img.shields.io/badge/License-MIT-gray?style=flat-square" alt="License" />
  </p>
</div>

---

## 🎯 Why Refract for Microsoft 365 Copilot?

When business users ask Microsoft 365 Copilot:
* *"Draft an update email to the executive team on our project status"*
* *"Summarize that deck John shared last week"*
* *"Why did Copilot hallucinate these numbers?"*

Standard Copilot frequently stumbles over **diffuse enterprise context**:
* It doesn't know *which* of the 14 project files you mean.
* It conflates internal confidential drafts with external client summaries.
* When you reply *"that's not what I asked, make it more detailed"*, Copilot apologizes and enters a **hallucination failure loop**.

**Refract fixes this before your prompt executes.**

Refract evaluates your draft prompt across the **5-Dimension Enterprise Trajectory Rubric**, automatically grounding ambiguous pronouns (*"this doc"*, *"that meeting"*) into specific Microsoft Graph entities (SharePoint, OneDrive, Outlook, Teams) and synthesizing **3 focused execution spectrums**.

---

## ⚡ The Difference in Microsoft 365 (Before vs. After)

| When You Type... | Standard Copilot ❌ | With Refract 💠 |
| :--- | :--- | :--- |
| **`"Draft a project update email to leadership"`** | Writes generic corporate fluff without mentioning your milestones, metrics, or blockers. | **⚡ Precision Spectrum**: Formats a 3-bullet executive update, prompts you for specific KPIs, and links to your active SharePoint project folder. |
| **`"Summarize that presentation from yesterday"`** | Pulls the wrong deck or hallucinates slides from a 3-month-old file. | **Deictic Grounding**: Queries Microsoft Graph for meetings and files shared in the last 24 hours, confirming the exact deck before summarizing. |
| **`"Still wrong, try again"`** *(Turn 3)* | **Failure Loop**: Repeats the same incorrect text and wastes your meeting prep time. | **🔬 Root-Cause Rescue**: Halts blind retries, identifies why Copilot failed (e.g. missing SharePoint read permissions or ambiguous date scope), and fixes the query. |
| **`"Prepare board meeting notes"`** | Mixes internal draft speculation with official corporate records. | **🛡️ Strict Executive Spec**: Enforces formal tone, executive summary first, bulleted decisions, and mandatory source citations. |

---

## 💠 The 3 Enterprise Spectrums

Whenever Refract enhances a prompt, it synthesizes 3 tailored execution spectrums:

* ⚡ **Precision Spectrum (Context-Grounded — Default)**
  * *Best for*: Everyday emails, status reports, and fast document drafting.
  * *What it does*: Bounds your request to specific SharePoint files and date ranges with clear bulleted takeaways and zero generic fluff.

* 🔬 **Root-Cause / Diagnostic Spectrum (Hypothesis-First)**
  * *Best for*: Breaking out of Copilot hallucination loops or fixing missing data.
  * *What it does*: Halts blind retries. States the top 2 diagnostic hypotheses (missing file access, ambiguous dates, or prompt conflict) and isolates the data source before generating content.

* 🛡️ **Strict Executive Spec (Guardrailed + Cited)**
  * *Best for*: Board memos, client proposals, policy documents, and compliance reviews.
  * *What it does*: Enforces formal executive tone, mandatory source citations, confidentiality flags, and a strict verification checklist.

---

## 🚀 How to Install & Use (2 Quick Options)

You have two frictionless ways to run Refract inside your Microsoft 365 Copilot:

### Option 1: Zero-Code Setup via M365 Copilot Agent Builder (3 Minutes)

If you are using the web interface in Microsoft 365 Copilot:

1. Open **Microsoft 365 Copilot** and click **+ Create an agent** (or open the Agent Builder).
2. **Name**: `Refract`
3. **Description**: `AI Context & Prompt Trajectory Engine. Grounds diffuse prompts in your files, emails, and meetings into 3 focused execution spectrums.`
4. **Instructions**: Paste the contents of [`appPackage/instructions.txt`](appPackage/instructions.txt).
5. **Work Content**: Toggle **ON** Cloud files (SharePoint/OneDrive), Outlook, Teams, and Web search.
6. **Suggested Prompts**:
   * *`⚡ Refract Draft Prompt`*: `Refract this draft prompt into 3 execution spectrums: "Draft a project status update email to leadership based on our recent work"`
   * *`🔬 Rescue Failure Loop`*: `Copilot gave me a vague, hallucinated response when I asked for last week's sales figures. Diagnose why it failed and fix the query.`
   * *`🛡️ Strict Executive Spec`*: `Turn this thought into a strict, citation-backed executive memo prompt: "Summarize the key decisions from yesterday's team meeting"`
7. Click **Create**!

---

### Option 2: 1-Click Package Sideloading (`refract-m365-copilot.zip`)

If you want the ready-to-use, version-controlled package:

1. Download the pre-built [`refract-m365-copilot.zip`](refract-m365-copilot.zip) from this repository.
2. In **Microsoft Teams**:
   * Click **Apps** in the left sidebar → **Manage your apps** (bottom-left) → **Upload an app** → **Upload a customized app**.
   * Select `refract-m365-copilot.zip`.
3. Refract is immediately installed in your personal Copilot environment!
4. *(Optional Tenant Deployment)*: A tenant administrator can upload `refract-m365-copilot.zip` in **[Microsoft 365 Admin Center](https://admin.microsoft.com)** under **Settings** → **Integrated apps** to deploy Refract company-wide.

---

## 💬 How Invocation Works

* **In Dedicated Agent Chat**: Click **Refract** in your Copilot right-hand rail. **Every message is automatically processed by Refract** without typing `@Refract` each time.
* **In General Copilot Chat**: Type **`@Refract <your prompt>`** in any Microsoft 365 Copilot Chat (BizChat) or Teams channel.
* **In Word / PowerPoint / Outlook**: Copy the generated ⚡ **Precision Spectrum** prompt directly into in-app Copilot to generate flawless first-turn documents and decks.

---

## 🛠️ Developer: Packaging from Source

Refract uses a zero-dependency Python packager (no npm or Azure CLI required):

```bash
# Package the Microsoft 365 Declarative Agent zip
python3 scripts/build_m365_package.py

# Run automated validation tests
python3 -m unittest discover -s tests -v
```

---

## 🌿 Repository Branch Structure

| Branch | Target Platform | Status |
| :--- | :--- | :--- |
| **`main`** | Primary release branch & cross-platform documentation | ✅ Active |
| **`antigravity-extension`** | **Google Antigravity Native Plugin** (`plugin.json`, `hooks.json`, `skills/`, `rules/`) | ✅ Ready |
| **`vscode-extension`** | **VS Code Marketplace Extension** (`MDMS.refract` v1.0.1) | ✅ Live on Marketplace |
| **`m365-copilot`** | **Microsoft 365 Copilot Declarative Agent** (`appPackage/`, `manifest.json`) | ✅ Ready (v1.0.0) |

---

## 📄 License
MIT
