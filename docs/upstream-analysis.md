# Upstream Analysis

This file records what was actually inspected in the local clones on 2026-03-19, not just what the landing pages claim.

## `obra/superpowers`

Repository role: baseline development workflow engine.

Observed structure:

- `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`
- `.codex/INSTALL.md`
- `.opencode/INSTALL.md`
- `skills/brainstorming/`
- `skills/writing-plans/`
- `skills/executing-plans/`
- `skills/subagent-driven-development/`
- `skills/test-driven-development/`
- `skills/requesting-code-review/`
- `skills/systematic-debugging/`
- `tests/claude-code/`, `tests/opencode/`, `tests/skill-triggering/`

What it is:

- a multi-skill software delivery system
- optimized around planning discipline, TDD, review gates, and agent execution
- already adapted for Claude Code, Codex, OpenCode, Cursor, and Gemini

What matters for `supernb`:

- it is the cleanest upstream foundation for implementation planning and execution
- its Codex and OpenCode install docs are already good enough to reuse
- its strength is software execution discipline, not market research or UI review

## `FradSer/dotclaude`

Repository role: plugin marketplace with multiple Claude Code plugins.

Observed structure:

- `.claude-plugin/marketplace.json`
- plugin folders like `git/`, `gitflow/`, `github/`, `review/`, `office/`, `superpowers/`
- `superpowers/scripts/setup-superpower-loop.sh`
- `superpowers/hooks/stop-hook.sh`
- `superpowers/skills/behavior-driven-development/`
- `superpowers/skills/agent-team-driven-development/`

What it is:

- a curated plugin marketplace for Claude Code
- the relevant piece for `supernb` is the `superpowers@frad-dotclaude` plugin
- that plugin adds BDD-focused execution and a stronger agent-team story than upstream `obra/superpowers`

What the so-called `ralph-loop` is in practice:

- a shell script creates a per-session or per-task loop state file in `.claude/`
- a Stop hook intercepts session exit
- when the completion promise is not satisfied, the hook blocks exit and reinjects the task back into the same session
- this produces a self-referential execution loop that keeps working until the promise is true or a max iteration is reached

Why it matters for `supernb`:

- it is the closest piece in the inspected code to "keep going until the work is actually done"
- it fits the implementation stage after PRD and design are approved
- it should be used with explicit completion promises and small task batches to avoid runaway loops

## `pbakaus/impeccable`

Repository role: design fluency layer and provider bundle generator.

Observed structure:

- `source/skills/frontend-design/`
- `source/skills/audit/`, `polish/`, `normalize/`, `critique/`, `typeset/`, `arrange/`, `colorize/`
- `scripts/build.js`
- `server/index.js`
- `public/antipattern-examples/`
- no committed `dist/` in the fresh clone

What it is:

- a design-focused skill pack with one foundational design skill and 20 steering commands
- a build system transforms source material into provider-specific formats for Claude Code, Codex, OpenCode, Gemini, Cursor, and others
- it explicitly encodes UI anti-patterns, contrast issues, spacing issues, and generic-AI-design avoidance

Why it matters for `supernb`:

- it gives `supernb` a concrete UI/UX governance layer instead of generic "make it prettier" prompts
- its design review commands are as important as its design generation commands
- because `dist/` is generated, any update flow must rebuild it before installation

## Local `sensortower-research` Skill

Inspected files:

- `SKILL.md`
- `scripts/sensortower_cli.py`
- `references/api-surface.md`
- `references/review-analysis.md`

What it is:

- a research workflow on top of Sensor Tower APIs
- includes search, metadata, sales, keywords, reviews, review-summary, ratings, creatives, and raw endpoint mode
- includes a review-insights mode to cluster complaints and requests

Why it matters for `supernb`:

- it is the evidence engine for PRD quality
- it closes a major gap that both `superpowers` and `impeccable` do not address
- it makes competitor analysis and review mining reproducible instead of anecdotal

## Integration Conclusion

`supernb` should treat these projects as four non-overlapping layers:

1. Research intelligence: `sensortower-research`
2. Product planning and software execution: `superpowers`
3. Long-running autonomous implementation loop: `superpowers@frad-dotclaude`
4. UI/UX generation and enforcement: `impeccable`

That layering is the basis of the repository structure and skills in this repo.

