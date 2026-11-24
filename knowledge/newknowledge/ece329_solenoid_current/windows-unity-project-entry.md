# Windows 重启后恢复已验收的 Builder 实验

本次交付的手册清单和代码归档均对应验收版本 `9837A290F86A9F5B9AE131B99EE3E94F5B13ECB9F1F536CBDF882BA1CFF759B9`。学生手册为 2 页，单实验开发者手册为 3 页，增补后的项目总手册为 56 页。已核对三份 PDF 和两份 DOCX 与各自生成或导出记录的 SHA-256。

用户重启 Windows 后，原先通过 `subst` 创建的 Z 盘消失。从原长路径打开场景时，截图显示基础测试通过 10 项，同时 Console 有一条指向深层生成目录的 `DirectoryNotFoundException`。截图没有显示完整文件名，无法据此判定哪个资源缺失。

遇到这个现象时，从当前交付根运行 `python emvr-lab-workflow/scripts/builder.py ece329_solenoid_current unity-project`。其他实验换成相应编号。将输出的持久目录联接作为 Unity Hub 的工程入口。若原长路径工程正在编辑，先保存并关闭，再从新条目打开。继续使用原工作区的场景、归档和 Gate 记录。

复查时清空 Console，重复触发原错误的操作。若仍有红色错误，记录第一条完整路径和调用栈，再分别检查资源是否存在以及 Unity 实际打开的工程目录。本次交付未附场景，截图中的模拟手柄也不能作为已完成实体头显验收的证据。
