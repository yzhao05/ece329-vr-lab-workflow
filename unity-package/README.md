# 在 Unity 中安装

在 Unity 2022.3 的 **Window → Package Manager** 中点 **+ → Add package from tarball…**，选择 [com.emvr.lab-common-0.7.0.tgz](com.emvr.lab-common-0.7.0.tgz)。成功解析后，包列表应显示 **EMVR Lab Common 0.7.0**。包内声明了 Input System、UGUI、XR Interaction Toolkit、XR Management 和 OpenXR 的依赖版本。

此包从 [Builder 的 Common 源目录](../reusable-code/EMVR_Blind_BuilderPack/UnityProject/LocalPackages/com.emvr.lab-common/) 打包，保留程序集、编辑器工具、资源 GUID 和组件源文件。Builder 生成的 Unity 工程直接使用该目录的同版本本地副本；在其他工程中使用上方 tarball 即可。Design 对话与 Builder 审批通过 [统一 Skill](../emvr-lab-workflow/SKILL.md) 执行。
