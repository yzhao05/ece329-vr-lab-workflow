---
name: emvr-lab-workflow
description: 在宿主 Agent 对话中开始或续接 ECE329 电磁学 VR 实验设计、查询课程依据、导出已确认的方案，或从已确认设计和用户自带方案进入 Unity Builder。
---

# ECE329 VR 实验设计与构建

用户在聊天里讨论、修订并确认方案。主 Agent 负责打开流程网页、执行命令、展示证据和可修改的草稿，并把用户的实际决定写回工作流。以下路径均以本文件上一级的**交付根目录**为基准。下文的 `viewer.py`、`workflow.py` 均指 `emvr-lab-workflow/scripts/` 中的同名脚本，用宿主的 Python 3.11+ 执行。例：

```sh
python emvr-lab-workflow/scripts/viewer.py open --new
```

## 启用时先打开网页

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
- **执行步骤**　采用统一 EMVR 规则。结合讲义说明主公式、辅助关系和适用边界，逐步讨论方法与方向。每轮提出一个能推进当前阶段的问题，给出有出处的参考、反馈或可修改的阶段草稿。用 `workflow.py turn DESIGN_ID --message "用户原话" --turn-id TURN_ID` 保存该轮。仅当用户明确确认当前草稿时附加 `--complete-stage`；最终阶段须确认整份方案。用户不用另写学生总结。语言改变时附加 `--language en` 或 `--language zh`。
- **成功后**　按返回的阶段、细项和 `revision` 展示实际修订。普通讨论、引用资料、Agent 自拟草稿均留待用户核对。将适用的 `experience_rules` 纳入本轮反馈。
- **失败时**　按 `completion_error` 补缺项；“前面那个”有多个解释时，用当前可见的候选 ID 澄清。需要结构化解释时，将原话、`turn_id` 和解析结果作为 UTF-8 JSON 传给 `turn DESIGN_ID --stdin-json`。重试同一轮沿用同一 ID 和内容。见[宿主输入协议](references/agent-turns.md)。

## 导出已确认方案

- **触发条件**　用户要导出，或准备把本 Skill 的设计交给 Builder。
- **所需输入**　设计编号和要交付的已确认版本。核对 `show` 的 `check.report_ready` 与 `check.builder_ready`，二者对应引擎的 `report_ready` 和 `builder_input_ready`。
- **执行步骤**　两项均为真时运行 `workflow.py export DESIGN_ID`。默认使用当前对话语言；用户指定其他语言时附加 `--language en` 或 `--language zh`。一次性的导出语言选择仅适用于该次文件。
- **成功后**　从返回的 `artifacts` 路径交付同一版本的 `design.pdf`、`builder-gate1-input.pdf`、`builder-gate1-input.json`，说明版本及语言。不同语言各存一份展示文件，共用原方案机器标识。
- **失败时**　未就绪则回到具体待确认项。若返回 `translation_required`，把 `translations` 对象写为 UTF-8 JSON，逐条译成目标语言，保留原文键、数值、公式、对象 ID 和路径；给原命令追加 `--translations 文件路径` 重试，直到返回 `artifacts`。

## 进入或续接 Builder

详细规程集中在 [builder-workflow.md](../reusable-code/EMVR_Blind_BuilderPack/.agents/skills/build-unity-vr-lab-blind/builder-workflow.md)。选定工作区后读取**该工作区内**的同名文件，从 **Create or resume a run** 及当前 Gate 开始。该文件还说明主 Agent 应在何时从交付根调用代码归档工具，固定目标为 `reusable-code/newcode/`。

| 触发条件 | 所需输入 | 执行步骤 | 成功后的动作 | 失败后的处理 |
| --- | --- | --- | --- | --- |
| 构建在本 Skill 中已确认的设计 | `design_id`、已确认版本和交接语言 | 打开该设计的页面，核对导出就绪状态，运行 `workflow.py builder-init DESIGN_ID`，语言覆盖与翻译重试方式同导出。核对 `revision`、`builder_inputs` 与目标版本 | 沿用设计标签页，进入返回的 `builder_workspace`，以工作区 `LabSpecs/<lab_id>/design-input/` 中该版 PDF 和 JSON 为依据，查询当前 Gate | 未就绪则返回原设计；指定的是其他修订时先澄清版本。重试时沿用相同设计和版本。已建工作区保留建档时的输入语言 |
| 用户已有外部方案，只想搭建 | 用户提供的方案文件或正文、所选版本、实验标识及目标工作区 | 有多个版本先请用户指定。按规程选定独立工作区和 `lab_id`，打开其 Builder 页，以指定方案作为需求依据。按规程建档或续接。新实验使用 integrated-development；明确要求盲重建才走 blind-rebuild。手册语言可在原生 `new` 指定 `--manual-language` | 在运行工作区执行 `python Tools/labflow/labflow.py status --lab-id LAB_ID`，说明采用的版本、当前 Gate、待确认事项，直接与用户讨论构建 | 缺少文件、版本或关键要求时仅追问缺项。在本路径中保持 Builder 身份，不为附件创建 Design 会话 |
| 继续已有 Builder | 已关联的设计编号，或工作区与 `lab_id` | 关联设计打开设计页；独立运行打开绑定工作区与 `lab_id` 的页面。在原工作区运行上述 `status` | 依据实际状态从当前 Gate 和待确认项继续 | 有多个工作区或编号时先让用户选择；状态读取失败时核对原路径和标识，再重试 |

## 资料、反馈与完成后复盘

| 触发条件 | 所需输入 | 执行步骤 | 成功后的动作 | 失败后的处理 |
| --- | --- | --- | --- | --- |
| 查课程依据、设计经验或构建参考 | 问题中的概念、用途 | 用 `workflow.py knowledge "关键词" --scope design` 或 `--scope builder` 检索[知识库目录](../knowledge/catalog.json) | 引用讲义标题和真实页码，或来源文件的相对路径和行号 | 缩小关键词或回到索引核对，说明仍缺少的依据 |
| 用户反馈某轮有误，或维护者要审阅经验规则 | 设计编号、具体问题和稳定的 `request_id`；审阅时需要候选版本 | 用 `workflow.py feedback DESIGN_ID --submit` 从 UTF-8 JSON 输入提交，如 `{"message":"修改没有更新到草稿","category":"cross_stage_edit","request_id":"feedback-turn-004"}`。用 `feedback-process --ticket TICKET_ID` 读取证据和格式，再用同一命令加 `--candidate 文件路径` 提交含 `ticket_id`、`candidate` 的分析。维护者明确审阅后，用 `experience-review EXPERIENCE_ID` 从 JSON 输入提交 `decision`、`version`、`note`，可执行规则还需原生验证凭证 | 保存工单号，后续依据实际启用并返回的 `experience_rules` 调整反馈 | 用 `feedback DESIGN_ID` 核对队列，同一反馈沿用同一请求 ID。已配置模型时可用 `workflow.py --provider environment feedback-process` 处理一条；未获批准的候选继续待审 |
| 同一实验完成 Design 和 Builder，且 Gate 8 两本手册均已批准 | 关联设计编号、已验收的版本、两个流程的实际问题与证据 | 主 Agent 用 UTF-8 Markdown 记录问题、触发条件、处理方法、验证结果和仍有限制；没有遇到问题时据实记录。执行 `workflow.py retrospective DESIGN_ID --notes 文件路径` | 核对返回的 `knowledge_update` 位于 `knowledge/newknowledge/<design_id>/<设计指纹>.md`。同版本重试更新同一记录 | 尚未完成时回到对应工作区核对状态；等到条件满足后再提交复盘 |

**新增知识固定写入交付根下的 `knowledge/newknowledge/`。** 原 `knowledge/extensions/` 的内容继续供检索。新增 Markdown、TXT、JSON，或附同名文字索引的 PDF。新建集成 Builder 工作区会得到当时的 `KnowledgeBase/extensions/newknowledge/` 副本。规则审阅保存在所用状态目录的 `design.sqlite3`，知识库复盘供以后检索参考。

| 现有资料 | 相对交付根的位置 |
| --- | --- |
| 课程概念、公式、设计模式和补充索引 | `emvr-lab-workflow/design/src/ece329_workflow/knowledge/` |
| 原始讲义和补充 PDF | `knowledge/sources/` |
| Builder 指南和复建经验 | `reusable-code/EMVR_Blind_BuilderPack/KnowledgeBase/docs/`、`reusable-code/EMVR_Blind_BuilderPack/KnowledgeBase/rebuild-lessons/` |
| Builder 复用档案及准入规则 | `reusable-code/EMVR_Blind_BuilderPack/KnowledgeBase/ReusableCodeArchive/`、`reusable-code/EMVR_Blind_BuilderPack/Policies/` |

外部工程的 Unity 包导入步骤见[使用者 README](../README.md#在自己的-unity-工程中导入-common-包)。若用户要求关闭本地进度页服务，执行 `viewer.py close`。对外静态发布仅使用 `web/` 和用户选定的 `web/data/` 快照。
