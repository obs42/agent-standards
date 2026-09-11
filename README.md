# 共享 Agent 规范

统一维护个人通用 Skill 与开发约定；项目使用本地、带来源记录的副本。日常任务不依赖网络，明确要求同步时才获取更新。

共享仓库：[obs42/agent-standards](https://github.com/obs42/agent-standards)。这是私有仓库，其他电脑首次使用需要 GitHub 账号的读取权限。网页登录和电脑 Git 登录分别进行一次；不把密码或令牌复制到项目中。

## 内容

- `rules/development.md`：通用设计、交付与工具启动约定。
- `skills/module-registry/`：我方模块文档维护。
- `skills/competitor-research/`：竞品结论与证据记录。
- `skills/sync-agent-rules/`：检查和同步以上内容，包括同步器自身。
- `skills/grill-me/`：分轮追问方案，合并旧 `grilling` 正文。
- `skills/handoff/`：会话交接，共用正文加 Codex 操作参考。
- `skills/unity-mcp/`、`skills/unity-scene-rpc/`：按当前服务能力操作 Unity。
- `skills/unity-compile-check/`、`skills/unity-console/`：编译核对与日志定位。
- [个人 Skill 清单](rules/skill-catalog.md)：来源、合并结果及外部包；共 9 个共享 Skill。
- `manifest.json`：明确的分发文件清单；清单外文件不安装。

项目的 TEAM_RULES、架构、竞品结论、账号配置和日志仍由项目维护。本仓库不收集账号凭据或其他工具的内置 Skill。项目定制写在项目规则中，不直接改安装副本。

## 第一次接入

需要 Python 3.10+；远程同步还需要 Git 及仓库读取权限。先取得本仓库本地副本，阅读 Skill 与脚本，然后执行：

```powershell
python skills/sync-agent-rules/scripts/sync_rules.py --source . --project D:/path/to/project --check
python skills/sync-agent-rules/scripts/sync_rules.py --source . --project D:/path/to/project --apply
```

`--source .` 是本地快照方式，适合首次试用。正式接入使用 `--source https://github.com/obs42/agent-standards.git --ref main`；安装会记录真实提交号。同步 Skill 已内置此默认下载地址。不要填写凭据到 URL 中，使用 Git 自身的认证。

安装把 Skill 放入目标项目 `.agents/skills/`，通用原则放入 `.agents/shared/`，仅在 AGENTS.md 末尾维护一个标记区块。原有 AGENTS 内容与 TEAM_RULES 不覆盖。来源、跟踪分支、提交号和已安装内容摘要保存在 `.agents/shared/lock.json`。

## 日后使用

接入后，对读取项目 AGENTS.md 的助手说：**“同步共享规则”**。它会读取本地 sync-agent-rules Skill，检查来源及差异，再更新无冲突内容。无需每次提供 URL 或人工复制。

不读取 AGENTS.md、也不发现 `.agents/skills/` 的工具，首次需在该工具已确认支持的项目入口增加一句：

> 请先读取本项目 AGENTS.md；用户要求同步共享规则时，读取 `.agents/skills/sync-agent-rules/SKILL.md` 并执行。

不猜测工具的配置文件名，不自动修改账号级配置；第一次接入新工具仍需要一次引导。

## 更新与冲突

- `--check` 默认只报告计划与文本差异；`--apply` 执行无冲突更新并记录版本。
- 修改过的安装文件或标记区块会阻止整次更新；先保留本地改动，决定放回项目规则还是修改共享源，再重试。没有强制覆盖选项。
- 更新前备份将被改写的文件到 `.agents/shared/backups/`；该目录内的本地 `.gitignore` 忽略备份，lock 和安装内容可以随项目提交。
- 清单移除的文件保留并报告，不静默删除。同步不会自动提交、推送、执行来自共享仓库的其他脚本或启动业务工具。
- 网络、认证或校验失败保留原安装；不会把没有完成的同步记录为成功。

源仓库变更经测试后再提交和推送；各项目明确同步时才采用新版本。同步只分发说明和清单内资源，不安装 MCP 服务或第三方 CLI。账号下已有同名 Skill 不会被覆盖；实际接入时核对冲突，避免新旧正文同时影响任务。
