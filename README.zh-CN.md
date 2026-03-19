# supernb

[English](./README.md) | [简体中文](./README.zh-CN.md)

`supernb` 是一个编排层，它把 5 类能力组合成一条产品开发工作流：

- 使用最新 `obra/superpowers` 作为默认的规划和交付引擎
- 使用 `superpowers@frad-dotclaude` 作为 Claude Code 下可选的 loop 执行增强层
- 使用 `impeccable` 负责 UI/UX 生成、审查、design system 定义和落地后的质量控制
- 内置 `sensortower-research` 用于竞品调研、评论挖掘和有证据支撑的 PRD 产出
- 内置翻译 skills 用于本地化提取、key 同步和多语言补全

`supernb` 的目标不是生成一个 MVP，而是把“产品想法 -> 调研 -> PRD -> 设计 -> 实现 -> 验证 -> 商业化交付”变成可重复执行的流程，并默认以千万 DAU 级产品标准来要求各个环节，而不是按 demo 水平交付。

`supernb` 本身与框架无关。平台、技术栈、语言、仓库形式都来自用户需求和项目上下文，而不是系统内部写死的前提。

`supernb` 同时把国际化当成强约束：无论是 app 还是 web，面向用户的文案都不允许硬编码在代码里。

## 这个仓库是什么

这个仓库不会去 fork 并重写上游项目，而是作为协调层存在：

- `skills/` 定义 `supernb` 自己的编排规则
- `bundles/` 存放可直接分发的一次性安装 skills
- `scripts/` 负责同步上游仓库、安装、更新和控制平面
- `docs/` 记录架构、上游分析和安装文档
- `artifacts/` 是 research、PRD、design、plan、release 的产物工作区

它有两件核心工作：

- 负责完整产品交付编排
- 负责把所有已集成上游能力路由到最合适的单项 skill
- 提供稳定的命令入口
- 提供基于 initiative spec 的执行控制平面

`supernb` 自带的模板和产物目录是增量层，不是替代层。它们的作用是承接和组织输出，而不是缩减 upstream `superpowers` 原生文档能力。

## 分发模型

`supernb` 目前有两条分发路径：

- 最新 upstream 仓库不会直接 vendoring 进 git，bootstrap 会把它们拉到本地 `upstreams/`
- 本地分发型 skills 会提交在 `bundles/skills/` 下，方便首次安装时一次补齐

安装器默认是幂等的：

- 如果目标 skill 或 plugin 已存在，就跳过
- 如果缺失，就自动补装
- Claude Code 默认 `superpowers` plugin 缺失时会自动安装
- OpenCode 项目的 `opencode.json` 会自动补上 upstream `superpowers`

## 上游项目

基于 2026-03-19 本地检查结果：

- `obra/superpowers`
  - 包版本：`5.0.4`
  - 提供成熟的 skills 驱动软件交付流程
  - 关键能力：brainstorming、plans、TDD、subagent-driven development、review、worktrees
- `FradSer/dotclaude`
  - 相关 plugin：`superpowers` 版本 `2.0.0`
  - 关键增强：BDD 导向执行，以及可选的 Superpower Loop 状态 / hook 自动化
  - `ralph-loop` 在这里不是单独仓库，而是 `scripts/setup-superpower-loop.sh` 和 `hooks/stop-hook.sh` 里的 loop 机制
- `pbakaus/impeccable`
  - 包版本：`1.5.1`
  - 提供跨 provider 的设计 skill 系统和构建管线
- 内置 `sensortower-research`
  - 一个 Python CLI 包装层，用来调用校验过的 Sensor Tower 接口并做评论洞察
- 内置翻译 skills
  - `flutter-l10n-translation` 用于 Flutter ARB 本地化
  - `android-i18n-translation` 用于 Android `strings.xml` 提取和多语言翻译

更多细节见：[docs/upstream-analysis.md](./docs/upstream-analysis.md)

## 工作流

`supernb` 强制执行一个有 gate 的流程：

1. 先做 research。先做竞品、评论、功能机会分析，再写 PRD。
2. 再做 PRD。每份 PRD 都必须回指 research window 和竞品证据。
3. 再做 design。用 `impeccable` 定义视觉方向、design system、关键旅程页面，以及对比度、可读性和交互质量规则。
4. 再做 implementation。用最新 `superpowers` 做规划、测试先行、执行和验证；只有当 Claude Code 任务确实需要有限持久循环时，才启用 Frad loop。
5. 持续提交。每个经过验证的 batch 都应该提交到 git。

架构说明见：[docs/architecture.md](./docs/architecture.md)

## 快速开始

最快安装方式：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh)
```

如果自动探测不明确：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness codex
```

安装后可以先用这三个主命令入口：

```bash
./scripts/supernb show-command full-product-delivery
./scripts/supernb render-command --command full-product-delivery --goal "Build a 1000W DAU 级产品" --product-category "finance" --markets "SEA" --research-window "last 90 days" --stack "your stack" --quality-bar "10m-dau-grade"
./scripts/supernb save-command --command full-product-delivery --title "1000W DAU 交付 Brief" --goal "Build a 1000W DAU 级产品" --product-category "finance" --markets "SEA" --research-window "last 90 days" --stack "your stack" --quality-bar "10m-dau-grade"
```

新手指南见：[docs/quickstart.md](./docs/quickstart.md)

## Keys 和环境变量

`supernb` 本身不是“必须先配一堆 key 才能启动”的项目。  
安装、编排、PRD、design、delivery 流程默认都不要求额外凭证。只有当你真的调用某些 bundled skills 时，才需要对应环境变量。

推荐原则：

- 尽量把 key 配在启动 harness 的 shell 环境里，例如 `~/.zshrc` 或 `~/.bashrc`
- 改完环境变量后，重启 Claude Code / Codex / OpenCode，让新会话继承这些变量
- 不要把真实 key 写进仓库、`initiative.yaml`、command brief 或 git 提交

常见配置方式：

```bash
echo 'export SENSORTOWER_AUTH_TOKEN="st_your_token"' >> ~/.zshrc
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
source ~/.zshrc
```

或者只在当前终端会话里临时配置：

```bash
export SENSORTOWER_AUTH_TOKEN="st_your_token"
export OPENAI_API_KEY="sk-..."
```

环境变量说明：

| Key | 用途 | 是否必须 | 建议配置位置 | 说明 |
| --- | --- | --- | --- | --- |
| `SENSORTOWER_AUTH_TOKEN` | `sensortower-research` 主 API token | 只在使用 Sensor Tower 调研时必须 | `~/.zshrc` / `~/.bashrc` / 启动 harness 的 shell | 推荐优先使用这个名字 |
| `SENSORTOWER_AUTH_TOKEN_BACKUP` | `sensortower-research` 备用 token | 可选 | 同上 | 主 token 限流或失败时回退 |
| `SENSORTOWER_API_TOKEN` | `sensortower-research` 兼容别名 | 可选 | 同上 | 如果已经配了 `SENSORTOWER_AUTH_TOKEN`，通常不需要再配 |
| `SENSOR_TOWER_API_TOKEN` | `sensortower-research` 兼容别名 | 可选 | 同上 | 同上 |
| `SENSORTOWER_API_TOKEN_BACKUP` | `sensortower-research` 备用 token 兼容别名 | 可选 | 同上 | 同上 |
| `SENSOR_TOWER_API_TOKEN_BACKUP` | `sensortower-research` 备用 token 兼容别名 | 可选 | 同上 | 同上 |
| `OPENAI_API_KEY` | `flutter-l10n-translation`、`android-i18n-translation` 以及相关翻译脚本的 OpenAI 模式 | 只在使用 AI 翻译补全时必须 | `~/.zshrc` / `~/.bashrc` / 启动 harness 的 shell | 也可以改用脚本的 `--api-key` 参数，但环境变量更适合跨 harness |

可以这样理解“是否必须”：

- 如果你只是用 `supernb` 做编排、PRD、UI/UX、代码实现，一般不需要额外 key
- 如果要用 `sensortower-research`，至少配置一个 Sensor Tower token，推荐 `SENSORTOWER_AUTH_TOKEN`
- 如果要用 OpenAI 翻译补全，配置 `OPENAI_API_KEY`
- `android-i18n-translation` 的 `--provider google` 路径在当前仓库里不要求额外环境变量；只有 OpenAI 路径需要 `OPENAI_API_KEY`

建议优先使用的标准命名：

```bash
export SENSORTOWER_AUTH_TOKEN="st_your_token"
export OPENAI_API_KEY="sk-..."
```

这样最不容易和内置 skill 文档、CLI 脚本以及后续排查流程产生偏差。

## 安装与更新

bootstrap 当前会做这些事：

- 同步 `superpowers`、`dotclaude`、`impeccable`
- 安装 bundled `sensortower-research`、`flutter-l10n-translation`、`android-i18n-translation`
- 已安装的 skills 不重复覆盖
- 在隔离本地缓存里构建 `impeccable`
- Claude Code 缺失默认 `superpowers` plugin 时自动安装
- OpenCode 项目配置里自动补上 `superpowers` plugin entry

统一更新命令：

```bash
make update
```

这个命令会：

- 在仓库干净且位于默认分支时更新 `supernb` 自身
- 如果 worktree 脏了，或当前不在默认分支，就安全跳过 self-update
- 更新 `superpowers`、`dotclaude`、`impeccable`
- 默认重建 `impeccable`
- 把 JSON 和 Markdown 更新报告写到 `artifacts/updates/`

如果你只想更新 upstream cache：

```bash
make update-upstreams
```

如果你已经 clone 了仓库：

```bash
make bootstrap
```

当前项目下直接安装 Claude Code 资产：

```bash
./scripts/supernb build-impeccable
./scripts/supernb install-claude-code .
```

如果你安装到 `"$HOME"`，那受管的 Claude Code skills 会放在 `~/.claude/skills/`。这种用户全局安装模式下，具体业务项目里没有自己的 `.claude/` 目录也是正常的。

如果你要显式指定 harness / project：

```bash
make bootstrap HARNESS=claude-code PROJECT_DIR=/path/to/project
make bootstrap HARNESS=opencode PROJECT_DIR=/path/to/project
make bootstrap HARNESS=codex
```

详细安装文档：

- Claude Code: [docs/install/claude-code.md](./docs/install/claude-code.md)
- Claude Code loop mode: [docs/install/claude-code-loop-mode.md](./docs/install/claude-code-loop-mode.md)
- Codex: [docs/install/codex.md](./docs/install/codex.md)
- OpenCode: [docs/install/opencode.md](./docs/install/opencode.md)

## 默认与可选引擎

- 所有支持 harness 的默认基线：最新 `obra/superpowers`
- Claude Code 下的可选增强层：`superpowers@frad-dotclaude`
- `execute-next` 目前只对 Codex 和 Claude Code 提供 direct bridge。OpenCode 仍然是“准备 prompt + 手动执行”的路径。
- 不要在同一个 Claude Code 环境里并列安装两个同名 `superpowers` plugin
- 在 `supernb` 里，`dotclaude` 被视为执行增强层，而不是主工作流底座

## Initiative 控制平面

新 initiative 的标准入口：

```bash
./scripts/supernb init-initiative my-product "My Product"
./scripts/supernb run --initiative-id 2026-03-19-my-product
```

这一套会：

- 默认在产品项目里创建 `.supernb/initiatives/<initiative-id>/initiative.yaml`
- 创建 initiative 局部的 `run-status.md` 和 `next-command.md`
- 创建 initiative 局部的 `certification-state.json`，作为 phase certification 的真相源
- 创建 initiative 局部的 `phase-packet.md`、`run-log.md` 和归档 `command-briefs/`
- 创建 initiative 局部的 `phase-results/`
- 创建 initiative 局部的 `executions/`
- 为每次 execution 生成 `prompt-with-report.md`、`result-suggestion.md/json`、`phase-readiness.md/json`
- 计算当前 phase 是 blocked、ready 还是 complete
- 在下一阶段 ready 时生成结构化 command brief

新产品 initiative 推荐流程：

1. 运行 `./scripts/supernb init-initiative my-product "My Product"`。
2. 在产品项目里的 `.supernb/initiatives/<initiative-id>/initiative.yaml` 中填写信息。
3. 运行 `./scripts/supernb run --initiative-id <initiative-id>`。
4. 用 `./scripts/supernb execute-next --initiative-id <initiative-id> [--harness ... --project-dir ...]` 执行当前 phase。
   直接通过 Codex 或 Claude Code 执行时，回复里必须带结构化 `REPORT JSON` block；否则 packet 会被降级成 `needs-follow-up`，不能干净通过 certification。
   `--dry-run` 只用于预演，certification 会优先选择最新的真实非 dry-run packet。
   如果是 OpenCode，这一步会先准备 execution packet 和 prompt，再由你在 OpenCode 里手动执行。
5. 用 `./scripts/supernb apply-execution --initiative-id <initiative-id> --packet <execution-packet-dir> [--certify|--apply-certification]` 回写执行结果。
6. 对 OpenCode 或其他手动执行场景，用 `./scripts/supernb import-execution --initiative-id <initiative-id> --phase <phase> --report-json /path/to/report.json` 导入结构化执行结果，再应用该 packet。
7. 如果你需要单独认证某个阶段，运行 `./scripts/supernb certify-phase --initiative-id <initiative-id> --phase <phase>`。
8. 只有在你想覆盖 packet 建议时，才手动运行 `./scripts/supernb record-result ...`。
9. 只有在你想绕过认证助手时，才手动运行 `./scripts/supernb advance-phase ...`。

如果是此前已经创建过的旧 initiative，想升级到更深的模板和更严格的 gate：

1. 运行 `./scripts/supernb upgrade-artifacts --initiative-id <initiative-id>`。
2. 补齐现有 research、PRD、design、plan、release 文档中新增的章节。
3. 再次运行 `./scripts/supernb run --initiative-id <initiative-id>`，并重新做对应 phase 的 certification。

如果是更早期的松散 `.supernb` 项目，还没有 initiative 结构：

1. 先运行 `./scripts/supernb init-initiative ...` 创建新 initiative。
2. 再运行 `./scripts/supernb migrate-legacy --initiative-id <initiative-id> [--legacy-root /path/to/.supernb]`。
3. 检查 `legacy-import/`，把需要保留的内容并回 initiative 作用域文档，然后重新执行 `./scripts/supernb run`。

如果经过大量 dry-run 和重试后需要清理产物：

- 用 `./scripts/supernb clean-initiative --initiative-id <initiative-id>` 预览旧 command brief、dry-run packet、unsupported packet 和较旧 execution artifact。
- 仅在确认预览结果后，再加 `--apply` 真正删除。

## 常用命令

```bash
make update
make update-upstreams
make bootstrap
make install-claude-code PROJECT_DIR=/path/to/project
make verify-installs
make build-impeccable
make init-initiative INITIATIVE=my-product TITLE="My Product"
make run-initiative INITIATIVE_ID=2026-03-19-my-product
make execute-next INITIATIVE_ID=2026-03-19-my-product HARNESS=codex PROJECT_DIR=/path/to/repo DRY_RUN=1
make apply-execution INITIATIVE_ID=2026-03-19-my-product PACKET=/path/to/packet CERTIFY=1
make import-execution INITIATIVE_ID=2026-03-19-my-product PHASE=delivery REPORT_JSON=/path/to/report.json
make certify-phase INITIATIVE_ID=2026-03-19-my-product PHASE=research
make upgrade-artifacts INITIATIVE_ID=2026-03-19-my-product
make migrate-legacy INITIATIVE_ID=2026-03-19-my-product LEGACY_ROOT=/path/to/.supernb
make clean-initiative INITIATIVE_ID=2026-03-19-my-product
make test
make record-result INITIATIVE_ID=2026-03-19-my-product STATUS=succeeded SUMMARY="Research batch finished"
make advance-phase INITIATIVE_ID=2026-03-19-my-product PHASE=research STATUS=approved ACTOR="supernb"
make check-copy
make init-i18n STACK=web TARGET_LOCALES="zh-CN,ja"
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a 1000W DAU 级 finance app" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" QUALITY_BAR="10m-dau-grade" STACK="flutter"
make save-command COMMAND=full-product-delivery TITLE="1000W DAU Finance App Brief" GOAL="Build a 1000W DAU 级 finance app" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" QUALITY_BAR="10m-dau-grade"
make install-codex
make install-claude-code
make install-opencode
```

也可以直接用脚本：

```bash
./scripts/supernb update-upstreams
./scripts/supernb update
./scripts/supernb bootstrap
./scripts/supernb install-claude-code /path/to/project
./scripts/supernb verify-installs --project-dir /path/to/project
./scripts/supernb build-impeccable
./scripts/supernb init-initiative my-product "My Product"
./scripts/supernb run --initiative-id 2026-03-19-my-product
./scripts/supernb execute-next --initiative-id 2026-03-19-my-product --harness codex --project-dir /path/to/repo --dry-run
./scripts/supernb apply-execution --initiative-id 2026-03-19-my-product --packet /path/to/packet --certify
./scripts/supernb import-execution --initiative-id 2026-03-19-my-product --phase delivery --report-json /path/to/report.json
./scripts/supernb certify-phase --initiative-id 2026-03-19-my-product --phase research
./scripts/supernb upgrade-artifacts --initiative-id 2026-03-19-my-product
./scripts/supernb migrate-legacy --initiative-id 2026-03-19-my-product --legacy-root /path/to/.supernb
./scripts/supernb clean-initiative --initiative-id 2026-03-19-my-product
./scripts/supernb test
./scripts/supernb record-result --initiative-id 2026-03-19-my-product --status succeeded --summary "Research batch finished"
./scripts/supernb advance-phase --initiative-id 2026-03-19-my-product --phase research --status approved --actor "supernb"
./scripts/supernb check-copy
./scripts/supernb init-i18n --stack web --target-dir . --target-locales "zh-CN,ja"
./scripts/supernb show-command full-product-delivery
./scripts/supernb render-command --command full-product-delivery --goal "Build a 1000W DAU 级 finance app" --product-category finance --markets SEA --research-window "last 90 days" --quality-bar "10m-dau-grade" --stack flutter
./scripts/supernb save-command --command full-product-delivery --title "1000W DAU Finance App Brief" --goal "Build a 1000W DAU 级 finance app" --product-category finance --markets SEA --research-window "last 90 days" --quality-bar "10m-dau-grade"
```

## 仓库结构

```text
supernb/
├── artifacts/
│   ├── commands/
│   ├── design/
│   ├── initiatives/
│   ├── plans/
│   ├── prd/
│   ├── releases/
│   └── research/
├── bundles/
│   └── skills/
├── commands/
├── docs/
├── scripts/
├── skills/
└── upstreams/        # 本地缓存，不提交进 git
```

## 更多文档

工作流说明：[docs/workflows/end-to-end.md](./docs/workflows/end-to-end.md)

使用场景：[docs/usage-scenarios.md](./docs/usage-scenarios.md)

能力矩阵：[docs/capability-matrix.md](./docs/capability-matrix.md)

i18n 指南：[docs/i18n-stack-guidance.md](./docs/i18n-stack-guidance.md)

initiative spec：[docs/initiative-spec.md](./docs/initiative-spec.md)

命令入口：[commands/README.md](./commands/README.md)

harness mapping：[docs/commands/README.md](./docs/commands/README.md)

## 备注

- bundled `sensortower-research` 仍然要求你配置有效的 Sensor Tower token
- 所有用户可见文案都应该外置到本地化资源，而不是硬编码在代码里
- `impeccable` 的 bundle 是从源码构建到 `.supernb-cache/impeccable-dist`，不会直接提交
- `upstreams/` 有意作为本地 cache 存在，这样 `supernb` 可以跟踪最新上游代码而不把整个上游仓库直接 vendoring 进 git
