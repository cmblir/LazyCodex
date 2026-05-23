<div align="center">

# 💤 LazyCodex

<img src="./docs/logo/mascot.svg" alt="LazyCodex mascot — sleepy terminal robot" width="200" height="200" />

**The local setup console for Codex.**

_Stop hand-editing every config file. Open one dashboard and wire Codex from there._

[![한국어](https://img.shields.io/badge/🇰🇷_한국어-blue)](./README.ko.md)
[![中文](https://img.shields.io/badge/🇨🇳_中文-red)](./README.zh.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-v3.99.33-green.svg)](./CHANGELOG.md)

</div>

LazyCodex is a **local-first setup and operations dashboard** for Codex. It turns the scattered files under `~/.codex/` into clickable screens for agents, skills, hooks, plugins, MCP connectors, permissions, sessions, projects, models, and workflows. Everything ships behind one `python3 server.py` — Python stdlib, single-file HTML, no runtime build step.

> Official Codex references used by this dashboard: <https://developers.openai.com/codex> and the OpenAI Docs MCP server at <https://developers.openai.com/mcp>.

**No cloud. No telemetry. No package to install.**

---

## What LazyCodex helps you set up

| Area | What you get |
|---|---|
| First run | Detect Python, Codex CLI, `CODEX_HOME`, data stores, and missing setup steps |
| Codex config | Edit official `~/.codex/config.toml` settings: model, provider, reasoning, approvals, sandbox, profiles, shell environment policy, MCP, plugins, skills, and subagents |
| Safety | Manage official Codex rules, hooks, sandbox combinations, permission profiles, backups, and static security scans |
| Extensions | Configure MCP servers, plugins, marketplaces, skills, agents, slash commands, and project agents |
| Operations | Reindex sessions, inspect costs and token metrics, replay sessions, watch active CLI processes |
| Automation | Use LazyCodex local automation separately: DAG workflows, Crew Wizard flows, Auto-Resume bindings, legacy routines, and notification paths |

The product style is intentionally "lazy": show the current state, suggest the next useful action, and keep the underlying files local and readable.

## 🚀 Quick start

```bash
git clone https://github.com/cmblir/LazyCodex.git
cd LazyCodex
python3 server.py
# → http://127.0.0.1:19500
```

Requires Python 3.10+ and OpenAI's `codex` CLI on `$PATH` (optional — the dashboard works without it; only Codex-bound features need it).

```bash
# Optional environment overrides
PORT=19500 python3 server.py
LOG_LEVEL=DEBUG python3 server.py
CODEX_HOME=/path/to/.codex python3 server.py
```

Open **Start Here** for the setup checklist, then move through **Settings**, **MCP Connectors**, **Permissions**, **Plugins**, and **Workflows** as needed.

---

## 🔄 Auto-Resume with live TTY injection (v3.65.0+)

When a Codex session hits a rate-limit or selection prompt, Auto-Resume can now inject keystrokes into the **live terminal** — not just spawn a separate subprocess. macOS only:

- **Strategy A**: TTY-targeted AppleScript (iTerm, Terminal.app) — no focus shift
- **Strategy B**: System Events keystroke fallback (Warp, kitty, WezTerm, Alacritty, Ghostty, Hyper, Tabby, VS Code, Cursor) — clipboard-paste, handles arbitrary Unicode

Pass `pressChoice: "1"` (default) to dismiss `1) Continue / 2) Quit` selection prompts before injecting your prompt. Permission gate: System Events fallback requires Accessibility permission for python3 (granted once via System Settings → Privacy & Security → Accessibility).

```
POST /api/auto_resume/inject_live
{ "sessionId": "...", "prompt": "계속 시작.", "pressChoice": "1" }
```

Time-based deadlines (`durationSec` / `deadlineMs`) replace the legacy `maxAttempts` cap — pick how long, not how many tries.

---

## 📐 Architecture

```
LazyCodex/
├── server.py                  # entry — binds 127.0.0.1:19500 (override via PORT env)
├── server/                    # ~25 stdlib-only Python modules
│   ├── routes.py              # single dispatch table
│   ├── workflows.py           # DAG engine (ThreadPoolExecutor)
│   ├── ai_providers.py        # provider registry (codex/openai/gemini/ollama/...)
│   ├── auto_resume.py         # rate-limit retry loop with deadlineMs
│   ├── auto_resume_inject.py  # macOS live TTY injection (v3.65)
│   └── ...
├── dist/                      # single-file SPA (HTML + app.js + locales)
└── tests/  # pytest unit specs + Playwright E2E
```

### Data stores

| Path | Purpose | Override env |
|---|---|---|
| `~/.codex-dashboard.db` | SQLite — session index, costs, telemetry | `CODEX_DASHBOARD_DB` |
| `~/.codex-dashboard-workflows.json` | Workflows + runs + custom templates | `CODEX_DASHBOARD_WORKFLOWS` |
| `~/.codex-dashboard-ai-providers.json` | API keys, custom CLIs, fallback chain | `CODEX_DASHBOARD_AI_PROVIDERS` |
| `~/.codex-dashboard-auto-resume.json` | Auto-resume bindings | `CODEX_DASHBOARD_AUTO_RESUME` |
| `~/.codex/` | Codex CLI's own state — read-only | `CODEX_HOME` |

All writes go through atomic `tmp + rename` (`server/utils.py::_safe_write`).

---

## 🌍 i18n

Korean is the source language. Every user-visible string passes through `t('한국어 원문')` and resolves via `dist/locales/{ko,en,zh}.json`. Run `make i18n-refresh` after adding new strings.

---

## 🛠️ Troubleshooting

**"port 19500 already in use"** — `server.py` auto-kills the prior occupant of `$PORT` before binding. If you'd rather pin a different port: `PORT=8080 python3 server.py`. The default moved from 8080 → 19500 in v3.99 because 8080 is a heavily-shared local-dev port (Tomcat / http-server / dozens of tutorials) and PWA install state from another project at that origin was hijacking the dashboard's "Open in app" button on shared machines. If you have existing scripts / shortcuts pointing at 8080, set `PORT=8080` to keep them working.

**"Open in app" launches some other application** — Chrome PWAs are scoped per-origin (`http://127.0.0.1:<port>`) so any PWA you previously installed on the same port hijacks the launch. Visit `chrome://apps`, remove any non-LazyCodex entry pointing at that port, then `chrome://settings/content/all` → search the port → "Delete data" to wipe the cached install state. The v3.99 manifest also sets an explicit `id` so Chrome treats this dashboard as its own app even when you have other localhost PWAs installed at the same origin.

**"command not found: codex"** — install [Codex CLI](https://developers.openai.com/codex/cli). The dashboard's tabs that don't depend on `codex` (workflow editor, AI providers, MCP, etc.) work without it.

**Auto-Resume live injection silently failing** — on macOS, grant Accessibility permission to `python3` in System Settings → Privacy & Security → Accessibility. The dashboard surfaces error code `1002 / -1719` with a hint when it's missing.

**Toast 📋 button breaking with broken-HTML output** — fixed in v3.66.0.

---

## 🤝 Contributing

```bash
make i18n-refresh          # required after touching any t('...') strings
python3 -m pytest tests/   # Python suite
npx playwright test        # CLI/daemon suite
node scripts/e2e-dashboard-qa.mjs   # full dashboard probe
```

Branches: `feat/*`, `fix/*`, `chore/*`. Annotated tags only (`git tag -a vX.Y.Z -m "..."`). Don't push directly to `main` from a fork without review.

See [CHANGELOG.md](./CHANGELOG.md) for the full per-release log.

---

## Star History

<a href="https://www.star-history.com/?repos=cmblir/lazycodex&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=cmblir/lazycodex&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=cmblir/lazycodex&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=cmblir/lazycodex&type=date&legend=top-left" />
 </picture>
</a>

---

## 📝 License

[MIT](./LICENSE) — free for personal and commercial use.

---

## 🙏 Acknowledgements

- [OpenAI Codex CLI](https://developers.openai.com/codex/cli) — the official CLI this dashboard integrates with
- [n8n](https://n8n.io) — workflow editor inspiration
- [lazygit](https://github.com/jesseduffield/lazygit) / [lazydocker](https://github.com/jesseduffield/lazydocker) — the "lazy" spirit

<div align="center"><sub>Made with 💤 for those who'd rather click than type.</sub></div>
