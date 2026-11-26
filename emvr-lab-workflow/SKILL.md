---
name: emvr-lab-workflow
description: 在宿主 Agent 对话中开始或续接 ECE329 电磁学 VR 实验设计、查询课程依据、导出已确认的方案，或从已确认设计和用户自带方案进入 Unity Builder。
---

# ECE329 VR 实验设计与构建

用户在聊天里讨论、修订并确认方案。主 Agent 负责打开流程网页、执行命令、展示证据和可修改的草稿，并把用户的实际决定写回工作流。以下路径均以本文件上一级的**交付根目录**为基准。下文的 `viewer.py`、`workflow.py` 均指 `emvr-lab-workflow/scripts/` 中的同名脚本，示例中的 `python` 指 README 第 2 节已安装设计引擎的项目解释器。Windows 使用 `.venv/Scripts/python.exe`，macOS 使用 `.venv/bin/python`。从交付根运行，例如：

```sh
python emvr-lab-workflow/scripts/viewer.py open --new
```

## 启用时先打开网页

每轮回复开头展示当前流程、Gate 编号、名称（设计有细项时也展示细项）和状态。按对话语言表达工具返回的 `status_line`。Design 用本轮 create/turn/show 的结果；Builder 在本轮操作后用 status 的结果。遇到错误时保留原 Gate，说明卡在哪里、缺哪项输入或证据。工作区尚未建档时明确写“准备中，尚未进入 Gate 0”。

一条用户消息最多推进一个 Gate。主 Agent 为该消息使用稳定的 turn_id，重试和同一消息内的工具调用沿用该 ID。只处理当前 Gate；完成当前关后可以预告下一关，等用户的下一条真实消息再执行下一关。续接旧 Builder 工作区也采用这条规则。用户对同关多个细项的回答一次写入。Design 先说明采纳了哪项想法，再围绕当前决策引导讨论；当用户的回答已经决定了你展示的草稿，直接记录并推进这一阶段。推导、命名和状态汇报无需另问“继续吗”。尚有不同设计方向或到了整份方案定稿时，交由用户决定。

Codex 每次启用本 Skill，先打开与任务对应的实时网页，再开始提问、检索或写入。其他宿主使用相同的本地入口。已知设计编号用 `viewer.py open DESIGN_ID`，新设计用 `open --new`，独立 Builder 用 `open --builder-workspace "PACK" --lab-id LAB_ID`。仅查资料、尚待辨认目标或尚未确定工作区时，先用 `viewer.py open`，定位后再切到对应页面。根据最新页找到的实验仍需与用户所指实验核对。

若浏览器未弹出，打开命令返回的 `url`。有内置浏览器的宿主可加 `--url-only` 并实际打开该 URL。启动失败时检查报错中的日志、网页目录和桌面权限，修正后对同一目标重试。页面打开后沿用本次标签页。每轮通过 `turn` 保存设计，每关通过原生 Builder 工具记录状态，页面约每 2.5 秒刷新。网页语言独立切换，首次默认英文。

会话默认在 `emvr-lab-workflow/state/`；交付根已有旧版 `state/` 时会续用。自定义目录时，在查看器和工作流子命令**之前**传入相同的 `--state-dir` 和 `--web-dir`。引擎缺失时用当前解释器执行 `python -m pip install ./emvr-lab-workflow/design`，再重试原步骤。默认由宿主理解对话，若已配置原 Design 模型适配器，可在工作流子命令之前传 `--provider environment`。

## 新建设计

- **触发条件**　用户明确要开始一个新实验。
- **所需输入**　用户的实验想法和当前对话语言。目标尚不清楚时，先询问其关心的电磁现象。
- **执行步骤**　先用 `viewer.py open --new` 打开页面，保存返回的 `viewer_session`。执行 `workflow.py create "用户的原话" --language zh --viewer-session TOKEN`，把 TOKEN 换为实际令牌；英语对话用 `en`。
- **成功后**　记下并告知 `design_id`。依据返回的 `assistant_message`、`student_task`、`stage_payload` 和适用的 `experience_rules` 提出第一个设计问题。
- **失败时**　已有令牌就沿用它重试 `create`。若令牌已绑定，核对返回的原编号后续接。

## 继续已有设计

- **触发条件**　用户说“继续上次的螺线管实验”等续接请求。
- **所需输入**　原 `design_id`，或能唯一定位实验的线索，如想法、上次问题、页面链接。先查当前会话和用户提供的记录；必要时在本次网页目录的 `data/<design_id>.json` 中核对实验想法和进度。
- **执行步骤**　若两个设计都匹配，列出各自编号、主题及当前阶段，请用户选一个。唯一确定后用 `viewer.py open DESIGN_ID` 打开该页，再用 `workflow.py show DESIGN_ID` 读取已保存的 `revision`、`flow`、`notes`、检查结果以及可用的当前阶段回复。
- **成功后**　简述已确认内容，接着上次待核对的草稿或问题聊。若设计已完成，说明可导出的文件或关联 Builder 的当前 Gate。
- **失败时**　编号未知或匹配为空，核对状态目录、旧对话或页面链接，再请用户补一条辨识线索。网页故障重开**同一编号**。整个续接路径都不调用 `create` 或 `open --new`。

## 讨论、修订与确认

- **触发条件**　用户在当前设计中回答问题、索取参考、修改草稿或确认阶段。
- **所需输入**　设计编号、当前草稿、用户本轮原话和对话语言。
- **执行步骤**　采用统一 EMVR 规则。结合讲义说明主公式、辅助关系和适用边界，逐步讨论方法与方向。把同一阶段可一起决定的细项组成一份可修改的草稿。例如把课程映射、实验名称和实验 ID 一起给出，或把控件、固定探针、初始值与重置行为一起给出。只追问会改变设计且尚未确定的选择。用户认可整份可见草稿后，用同一条原话、同一 turn_id 和结构化字段更新一次保存各项。根据返回的实际缺项继续。已确认的信息和按已知公式直接算出的值直接沿用，给出必要的依据；不为查资料、计算或整理再索要“继续”。没有明确指向一份可见草稿的“继续”不能代替确认。接入本 Skill 的主 Agent 负责理解每条回复，用 `workflow.py turn DESIGN_ID --stdin-json` 一次提交原话、turn_id、interpretation 及本轮所有明确的字段值。用户直接给出的值即可记录；只有助手提出的候选值需要用户认可。仅当用户明确确认当前草稿时在 JSON 中设置 `complete_stage: true`；最终阶段须确认整份方案。用户不用另写学生总结。语言改变时在 JSON 中设置 `language` 为 `en` 或 `zh`。
- **成功后**　按返回的阶段、细项和 `revision` 展示实际修订。普通讨论、引用资料、Agent 自拟草稿均留待用户核对。将适用的 `experience_rules` 纳入本轮反馈。
- **失败时**　按 `completion_error` 补缺项；“前面那个”有多个解释时，用当前可见的候选 ID 澄清。需要结构化解释时，将原话、`turn_id` 和解析结果作为 UTF-8 JSON 传给 `turn DESIGN_ID --stdin-json`。重试同一轮沿用同一 ID 和内容。见[宿主输入协议](references/agent-turns.md)。

## 导出已确认方案

- **触发条件**　用户要导出，或准备把本 Skill 的设计交给 Builder。
- **所需输入**　设计编号和要交付的已确认版本。核对 `show` 的 `check.report_ready` 与 `check.builder_ready`，二者对应引擎的 `report_ready` 和 `builder_input_ready`。
- **执行步骤**　两项均为真时运行 `workflow.py export DESIGN_ID`。默认使用当前对话语言；用户指定其他语言时附加 `--language en` 或 `--language zh`。一次性的导出语言选择仅适用于该次文件。
- **成功后**　从返回的 `artifacts` 路径交付同一版本的 `design.pdf`、`builder-gate1-input.pdf`、`builder-gate1-input.json`，说明版本及语言。不同语言各存一份展示文件，共用原方案机器标识。
- **失败时**　未就绪则回到具体待确认项。若返回 `translation_required`，把 `translations` 对象写为 UTF-8 JSON，逐条译成目标语言，保留原文键、数值、公式、对象 ID 和路径；给原命令追加 `--translations 文件路径` 重试，直到返回 `artifacts`。

## 进入或续接 Builder

**当前关卡内可自主修复。** 命令的工作目录、参数或路径写法有误，或本实验新生成的脚本有编译、组件连接等可逆错误时，主 Agent 可自行定位、修正并重跑原检查，再向用户报告改动与证据。运行包里的受保护工具有已发布修复时，先从更新后的交付根用 `builder.py "PACK"` 转发原命令。只有修复涉及受保护源文件、覆盖已有实验、改变已确认需求或确实需要用户操作时，才交回对应决定。保留当前 Gate、原始哈希与用户批准记录。

Gate 0 首次保存基线若遇到 Windows `relative_to` 路径前缀错误，读取原工作区的 `status`，尚无已登记基线时用 `builder.py "PACK" capture-gate0-baseline --lab-id LAB_ID` 重试。对已有基线做完整性复查。若已登记阻塞，再据实际结果用 `retrospective --resolve` 关闭同一事件，处理其余 Gate 0 待办。

Gate 5A 若模拟头显的姿态在变、Game 视角仍不动，先检查正在渲染的主相机。可用 **Tools → EMVR → Diagnostics → Check Head Tracking** 查看三个输入动作的实际名称及 Play Mode 启用状态。具体复查顺序见 Builder 规程；用户已提供的 Input Debugger 观察直接沿用。旧工作区也按实际进度排错：当前构建的照明已经生成、保存并核验时，直接检查输入或相机；重建场景或照明失效时再生成。

Gate 6 验收后，Gate 8A 先为本实验制作学生手册和开发者手册。Gate 8B 增补项目总手册时，优先使用用户指定的当前原稿；首次制作可使用交付根自带的 `knowledge/sources/EM VR Lab Development Handbook.docx`。从交付根解析为绝对路径，作为 `handbooks.py stage-master --source` 的输入。若本项目已有增补后的总手册，续用该版，保留既有章节。增补文件写入当前工作区的 `BuildEvidence/<lab_id>/handbooks/project-master/`，保留输入原稿。

用 `builder.py "PACK" approve-gate --lab-id LAB_ID --gate N --note "用户原话" --turn-id TURN_ID` 记录当前 Gate 的批准。原生规程中所有 approve-gate 示例在统一 Skill 中采用此入口。Gate 8 还须加下文的 `--notes` 参数，在这次批准中完成复盘归档。Gate 6 通过这个入口同步发布 Gate 5B 已选源码，核对返回的 `archive`。若归档提示同一验收指纹下的文件内容冲突，先对照已验收版本核对两份文件，再恢复归档。若原工作区已记录 Gate 6 验收但复制失败，按 Builder 规程重试 `code_archive.py publish`，沿用原验收。一次集中询问本关缺少的材料或验收证据。状态查询本身不消耗一次批准。

首次交接或恢复 Builder 后，把构建编号 `lab_id` 和 Builder 工作区完整路径 `builder_workspace`（下文的 PACK）交给用户保存。关联 Design 时同时给出 `design_id`；这三项可直接读取 `builder-init` 的成功结果。独立 Builder 沿用实际建档的 `lab_id` 和 PACK。在交付根用项目解释器执行 `python emvr-lab-workflow/scripts/builder.py "PACK" status --lab-id LAB_ID`。规程中的其他 labflow 子命令也通过这个入口转发，适用于已经冻结 Gate 0 基线的旧工作区。若是旧包，请使用更新后的交付根执行，保留原 PACK 和实验编号。

Windows 下 Gate 4 必须通过交付根的 `builder.py "PACK" scaffold --lab-id LAB_ID` 生成骨架，把成功输出中的 `unity_editor_project` 给用户在 Hub 中打开。旧工作区规程中直接打开 UnityProject 的说明也按本条执行。Gate 5/6 续接或首次打开时，从交付根执行 `python emvr-lab-workflow/scripts/builder.py "PACK" unity-project`。Windows 默认在当前用户的 `%LOCALAPPDATA%\EMVR` 中创建可跨重启复用的目录联接，向用户提供命令输出的完整路径，在 Unity Hub 中添加一次。对于 Design 交接创建的运行，可用构建编号 `lab_id` 代替 PACK 查找工程；独立 Builder 使用实际 PACK 路径。若有多个匹配，先确认具体工作区。使用自定义状态目录时在构建编号或 PACK 前加 `--state-dir "STATE"`。入口失败时停在本关，不向用户提供长路径作为后备入口。若默认位置不可写，可在命令的 PACK 前指定 `--entry-dir "可写的本机短目录"`，以后沿用同一目录（或设置 `EMVR_UNITY_ENTRY_DIR`）。若宿主没有创建联接的权限，请用户从本机 PowerShell 运行同一条 unity-project 命令并返回成功输出。旧条目已打开时，先保存并关闭，再从新入口打开。Gate 记录、归档和完整性检查继续使用原 PACK。遇到 Unity 重建空 Plugins 目录时保留目录及其 .meta，并复查原基线。


`unity-project` 用于获取工程入口。Gate 4 的 `scaffold` 会安装网页预览与 XR 保存防护。旧工作区需要补装时，在 Gate 4 或 Gate 5A 验证通过前运行 `python emvr-lab-workflow/scripts/builder.py "PACK" prepare-editor --lab-id LAB_ID`。通过 5A 后沿用已验证的编辑器工具。

Gate 5A 若已导入的 `XR Interaction Setup.prefab` 报副本哈希不符，请用户保存场景并关闭该工程。包括旧工作区在内，从更新后的交付根执行 `python emvr-lab-workflow/scripts/builder.py "PACK" repair-xr-import --lab-id LAB_ID`。恢复成功后用短入口重开，复测鼠标和 XR 射线交互，保存场景并重跑本关校验。命令拒绝的差异保留给维护者检查。

详细规程集中在 [builder-workflow.md](../reusable-code/EMVR_Blind_BuilderPack/.agents/skills/build-unity-vr-lab-blind/builder-workflow.md)。选定工作区后读取**该工作区内**的同名文件，从 **Create or resume a run** 及当前 Gate 开始。续接旧工作区时，沿用其中记录的验收要求与证据；兼容命令和 Gate 5A 排错步骤以更新后交付根的说明为准。规程还说明何时从交付根调用代码归档工具，固定目标为 `reusable-code/newcode/`。

| 触发条件 | 所需输入 | 执行步骤 | 成功后的动作 | 失败后的处理 |
| --- | --- | --- | --- | --- |
| 构建在本 Skill 中已确认的设计 | `design_id`、已确认版本和交接语言 | 打开该设计的页面，核对导出就绪状态，运行 `workflow.py builder-init DESIGN_ID`，语言覆盖与翻译重试方式同导出。核对 `revision`、`builder_inputs` 与目标版本 | 沿用设计标签页，进入返回的 `builder_workspace`，以工作区 `LabSpecs/<lab_id>/design-input/` 中该版 PDF 和 JSON 为依据，查询当前 Gate | 未就绪则返回原设计；指定的是其他修订时先澄清版本。重试时沿用相同设计和版本。已建工作区保留建档时的输入语言 |
| 用户已有外部方案，只想搭建 | 用户提供的方案文件或正文、所选版本、实验标识及目标工作区 | 有多个版本先请用户指定。按规程选定独立工作区和 `lab_id`，打开其 Builder 页，以指定方案作为需求依据。按规程建档或续接。新实验使用 integrated-development；明确要求盲重建才走 blind-rebuild。手册语言可在原生 `new` 指定 `--manual-language` | 从交付根执行 `python emvr-lab-workflow/scripts/builder.py "PACK" status --lab-id LAB_ID`，说明采用的版本、当前 Gate、待确认事项，直接与用户讨论构建 | 缺少文件、版本或关键要求时仅追问缺项。在本路径中保持 Builder 身份，不为附件创建 Design 会话 |
| 继续已有 Builder | 已关联的设计编号，或工作区与 `lab_id` | 关联设计打开设计页；独立运行打开绑定工作区与 `lab_id` 的页面。从交付根运行上述 `status`，传入原工作区完整路径和 `lab_id` | 依据实际状态从当前 Gate 和待确认项继续 | 有多个工作区或编号时先让用户选择；状态读取失败时核对原路径和标识，再重试 |

从附件直接搭建时，优先读取附件的本地原件或用户指定的交接目录。如果只读到了预览，但其中有设计编号和版本，可在同一状态目录运行 `workflow.py find-handoff DESIGN_ID --revision N` 查找本地导出。如果项目解释器已失效，可先在所用状态目录的 `handoffs/<design_id>/` 中核对指定版本的两份 PDF 和 Builder JSON，再按 README 第 2 节修复环境。核对版本、指纹、语言及附件内容；无法确认与用户指定的附件一致或存在多个可能版本时，请用户指定原件路径。此查询不创建构建，也不需要下载附件。若已删除旧构建，告知用户旧 Gate 进度需从备份恢复；用户明确要求从 Gate 0 重建关联设计时，运行 `workflow.py builder-init DESIGN_ID --rebuild-missing`。从独立附件搭建时，按独立 Builder 规程新建。

恢复工作区时，若 `builder_inputs_match_export` 为 `false`，向用户说明原构建输入位于 `builder_inputs`，本次导出位于 `artifacts`。先核对差异，让用户选择沿用原输入或用本次导出另开独立工作区，再推进 Gate。

## 资料、反馈与完成后复盘

| 触发条件 | 所需输入 | 执行步骤 | 成功后的动作 | 失败后的处理 |
| --- | --- | --- | --- | --- |
| 查课程依据、设计经验或构建参考 | 问题中的概念、用途 | 用 `workflow.py knowledge "关键词" --scope design` 或 `--scope builder` 检索[知识库目录](../knowledge/catalog.json) | 引用讲义标题和真实页码，或来源文件的相对路径和行号 | 缩小关键词或回到索引核对，说明仍缺少的依据 |
| 用户反馈某轮有误，或维护者要审阅经验规则 | 设计编号、具体问题和稳定的 `request_id`；审阅时需要候选版本 | 用 `workflow.py feedback DESIGN_ID --submit` 从 UTF-8 JSON 输入提交，如 `{"message":"修改没有更新到草稿","category":"cross_stage_edit","request_id":"feedback-turn-004"}`。用 `feedback-process --ticket TICKET_ID` 读取证据和格式，再用同一命令加 `--candidate 文件路径` 提交含 `ticket_id`、`candidate` 的分析。维护者明确审阅后，用 `experience-review EXPERIENCE_ID` 从 JSON 输入提交 `decision`、`version`、`note`，可执行规则还需原生验证凭证 | 保存工单号，后续依据实际启用并返回的 `experience_rules` 调整反馈 | 用 `feedback DESIGN_ID` 核对队列，同一反馈沿用同一请求 ID。已配置模型时可用 `workflow.py --provider environment feedback-process` 处理一条；未获批准的候选继续待审 |
| Gate 8A 和 8B 均可验收 | 当前工作区、实验编号、两个流程的证据，以及用户对 Gate 8 的批准 | 主 Agent 在请求最终批准前准备 UTF-8 Markdown 复盘，写明实际问题、触发条件、处理、验证和遗留限制；如无已知问题据实记录。仅走 Builder 时总结本次搭建。收到批准后运行下方命令 | 同一次调用返回 `knowledge_update`、`newcode`、`newknowledge`，按下文核对后报告完成 | 若已验收但写入失败，解决写入错误后用同一原话和 turn-id 重试，继续归档已保存的草稿 |

```text
python emvr-lab-workflow/scripts/builder.py "PACK" approve-gate --lab-id LAB_ID --gate 8 --note "用户原话" --turn-id TURN_ID --notes "复盘草稿.md"
```

与设计关联的复盘存入 `knowledge/newknowledge/<design_id>/<设计指纹>.md`；独立 Builder 使用 `knowledge/newknowledge/builder/<lab_id>/<验收版本指纹>.md`。草稿由主 Agent 在工作区证据目录准备，只记录与实验有关的事实。旧版已验收的运行可用上述入口补档；状态为待归档时无需再次向用户请求批准。

**Gate 8 的最后一步由主 Agent 整理维护者上传副本。** 将提交名与手册确认一起收集，已知提交名时给上方命令加 `--submitter "名字"`，未指定则沿用构建编号 `lab_id`。默认带上本次复盘；本轮另有新增知识文件时，对每个文件追加一次 `--knowledge-file "相对于 knowledge/newknowledge 的路径"`。沿用本次构建使用的 `--state-dir`（如有）。命令会在状态目录的 `uploads/<lab_id>/` 中生成两个独立的本地上传副本。对照开发手册核对该版本的源码和本地依赖，遇到项目特有的其他源码类型时由 Agent 补入副本并保留相对路径与元数据。核对两个文件夹后给出 `newcode`、`newknowledge` 的完整路径、实验编号和关联的设计编号，让用户自行上传或压缩。手册和复盘已验收但副本整理失败时，说明“Gate 8 已验收，上传副本待整理”，修正错误后运行 `builder.py "PACK" prepare-upload --lab-id LAB_ID`，沿用原提交名及额外知识文件，无需再次批准。[用户提交步骤](../README.md#knowledge-archive)

**新增知识固定写入交付根下的 `knowledge/newknowledge/`。** 原 `knowledge/extensions/` 的内容继续供检索。新增 Markdown、TXT、JSON，或附同名文字索引的 PDF。新建集成 Builder 工作区会得到当时的 `KnowledgeBase/extensions/newknowledge/` 副本。规则审阅保存在所用状态目录的 `design.sqlite3`，知识库复盘供以后检索参考。

| 现有资料 | 相对交付根的位置 |
| --- | --- |
| 课程概念、公式、设计模式和补充索引 | `emvr-lab-workflow/design/src/ece329_workflow/knowledge/` |
| 原始讲义和补充 PDF | `knowledge/sources/` |
| Builder 指南和复建经验 | `reusable-code/EMVR_Blind_BuilderPack/KnowledgeBase/docs/`、`reusable-code/EMVR_Blind_BuilderPack/KnowledgeBase/rebuild-lessons/` |
| Builder 复用档案及准入规则 | `reusable-code/EMVR_Blind_BuilderPack/KnowledgeBase/ReusableCodeArchive/`、`reusable-code/EMVR_Blind_BuilderPack/Policies/` |

外部工程的 Unity 包导入步骤见[使用者 README](../README.md#在自己的-unity-工程中导入-common-包)。若用户要求关闭本地进度页服务，执行 `viewer.py close`。对外静态发布仅使用 `web/` 和用户选定的 `web/data/` 快照。
