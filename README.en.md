# ECE329 VR Lab Design and Builder: from installation to your first experiment

[简体中文教程](README.md) · English

Follow one example from start to finish: how does current affect the magnetic field at the center of a long solenoid? You will set up the project, discuss the experiment with an agent, export the design, and optionally build it in Unity. Complete steps 1–3 once. On later visits, start at step 4. In step 3, follow only the instructions for your desktop app.

## 1. Download the project and open its folder

1. On the project's GitHub page choose **Code → Download ZIP**. On Windows, right-click the ZIP and select **Extract All**. On macOS, double-click it. If your instructor provided an extracted folder, open that folder.
2. Find the folder where you can see `README.md`, `emvr-lab-workflow`, `knowledge`, `web`, `unity-package`, and `reusable-code` together. This is the **repository root**. Keep those directories together.
3. **Windows:** in File Explorer, open that folder, type `powershell` in the address bar, and press Enter. **macOS:** open Terminal, type `cd ` with a trailing space, drag the folder into Terminal, and press Return. Use this window for the setup commands below.

## 2. Install Python and the design engine

1. On Windows, run `py --version`. On macOS, run `python3 --version`. If the command is missing or the version is earlier than **3.11**, install Python 3.11 or later from [Python downloads](https://www.python.org/downloads/), then reopen the terminal as in step 1. On Windows, if only `python --version` works and reports a supported version, use `python` in place of `py` on the first line below.
2. Run the **three lines for your operating system**, in order. They create a project environment, install the engine, and search the bundled course materials for “solenoid.” Your agent will use this same environment.

   **Windows · PowerShell**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install ./emvr-lab-workflow/design
   .\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

   **macOS · Terminal**

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install ./emvr-lab-workflow/design
   .venv/bin/python emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

3. Look for output containing `course` and `formulas`. You're ready to connect the desktop agent. The default engine uses your host agent without a separate model API key. You can finish step 5 before installing Unity.

## 3. Load the skill in your desktop agent (choose one)

Install and sign in to the desktop app you want to use, then follow its subsection below. Each app has a project skills directory. You will create a short **entry file** there that tells the agent to read the [full skill](emvr-lab-workflow/SKILL.md) from this checkout. This keeps the scripts, course materials, and viewer together and picks up workflow changes when you update the repository.

Desktop installers and setup · [Codex](https://developers.openai.com/codex/app/) · [Claude Desktop](https://claude.com/download) · [Cursor](https://cursor.com/download) · [VS Code](https://code.visualstudio.com/download)

**Entry file contents:** when your app's instructions below open an empty file, copy this entire block, starting with the first `---`, and save it as plain text named `SKILL.md`. If Notepad asks whether to create it, choose **Yes**. In **Save As**, choose **All files** and check the filename has no extra `.txt` extension. In macOS TextEdit, choose **Format → Make Plain Text** if the document is in rich-text mode. If the entry already exists, check that it points to this project.

```markdown
---
name: emvr-lab-workflow
description: Design, resume, export, or build an ECE329 electromagnetism VR lab in this local project.
---

Read the complete emvr-lab-workflow/SKILL.md in the open repository root and follow it.
Run its commands from that root using the project's .venv Python interpreter.
Resolve the procedures, scripts, and knowledge paths against the original repository.
```

### 3A. Codex

1. Sign in to the Codex desktop app. In the projects sidebar, create or open a local project and select the repository folder from step 1. If you already have a project, open its menu, choose **Edit project → Add folder**, and make that folder the current working directory. Use the local checkout.
2. This client's project entry is `.agents/skills/emvr-lab-workflow/SKILL.md`. In the terminal from step 1, run the two lines for your operating system to open the entry file.

   **Windows · PowerShell**

   ```powershell
   New-Item -ItemType Directory -Force .agents/skills/emvr-lab-workflow | Out-Null
   notepad ".\.agents\skills\emvr-lab-workflow\SKILL.md"
   ```

   **macOS · Terminal**

   ```sh
   mkdir -p .agents/skills/emvr-lab-workflow
   touch .agents/skills/emvr-lab-workflow/SKILL.md && open -e .agents/skills/emvr-lab-workflow/SKILL.md
   ```

3. Paste the entire “Entry file contents” block above into the empty file and save it. If your app shows **Skills** in the sidebar, open it to browse discovered skills. Start a fresh chat in this project, type `$emvr-lab-workflow` in the composer, and select the matching skill. [OpenAI · Local skill discovery](https://developers.openai.com/codex/skills) · [OpenAI · Local projects](https://learn.chatgpt.com/docs/projects)

### 3B. Claude Desktop

1. Sign in to Claude Desktop and switch to **Code**. Start a session, choose your computer under **Local** in the environment selector, then choose **Open folder…** in the adjacent folder picker. Select the repository root. If offered worktree isolation, use the original folder so later sessions see the same experiment records.
2. This client's project entry is `.claude/skills/emvr-lab-workflow/SKILL.md`. In the terminal from step 1, run the two lines for your operating system to open the entry file.

   **Windows · PowerShell**

   ```powershell
   New-Item -ItemType Directory -Force .claude/skills/emvr-lab-workflow | Out-Null
   notepad ".\.claude\skills\emvr-lab-workflow\SKILL.md"
   ```

   **macOS · Terminal**

   ```sh
   mkdir -p .claude/skills/emvr-lab-workflow
   touch .claude/skills/emvr-lab-workflow/SKILL.md && open -e .claude/skills/emvr-lab-workflow/SKILL.md
   ```

3. Paste the entire “Entry file contents” block above into the empty file and save it. Open a fresh local Code session. Type `/` in the composer or choose **+ → Slash commands**, then select `/emvr-lab-workflow`. [Anthropic · Desktop quickstart](https://code.claude.com/docs/en/desktop-quickstart) · [Anthropic · Skills](https://code.claude.com/docs/en/skills)

### 3C. Cursor

1. Open Cursor, choose **Open Folder**, and select the repository root. Sign in and open local Agent chat for that folder.
2. This client's project entry is `.cursor/skills/emvr-lab-workflow/SKILL.md`. In the terminal from step 1, run the two lines for your operating system to open the entry file.

   **Windows · PowerShell**

   ```powershell
   New-Item -ItemType Directory -Force .cursor/skills/emvr-lab-workflow | Out-Null
   notepad ".\.cursor\skills\emvr-lab-workflow\SKILL.md"
   ```

   **macOS · Terminal**

   ```sh
   mkdir -p .cursor/skills/emvr-lab-workflow
   touch .cursor/skills/emvr-lab-workflow/SKILL.md && open -e .cursor/skills/emvr-lab-workflow/SKILL.md
   ```

3. Paste the entire “Entry file contents” block above into the empty file and save it. Open **Customize → Skills** in the sidebar to check discovery. In Agent chat, type `/` and select `emvr-lab-workflow`. [Cursor · Agent Skills](https://cursor.com/docs/skills)

### 3D. VS Code + GitHub Copilot

1. In VS Code, choose **File → Open Folder…** and select the repository root. Open Chat from the Copilot icon, sign in to GitHub when prompted, and choose a Copilot agent session with local file and terminal tools.
2. This client's project entry is `.github/skills/emvr-lab-workflow/SKILL.md`. In the terminal from step 1, run the two lines for your operating system to open the entry file.

   **Windows · PowerShell**

   ```powershell
   New-Item -ItemType Directory -Force .github/skills/emvr-lab-workflow | Out-Null
   notepad ".\.github\skills\emvr-lab-workflow\SKILL.md"
   ```

   **macOS · Terminal**

   ```sh
   mkdir -p .github/skills/emvr-lab-workflow
   touch .github/skills/emvr-lab-workflow/SKILL.md && open -e .github/skills/emvr-lab-workflow/SKILL.md
   ```

3. Paste the entire “Entry file contents” block above into the empty file and save it. Press **Ctrl+Shift+P** (**⇧⌘P** on macOS), run **Chat: Open Customizations**, and choose **Skills** to inspect the workspace entry. Open a fresh Copilot chat, type `/emvr-lab-workflow`, and select the command. [VS Code · Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)

## 4. Start an experiment in chat, then resume it

1. In the project chat, select the skill and add this request to the same message:

   > I want to design an ECE329 VR experiment to see how current affects the magnetic field at the center of a long solenoid. Open the live progress page and ask me the first design question.

2. On first use, the app may ask to run Python in the project or open the local page. Check the project and allow the requested operation. Look for a `design_id`, a first question, and the progress page. If a browser tab doesn't open, click the local URL returned by the agent. The four panels show workflow progress, course evidence, design notes, and design checks. The viewer starts in English and has a Chinese language switch at the top right. **Answer questions in the agent chat.**
3. Try “Which lecture supports that formula?” Then ask “Revise the draft to measure only at the center and hold the number of turns and coil length fixed.” Review the updated draft and say “Confirm this stage” when it matches your intent. Watch the corresponding progress items change on the page.
4. Keep the actual `design_id`. The next time you open the same local project, select the same skill and say “Continue design [paste my ID] from the last draft awaiting my confirmation.” Check that the ID and stage match. If several labs have similar names, choose the original one from the agent's suggestions.

## 5. Confirm the design and export it

1. At the end of the seven design stages, review the complete draft and say “I confirm the whole design. Please export it.” If the agent identifies a missing item, revise that item and confirm again.
2. Open the `artifacts` folder the agent returns. Look for `design.pdf` for you to read, `builder-gate1-input.pdf` for Builder to review, and `builder-gate1-input.json` for the structured handoff from the same version.
3. Exports follow the conversation language. To switch, say “Keep this design version and export another copy in Chinese.” Have the agent finish the translation and give you the resulting files. The viewer language switch controls the display.

## 6. Hand the plan to Builder

1. **For the design you just finished**, say “Start building from the version I just confirmed and exported.” Check the design version, Builder workspace, and current gate reported by the agent.
2. **If you already have a plan**, you can come straight here after step 3. Attach your chosen plan to the project chat, identify the version, and say “Go directly to Builder using this attachment.” The agent reviews the requirements in that plan. If there are several versions, confirm which one to use.
3. At each gate, review the evidence and anything awaiting your decision. Request a specific change or confirm the result. When asked to inspect the scene, use Unity Hub to open `UnityProject` in the run workspace identified by the agent and follow that gate's instructions. After Gate 6 scene acceptance, the agent archives the selected Gate 5B code. After both Gate 8 handbooks are approved for a linked design, it records problems and fixes in the [knowledge updates directory](knowledge/newknowledge/).

## 7. Import the Common package into your own Unity project (optional)

1. Builder-generated projects already reference Common. To reuse the components in **your own Unity 2022.3 project**, open that project through Unity Hub.
2. In the Unity Editor choose **Window → Package Manager**, then **+ → Add package from tarball…** at the top left. In the file picker, open this repository's `unity-package` directory and select [com.emvr.lab-common-0.7.0.tgz](unity-package/com.emvr.lab-common-0.7.0.tgz) directly.
3. Wait for dependency resolution and compilation. Under **Packages: In Project**, check for **EMVR Lab Common**, version **0.7.0**. If installation fails, check the dependency message in Package Manager and the first error in the Console. [Package details](unity-package/README.md)

## 8. Recover a missing skill, page, or session

1. **Skill missing from the picker?** Check that your app opened the root from step 1. In the project skills directory for your app, check the `emvr-lab-workflow/SKILL.md` entry, including both `---` delimiters around the name and description. Check for an accidental `.txt` extension, save, and start a fresh project chat. Restart the client if needed. To resume while checking discovery, you can explicitly ask it to “Read `emvr-lab-workflow/SKILL.md` from the repository root and continue design [my ID].”
2. **Missing module or knowledge files?** Rerun the knowledge query in step 2. If it succeeds, have the agent retry using the same `.venv` interpreter and the repository root as its working directory.
3. **Existing progress page won't open?** Ask the agent to reopen the same ID. To check manually from the root on Windows, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/viewer.py open DESIGN_ID`, substitute your actual ID, and open the returned `url`. Run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py show DESIGN_ID` to see the saved progress. On macOS use `.venv/bin/python` at the start of each command.
4. **Moved computers?** Sessions, handoff files, and Builder workspaces are normally in `emvr-lab-workflow/state/`. Older checkouts may use `state/` at the repository root. Transfer the original state directory, repeat steps 2–3 on the new machine, and resume using your original ID.

<details>
<summary>Optional: run the same workflow manually</summary>

From the repository root on Windows, use the commands below one at a time. On macOS replace the interpreter at the start of each line with `.venv/bin/python`.

1. For a **new** experiment, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/viewer.py open --new`. Open the returned URL and copy its `viewer_session`.
2. Run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py create "Compare solenoid fields as current changes" --language en --viewer-session TOKEN` with that token. Save the returned `design_id`. For an existing experiment, use step 8 to reopen its ID.
3. After the design is confirmed, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py export DESIGN_ID`. To build it, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py builder-init DESIGN_ID`. Substitute the actual ID in both commands. Use the returned `artifacts` and `builder_workspace` locations.

</details>

<details>
<summary>Maintainers: run the regression suite</summary>

From the repository root, use the interpreter from step 2 to install `"./emvr-lab-workflow/design[test,harness]"` with `-m pip install`, then run `-m pytest -q`. Offline tests can use `ECE329_GENERATOR=rule` and `ECE329_TEST_HARNESS_RUNTIME=1`. With Playwright and Chromium installed, run `node emvr-lab-workflow/tests/viewer.cjs` to check the viewer.

</details>
