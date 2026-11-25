# ECE329 VR 实验设计与构建：从安装到第一次实验

简体中文 · [English tutorial](README.en.md)

以长螺线管实验为例，首次使用先完成第 1～3 节。只做设计或导出 PDF，可直接到[第 5 节开始设计](#start-design)。要在 Unity 中搭建实验，请先完成[第 4 节的 Unity 配置](#install-unity)。已有方案或要继续搭建，见[第 7 节](#start-builder)。

**环境已配置好？** 在原项目中新开 Agent 聊天，[开始或继续设计](#start-design)，或[从已有方案开始搭建](#start-builder)。需要升级版本时，再看[第 9 节的更新步骤](#update)。

## 1. 下载项目，打开正确的文件夹

1. 选择一种下载方式。使用 Git 时，在要存放项目的父文件夹打开终端，运行 `git clone https://github.com/yzhao05/ece329-vr-lab-workflow.git`。使用 ZIP 时，在[项目仓库](https://github.com/yzhao05/ece329-vr-lab-workflow)点 **Code → Download ZIP**。Windows 下右键 ZIP 并选“全部解压”；macOS 下双击解压。如果老师已经发了完整文件夹，直接打开它。
2. 进入能同时看到 `README.md`、`emvr-lab-workflow`、`knowledge`、`web`、`unity-package` 和 `reusable-code` 的那一层。这就是下面说的**仓库根目录**。请保留这些文件夹的相对位置。
3. **Windows**：在这个文件夹的资源管理器地址栏输入 `powershell` 并按回车。**macOS**：打开“终端”，输入 `cd `（末尾留一个空格），把这个文件夹拖入终端，再按回车。后面的安装命令都在这个窗口运行。

**第一次使用时，在 Agent 中把这个项目根目录选为工作区。** 第 3 节会带你在所用的桌面端选中它。以后开始新实验或继续旧实验，都可以在同一项目下新开聊天。要接着做上次的设计，告诉 Agent 原来的 `design_id`。把已确认的设计交给 Builder 时，Agent 会为这次实验创建或恢复专属的构建工作区。到 Gate 4，在 Unity Hub 中选择 Agent 验证过的工程入口（`unity_editor_project`）。

## 2. 安装 Python 和设计引擎

1. Windows 在终端运行 `py --version`，macOS 运行 `python3 --version`。如果找不到命令，或显示的版本低于 **3.11**，从 [Python 官方下载页](https://www.python.org/downloads/) 安装适用于本机的 Python 3.11 或更高版本，再按第 1 步重新打开终端。Windows 若只有 `python --version` 可用且版本符合要求，下一步第一行把 `py` 换成 `python`。
2. 复制**自己系统对应的三行**，依次执行。第一行在项目里创建独立环境，第二行安装引擎，第三行向随包知识库查询“螺线管”。以后 Agent 也使用这个环境。

   **Windows · PowerShell**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install ./emvr-lab-workflow/design
   .\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

   **macOS · 终端**

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install ./emvr-lab-workflow/design
   .venv/bin/python emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

3. 在输出的 `course` 中找到 `formulas` 列表，并看到长螺线管公式 `long_solenoid_field`，就可以配置桌面 Agent。设计引擎默认使用宿主 Agent，无需单独设置模型 API 密钥。

## 3. 在桌面 Agent 中加载 Skill（四选一）

安装并登录你要用的客户端，然后只读下方对应的小节。每个客户端都有自己的项目 Skill 目录。下面的做法是在该目录放一个很小的**入口文件**，让 Agent 始终读取仓库里的[完整 Skill](emvr-lab-workflow/SKILL.md)。这样脚本、知识库和网页仍在同一个项目里，更新仓库时也能读到更新后的流程。

桌面客户端的官方下载与安装入口 · [Codex](https://developers.openai.com/codex/app/) · [Claude Desktop](https://claude.com/download) · [Cursor](https://cursor.com/download) · [VS Code](https://code.visualstudio.com/download)

**入口文件内容**：选好客户端并按对应步骤打开空文件后，从第一行 `---` 开始复制以下全部内容（不含代码框），保存为纯文本 `SKILL.md`。记事本询问是否新建时选“是”；若出现“另存为”，文件类型选“所有文件”，检查文件名没有多出 `.txt`。macOS 的“文本编辑”如处于富文本模式，先选 **格式 → 制作纯文本**。若入口文件已存在，先核对它指向本项目。

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

1. 打开 Codex 桌面端并登录。在侧栏的项目区新建或打开本地项目，选第 1 节找到的仓库根目录。**这一步就是选择 Codex 的工作区。** 如果从已有项目进入，打开项目菜单 **Edit project → Add folder**，选中同一文件夹并将其作为当前工作目录。
2. 此客户端的项目级入口是 `.agents/skills/emvr-lab-workflow/SKILL.md`。在第 1 节打开的仓库根目录终端中，按你的系统执行下面两行，打开入口文件。

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

3. 将上方“入口文件内容”中的全部文字粘贴到打开的空文件中并保存。 如果侧栏有 **Skills（技能）**，点开可浏览已发现的技能。回到该项目，新开一个聊天，在输入框键入 `$emvr-lab-workflow` 并选择对应 Skill。 [OpenAI · 本地 Skill 目录](https://developers.openai.com/codex/skills) · [OpenAI · 本地项目](https://learn.chatgpt.com/docs/projects)

### 3B. Claude Desktop

1. **选择 Claude Code 会话的工作区。** 打开 Claude 桌面端，登录后切到 **Code** 并新建会话。在输入框旁的环境选择器中选 **Local** 下的本机，再点旁边的 **Open folder…**，选中第 1 节找到的仓库根目录。这个文件夹就是本次会话的工作区。如果界面提供工作树隔离，使用原文件夹，以便继续读取同一份实验记录。
2. 此客户端的项目级入口是 `.claude/skills/emvr-lab-workflow/SKILL.md`。在第 1 节打开的仓库根目录终端中，按你的系统执行下面两行，打开入口文件。

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

3. 将上方“入口文件内容”中的全部文字粘贴到打开的空文件中并保存。 在这个本地 Code 项目新开会话。在输入框键入 `/`，或点 **+ → Slash commands**，选择 `/emvr-lab-workflow`。 [Anthropic · 桌面端入门](https://code.claude.com/docs/en/desktop-quickstart) · [Anthropic · Skills](https://code.claude.com/docs/en/skills)

### 3C. Cursor

1. **选择 Cursor Agent 的工作区。** 打开 Cursor，点 **Open Folder**，选中第 1 节找到的仓库根目录。登录后，在打开该文件夹的窗口里开始本地 Agent 对话。
2. 此客户端的项目级入口是 `.cursor/skills/emvr-lab-workflow/SKILL.md`。在第 1 节打开的仓库根目录终端中，按你的系统执行下面两行，打开入口文件。

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

3. 将上方“入口文件内容”中的全部文字粘贴到打开的空文件中并保存。 在侧栏 **Customize → Skills** 查看项目已发现的 Skill。在 Agent 聊天框输入 `/`，按名称选择 `emvr-lab-workflow`。 [Cursor · Agent Skills](https://cursor.com/docs/skills)

### 3D. VS Code + GitHub Copilot

1. **选择 GitHub Copilot 使用的工作区。** 在 VS Code 中点 **File → Open Folder…**，选中第 1 节找到的仓库根目录。Copilot 使用这个窗口的工作区。在同一窗口点 Copilot 图标打开 Chat，按提示登录 GitHub，选择能操作本地文件和终端的 Agent 会话。
2. 此客户端的项目级入口是 `.github/skills/emvr-lab-workflow/SKILL.md`。在第 1 节打开的仓库根目录终端中，按你的系统执行下面两行，打开入口文件。

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

3. 将上方“入口文件内容”中的全部文字粘贴到打开的空文件中并保存。 按 **Ctrl+Shift+P**（macOS 用 **⇧⌘P**），运行 **Chat: Open Customizations** 并选择 **Skills** 查看项目入口。新开 Copilot 聊天，输入 `/emvr-lab-workflow` 并选择出现的命令。 [VS Code · Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills)

<a id="install-unity"></a>

## 4. 为 Builder 配置 Unity

只做实验设计、导出 PDF 或查看网页上已导出的 3D 场景，可跳到[第 5 节](#start-design)。搭建实验时，Gate 4 会用到 Unity 编辑器。

### 4A. 安装 Unity Hub 和编辑器

1. **安装 Unity Hub。** 打开 Unity 下载页，选择你的操作系统，运行下载的安装程序。启动 Hub，用 Unity ID 登录。如果提示缺少许可证，在 **Settings（设置）→ Licenses（许可证）** 中激活你有权使用的许可证。[Unity Hub 官方下载](https://unity.com/download)
2. **安装项目使用的编辑器。** 本仓库的 Builder 工程指定 **2022.3.62f3c1**，末尾包含 `c1`。在 Hub 的 **Installs（安装）** 页查看已装版本。已有这个完整版本就进入下一步，否则点 **Install Editor（安装编辑器）** 查找该版本。如果列表中找不到，Windows 64 位用户可以下载下面的 Unity 官方安装程序。安装完成后，在 Hub 的 **Installs → Locate（定位）** 中选择刚安装的 `Editor\Unity.exe`，确认列表显示完整版本号。[项目版本记录](reusable-code/EMVR_Blind_BuilderPack/UnityProject/ProjectSettings/ProjectVersion.txt) · [Windows 64 位编辑器安装程序](https://download.unitychina.cn/download_unity/1623fc0bbb97/Windows64EditorInstaller/UnitySetup64-2022.3.62f3c1.exe)

### 4B. 首次配置 Unity 的语言和脚本编辑器

1. 第一次打开 Hub 时，选择 **Create account** 注册自己的 Unity ID，或用已有账号登录。需要中文界面时，在 Hub 的 **Settings → Appearance → Language** 中选择 **简体中文**。
2. Windows 用户如果需要阅读、修改或调试 C# 脚本，可以安装 Visual Studio。打开 **Visual Studio Installer**，选择 **安装**（已有安装则选 **修改**），在 **工作负载** 中勾选 **使用 Unity 的游戏开发**，然后应用更改。[微软安装指南](https://learn.microsoft.com/en-us/visualstudio/gamedev/unity/get-started/getting-started-with-visual-studio-tools-for-unity?pivots=windows)
3. 打开 Unity 工程后，在编辑器选择 **Edit → Preferences → External Tools**，将 **External Script Editor** 设为已安装的 Visual Studio。双击一个 C# 脚本，确认它在 Visual Studio 中打开。

### 4C. 设置 VR 插件和设备模拟器

Builder 工作区已带有项目的 XR 设置。使用 Builder 时，在 Gate 5A 按 Agent 的指引核对场景中的 XR 装置和模拟器。下面的手动安装步骤适用于你自己新建的 Unity 2022.3 工程。[Builder 的 Gate 5A 规程](reusable-code/EMVR_Blind_BuilderPack/README_USER.md#gate-5a通用基础验证)

1. 打开 **Edit → Project Settings → XR Plug-in Management**。首次配置时，点击 **Install XR Plug-in Management**（如有提示）。选择目标平台的标签页，启用 **OpenXR**。
2. 进入 **XR Plug-in Management → OpenXR**，在 **Interaction Profiles** 列表点击 **+**，添加目标设备对应的交互配置。原教程以 **Microsoft Hand Interaction Profile** 为例；请按实际手柄或手部追踪设备选择。
3. 打开 **Window → Package Manager**，从 **Unity Registry** 找到 **XR Interaction Toolkit**。要复现本仓库配置，选择 **2.6.5**。在该包的 **Samples** 标签页，分别点击 **Starter Assets** 和 **XR Device Simulator** 旁的 **Import**。[Builder 工程依赖](reusable-code/EMVR_Blind_BuilderPack/UnityProject/Packages/manifest.json)
4. 如果要在自己的工程里用键鼠模拟头显和手柄，可在 **Edit → Project Settings → XR Interaction Toolkit** 中启用 **Use XR Device Simulator in scenes**。Builder 的基础场景已经按 Gate 5A 放置模拟器时，保持自动添加选项关闭，以免出现两个模拟器。

<a id="在自己的-unity-工程中导入-common-包"></a>

### 4D. 在自己的 Unity 工程中导入 Common 包（按需）

1. Builder 生成的工程已经引用 Common。若想在**自己的 Unity 2022.3 工程**里复用组件，先通过 Unity Hub 打开那个工程。
2. 在 Unity 编辑器选 **Window → Package Manager**。点击左上角 **+ → Add package from tarball…**，在文件选择器中进入本仓库的 `unity-package` 文件夹，直接选择 [com.emvr.lab-common-0.7.0.tgz](unity-package/com.emvr.lab-common-0.7.0.tgz)。
3. 等待解析依赖并编译，在 **Packages: In Project** 中确认出现 **EMVR Lab Common**，版本 **0.7.0**。若安装失败，查看 Package Manager 的依赖提示和 Console 的第一条错误。[包说明](unity-package/README.md)

<a id="start-design"></a>

## 5. 开始或继续 Design

1. 在刚才的项目聊天里选中 Skill，在同一条消息里写：

   > 我想设计一个 ECE329 VR 实验，观察长螺线管中心的磁场如何随电流变化。请打开实时进度页，再问我第一个设计问题。

2. 第一次启动时，客户端可能询问是否允许在本项目运行 Python、打开本地网页。核对项目后允许本次操作。你应当看到设计编号（`design_id`）、第一个设计问题和进度页。如果系统没自动弹出网页，点击 Agent 返回的本机链接。网页的四部分是当前流程、讲义依据、设计摘要和设计检查；右上角可从默认英文切换到中文。**回复问题的位置是 Agent 聊天框。**
3. 可以先说“给我看这个公式的讲义依据”，再说“把草稿改成只测线圈中心，固定匝数和长度”。可以在同一条回复里接受草稿并说明要改的细节，例如讨论电流滑块时说“上限用草稿中的 2 A，把步长改为 0.1 A”。Agent 会一起记录已决定的事项，再就剩余选择提问。准备定稿时按第 6 节确认整份方案。
4. 记下实际的 `design_id`。下次打开同一项目、选中同一 Skill，说“继续设计，编号是［粘贴原编号］，从上次待确认的草稿开始”。核对 Agent 返回的**编号与阶段**。只有主题而有多个同名实验时，先从候选中选出原实验。

可在[第 10 节的 Design 流程](#design-stages)查看当前阶段要完成的内容。

<a id="export-design"></a>

## 6. 确认整份方案并导出

1. 七个设计阶段完成后，核对汇总草稿，明确回复“确认整份方案，请导出”。如果 Agent 指出缺项，先修订该项，再确认。
2. 打开 Agent 返回的 `artifacts` 文件夹。应有 `design.pdf`（供你阅读）、`builder-gate1-input.pdf`（供 Builder 核对需求）和 `builder-gate1-input.json`（同版结构化交接数据）。
3. 报告默认使用对话语言。需要另一种语言时，说“保留这一版设计，再导出一份英文 PDF”。请 Agent 完成翻译并给出实际文件位置；网页的语言按钮只管显示。

<a id="start-builder"></a>

## 7. 开始或继续 Builder

1. **沿用刚完成的设计**：在原聊天说“用刚确认并导出的这版方案开始搭建”。核对 Agent 报出的设计版本、Builder 工作区和当前 Gate（构建关卡）。
2. **已经有自己的方案**：在已配置的项目聊天里，把目标文件附到聊天里，指明版本，说“只用附件这一版直接进入 Builder”。Agent 会从这份方案开始核对需求；有多个版本时先让它确认选中了哪一份。
3. **继续已有构建**。在同一项目的聊天里告诉 Agent：“继续 Builder 工作区［路径］里的［lab_id］。” 这里填写 Agent 之前为该实验给出的构建工作区路径。核对当前 Gate 和待办事项。每一关的检查与批准顺序见[第 10 节的 Builder 流程](#builder-gates)。

**附件下载遇到 DNS 错误时**，如果用的是本项目导出的方案，可以告诉 Agent：“请用设计编号和版本查找本地交接文件。” 提供已知的 `design_id`、修订号和语言，或直接给出自己保存的交接目录。导出文件在状态目录的 `handoffs/` 下，构建进度在对应的 Builder 工作区中。删除本次构建目录后，要继续原 Gate 需恢复该目录的备份；如果希望从 Gate 0 重新开始，请明确告诉 Agent 用保留的方案重新搭建。

**首次进入 Builder 时，记下续接信息。** 从已确认的设计进入时，可以直接对 Agent 说：“请把设计编号 `design_id`、构建编号 `lab_id` 和本次 Builder 工作区的完整路径列给我，方便下次继续。” 如果直接从附件开始搭建，只需保存构建编号 `lab_id` 和 Builder 工作区的完整路径。

### 在 Gate 4 打开工程并检查编译

1. **在 Gate 4 打开本次实验。** 等 Agent 告知脚手架已生成，在 Hub 选 **Projects（项目）→ Add → Add project from disk**，选择 Agent 给出的 `unity_editor_project`。Windows 上直接选择这个短入口目录，即使它的名称是一串字符。选中项目并用第 4 节安装的版本打开。[Unity Hub 项目操作说明](https://docs.unity.com/en-us/hub/projects-window-reference)
2. **核对编译结果。** 保持编辑模式，等待资源导入和 C# 自动编译结束，打开 **Window → General → Console**。如果红色错误数为 0，把结果告诉 Agent，继续 Gate 4 验收。如果有错误，把第一条红色错误的完整文字发给 Agent。此步无需点击 Play 或打包应用。

**Windows 重启后继续打开同一个工程。** 第一次使用或从旧 Z 盘迁移时，保存并关闭旧工程。在仓库根目录的 PowerShell 执行下面的命令。从 Design 进入 Builder 时，填入上面记下的构建编号 `lab_id`，例如 `ece329_solenoid_current`。独立运行 Builder 时，把示例编号换成带引号的 Builder 工作区完整路径（包含 `UnityProject` 的那一层）。

```powershell
.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/builder.py ece329_solenoid_current unity-project
```

复制输出的完整路径，在 Unity Hub 选 **Projects → Add → Add project from disk**，添加并打开一次。以后重启直接选这个 Hub 条目。这个入口是持久目录联接，默认保存在本机用户目录下，指向原场景和 Gate 记录。若同一编号对应多次运行，用命令列出的目标工作区完整路径替换构建编号 `lab_id` 再执行。

如果短入口创建失败，请留在当前 Gate。可在仓库根目录用自己的 PowerShell 运行上面的命令。如果默认目录不可写，在构建编号或工作区路径前加 `--entry-dir "本机可写短目录"`，以后继续使用同一目录。保存并关闭已从长路径打开的工程，再从成功输出的入口重新打开。

### 在网页中查看场景

在 Unity 中保存含可见模型的实验场景后，关闭编辑器也可以点击进度页右上角的 **Unity 3D**。浏览器会在本机加载已导出的模型。按住鼠标左键拖动可旋转，滚轮可缩放，按住右键拖动可平移。点选模型或从列表选择物体后，点击 **聚焦物体** 可近看，点击 **查看全景** 可恢复整体视角。点击 **工作流详情** 返回进度页。

编辑器打开时预览会更新，关闭后显示最近保存的版本。预览使用网格形状、基本材质颜色和世界变换；贴图、Unity 专用着色器和 VR 交互需要在 Unity 中查看。新工作区在 Gate 4 安装预览工具。旧工作区缺少预览工具时，可在 Gate 4 或 Gate 5A 验证通过前让 Agent 补装，再打开并保存目标场景。已通过 5A 的工作区沿用验收时的编辑器工具。尚无可预览模型时按钮为灰色。

## 8. 手动操作与排错

1. **Skill 名称没有出现**：确认客户端打开的是第 1 步的根目录。在第 3 步所选客户端的项目目录中检查 `emvr-lab-workflow/SKILL.md` 入口文件，确认名称和描述位于两行 `---` 之间。确认不是 `SKILL.md.txt`，保存后新开项目聊天，必要时重启客户端。临时续接也可在聊天里明确说“请读取仓库根目录下的 `emvr-lab-workflow/SKILL.md` 并从设计编号 `design_id`［填入原编号］继续”。
2. **提示缺模块或找不到知识库**：回到第 2 步重新执行知识库查询。如果能查到，请 Agent 使用同一个 `.venv` 解释器，并从第 1 步的根目录运行原操作。
3. **已有实验的网页打不开**：让 Agent 重开同一编号。手动检查时，在包根执行 `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/viewer.py open DESIGN_ID`，把 `DESIGN_ID` 换成实际编号并打开返回的 `url`。用 `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py show DESIGN_ID` 核对进度。macOS 将命令开头换为 `.venv/bin/python`。
4. **换电脑后找不到旧实验**：复制原状态目录（默认是 `emvr-lab-workflow/state/`，旧项目也可能使用根目录的 `state/`）。其中包含设计会话和从设计创建的 Builder 工作区。直接从附件搭建时，还要迁移实际使用的独立 Builder 工作区。按[第 9B 节](#update-zip)恢复已有源码和知识库归档，在新电脑上完成第 2～3 节的配置。继续设计时提供 `design_id`；继续独立构建时提供 `lab_id` 和迁移后工作区的完整路径。
5. **Unity Hub 找不到原工程**。请 Agent 定位原工作区，再参照[第 7 节](#start-builder)，按运行类型用构建编号 `lab_id` 或 Builder 工作区完整路径取回工程入口。

### Unity 安装或打开工程时遇到问题

- **Hub 一直排队或提示下载校验失败**。先在 Hub 的下载列表查看失败项。若只有语言包失败，可先完成编辑器安装，再补装语言包。若编辑器本身反复失败，Windows 用户可以使用[第 4 节](#install-unity)的独立安装程序，再用 **Installs → Locate** 登记。
- **打开工程时提示 `contains a locked Library`**。先关闭已打开该工作区的 Unity 编辑器，确认相关进程已退出，再从 Hub 重试。如果是解压得到的工程且仍提示锁定，关闭编辑器，把该工程里的 `Library` 改名为 `Library.backup`，重新打开并等待 Unity 重建导入缓存。保留 `Assets`、`Packages` 和 `ProjectSettings`。
- **Gate 5A 保存后提示 `XR Interaction Setup.prefab` 导入副本哈希不同。** 保存场景并关闭该 Unity 工程。按[第 9 节](#update)更新后，在同一项目的聊天中提供原 Builder 工作区路径和 `lab_id`，请 Agent “恢复 XR 导入副本，在 Gate 5A 复测”。Agent 会核对导入记录、备份可识别的改写并恢复批准版本。用 Agent 给出的入口重开工程，复测鼠标和 XR 射线交互。其他差异交给维护者检查。

<details>
<summary>可选：手动运行同一流程</summary>

以下命令在仓库根目录的 PowerShell 中逐条执行。macOS 将每条命令开头的解释器换为 `.venv/bin/python`。

1. **新实验**先运行 `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/viewer.py open --new`，打开返回的 URL 并复制 `viewer_session`。
2. 运行 `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py create "研究长螺线管中心的磁场如何随电流变化" --language zh --viewer-session TOKEN`，将 TOKEN 换成刚复制的令牌，记下返回的 `design_id`。已有设计可直接运行上方排错第 3 项的 `viewer.py open DESIGN_ID` 和 `workflow.py show DESIGN_ID`，两处都填原来的设计编号。
3. 用这个 `design_id` 在 Agent 聊天中继续讨论并确认方案。手动提交一轮设计回复时，按[Agent 输入协议](emvr-lab-workflow/references/agent-turns.md)向 `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py turn DESIGN_ID --stdin-json` 提供本轮 JSON。
4. 整份设计确认后，运行 `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py export DESIGN_ID` 导出。要开始搭建，再运行 `.\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py builder-init DESIGN_ID`。两处 DESIGN_ID 都换成实际设计编号，根据 `artifacts` 和 `builder_workspace` 找到文件及工作区。

</details>

<details>
<summary>维护者：运行自动回归</summary>

在根目录用第 2 步的环境安装 `"./emvr-lab-workflow/design[test,harness]"`（使用 `-m pip install`），再运行 `-m pytest -q`。离线测试可设置 `ECE329_GENERATOR=rule` 和 `ECE329_TEST_HARNESS_RUNTIME=1`。已安装 Playwright 和 Chromium 时可运行 `node emvr-lab-workflow/tests/viewer.cjs`。

</details>

<a id="update"></a>

## 9. 更新已有安装并继续实验

先记下当前 `design_id`。如果已进入 Builder，也记下 `lab_id`、当前 Gate 和原 Builder 工作区的实际路径。等待本轮 Agent 操作结束，保存并关闭 Unity 编辑器。可以让 Agent 关闭本项目的本地进度页服务，再开始更新。

<a id="update-git"></a>

### 9A. 用 Git 克隆的项目

1. 在原仓库根目录打开终端，逐行运行下面三条命令。第一条应显示本项目的根目录，第二条应指向下方的项目仓库，第三条显示当前分支和文件改动。[项目仓库](https://github.com/yzhao05/ece329-vr-lab-workflow)

   ```sh
   git rev-parse --show-toplevel
   git remote get-url origin
   git status --short --branch
   ```

2. 如果当前在 `main`，在同一目录拉取更新。若你改过受 Git 跟踪的文件，先备份或提交自己的改动。若你在自建分支上，先保存工作并切回 `main`。执行：

   ```sh
   git pull --ff-only origin main
   git log -1 --oneline
   ```

   拉取成功后，第二行显示本地最新提交。若 Git 提示会覆盖文件或分支已分叉，先停下，保留本地改动并处理提示，再继续。

3. 保留原来的实验目录和 `.venv`，继续下面的[更新后验证](#update-check)。

<a id="update-zip"></a>

### 9B. 用 Download ZIP 或老师发来的文件夹

1. 在[项目仓库](https://github.com/yzhao05/ece329-vr-lab-workflow)选择 `main`，点 **Code → Download ZIP**，或取得老师发的新版 ZIP。解压到单独的临时文件夹。找到里面同时包含 `README.md`、`emvr-lab-workflow` 和 `web` 的那一层。
2. 关闭原项目的终端和 Agent 项目窗口。在原文件夹的上一级，把旧文件夹改名为备份（例如在末尾加 `-backup`），再把解压出的新版根文件夹放到**原来的完整路径**。这样已有的 Builder 工作区路径和 Unity Hub 项目位置仍可沿用。
3. 从备份复制**本机实验数据**到新版中的相同相对位置。默认要复制完整的 `emvr-lab-workflow/state/`；若原来用的是根目录 `state/`，就恢复到根目录。如果备份里有 `web/data/`，把这个目录也复制回来，它保存已发布的本地进度快照和最近实验的入口。独立 Builder 如果建在 `reusable-code/EMVR_Blind_BuilderPack/RebuildWorkspaces/`，还要复制里面实际用过的实验工作区。外置工作区或自定义状态目录继续使用原路径。
4. 若有自己积累的材料，合并 `knowledge/newknowledge/`、`reusable-code/newcode/` 以及其他目录中自己添加的文件；遇到同名文件先比对内容。按需恢复本机 `.env` 配置。在新版根目录重新执行第 2 步创建 `.venv`，再按第 3 步为自己的客户端创建 Skill 入口。保留旧文件夹，直到核对完实验进度。

如果自定义的状态目录、网页数据目录或独立 Builder 工作区也在旧项目文件夹内，请从备份恢复到原来的相对位置。

<a id="update-check"></a>

### 9C. 验证更新并续接原进度

1. Git 用户在原环境中运行下面两行。ZIP 用户如果刚完成第 2 步的安装和知识库查询，可以直接进行下一项。

   **Windows · PowerShell**

   ```powershell
   .\.venv\Scripts\python.exe -m pip install ./emvr-lab-workflow/design
   .\.venv\Scripts\python.exe emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

   **macOS · 终端**

   ```sh
   .venv/bin/python -m pip install ./emvr-lab-workflow/design
   .venv/bin/python emvr-lab-workflow/scripts/workflow.py knowledge "solenoid" --scope design
   ```

2. 在 `course` 的 `formulas` 列表中看到 `long_solenoid_field` 后，在更新后的项目里新开 Agent 聊天，选中 Skill，说“继续实验［原 design_id］，打开进度页，告诉我当前 Gate 和待处理事项”。独立 Builder 可说“继续原工作区［实际路径］里的［lab_id］”。核对编号、Gate 和上次待处理事项。Windows 上需要打开 Unity 时，使用 Agent 为原工作区返回的短路径。

## 10. Design 和 Builder 工作流

<a id="design-stages"></a>

### Design 工作流的七个阶段

在 Agent 聊天里讨论，按进度页上的阶段核对草稿。同一阶段的几个简单问题可以一起回答，例如在一条消息里给出实验名称、接受建议的实验 ID，并说明想测哪个物理量。

1. **实验想法完善**。说明想研究的现象，以及希望学生学会什么。和 Agent 对照讲义，确定研究问题、理论依据和预期趋势。
2. **变量与条件**。决定学生能调什么、测什么、哪些条件保持固定。例如只改变电流，把探针固定在螺线管中心。
3. **概念实验流程**。按学生的操作顺序核对草稿，从进入场景、调节参数，到记录数据和重置实验。
4. **预期数据可视化窗口**。选定读数、单位和图表，说明何时刷新读数、何时把一个点加入图中。
5. **可能结果及解释**。讨论预期数据会呈现什么规律，学生如何解释结果，以及用什么标准验收。
6. **设计价值、可行性与局限性**。说明 VR 能帮助学生观察什么、模型依赖哪些假设，并核对 Unity 实现方案。
7. **EMVR方案汇总**。通读整份草稿，尤其检查前面改过的条件是否贯穿操作、图表和验收标准。确认后按[第 6 节](#export-design)导出同一版方案。

<a id="builder-gates"></a>

### Builder 工作流的关卡顺序

当前版本依次完成 Gate 0～6，然后直接进入 Gate 8，没有独立的 Gate 7。

每次查看 Agent 报出的当前 Gate、验证结果和待办事项。批准后，Agent 记录本关结果并告诉你下一关。下一条消息可以直接提供下一关的材料或问题。需要在 Unity 里操作时，使用 Agent 给出的工程入口。

1. **Gate 0 · 边界核验**。核对输入方案和工作区，建立受保护文件的初始记录。
2. **Gate 1 · 确认实验需求**。核对构建简报，一次补齐缺少的课程、手册或评分信息。
3. **Gate 2 · 准备接口契约**。核对配置中的参数、交互、数据记录与验收条件是否符合简报。
4. **Gate 3 · 审核实现设计**。查看场景、组件和测试计划，确认这些安排能实现实验。
5. **Gate 4 · 生成工程脚手架**。用 Unity 打开工程并刷新，向 Agent 报告 Console 编译结果。
6. **Gate 5 · 验证复用基础与领域切片**。5A 先验证房间、照明和基础交互；5B 再实现本实验的模型、控件和测量逻辑，并按要求测试。
7. **Gate 6 · 验证 Unity 场景并验收**。按验收标准在 Unity 中实际操作并反馈结果。通过后，Agent 将选定的 Gate 5B 源码归档到 `reusable-code/newcode/`。在其他工程中重用这些文件时，先核对[组件依赖](reusable-code/README.md)。
8. **Gate 8 · 完成实验与开发手册**。8A 核对本实验的学生手册和开发者手册，8B 核对项目总手册的增补章节。两部分均可验收后，按[最后一步](#knowledge-archive)确认并检查知识库归档。

<a id="knowledge-archive"></a>

## 11. 最后一步：确认知识库归档

1. 在 Gate 8 核对两部分手册后，告诉 Agent：“我批准本次 Gate 8，请给我归档路径。”
2. Agent 在记录这次批准时同步写入复盘。一次 Gate 8 批准即可完成手册验收与知识库归档。Design 接 Builder 的实验总结两段流程；直接从 Builder 开始的实验总结本次搭建。复盘应写明遇到的问题、触发条件、处理办法、验证结果和遗留限制。若没有已知问题，如实记录即可。
3. 打开 Agent 返回的 `knowledge_update` 所指向的 Markdown 文件，核对归档内容。路径以仓库根目录为准：关联设计的实验保存在 `knowledge/newknowledge/<design_id>/<设计指纹>.md`，独立 Builder 保存在 `knowledge/newknowledge/builder/<lab_id>/<验收版本指纹>.md`。如果页面显示“验收通过，待归档复盘”，请 Agent 恢复原工作区，用已有批准重试归档，直到返回可打开的文件。
4. **上传 Agent 整理好的两个文件夹。** 审阅 Gate 8 手册时，可在批准消息里加一句“提交名用张三”。Agent 会在同一次验收中整理 `张三_newcode`（本次构建源码）和 `张三_newknowledge`（本次知识库更新），给出两个本地路径。未指定名字时默认用构建编号 `lab_id`。按路径打开，直接上传或分别压缩后发送给维护者。如果页面显示“上传副本待整理”，让 Agent 在原实验中重试。它会沿用提交名和补充文件清单，两个副本都就绪后页面显示完成。
