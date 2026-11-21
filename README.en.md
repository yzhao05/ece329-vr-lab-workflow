# ECE329 VR Lab Design and Builder: from installation to your first experiment

[简体中文教程](README.md) · English

Already installed? Go to [update a Git clone](#update-git) or [update a ZIP download](#update-zip).

You can design an experiment, export PDFs and view an already exported 3D scene in the browser without installing Unity. To build the experiment, you will need the Unity Editor at Builder Gate 4 to compile the C# scripts. For your first build, see [install Unity and check compilation](#install-unity).

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

Save the lab scene with visible models in Unity. You can then close the editor and click **Unity 3D** in the progress page. The browser loads the exported geometry locally. Left-drag to orbit, scroll to zoom, or right-drag to pan. Pick a model in the scene or select it from the list, then click **Focus object** for a closer look. **Fit scene** restores the overview. Click **Workflow details** to return.

The preview updates while the editor is open and shows the last saved version after it closes. It displays mesh geometry, base material colors and world transforms. Use Unity to inspect textures, custom shaders and VR interactions. When upgrading an older workspace, ask the agent to run the `unity-project` command below for that workspace, then open and save the lab scene once in Unity. The button stays disabled until the scene has exported geometry.

On Windows, open the short project path returned by the agent in Unity Hub (for example `Z:\UnityProject`). To resume an existing run, ask the agent to run `builder.py "PACK" unity-project` for the original Builder workspace and continue with the same lab ID. The original workspace holds the gate records.

1. **For the design you just finished**, say “Start building from the version I just confirmed and exported.” Check the design version, Builder workspace, and current gate reported by the agent.
2. **If you already have a plan**, you can come straight here after step 3. Attach your chosen plan to the project chat, identify the version, and say “Go directly to Builder using this attachment.” The agent reviews the requirements in that plan. If there are several versions, confirm which one to use.
3. At each gate, review the evidence and anything awaiting your decision. Request a specific change or confirm the result. When asked to inspect the scene, use Unity Hub to open `UnityProject` in the run workspace identified by the agent and follow that gate's instructions. After Gate 6 scene acceptance, the agent archives the selected Gate 5B code. After the student manual, single-lab developer handbook and project handbook update receive joint Gate 8 approval for a linked design, it records problems and fixes in the [knowledge updates directory](knowledge/newknowledge/).

<a id="install-unity"></a>

### First build: install Unity and check compilation

1. **Install Unity Hub.** Open the Unity download page, select your operating system and run the installer. Start the Hub and sign in with your Unity ID. If prompted for a license, open **Settings → Licenses** and activate the license you are entitled to use. [Download Unity Hub](https://unity.com/download)
2. **Install the project's Editor version.** The Builder project specifies **2022.3.62f3c1**, including the `c1` suffix. Check **Installs** in the Hub. If that exact version is already installed, continue to the next step. Otherwise, select **Install Editor** and look for it. If it is missing from the list on 64-bit Windows, download and run Unity's installer linked below. Then use **Installs → Locate** to select the installed `Editor\Unity.exe` and verify the full version in the list. [Project version](reusable-code/EMVR_Blind_BuilderPack/UnityProject/ProjectSettings/ProjectVersion.txt) · [Windows 64-bit Editor installer](https://download.unitychina.cn/download_unity/1623fc0bbb97/Windows64EditorInstaller/UnitySetup64-2022.3.62f3c1.exe)
3. **Open your experiment at Gate 4.** Once the agent reports that the scaffold is ready, choose **Projects → Add → Add project from disk** in the Hub. Select the `UnityProject` folder the agent gave you for this run. On Windows, use the short path it provides, such as `Z:\UnityProject`. Open the project with the Editor version above. [Unity Hub project instructions](https://docs.unity.com/en-us/hub/projects-window-reference)
4. **Check compilation.** Stay in Edit mode and wait for asset import and automatic C# compilation to finish. Open **Window → General → Console**. If the red error count is zero, report that result to the agent to continue Gate 4 acceptance. If there are errors, send the agent the full text of the first red error. You can leave Play and Build unused for this check.

### Set up the Hub language and C# editor

1. When you first open the Hub, select **Create account** to register your own Unity ID, or sign in with an existing account. To change the interface language, open **Settings → Appearance → Language** and choose your preferred language.
2. On Windows, install Visual Studio if you want to read, edit or debug C# scripts there. Open **Visual Studio Installer**, select **Install** (or **Modify** for an existing installation), select **Game development with Unity** under **Workloads**, and apply the change. [Microsoft installation guide](https://learn.microsoft.com/en-us/visualstudio/gamedev/unity/get-started/getting-started-with-visual-studio-tools-for-unity?pivots=windows)
3. With the project open in Unity, choose **Edit → Preferences → External Tools** and set **External Script Editor** to your Visual Studio installation. Double-click a C# script to check that it opens in Visual Studio.

### Set up VR plug-ins and the device simulator

The Builder workspace includes its XR settings. When using Builder, follow the agent's Gate 5A instructions to check the XR rig and simulator in the scene. Use the following manual setup for a Unity 2022.3 project you create yourself. [Builder Gate 5A procedure](reusable-code/EMVR_Blind_BuilderPack/README_USER.md)

1. Open **Edit → Project Settings → XR Plug-in Management**. Select **Install XR Plug-in Management** if prompted. Choose the tab for your target platform and enable **OpenXR**.
2. Under **XR Plug-in Management → OpenXR**, select **+** in **Interaction Profiles** and add the profile for the target device. The original tutorial uses **Microsoft Hand Interaction Profile** as an example. Choose the profile for the controllers or hand tracking you intend to use.
3. Open **Window → Package Manager** and find **XR Interaction Toolkit** in the **Unity Registry**. Select **2.6.5** to match the Builder project. On the package's **Samples** tab, click **Import** next to **Starter Assets** and **XR Device Simulator**. [Builder project dependencies](reusable-code/EMVR_Blind_BuilderPack/UnityProject/Packages/manifest.json)
4. To simulate a headset and controllers with a mouse and keyboard in your own project, enable **Use XR Device Simulator in scenes** under **Edit → Project Settings → XR Interaction Toolkit**. In a Builder scene where Gate 5A already places a simulator, leave automatic insertion off to avoid creating a second one.

### Troubleshoot Unity installation and project import

- **Hub downloads stay queued or fail validation.** Check which item failed in the Hub download list. If only a language pack failed, finish installing the Editor and add the language pack later. If the Editor download repeatedly fails on Windows, use the standalone installer above and register it through **Installs → Locate**.
- **Unity reports `contains a locked Library`.** Close the Editor instance using that workspace, verify its process has exited, and retry from the Hub. If the project came from an archive and the lock persists, close the Editor, rename the project's `Library` directory to `Library.backup`, then reopen it and let Unity rebuild its import cache. Keep `Assets`, `Packages` and `ProjectSettings` in place.

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
3. Copy **your local experiment data** from the backup to the same relative locations in the new installation. Copy the entire `emvr-lab-workflow/state/` directory, or restore `state/` at the project root if that was your previous location. If you created standalone runs under `reusable-code/EMVR_Blind_BuilderPack/RebuildWorkspaces/`, copy those run directories too. Continue using the original paths for external workspaces and custom state directories.
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

2. Once the query returns `course` and `formulas`, open a fresh agent chat in the updated project, select the skill, and say “Resume experiment [original design_id], open its progress page, and tell me the current gate and pending task.” For standalone Builder, say “Resume [lab_id] in the original workspace at [full path].” Check that the ID, gate, and pending task match your previous session. On Windows, use the short path returned by the agent when you next open that workspace in Unity.
