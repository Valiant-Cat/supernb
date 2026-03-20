# Platform Install Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe `supernb` installation as three platform-native product experiences for Claude Code, Codex, and OpenCode while preserving the existing runtime and install scripts.

**Architecture:** Keep the underlying install scripts and control plane unchanged. Shift the user-facing information architecture so the root README becomes a platform selector, each platform gets its own product-style page, and Codex/OpenCode gain native `INSTALL.md` entrypoints similar to upstream `superpowers`.

**Tech Stack:** Markdown docs, shell install scripts, repository navigation structure

---

### Task 1: Add failing expectations for platform-native install entrypoints

**Files:**
- Create: `.codex/INSTALL.md`
- Create: `.opencode/INSTALL.md`
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Define the new public documentation shape**

Document the required surface:
- root README acts as product overview + platform selector
- Claude Code, Codex, and OpenCode each have dedicated product-style install pages
- Codex and OpenCode expose platform-native `INSTALL.md` entrypoints
- old `docs/install/*.md` paths remain valid and point to the new pages

- [ ] **Step 2: Verify current docs do not yet match this shape**

Run: `rg -n "Fetch and follow instructions|Choose Your Platform|Supernb for Claude Code|Supernb for Codex|Supernb for OpenCode" README.md README.zh-CN.md docs .codex .opencode`

Expected: missing or incomplete matches for the new product-page structure

- [ ] **Step 3: Write the new platform-native install entrypoints**

Create concise `INSTALL.md` docs for:
- `.codex/INSTALL.md`
- `.opencode/INSTALL.md`

These should tell the host agent to fetch, clone, and run the existing `supernb` install scripts using platform-native language.

- [ ] **Step 4: Verify the new entrypoints exist**

Run: `test -f .codex/INSTALL.md && test -f .opencode/INSTALL.md`

Expected: success

### Task 2: Restructure root README into a platform selector

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Replace bootstrap-first framing with platform-first framing**

Update the top-level install sections so the first user decision is platform choice, not bootstrap choice.

- [ ] **Step 2: Add platform selector sections**

For each README, add dedicated sections for:
- Claude Code
- Codex
- OpenCode

Each section should include:
- what you get on that platform
- quick install link/command
- link to the dedicated platform page

- [ ] **Step 3: Keep operational content, but de-emphasize it**

Retain environment variables, initiative control plane, and update information, but move them after the platform selection/install content.

- [ ] **Step 4: Verify README navigation is coherent**

Run: `rg -n "Choose Your Platform|Claude Code|Codex|OpenCode|docs/platforms" README.md README.zh-CN.md`

Expected: all three platforms appear in the platform selector section with platform-page links

### Task 3: Add dedicated platform product pages and preserve old links

**Files:**
- Create: `docs/platforms/claude-code.md`
- Create: `docs/platforms/codex.md`
- Create: `docs/platforms/opencode.md`
- Modify: `docs/install/claude-code.md`
- Modify: `docs/install/codex.md`
- Modify: `docs/install/opencode.md`

- [ ] **Step 1: Create dedicated platform pages**

Each platform page should follow one structure:
- What You Get
- Quick Install
- Manual Install
- Verify
- Update
- How It Works
- Troubleshooting

- [ ] **Step 2: Tailor each page to native platform expectations**

Examples:
- Claude Code: managed plugin + install script
- Codex: native skill discovery + `.codex/INSTALL.md`
- OpenCode: native plugin/config + `.opencode/INSTALL.md`

- [ ] **Step 3: Convert old install docs into compatibility entrypoints**

Keep `docs/install/*.md` paths valid by turning them into thin redirect-style wrappers that point to the new `docs/platforms/*.md` pages.

- [ ] **Step 4: Verify no public install path is orphaned**

Run: `find docs/platforms docs/install -maxdepth 1 -type f | sort`

Expected: platform pages exist and install-page compatibility files still exist

### Task 4: Review copy consistency and verify command coherence

**Files:**
- Modify as needed: platform pages, README files, install compatibility files

- [ ] **Step 1: Check for stale unified-bootstrap-first messaging**

Run: `rg -n "bootstrap-supernb|auto-detect harness|unified update path|Fastest path" README.md README.zh-CN.md docs/platforms docs/install .codex .opencode`

Expected: remaining references are deliberate and secondary, not the primary onboarding story

- [ ] **Step 2: Check for stale cross-platform ambiguity**

Run: `rg -n "install-claude-code|install-codex|install-opencode|supernb-loop@supernb|Fetch and follow instructions" README.md README.zh-CN.md docs/platforms docs/install .codex .opencode`

Expected: each platform page only promotes the commands appropriate for that platform

- [ ] **Step 3: Final verification**

Run:
- `python3 -m unittest tests.test_supernb_control_plane`
- `python3 -m unittest tests.test_supernb_cli_integration`

Expected: existing runtime/install tests remain green, confirming the docs/entrypoint restructure did not break the underlying product behavior
