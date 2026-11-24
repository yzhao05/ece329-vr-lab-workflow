# Builder 可复用代码

| 内容 | 位置 |
| --- | --- |
| 可安装 Unity Package 的 Common 源码、程序集与编辑器工具 | [UnityProject/LocalPackages/com.emvr.lab-common](EMVR_Blind_BuilderPack/UnityProject/LocalPackages/com.emvr.lab-common/) |
| Gate 5 的 Runtime、Editor 和 EditMode 测试 | [ReusableFoundation/Gate5MinimalSlice/Source](EMVR_Blind_BuilderPack/ReusableFoundation/Gate5MinimalSlice/Source/) |
| 房间模型、材质、XR 模板及配套资源 | [ApprovedAssets](EMVR_Blind_BuilderPack/ApprovedAssets/) |
| 原生 Builder 工作流、脚手架与验证命令 | [Tools/labflow](EMVR_Blind_BuilderPack/Tools/labflow/) |
| 复用边界与清单 | [Policies](EMVR_Blind_BuilderPack/Policies/) |

保留 Builder 基础包的内部结构，供每次实验复制独立工作区。创建已确认方案的工作区使用 [统一 Skill](../emvr-lab-workflow/SKILL.md) 中的 `builder-init`。

Gate 8 由 Agent 对照已验收工程补齐 Gate 6 源码归档的依赖，整理好 `名字_newcode` 和 `名字_newknowledge` 两个上传副本。用户按 Agent 给出的路径提交给维护者。[用户提交步骤](../README.md#knowledge-archive)

### 复用已归档的螺线管实验源码

Gate 6 会将选定的源码及其 Unity 元数据写入 `newcode/<lab_id>/<验收指纹>/`。螺线管示例的场景构建器和交互脚本依赖 Common、Gate 5A 基础组件，以及绘制散点图的 `SolenoidScatterPlot`。用户提供的 ZIP 包含三个实验脚本，没有附上绘图组件。

在干净工程中重建该示例时，先准备 Common 和 Gate 5A 基础组件，然后把归档中的 `Editor/`、`Scripts/` 及元数据复制到工程的 `Assets/` 下。如果工程中缺少 `SolenoidScatterPlot`，将[补充的绘图组件](companions/ece329_solenoid_current/SolenoidScatterPlot.cs)连同相邻的 `.meta` 放入运行时脚本目录。这个补充实现按原面板的坐标范围绘制理论虚线和已记录的测量点。已有验收场景应继续使用自己的原组件和 GUID。

**Reusing the solenoid example.** Prepare Common and the Gate 5A foundation, then copy the archived `Editor/` and `Scripts/` folders with their metadata into the project's `Assets/`. The supplied ZIP omits the scatter plot component referenced by the sample. For a fresh build, add the [companion plotting script](companions/ece329_solenoid_current/SolenoidScatterPlot.cs) and its adjacent `.meta` to a runtime scripts folder if that type is missing. An existing accepted scene should keep its original component and GUID.
