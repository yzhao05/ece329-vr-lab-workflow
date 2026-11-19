# Builder 可复用代码

| 内容 | 位置 |
| --- | --- |
| 可安装 Unity Package 的 Common 源码、程序集与编辑器工具 | [UnityProject/LocalPackages/com.emvr.lab-common](EMVR_Blind_BuilderPack/UnityProject/LocalPackages/com.emvr.lab-common/) |
| Gate 5 的 Runtime、Editor 和 EditMode 测试 | [ReusableFoundation/Gate5MinimalSlice/Source](EMVR_Blind_BuilderPack/ReusableFoundation/Gate5MinimalSlice/Source/) |
| 房间模型、材质、XR 模板及配套资源 | [ApprovedAssets](EMVR_Blind_BuilderPack/ApprovedAssets/) |
| 原生 Builder 工作流、脚手架与验证命令 | [Tools/labflow](EMVR_Blind_BuilderPack/Tools/labflow/) |
| 复用边界与清单 | [Policies](EMVR_Blind_BuilderPack/Policies/) |

保留 Builder 基础包的内部结构，供每次实验复制独立工作区。创建已确认方案的工作区使用 [统一 Skill](../emvr-lab-workflow/SKILL.md) 中的 `builder-init`。
