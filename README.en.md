# ECE329 VR Lab Design and Builder: from installation to your first experiment

[简体中文教程](README.md) · English

This tutorial follows a long-solenoid experiment. On first use, complete sections 1–3. For design and PDF export, go straight to [section 5](#start-design). To build the scene in Unity, first complete [Unity setup in section 4](#install-unity). If you already have a plan or want to resume a build, go to [section 7](#start-builder).

**Already set up?** Open a new agent chat in the same project to [start or resume a design](#start-design) or [build from an existing plan](#start-builder). When you want to upgrade, follow the [update steps in section 9](#update).

## 1. Download the project and open its folder

1. Choose one download method. For Git, open a terminal in the parent folder and run `git clone https://github.com/yzhao05/ece329-vr-lab-workflow.git`. For ZIP, open the [project repository](https://github.com/yzhao05/ece329-vr-lab-workflow) and choose **Code → Download ZIP**. On Windows, right-click the ZIP and select **Extract All**. On macOS, double-click it. If your instructor provided an extracted folder, open that folder.
2. Find the folder where you can see `README.md`, `emvr-lab-workflow`, `knowledge`, `web`, `unity-package`, and `reusable-code` together. This is the **repository root**. Keep those directories together.
3. **Windows:** in File Explorer, open that folder, type `powershell` in the address bar, and press Enter. **macOS:** open Terminal, type `cd ` with a trailing space, drag the folder into Terminal, and press Return. Use this window for the setup commands below.

**The first time you use the project, select this repository root as your agent’s workspace.** Section 3 shows where to select it in your desktop app. You can then open a new chat in the same project to start another experiment or resume an earlier one. To resume a design, give the agent its original `design_id`. When you hand a confirmed design to Builder, the agent creates or restores a dedicated build workspace for that experiment. At Gate 4, select the verified project entry (`unity_editor_project`) in Unity Hub.

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

3. Under `course`, look for the `formulas` list and the entry `long_solenoid_field`. You're ready to connect the desktop agent. The default engine uses your host agent without a separate model API key.

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

1. Sign in to the Codex desktop app. In the projects sidebar, create or open a local project and select the repository root you found in section 1. **This selects your Codex workspace.** If you already have a project, open its menu, choose **Edit project → Add folder**, and make that same folder the current working directory.
2. This client's project entry is `.agents/skills/emvr-lab-workflow/SKILL.md`. In the terminal you opened at the repository root in section 1, run the two lines for your operating system to open the entry file.

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

1. **Select the workspace for your Claude Code session.** Sign in to Claude Desktop, switch to **Code**, and start a session. Choose your computer under **Local** in the environment selector. In the adjacent folder picker, choose **Open folder…** and select the repository root you found in section 1. This folder is the session’s workspace. If offered worktree isolation, use the original folder so later sessions see the same experiment records.
2. This client's project entry is `.claude/skills/emvr-lab-workflow/SKILL.md`. In the terminal you opened at the repository root in section 1, run the two lines for your operating system to open the entry file.

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

1. **Select the workspace for Cursor Agent.** Open Cursor, choose **Open Folder**, and select the repository root you found in section 1. Sign in and start a local Agent chat in the window where you opened that folder.
2. This client's project entry is `.cursor/skills/emvr-lab-workflow/SKILL.md`. In the terminal you opened at the repository root in section 1, run the two lines for your operating system to open the entry file.

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

1. **Select the workspace GitHub Copilot will use.** In VS Code, choose **File → Open Folder…** and select the repository root you found in section 1. Copilot uses the workspace open in that window. In the same window, open Chat from the Copilot icon, sign in to GitHub when prompted, and choose an agent session with local file and terminal tools.
2. This client's project entry is `.github/skills/emvr-lab-workflow/SKILL.md`. In the terminal you opened at the repository root in section 1, run the two lines for your operating system to open the entry file.

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

<a id="install-unity"></a>

## 4. Set up Unity for Builder

For design, PDF export, or an existing browser 3D preview, skip to [section 5](#start-design). Builder uses the Unity Editor to compile the project at Gate 4.

### 4A. Install Unity Hub and the Editor

1. **Install Unity Hub.** Open the Unity download page, select your operating system and run the installer. Start the Hub and sign in with your Unity ID. If prompted for a license, open **Settings → Licenses** and activate the license you are entitled to use. [Download Unity Hub](https://unity.com/download)
2. **Install the project's Editor version.** The Builder project specifies **2022.3.62f3c1**, including the `c1` suffix. Check **Installs** in the Hub. If that exact version is already installed, continue to the next step. Otherwise, select **Install Editor** and look for it. If it is missing from the list on 64-bit Windows, download and run Unity's installer linked below. Then use **Installs → Locate** to select the installed `Editor\Unity.exe` and verify the full version in the list. [Project version](reusable-code/EMVR_Blind_BuilderPack/UnityProject/ProjectSettings/ProjectVersion.txt) · [Windows 64-bit Editor installer](https://download.unitychina.cn/download_unity/1623fc0bbb97/Windows64EditorInstaller/UnitySetup64-2022.3.62f3c1.exe)

### 4B. Set up the Hub language and C# editor

1. When you first open the Hub, select **Create account** to register your own Unity ID, or sign in with an existing account. To change the interface language, open **Settings → Appearance → Language** and choose your preferred language.
2. On Windows, install Visual Studio if you want to read, edit or debug C# scripts there. Open **Visual Studio Installer**, select **Install** (or **Modify** for an existing installation), select **Game development with Unity** under **Workloads**, and apply the change. [Microsoft installation guide](https://learn.microsoft.com/en-us/visualstudio/gamedev/unity/get-started/getting-started-with-visual-studio-tools-for-unity?pivots=windows)
3. With the project open in Unity, choose **Edit → Preferences → External Tools** and set **External Script Editor** to your Visual Studio installation. Double-click a C# script to check that it opens in Visual Studio.

### 4C. Set up VR plug-ins and the device simulator

The Builder workspace includes its XR settings. When using Builder, follow the agent's Gate 5A instructions to check the XR rig and simulator in the scene. Use the following manual setup for a Unity 2022.3 project you create yourself. [Builder Gate 5A procedure](reusable-code/EMVR_Blind_BuilderPack/README_USER.md#gate-5a通用基础验证)

1. Open **Edit → Project Settings → XR Plug-in Management**. Select **Install XR Plug-in Management** if prompted. Choose the tab for your target platform and enable **OpenXR**.
2. Under **XR Plug-in Management → OpenXR**, select **+** in **Interaction Profiles** and add the profile for the target device. The original tutorial uses **Microsoft Hand Interaction Profile** as an example. Choose the profile for the controllers or hand tracking you intend to use.
3. Open **Window → Package Manager** and find **XR Interaction Toolkit** in the **Unity Registry**. Select **2.6.5** to match the Builder project. On the package's **Samples** tab, click **Import** next to **Starter Assets** and **XR Device Simulator**. [Builder project dependencies](reusable-code/EMVR_Blind_BuilderPack/UnityProject/Packages/manifest.json)
4. To simulate a headset and controllers with a mouse and keyboard in your own project, enable **Use XR Device Simulator in scenes** under **Edit → Project Settings → XR Interaction Toolkit**. In a Builder scene where Gate 5A already places a simulator, leave automatic insertion off to avoid creating a second one.

### 4D. Import the Common package into your own Unity project (optional)

1. Builder-generated projects already reference Common. To reuse the components in **your own Unity 2022.3 project**, open that project through Unity Hub.
2. In the Unity Editor choose **Window → Package Manager**, then **+ → Add package from tarball…** at the top left. In the file picker, open this repository's `unity-package` directory and select [com.emvr.lab-common-0.7.0.tgz](unity-package/com.emvr.lab-common-0.7.0.tgz) directly.
3. Wait for dependency resolution and compilation. Under **Packages: In Project**, check for **EMVR Lab Common**, version **0.7.0**. If installation fails, check the dependency message in Package Manager and the first error in the Console. [Package details](unity-package/README.md)

<a id="start-design"></a>

## 5. Start or resume Design

1. In the project chat, select the skill and add this request to the same message:

   > I want to design an ECE329 VR experiment to see how current affects the magnetic field at the center of a long solenoid. Open the live progress page and ask me the first design question.

2. On first use, the app may ask to run Python in the project or open the local page. Check the project and allow the requested operation. Look for a `design_id`, a first question, and the progress page. If a browser tab doesn't open, click the local URL returned by the agent. The four panels show workflow progress, course evidence, design notes, and design checks. The viewer starts in English and has a Chinese language switch at the top right. **Answer questions in the agent chat.**
3. Try “Which lecture supports that formula?” Then ask “Revise the draft to measure only at the center and hold the number of turns and coil length fixed.” You can accept parts of the draft and revise others in one reply, for example, when discussing the current slider, “Keep the 2 A maximum and change the step size to 0.1 A.” The agent records those decisions together and asks about remaining choices. When the whole plan is ready, confirm it in section 6.
4. Keep the actual `design_id`. The next time you open the same local project, select the same skill and say “Continue design [paste my ID] from the last draft awaiting my confirmation.” Check that the ID and stage match. If several labs have similar names, choose the original one from the agent's suggestions.

See the [Design stages in section 10](#design-stages) for what to review at each stage.

<a id="export-design"></a>

## 6. Confirm the design and export it

1. At the end of the seven design stages, review the complete draft and say “I confirm the whole design. Please export it.” If the agent identifies a missing item, revise that item and confirm again.
2. Open the `artifacts` folder the agent returns. Look for `design.pdf` for you to read, `builder-gate1-input.pdf` for Builder to review, and `builder-gate1-input.json` for the structured handoff from the same version.
3. Exports follow the conversation language. To switch, say “Keep this design version and export another copy in Chinese.” Have the agent finish the translation and give you the resulting files. The viewer language switch controls the display.

<a id="start-builder"></a>

## 7. Start or resume Builder

1. **For the design you just finished**, say “Start building from the version I just confirmed and exported.” Check the design version, Builder workspace, and current gate reported by the agent.
2. **If you already have a plan**, attach your chosen plan to the project chat, identify the version, and say “Go directly to Builder using this attachment.” The agent reviews the requirements in that plan. If there are several versions, confirm which one to use.
3. **Resume a build.** In a chat in the same project, tell the agent, “Resume [lab_id] in the Builder workspace at [path].” Use the build workspace path the agent previously gave you for that experiment. Check the current gate and pending task. See the [Builder gates in section 10](#builder-gates) for the checks and approvals.

**If an attachment download fails with a DNS error**, and the plan came from this project, ask the agent to find the local handoff by design ID and revision. Give it the known `design_id`, revision and language, or the export folder you saved. Exports are under `handoffs/` in the state directory. Gate progress belongs to the Builder workspace. If you deleted that workspace, restore its backup to resume at the previous gate, or explicitly ask to start again at Gate 0 from the saved plan.

**Save the details you’ll need to resume the build.** When you first enter Builder from a confirmed design, ask the agent, “Please list my design ID (`design_id`), build ID (`lab_id`), and the full path to this Builder workspace so I can resume next time.” If you start directly from an attachment, you only need to save the build ID and the full Builder workspace path.

### Open the project and check compilation at Gate 4

1. **Open your experiment at Gate 4.** Once the agent reports that the scaffold is ready, choose **Projects → Add → Add project from disk** in the Hub. Select the `unity_editor_project` path the agent gives you. On Windows, select that short entry directly, even if the folder name looks like a string of random characters. Open the project with the Editor version installed in section 4. [Unity Hub project instructions](https://docs.unity.com/en-us/hub/projects-window-reference)
2. **Check compilation.** Stay in Edit mode and wait for asset import and automatic C# compilation to finish. Open **Window → General → Console**. If the red error count is zero, report that result to the agent to continue Gate 4 acceptance. If there are errors, send the agent the full text of the first red error. You can leave Play and Build unused for this check.

**Reopen the same project after restarting Windows.** When first setting up the project or migrating from the old Z: drive, save and close the old project. Run this command in PowerShell at the repository root. For a build created from Design, enter the build ID (`lab_id`) you saved above, for example `ece329_solenoid_current`. For a standalone Builder run, replace the example ID with the quoted full path of the Builder workspace containing `UnityProject`.

```powershell
.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/builder.py ece329_solenoid_current unity-project
```

Copy the printed path and select **Projects → Add → Add project from disk** in Unity Hub. After a restart, open that same Hub entry. This persistent directory junction points to the original project and preserves its scene and gate records. Its default location is in your user profile. If several runs share a lab ID, rerun the command with the intended workspace path from the list.

If entry creation fails, stay at the current gate. Run the command above in your own PowerShell at the repository root. If the default directory is unwritable, add `--entry-dir "SHORT_WRITABLE_LOCAL_DIRECTORY"` before the build ID or workspace path and reuse that directory. Save and close any project opened at the long path, then reopen it using the verified output.

### View the scene in the browser

Save the lab scene with visible models in Unity. You can then close the editor and click **Unity 3D** in the progress page. The browser loads the exported geometry locally. Left-drag to orbit, scroll to zoom, or right-drag to pan. Pick a model in the scene or select it from the list, then click **Focus object** for a closer look. **Fit scene** restores the overview. Click **Workflow details** to return.

The preview updates while the editor is open and shows the last saved version after it closes. It displays mesh geometry, base material colors and world transforms. Use Unity to inspect textures, custom shaders and VR interactions. New workspaces install the preview tools at Gate 4. If an older workspace needs them, ask the agent to install them at Gate 4 or before Gate 5A passes, then open and save the lab scene. Workspaces that have passed 5A retain the tools used for validation. The button stays disabled until the scene has exported geometry.

## 8. Manual operation and troubleshooting

1. **Skill missing from the picker?** Check that your app opened the root from step 1. In the project skills directory for your app, check the `emvr-lab-workflow/SKILL.md` entry, including both `---` delimiters around the name and description. Check for an accidental `.txt` extension, save, and start a fresh project chat. Restart the client if needed. To resume while checking discovery, you can explicitly ask it to “Read `emvr-lab-workflow/SKILL.md` from the repository root and continue design [my ID].”
2. **Missing module or knowledge files?** Rerun the knowledge query in step 2. If it succeeds, have the agent retry using the same `.venv` interpreter and the repository root as its working directory.
3. **Existing progress page won't open?** Ask the agent to reopen the same ID. To check manually from the root on Windows, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/viewer.py open DESIGN_ID`, substitute your actual ID, and open the returned `url`. Run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py show DESIGN_ID` to see the saved progress. On macOS use `.venv/bin/python` at the start of each command.
4. **Moved computers?** Copy the original state directory, normally `emvr-lab-workflow/state/` or, in older checkouts, `state/` at the repository root. It contains your design sessions and the Builder workspaces created from them. If you built directly from an attachment, also transfer that standalone Builder workspace. Restore any source and knowledge archives as described in [section 9B](#update-zip) and complete sections 2–3 on the new computer. To resume a design, provide its `design_id`. To resume a standalone build, provide its `lab_id` and the full path to the transferred workspace.
5. **Unity Hub no longer lists the project?** Ask the agent to locate the original workspace, then use the lab ID or workspace path for your type of run as described in [section 7](#start-builder).

### Troubleshoot Unity installation and project import

- **Hub downloads stay queued or fail validation.** Check which item failed in the Hub download list. If only a language pack failed, finish installing the Editor and add the language pack later. If the Editor download repeatedly fails on Windows, use the standalone installer in [section 4](#install-unity) and register it through **Installs → Locate**.
- **Unity reports `contains a locked Library`.** Close the Editor instance using that workspace, verify its process has exited, and retry from the Hub. If the project came from an archive and the lock persists, close the Editor, rename the project's `Library` directory to `Library.backup`, then reopen it and let Unity rebuild its import cache. Keep `Assets`, `Packages` and `ProjectSettings` in place.
- **Gate 5A reports a hash mismatch for the imported `XR Interaction Setup.prefab` after saving.** Save the scene and close the Unity project. After [updating the workflow](#update), give the agent the original Builder workspace path and `lab_id` in a chat in the same project. Ask it to “Restore the XR import and retest at Gate 5A.” The agent checks the import receipt, backs up recognized input-reference changes, and restores the approved copy. Reopen the project using the returned entry and retest mouse and XR ray input. Other differences require maintainer review.

<details>
<summary>Optional: run the same workflow manually</summary>

From the repository root on Windows, use the commands below one at a time. On macOS replace the interpreter at the start of each line with `.venv/bin/python`.

1. For a **new** experiment, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/viewer.py open --new`. Open the returned URL and copy its `viewer_session`.
2. Run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py create "Compare solenoid fields as current changes" --language en --viewer-session TOKEN` with that token. Save the returned `design_id`. For an existing design, run the `viewer.py open DESIGN_ID` and `workflow.py show DESIGN_ID` commands in troubleshooting item 3 above, using the original design ID in both.
3. Use that `design_id` in the agent chat to discuss and confirm the design. To submit a design turn manually, send the JSON for that turn to `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py turn DESIGN_ID --stdin-json` as described in the [agent input protocol](emvr-lab-workflow/references/agent-turns.md).
4. After the design is confirmed, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py export DESIGN_ID`. To build it, run `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py builder-init DESIGN_ID`. Substitute the actual design ID in both commands. Use the returned `artifacts` and `builder_workspace` locations.

</details>

<details>
<summary>Maintainers: run the regression suite</summary>

From the repository root, use the interpreter from step 2 to install `"./emvr-lab-workflow/design[test,harness]"` with `-m pip install`, then run `-m pytest -q`. Offline tests can use `ECE329_GENERATOR=rule` and `ECE329_TEST_HARNESS_RUNTIME=1`. With Playwright and Chromium installed, run `node emvr-lab-workflow/tests/viewer.cjs` to check the viewer.

</details>

<a id="update"></a>

## 9. Update an existing installation and resume your experiment

Note your current `design_id`. If you have started Builder, also note the `lab_id`, current gate, and the original Builder workspace’s full path. Let the agent finish its current action, then save and close the Unity Editor. Ask the agent to stop this project's local progress viewer before updating.

<a id="update-git"></a>

### 9A. Update a Git clone

1. Open a terminal in the original repository root and run these commands one at a time. The first should show this project's root, the second should point to the project repository, and the third shows your branch and local changes. [Project repository](https://github.com/yzhao05/ece329-vr-lab-workflow)

   ```sh
   git rev-parse --show-toplevel
   git remote get-url origin
   git status --short --branch
   ```

2. On `main`, pull the update in the same directory. If you edited tracked files, back up or commit your changes first. If you are on a personal branch, save your work and switch back to `main` before running these commands.

   ```sh
   git pull --ff-only origin main
   git log -1 --oneline
   ```

   After a successful pull, the second command shows your latest local commit. If Git says files would be overwritten or the branches have diverged, stop here and resolve that message while preserving your local work.

3. Keep your existing experiment directories and `.venv`, then [verify the update](#update-check).

<a id="update-zip"></a>

### 9B. Update a ZIP download or a folder from your instructor

1. Select `main` in the [project repository](https://github.com/yzhao05/ece329-vr-lab-workflow) and choose **Code → Download ZIP**, or get the updated ZIP from your instructor. Extract it into a separate temporary folder. Locate the directory that contains `README.md`, `emvr-lab-workflow`, and `web` together.
2. Close terminals and agent project windows using the old folder. From its parent directory, rename the old folder as a backup (for example, append `-backup`). Place the newly extracted project root at the **exact original path**. This keeps existing Builder workspace paths and Unity Hub project locations usable.
3. Copy **your local experiment data** from the backup to the same relative locations in the new installation. Copy the entire `emvr-lab-workflow/state/` directory, or restore `state/` at the project root if that was your previous location. If the backup contains `web/data/`, copy that directory too. It holds the published local progress snapshots and the pointer to your most recent experiment. If you created standalone runs under `reusable-code/EMVR_Blind_BuilderPack/RebuildWorkspaces/`, copy those run directories too. Continue using the original paths for external workspaces and custom state directories.
4. Merge any personal additions in `knowledge/newknowledge/`, `reusable-code/newcode/`, or other directories where you added material. Compare files with matching names before replacing them. Restore your local `.env` configuration if needed. In the new root, follow step 2 to create a fresh `.venv`, then step 3 to create the skill entry for your client. Keep your backup until you have verified your progress.

If your custom state directory, viewer data directory, or standalone Builder workspace was inside the old project folder, restore it from the backup at the same relative path.

<a id="update-check"></a>

### 9C. Verify the update and resume

1. For a Git clone, run the two lines for your operating system in the existing environment. If you just installed the engine and ran the knowledge query in step 2 for a ZIP update, go straight to the next item.

   **Windows · PowerShell**

   ```powershell
   .\.venv\Scripts\python.exe -m pip install ./emvr-lab-workflow/design
   .\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

   **macOS · Terminal**

   ```sh
   .venv/bin/python -m pip install ./emvr-lab-workflow/design
   .venv/bin/python emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

2. Once you see `long_solenoid_field` in the `formulas` list under `course`, open a fresh agent chat in the updated project, select the skill, and say “Resume experiment [original design_id], open its progress page, and tell me the current gate and pending task.” For standalone Builder, say “Resume [lab_id] in the original workspace at [full path].” Check that the ID, gate, and pending task match your previous session. On Windows, use the short path returned by the agent when you next open that workspace in Unity.

## 10. Design and Builder workflows

<a id="design-stages"></a>

### The seven Design stages

Discuss the draft in the agent chat and follow the current stage on the progress page. You can answer related questions together. For example, give the experiment a title, accept the suggested lab ID, and specify what students will measure in one reply.

1. **Refine the experiment idea.** Describe the phenomenon and what students should learn. Use the lecture references to agree on a research question, a model, and an expected trend.
2. **Define variables and conditions.** Decide what students can change, what they measure, and what stays fixed. For example, vary the current while keeping the probe at the center of the solenoid.
3. **Outline the experimental procedure.** Walk through the draft from the student's perspective, from entering the scene and adjusting controls to recording data and resetting the experiment.
4. **Plan the data display.** Choose readouts, units, and graphs. Specify when the readout updates and when a point is added to the plot.
5. **Interpret possible results.** Discuss the expected pattern, how students should explain it, and how to judge whether the experiment meets its acceptance criteria.
6. **Review value, feasibility, and limitations.** Explain what VR helps students observe, identify the model's assumptions, and review the proposed Unity implementation.
7. **Review the complete EMVR design.** Check that revisions carry through to the procedure, graphs, and acceptance criteria. Confirm the draft and export that version using [section 6](#export-design).

<a id="builder-gates"></a>

### The Builder gates in order

In this version, Builder runs Gates 0 through 6 and then goes directly to Gate 8. There is no separate Gate 7.

At each gate, check the current gate, verification results, and outstanding items reported by the agent. When you approve a gate, the agent records the result and identifies the next gate. Your next message can supply materials or ask a question for that gate. When a check requires Unity, use the project path supplied by the agent.

1. **Gate 0 · Verify the workspace.** Check the input plan and workspace and establish the baseline for protected files.
2. **Gate 1 · Confirm requirements.** Review the build brief and supply any missing course, manual, or grading details together.
3. **Gate 2 · Prepare interface contracts.** Check that the configuration describes the agreed parameters, interactions, data recording, and acceptance criteria.
4. **Gate 3 · Review the implementation design.** Review the planned scene, components, and tests against the experiment requirements.
5. **Gate 4 · Generate the project scaffold.** Open and refresh the project in Unity and report the compilation result from the Console.
6. **Gate 5 · Verify the foundation and experiment implementation.** In 5A, check the room, lighting, and basic interactions. In 5B, the agent implements the lab-specific model, controls, and measurements. Follow the requested tests.
7. **Gate 6 · Accept the Unity scene.** Try the experiment in Unity against the acceptance criteria and report the results. After acceptance, the agent archives the selected Gate 5B source files in `reusable-code/newcode/`. Before using those files in another project, check the [component dependencies](reusable-code/README.md).
8. **Gate 8 · Complete the handbooks.** In 8A, review this lab's student and developer handbooks. In 8B, review the new material in the project master handbook. When both are ready, follow the [final step](#knowledge-archive) to approve them and verify the knowledge archive.

<a id="knowledge-archive"></a>

## 11. Final step: verify the knowledge archive

1. After reviewing both parts of Gate 8, tell the agent, “I approve Gate 8 for this run. Please give me the archive path.”
2. The agent writes the retrospective when it records that approval. One Gate 8 approval covers both handbook acceptance and archiving. A linked run covers both Design and Builder. A standalone Builder run covers the build. The record should describe actual issues, what triggered them, how they were handled, what was verified, and any remaining limitations. If there were no known issues, the record should say so.
3. Open the Markdown file identified by `knowledge_update` and check the archived notes. Paths are relative to the repository root. Linked runs use `knowledge/newknowledge/<design_id>/<design-fingerprint>.md`. Standalone Builder runs use `knowledge/newknowledge/builder/<lab_id>/<acceptance-fingerprint>.md`. If the page shows “Accepted, retrospective pending”, ask the agent to resume the same workspace and retry archiving with the existing approval until it returns a file you can open.
4. **Upload the two folders prepared by the agent.** When approving the Gate 8 handbooks, you can add “Use Alex as my submission name.” The agent prepares `Alex_newcode` (source for this build) and `Alex_newknowledge` (this run’s knowledge updates) and returns both local paths. The build ID (`lab_id`) is the default name. Open the folders and send them to the maintainer directly or as two ZIP files. If the page shows “Accepted, upload folders pending”, ask the agent to retry the same handoff. It reuses your submission name and list of additional files. The page shows completion once both folders are ready.
