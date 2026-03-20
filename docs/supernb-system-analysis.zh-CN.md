# supernb 系统分析与融合说明

更新时间：2026-03-19

## 1. 先说结论

`supernb` 的本质不是一个新的单体产品，也不是对 `superpowers` 的 fork。

它是一个多上游能力编排层，目标是把下面几类原本分散的能力，组织成一条可执行、可追踪、可认证、可复用的产品交付链路：

1. `superpowers` 负责软件交付方法学。
2. `sensortower-research` 负责市场与竞品证据。
3. `impeccable` 负责 UI/UX 方向与质量治理。
4. 现在由内置 `supernb-loop@supernb` 负责 Claude Code prompt-first planning / delivery 所需的 Ralph Loop 持久执行增强。
5. 本地化 skills 负责把 i18n 变成工程约束，而不是收尾动作。

所以 `supernb` 的设计中心不是“再增加一个更强的 agent”，而是：

- 用 phase gate 管流程
- 用 initiative 管状态
- 用 command brief 管调用入口
- 用 execution packet 管执行证据
- 用 certification 管阶段推进

这就是整个仓库最核心的设计思想。

## 2. `superpowers` 的设计理念

`superpowers` 是 `supernb` 的默认执行底座，但它解决的是“怎么把软件开发做得更像一个纪律系统”，不是“怎么定义产品”。

从代码和 skill 结构看，它的核心思想有 4 条：

### 2.1 先设计，再实现

`skills/brainstorming/SKILL.md` 里把设计评审设成硬门禁：

- 先理解上下文
- 一次只问一个问题
- 给 2-3 个方案和 tradeoff
- 分段呈现设计并获得确认
- 写 spec 文档
- 做 spec review loop
- 用户确认后才允许进入 plan

这说明 `superpowers` 的第一原则是：不要把“编码”当成起点，而要把“规格形成”当成起点。

### 2.2 先 plan，再动代码

`skills/writing-plans/SKILL.md` 强调：

- plan 必须假设执行者几乎没有上下文
- 每个 task 必须小到 2-5 分钟
- 必须给出精确文件路径、代码、验证命令、提交命令
- plan 是给“可机械执行的 agent worker”看的，不是给人类做概览的

这意味着 `superpowers` 的 plan 不是项目管理文档，而是 agent execution contract。

### 2.3 通过 subagent 把执行流水线化

`skills/subagent-driven-development/SKILL.md` 体现了它最强的工程思想：

- controller 不自己吞下所有上下文
- 每个 task 分派全新 subagent
- implementer 和 reviewer 分离
- review 分两层：spec compliance -> code quality
- 每个 task 通过后才进入下一个

这是一套“任务最小化 + 上下文隔离 + 双重审核”的执行架构。

### 2.4 证据优先，而不是“我觉得完成了”

`test-driven-development` 和 `verification-before-completion` 两个 skill 是它的方法学地基：

- 没有 failing test，不允许写生产代码
- 没有 fresh verification evidence，不允许宣称完成

所以 `superpowers` 的设计哲学可以浓缩成一句话：

**把软件开发从“经验驱动的连续 improvisation”改造成“规格驱动、测试驱动、验证驱动的离散流程”。**

## 3. `superpowers` 的内部调用链

在默认理想路径里，`superpowers` 的调用链大致是：

1. `using-superpowers`
2. `brainstorming`
3. `using-git-worktrees`
4. `writing-plans`
5. `subagent-driven-development` 或 `executing-plans`
6. `test-driven-development`
7. `requesting-code-review`
8. `verification-before-completion`
9. `finishing-a-development-branch`

这个链路说明它的真正单位不是“功能”，而是“阶段化软件交付行为”。

其中最关键的关系是：

- `brainstorming` 决定 spec
- `writing-plans` 把 spec 压缩成 agent 可执行任务
- `subagent-driven-development` 把 plan 转成实际代码增量
- `TDD` 和 `verification` 作为每个增量的底层约束

所以 `superpowers` 更像一个 execution operating system，而不是 prompt collection。

## 4. `supernb` 为什么要建立在 `superpowers` 之上

因为 `superpowers` 很强，但它只覆盖了“设计到交付”的软件工程段，不覆盖完整的产品链条。

`supernb` 的判断非常清楚：

- `superpowers` 不负责市场证据
- `superpowers` 不负责商业视角 PRD 证据闭环
- `superpowers` 不负责高质量 UI/UX 审计
- `superpowers` 不把 i18n 当强约束
- `superpowers` 不负责阶段状态机、执行包、认证推进

所以 `supernb` 没有去替换它，而是在它外面再加四层：

1. research layer
2. design governance layer
3. initiative control plane
4. release certification layer

这就是这个仓库最成熟的地方：它没有错误地和上游重复造轮子。

## 5. `supernb` 的设计思想

### 5.1 把“从 idea 到 release”做成 phase-gated system

`docs/architecture.md` 和 `scripts/supernb-run.py` 一致说明，整个系统被拆成 6 个 phase：

1. research
2. prd
3. design
4. planning
5. delivery
6. release

每个 phase 都有：

- 主引擎
- 必要产物
- gate 条件
- 下一阶段前置依赖

这是一种很明显的控制平面思维，而不是 prompt engineering 思维。

### 5.2 initiative 是系统的状态源

`templates/initiative-spec.yaml`、`scripts/init-initiative.sh`、`scripts/supernb-run.py` 表明：

- 每个产品/项目以 initiative 为运行单元
- `.supernb/initiatives/<id>/initiative.yaml` 是 machine-readable source of truth
- 所有阶段、产物、执行、认证都围绕它展开

这让 `supernb` 从“会话式提示词系统”升级成“有状态工作流系统”。

### 5.3 command brief 是统一的人机协议

`commands/*.md` 和 `render-command.sh` / `save-command-brief.sh` 做的事情是：

- 把复杂系统统一成稳定调用格式
- 让 Claude Code / Codex / OpenCode 都吃同一种结构化输入
- 把 phase 目标转成可存档、可重放的 brief

所以 command 在这里不是文档，它是 orchestration protocol。

### 5.4 execution packet 是 `supernb` 的关键增量

`scripts/supernb-execute-next.py` 是整个仓库最关键的代码之一。

它做的不只是“调用 CLI”，而是：

1. 选择当前 phase
2. 选择 harness
3. 渲染 prompt
4. 注入 execution policy
5. 注入 machine-readable report contract
6. 调起 codex / claude
7. 抓取 stdout / stderr / response
8. 记录 git 前后状态
9. 检查是否真的产生 commit
10. 解析 workflow trace
11. 评估 artifact readiness
12. 生成 result suggestion
13. 生成 phase readiness
14. 产出 execution packet

也就是说，`supernb` 的执行单元不是“一次 agent 对话”，而是“一次带审计能力的可回放 execution packet”。

### 5.5 certification 把“产物存在”升级为“阶段可推进”

`scripts/supernb-certify-phase.py` 会检查：

- 模板占位符是否还存在
- section 是否缺失
- section 是否过薄
- 语义准备度是否足够
- planning / delivery 阶段是否具备 superpowers workflow evidence

这一步非常重要，因为它意味着：

`supernb` 不接受“文件写出来了”作为完成标准，而接受“文件结构完整 + 语义充分 + 流程证据完整”作为推进标准。

## 6. `supernb` 的真实调用链

从代码看，完整调用链大致如下：

### 6.1 初始化

1. `./scripts/supernb init-initiative <slug> <title>`
2. `init-initiative.sh` 创建 `.supernb/` 目录树、模板产物、initiative spec、run log、executions 目录

### 6.2 计算当前阶段

1. `./scripts/supernb run --initiative-id <id>`
2. `supernb-run.py` 读取 `initiative.yaml`
3. 根据 research/prd/design/planning/delivery/release 的状态与字段完整度计算 phase
4. 渲染 `next-command.md`
5. 生成 `run-status.md/json`

### 6.3 执行当前阶段

1. `./scripts/supernb execute-next --initiative-id <id>`
2. `supernb-execute-next.py` 读取 `next-command.md`
3. 自动选择 codex / claude / opencode
4. 追加 execution policy 和 response contract
5. 调用 harness
6. 产出 execution packet

### 6.4 回写结果

1. `./scripts/supernb apply-execution --initiative-id <id> --packet <dir>`
2. `supernb-apply-execution.py` 读取 packet 内的 `result-suggestion.json`
3. 调用 `record-result`
4. 可选调用 `certify-phase`
5. 可选自动 apply gate
6. 再次运行 `supernb run`

### 6.5 阶段认证

1. `./scripts/supernb certify-phase --initiative-id <id> --phase <phase>`
2. `supernb-certify-phase.py` 扫描目标 artifact
3. 判断 readiness
4. 生成 certification report
5. 可选调用 `advance-phase`

这是一个很完整的“状态机 + 执行器 + 审计器”设计。

## 7. 所有项目在 `supernb` 中的融合关系

现在可以把全部项目的职责统一起来：

### 7.1 `obra/superpowers`

定位：默认的软件交付引擎

负责：

- brainstorm
- spec
- plan
- TDD
- task execution
- code review
- verification
- worktree discipline

### 7.2 历史上的 `FradSer/dotclaude` `superpowers`

定位：Claude Code 下的可选 persistence enhancer

负责：

- bounded loop execution
- 更强的持续推进能力
- BDD / agent-team 风格增强

它不是默认底座，只是 delivery 阶段的可选强化器。

### 7.3 `pbakaus/impeccable`

定位：设计治理层

负责：

- UI/UX 方向建立
- hierarchy / spacing / contrast / polish 审查
- 设计前生成与设计后审计

它在 `supernb` 里不是“锦上添花”，而是 design gate 和 release audit 的组成部分。

### 7.4 `sensortower-research`

定位：研究证据引擎

负责：

- app lookup
- metadata
- sales / ranking / keyword / creatives
- reviews
- review-insights
- PRD 证据来源

它补的是 `superpowers` 和 `impeccable` 都不覆盖的产品研究层。

### 7.5 `flutter-l10n-translation` / `android-i18n-translation`

定位：本地化治理执行器

负责：

- 外置文案
- 提取硬编码字符串
- 同步 key
- 多语补全
- release 前本地化检查

它们让 i18n 从“建议”变成“交付规则”。

## 8. 整个项目当前最清晰的能力地图

可以把 `supernb` 的能力打成 5 个面：

### 8.1 产品发现能力

- 竞品分析
- 评论洞察
- 用户痛点抽取
- feature opportunity
- anti-feature 识别
- evidence-backed PRD

### 8.2 设计治理能力

- 视觉方向定义
- 页面级 IA 与状态设计
- 可读性 / 对比度 / hierarchy 审核
- 前后设计双审

### 8.3 工程交付能力

- 设计到 plan 的过渡
- 超细粒度 plan 拆解
- TDD
- subagent-driven development
- code review
- verification
- worktree / branch 结束流程

### 8.4 控制平面能力

- initiative 建模
- phase gate 计算
- next-command 生成
- execution packet 记录
- result suggestion
- certification / advance

### 8.5 全球化交付能力

- i18n 资源层约束
- 硬编码文案扫描
- 翻译补全
- 多 locale 交付规则

## 9. 这个系统最值得保留的设计原则

如果后续继续演进 `supernb`，我建议把以下原则视为不可轻易破坏的基线：

1. 不要让 `supernb` 变成 `superpowers` 的重复实现。
2. 不要让 artifact template 压扁 upstream 的 richer outputs。
3. 不要把 phase gate 退化成“写了个文件就算完成”。
4. 不要把 delivery 退化成一次大 prompt 全做完。
5. 不要把 i18n 从工程约束降级为可选事项。
6. 不要让 Ralph Loop 变成默认执行路径；当前实现已经内建到 `supernb-loop@supernb`。
7. 不要失去 execution packet 这层审计与回放能力。

## 10. 对 `supernb` 当前定位的最终定义

综合整个代码库，我认为最准确的表述是：

**`supernb` 是一个以 `superpowers` 为默认软件交付引擎，以 `initiative + phase gate + execution packet + certification` 为控制平面，以 research / design / i18n 为上层治理能力的全链路产品交付编排系统。**

如果再压缩成一句更直接的话：

**`superpowers` 解决“如何严谨地做软件”，`supernb` 解决“如何把产品研究、设计、实现、验证、发布整合成一套完整系统”。**

## 11. 后续建议

基于当前代码，我建议下一步优先做这 4 件事：

1. 在 README 和 docs 里统一一张“能力分层图”，把 research / design / execution / loop / i18n / certification 画成一页。
2. 给 `supernb` 增加一个正式的 capability matrix，明确每个 command、skill、upstream 的职责边界。
3. 给 initiative 流程补一份从 `init-initiative -> run -> execute-next -> apply-execution -> certify-phase` 的时序图。
4. 把 `supernb` 的“设计理念”单独提炼成对外文档，避免用户把它误解成 prompt bundle。
