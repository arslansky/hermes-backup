# ECC (Everything Claude Code) — Architecture Analysis

**Repo:** https://github.com/affaan-m/ECC  
**Version:** 2.0.0-rc.1 | **Stars:** 182K+ | **Forks:** 28K+ | **Contributors:** 170+  
**Harnesses:** Claude Code, Codex, Cursor, OpenCode, Gemini, Zed, GitHub Copilot  
**Languages:** 12 ecosystems (TypeScript, Python, Go, Java, Kotlin, Swift, C++, Rust, PHP, Perl, Dart, F#)

---

## 1. What ECC Is

ECC is a **harness-native operator system** — a battle-tested plugin that layers production-ready agents, skills, commands, hooks, rules, and MCP configurations on top of AI coding harnesses. It is not a config pack; it is a complete workflow system evolved over 10+ months of daily intensive use building real products.

ECC won the Anthropic x Forum Ventures hackathon (Sep 2025) and now serves as the shared workflow substrate for multiple AI coding tools. Its architecture is designed around **portability** — the same skill catalog, rules, and hooks adapt across different harness surfaces rather than being rewritten per tool.

---

## 2. Core Architecture

### 2.1 The Five Core Subsystems

```
Operator Surface (CLI/TUI/chat) → Harness Adapter Layer → Core Runtime
                                                         ├── Agents (61)
                                                         ├── Skills (246)
                                                         ├── Commands (76)
                                                         ├── Hooks (event-driven)
                                                         └── Rules (per-language)
```

**Agents (`agents/`)**
61 specialized subagents as markdown files with YAML frontmatter. Examples:
- `planner`, `architect`, `tdd-guide`, `code-reviewer`, `security-reviewer`
- Language-specific reviewers: `typescript-reviewer`, `go-reviewer`, `python-reviewer`, `java-reviewer`, `rust-reviewer`, etc.
- Build resolvers: `go-build-resolver`, `python-build-resolver`, `java-build-resolver`
- Domain specialists: `database-reviewer`, `mle-reviewer`, `harness-optimizer`, `loop-operator`

Agent format (YAML frontmatter + markdown):
```yaml
---
name: code-reviewer
description: Code quality and maintainability review
tools: [Read, Edit, Bash, Grep]
model: sonnet
---
```

**Skills (`skills/`)**
246 workflow definitions organized into buckets: `engineering/`, `productivity/`, `misc/`, `personal/`, `in-progress/`, `deprecated/`.

Skill format (YAML frontmatter + markdown sections):
```yaml
---
name: tdd-workflow
description: Test-driven development with 80%+ coverage required
origin: ecc-core
tools: [Read, Write, Edit, Bash]
---
# TDD Workflow

## When to Activate
## How It Works
## Examples
```

Key skill categories:
- **Engineering:** `coding-standards`, `backend-patterns`, `frontend-patterns`, `database-migrations`
- **AI/Agentic:** `agentic-engineering`, `autonomous-loops`, `agent-harness-construction`, `agent-architecture-audit`
- **Verification:** `verification-loop`, `e2e-testing`, `security-review`, `eval-harness`
- **Operations:** `content-engine`, `market-research`, `investor-materials`, `brand-voice`
- **Performance:** `benchmark-optimization-loop`, `data-throughput-accelerator`, `latency-critical-systems`
- **Cross-harness:** `deep-research`, `documentation-lookup`, `mcp-server-patterns`

**Commands (`commands/`)**
76 slash commands as standalone markdown files. Examples: `/plan`, `/code-review`, `/build-fix`, `/tDD`, `/e2e`, `/learn`, `/skill-create`, `/sessions`, `/harness-audit`, `/quality-gate`, `/multi-plan`, `/multi-execute`, `/loop-start`, `/instinct-import`, `/evolve`

**Hooks (`hooks/`, `scripts/hooks/`)**
Event-driven automation system with two layers:
- `hooks/hooks.json` — declarative hook graph (matcher → commands)
- `scripts/hooks/*.js` — executable implementations

Hook event types:
| Event | Phase | Purpose |
|-------|-------|---------|
| `PreToolUse` | Before tool | Block/warn on risky operations (dev server outside tmux, git push, secrets in prompt) |
| `PostToolUse` | After tool | Auto-format, TypeScript check, PR logging, quality gate |
| `Stop` | After response | Console.log audit, session summary, pattern extraction, cost tracking |
| `SessionStart` | Lifecycle start | Load prior context, detect package manager |
| `SessionEnd` | Lifecycle end | Persist session state, cleanup |
| `PreCompact` | Before compaction | Save state before context reduction |

Runtime controls via env vars:
- `ECC_HOOK_PROFILE=minimal|standard|strict`
- `ECC_DISABLED_HOOKS=...`
- `ECC_SESSION_START_MAX_CHARS=4000`

**Rules (`rules/`)**
Per-language coding standards in `rules/common/` (always apply) + language-specific directories. Organized by: `typescript/`, `python/`, `golang/`, `java/`, `kotlin/`, `swift/`, `cpp/`, `csharp/`, `ruby/`, `rust/`, `php/`, `perl/`, `dart/`, `fsharp/`, `angular/`, `arkts/`, `web/`, `zh/`

Rule format: Markdown with YAML frontmatter containing `description`, `globs`, `alwaysApply`.

### 2.2 Memory & Persistence Subsystem

ECC implements a sophisticated session memory system:

**Lifecycle contract:**
- `SessionStart` → Load bounded prior context (max chars configurable)
- `PreCompact` → Save state before context compaction
- `Stop` → Extract patterns, update session summary, track cost
- `SessionEnd` → Final persistence marker

**Continuous learning:** The `observe-runner.js` captures tool-use observations across sessions, enabling pattern extraction into reusable skills. The `instinct` system stores learned patterns with confidence scoring, import/export, and evolution into formal skills.

**State store:** SQLite-backed session infrastructure with query CLI, session adapters for structured recording, and skill evolution foundation.

### 2.3 Instinct System (Continuous Learning v2)

The instinct system captures and promotes learned patterns:

- **Instinct capture** — Auto-extract patterns from sessions via Stop hook
- **Confidence scoring** — Each instinct scored on repeatability
- **Import/export** — Portable instinct files
- **Evolution** — Cluster related instincts into formal skills via `/evolve`
- **TTL management** — `/prune` deletes expired pending instincts (30d)

### 2.4 Security Subsystem

**AgentShield (`ecc-agentshield` npm package):**
- 1282 tests, 102 security rules
- `/security-scan` command runs AgentShield directly
- Prompt injection detection, config risk analysis, CVE monitoring

**Hook-based security:**
- PreToolUse: Secret detection (sk-, ghp_, AKIA patterns), `.env`/`.key`/`.pem` file access blocking
- PostToolUse: Quality gate after edits
- Stop: Console.log audit, session summary

**ECC Tools GitHub App:**
- PR audits, security scanning
- Free tier + Pro/Enterprise plans
- Marketplace: https://github.com/marketplace/ecc-tools

**Security guides:**
- `the-security-guide.md` — Attack vectors, sandboxing, sanitization, CVEs, AgentShield
- Comprehensive OWASP-aligned security review prompts

### 2.5 Multi-Harness Adapter Architecture

ECC's defining architectural principle: **shared assets, thin adapters**.

```
skills/ (source of truth) → Claude Code plugin / Codex plugin / OpenCode plugin / Cursor rules / etc.
rules/  (source of truth) → per-harness translation
hooks/  (source of truth) → harness-native execution or instruction fallback
MCP/    (source of truth) → native config import per harness
```

**Harness support matrix:**
| Feature | Claude Code | Codex | OpenCode | Cursor | Gemini |
|---------|-------------|-------|----------|--------|--------|
| Agents | 61 | shared (AGENTS.md) | 12 | shared | instruction |
| Commands | 76 | instruction-based | 35 | shared | instruction |
| Skills | 246 | 32 (native format) | 37 | shared | instruction |
| Hooks | 8 event types | none (instruction) | 11 event types | 15 event types | none |
| Rules | 34 | instruction-based | 13 instructions | 34 (YAML) | instruction |

**DRY Adapter Pattern:** Cursor's hook adapter transforms Cursor's stdin JSON to Claude Code's format, allowing reuse of `scripts/hooks/*.js` without duplication.

**ECC 2.0 Rust control plane** (`ecc2/`):
- Alpha Rust implementation
- Commands: `dashboard`, `start`, `sessions`, `status`, `stop`, `resume`, `daemon`
- Cross-harness session management

### 2.6 Cross-Harness Architecture Principles

From `docs/architecture/cross-harness.md`:

1. **SKILL.md is the most portable unit** — YAML frontmatter with name, description, origin; describes when to use; states required tools without embedding secrets; keeps examples repo-relative.

2. **What travels unchanged:** Skills, rules/instructions, hook logic, MCP configs, install manifests, session/orchestration patterns.

3. **What gets adapted per harness:** Loading mechanism, enforcement behavior, command semantics.

4. **Adapters stay thin** — shared behavior belongs in `skills/`, `rules/`, `hooks/`, `scripts/`, `mcp-configs/`.

---

## 3. Hermes Context

ECC explicitly references Hermes as its public operator shell:

- **Hermes Boundary doc** defines how Hermes consumes ECC assets
- ECC skills imported into `~/.hermes/skills/ecc-imports/`
- Generated workflow packs from `skills/hermes-generated/`
- Operator patterns distilled from repeated Hermes sessions

ECC's architecture is explicitly designed so that Hermes can serve as the front-door operator surface while ECC provides the reusable workflow substrate.

---

## 4. Key Insights for Hermes Agent

### 4.1 What Hermes Should Adopt

**Instinct/Skill Evolution System**
ECC's instinct system (continuous learning v2) with confidence scoring, import/export, and evolution into formal skills is the most sophisticated learning loop in any agent harness system. Hermes should implement a similar pattern:
- Capture observations per session
- Score confidence based on repeatability  
- Allow promotion to formal skill with review

**Memory Persistence Lifecycle**
The SessionStart → PreCompact → Stop → SessionEnd contract is well-designed. Hermes should adopt a similar bounded context loading strategy with configurable max chars and opt-out.

**Skill Catalog Architecture**
The bucket organization (`engineering/`, `productivity/`, `misc/`, `personal/`) with SKILL.md format and YAML frontmatter is mature. Hermes skills should follow the same pattern for cross-pollination potential.

**Hook System Design**
ECC's two-layer hook architecture (declarative JSON graph + executable JS implementations) is clean and harness-agnostic enough to port. The PreToolUse/PostToolUse/Stop/Lifecycle event model should inform Hermes's automation layer.

**Multi-Harness Portability Model**
ECC proves that separating durable behavior (skills, rules, hooks) from harness-specific adapters enables one workflow catalog to serve multiple execution surfaces. Hermes should design its assets to be similarly portable.

**Operator Workflow Surface**
ECC's operator commands (loop-operator, harness-optimizer, connections-optimizer, brand-voice, social-graph-ranker, project-flow-ops) demonstrate how a harness system can manage complex multi-domain workflows. Hermes should build similarly domain-scoped operator capabilities.

### 4.2 What Hermes Does Differently

**ECC is a plugin; Hermes is an operator shell** — ECC extends coding harnesses, Hermes orchestrates across multiple domains (chat, cron, workspace, distribution). ECC's assets are installed; Hermes's assets are generated and maintained.

**ECC targets coding tasks; Hermes targets operational workflows** — ECC's agents are code reviewers, build fixers, security scanners. Hermes's agents are content operators, finance checkers, research summarizers.

**ECC is cross-harness by design; Hermes is terminal-native by design** — ECC's portability model solves multi-harness adaptation. Hermes's model solves multi-channel (Telegram/CLI/TUI) orchestration.

### 4.3 Security Model Comparison

ECC's AgentShield + hook-based secret detection + GitHub App PR scanning represents a mature security posture for a coding harness. Hermes should adopt similar:
- Input sanitization at system boundaries
- Secret detection in user prompts
- Security scanning for sensitive operations
- AgentShield integration path for code-related tasks

---

## 5. File Structure Summary

```
ECC/
├── agents/               # 61 specialized subagents (markdown + YAML frontmatter)
├── skills/               # 246 workflow skills organized in buckets
├── commands/             # 76 slash commands
├── hooks/                # Hook graph + memory-persistence lifecycle definitions
│   └── memory-persistence/
├── scripts/hooks/         # Executable hook implementations (Node.js)
├── rules/                # Per-language coding standards (common/ + language dirs)
├── src/llm/              # CLI tooling, provider abstractions, tools
├── contexts/             # Dev, research, review context files
├── docs/                 # Architecture docs, guides, translations
├── .mcp.json             # MCP server configurations
├── ecc2/                 # ECC 2.0 Rust control plane (alpha)
├── ecc_dashboard.py       # Tkinter desktop dashboard
├── agent.yaml            # ECC 2.0 manifest (skills + commands catalog)
├── package.json          # npm package definitions (ecc-universal, ecc-agentshield)
├── install.sh/ps1        # Cross-platform installer
├── AGENTS.md             # Root agent instructions (cross-harness)
├── CLAUDE.md             # Project guidance for coding harnesses
├── SOUL.md               # Core identity and principles
└── the-*-guide.md        # Shorthand, longform, security guides
```

---

## 6. Key Metrics

| Metric | Value |
|--------|-------|
| Stars | 182K+ |
| Forks | 28K+ |
| Contributors | 170+ |
| Languages | 12 ecosystems |
| Harnesses | 7 (Claude Code, Codex, OpenCode, Cursor, Gemini, Zed, Copilot) |
| Agents | 61 |
| Skills | 246 |
| Commands | 76 |
| Rules | 34 (common + per-language) |
| Hook event types | 8 (Claude Code) / 11 (OpenCode) / 15 (Cursor) |
| Security rules (AgentShield) | 102 |
| Test coverage | 1282+ tests |
| Install methods | Plugin, npm, manual, selective |
| License | MIT |

---

## 7. Conclusion

ECC is the most sophisticated and well-documented agent harness system in the open-source ecosystem. Its architecture — built around portable skill catalogs, thin harness adapters, event-driven hook automation, continuous learning via instincts, and security-first design — provides a proven template for building durable agentic systems.

For Hermes, the key takeaways are:
1. **Adopt the skill evolution system** — confidence-scored instincts that promote to formal skills
2. **Implement the memory persistence lifecycle** — bounded context loading with lifecycle hooks
3. **Follow the skill catalog format** — YAML frontmatter + markdown sections = portable across harnesses
4. **Design for multi-surface portability** — separate durable assets from execution surface adapters
5. **Build an operator command surface** — domain-scoped operators (loop, harness, content, research) rather than one monolithic agent

ECC proves that a well-designed harness system can serve as both a coding assistant and an operational automation platform — the same architecture scales from code review to business ops.