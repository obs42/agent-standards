---
name: unity-console
description: 定位 Unity Editor 或 Player 的报错、警告、异常堆栈和复现日志时使用。
---

# Unity 日志定位

先确认目标工程、Editor 或构建包、发生时间。选择项目可用的 MCP / SceneRpc Console 或日志文件；不禁止某一种通道，不为读日志强制安装服务。

文件入口按当前系统解析：Windows Editor 常见位置为 `%LOCALAPPDATA%/Unity/Editor/Editor.log`，macOS 为 `~/Library/Logs/Unity/Editor.log`，Linux 为 `~/.config/unity3d/Editor.log`；优先核对进程的自定义日志参数及实际文件。多实例时不要仅凭默认路径认定归属。

有复现过程时记录起始时间或文件字节偏移，只读之后增量，不清空用户日志。遇到轮转、重启、文件变小或更换，重新建立边界并说明；读取方式需兼容运行中的写入。没有边界时从尾部有限范围查找并注明可能包含历史错误。

围绕相关错误保留前后文和完整关键堆栈，不把全部日志倾倒给用户；输出前移除凭据。构建包改查对应 Player 日志或平台日志，不能用 Editor 的无错状态代替真机结果。

能在授权范围内自行复现就执行，确实需要用户操作时再请求。读取到错误、复现到错误与修复后不再出现分别报告。
