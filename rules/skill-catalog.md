# 个人 Skill 清单

整理日期：2026-09-11。本清单覆盖本次发现的个人安装目录；插件市场缓存不等于已安装清单，不批量导入。同步器按 manifest 安装 9 个共享 Skill，具体来源位置由本机确定，不要求其他电脑具有原路径。

| 共享名称 | 来源与处理 |
|---|---|
| module-registry | 原 wool 项目 Skill，维护模块信息 |
| competitor-research | 原 wool 项目 Skill，维护竞品证据与结论 |
| sync-agent-rules | 共享仓库同步器，保护项目定制 |
| grill-me | CodeBuddy 个人目录的 grill-me 与 grilling 合并；保留分轮追问，去除强制委派、穷尽所有分支和额外确认门槛 |
| handoff | CodeBuddy 的文档交接与 Codex 的新任务交接合并；Codex 的命名、原工作区、旧任务标记等个人偏好保留在参考文档 |
| unity-compile-check | CodeBuddy 个人目录；提取编译覆盖与证据要求，移除其他工程机器表、SVN 门禁、强改字符串及故意插错要求 |
| unity-console | CodeBuddy 个人目录；保留增量日志方法，移除禁止 MCP 和本机用户名绑定 |
| unity-scene-rpc | CodeBuddy 个人目录；保留目标工程核对与异步验证，具体 endpoint 查项目实际文档，移除每次抢焦点和外部脚本硬路径 |
| unity-mcp | WorkBuddy 的 unity-mcp-skill；整理为独立操作指引，不复制工具版本全表，不保证批处理原子性 |

以上是经过整理的共享版本，原个人目录未删除、覆盖或改成兼容入口；旧 grilling 名称不另分发一个重复 Skill，使用 grill-me。维护后续规则以本仓库为源，项目独有决定仍放项目入口。

## 保留外部来源的完整包

| 名称 | 本机元数据记录 | 使用与维护 |
|---|---|---|
| mp-cli-sup | SkillHub，slug `mp-cli-sup`，0.2.1 | 小程序运行时调试；含 CLI 契约、脚本与验证资源，需要实际 vince-mp 环境。按来源安装完整包，不仅复制 SKILL.md |
| unity-game-dev | SkillHub，slug `unity-game-dev`，2.0.0 | 通用 Unity 教程与示例集；按需从来源安装，不作为所有 Unity 任务的必读规则 |

上述来源和版本由本机 `_skillhub_meta.json` 读取，本次未联网确认下载地址、更新版本或可用性，未执行第三方脚本。需要安装时先核对可访问的发布源、完整依赖与适用条款。共享仓库不冒充这些包的上游。

## Skill 与实际工具

Unity MCP Skill 是使用说明，MCP 服务、Unity 插件和客户端连接需要各环境实际配置；SceneRpc Skill 同样依赖产品已接入的服务。不要复制包含令牌的 MCP 配置来实现同步。官方插件自带的 Skill 由插件安装和更新，本仓库只维护个人约定及来源记录。
