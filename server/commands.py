"""슬래시 명령어 (`~/.codex/commands/*.md` + 플러그인 커맨드) 목록 + 카테고리 + 번역 배치.

번역 배치 (`api_translate_batch`) 는 cmd/skill/plugin/agent 의 description
을 Codex CLI 한 번 호출로 번역 후 로컬 캐시에 저장 — skills/agents/plugins
를 순환 없이 참조하기 위해 late import 사용.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from threading import Lock

from .config import COMMANDS_DIR, PLUGINS_DIR
from .translations import _load_translation_cache, _save_translation_cache
from .utils import _parse_frontmatter, _safe_read, _strip_frontmatter


_BUILTIN_COMMANDS: list[tuple[str, str, str]] = [
    ("permissions", "Set what Codex can do without asking first.", "Relax or tighten approval requirements mid-session."),
    ("ide", "Include open files, current selection, and other IDE context.", "Pull editor context into the next prompt."),
    ("keymap", "Remap TUI keyboard shortcuts.", "Inspect and persist custom shortcut bindings in config.toml."),
    ("vim", "Toggle Vim mode for the composer.", "Switch between Vim normal/insert behavior and default editing mode."),
    ("sandbox-add-read-dir", "Grant sandbox read access to an extra directory.", "Windows-only helper for absolute directories outside readable roots."),
    ("agent", "Switch the active agent thread.", "Inspect or continue work in a spawned subagent thread."),
    ("apps", "Browse apps and connectors.", "Attach an app before asking Codex to use it."),
    ("plugins", "Browse installed and discoverable plugins.", "Inspect plugin tools, install suggested plugins, or manage availability."),
    ("hooks", "Review lifecycle hooks.", "Inspect configured hooks, trust changed hooks, or disable non-managed hooks."),
    ("clear", "Clear the terminal and start a fresh chat.", "Reset visible UI and conversation together."),
    ("compact", "Summarize the visible conversation to free tokens.", "Retain key points after long runs."),
    ("copy", "Copy the latest completed Codex output.", "Grab the latest finished response or plan text."),
    ("diff", "Show the Git diff.", "Review edits before committing or testing."),
    ("exit", "Exit the CLI.", "Same as /quit."),
    ("experimental", "Toggle experimental features.", "Enable optional features from the CLI."),
    ("approve", "Approve one retry of a recent auto review denial.", "Retry an action the auto reviewer denied."),
    ("memories", "Configure memory use and generation.", "Turn memory injection or generation on or off."),
    ("skills", "Browse and use skills.", "Select a relevant local skill for task-specific behavior."),
    ("feedback", "Send logs to Codex maintainers.", "Report issues or share diagnostics."),
    ("init", "Generate an AGENTS.md scaffold.", "Capture persistent instructions for the repository or subdirectory."),
    ("logout", "Sign out of Codex.", "Clear local credentials on a shared machine."),
    ("mcp", "List configured MCP tools.", "Check which external tools Codex can call."),
    ("mention", "Attach a file to the conversation.", "Point Codex at files or folders to inspect next."),
    ("model", "Choose the active model.", "Switch model and reasoning effort when available."),
    ("fast", "Toggle a Fast service tier.", "Use when the model catalog exposes Fast mode."),
    ("plan", "Switch to plan mode.", "Ask Codex to propose a plan before implementation."),
    ("goal", "Set, pause, resume, view, or clear a task goal.", "Requires features.goals."),
    ("personality", "Choose a communication style.", "Adjust response style without changing instructions."),
    ("ps", "Show experimental background terminals.", "Check long-running commands."),
    ("stop", "Stop all background terminals.", "Cancel background terminal work."),
    ("fork", "Fork the current conversation.", "Branch the active session to explore another approach."),
    ("side", "Start an ephemeral side conversation.", "Ask a focused follow-up without disrupting the main thread."),
    ("raw", "Toggle raw scrollback mode.", "Make terminal selection and copying less formatted."),
    ("resume", "Resume a saved conversation.", "Continue previous CLI work."),
    ("new", "Start a new conversation.", "Reset chat context without leaving the CLI."),
    ("quit", "Exit the CLI.", "Same as /exit."),
    ("review", "Ask Codex to review your working tree.", "Run after changes or before handoff."),
    ("status", "Display session configuration and token usage.", "Confirm model, approval policy, writable roots, and context."),
    ("debug-config", "Print config layer and requirements diagnostics.", "Debug precedence and policy requirements."),
    ("statusline", "Configure TUI status-line fields.", "Pick and reorder footer items and persist in config.toml."),
    ("title", "Configure terminal title fields.", "Pick title items such as project, branch, model, and task progress."),
    ("theme", "Choose a syntax-highlighting theme.", "Preview and persist a terminal theme."),
]


# ───────── 카테고리 휴리스틱 (키워드 → 카테고리 id) ─────────

CMD_CATEGORIES = [
    ("build",       "🔧 빌드 / 컴파일",     ["build", "compile", "resolve", "fix-build", "linker"]),
    ("test",        "🧪 테스트 / TDD",      ["test", "tdd", "jest", "pytest", "e2e", "fixtures"]),
    ("review",      "🔍 코드 리뷰",          ["review", "audit", "simplify", "quality"]),
    ("security",    "🔒 보안",              ["security", "bounty", "hipaa", "compliance", "phi", "privacy", "secret"]),
    ("plan",        "🏗️ 계획 / 아키텍처",    ["plan", "architect", "design", "rfc", "blueprint", "adr"]),
    ("agent",       "🤖 에이전트 / 오케스트레이션", ["agent", "orchestr", "devfleet", "harness", "fleet", "team-builder", "loop"]),
    ("commit",      "📝 커밋 / PR / Git",    ["commit", "pr-", "git", "prp", "merge", "branch"]),
    ("skill",       "✨ 스킬 관리",          ["skill", "hookify", "instinct"]),
    ("docs",        "📚 문서 / 검색",        ["docs", "documentation", "search", "research", "exa", "context7"]),
    ("deploy",      "🚀 배포 / DevOps",      ["deploy", "docker", "ci", "cd", "release", "canary"]),
    ("lang-rust",   "🦀 Rust",              ["rust"]),
    ("lang-go",     "🐹 Go",                ["go-", "go_", "golang"]),
    ("lang-kotlin", "🎯 Kotlin / KMP",       ["kotlin", "android", "compose", "ktor"]),
    ("lang-cpp",    "⚙️ C++",              ["cpp", "c++", "cmake"]),
    ("lang-csharp", "🟦 C# / .NET",          ["csharp", "dotnet", "c#"]),
    ("lang-java",   "☕ Java / Spring",      ["java", "spring", "jpa", "gradle"]),
    ("lang-python", "🐍 Python",            ["python", "django", "flask", "pytest"]),
    ("lang-flutter","📱 Flutter / Dart",     ["flutter", "dart"]),
    ("lang-swift",  "🍎 Swift / iOS",        ["swift", "swiftui", "xcode", "ios", "foundation-model"]),
    ("lang-ts",     "🌀 TypeScript / Node",  ["typescript", "node", "bun", "nestjs", "nextjs", "nuxt"]),
    ("lang-php",    "🐘 PHP / Laravel",      ["laravel", "php"]),
    ("lang-perl",   "🐫 Perl",              ["perl"]),
    ("lang-sql",    "🗄️ SQL / DB",          ["database", "postgres", "clickhouse", "supabase", "jpa", "migration"]),
    ("healthcare",  "🏥 헬스케어",           ["healthcare", "emr", "hipaa", "cdss", "ehr", "phi"]),
    ("content",     "✍️ 콘텐츠 / 마케팅",     ["content", "article", "brand-voice", "seo", "crosspost", "social"]),
    ("ops",         "🛡️ 운영 / 모니터링",     ["ops", "watch", "monitor", "canary-watch", "healthcheck", "observability"]),
    ("ai-ml",       "🧠 AI / ML",           ["ml", "pytorch", "llm", "codex-api", "codex_api", "agent-sdk", "rag"]),
    ("web3",        "⛓️ Web3 / EVM",        ["evm", "solidity", "web3", "defi", "x402", "keccak"]),
    ("other",       "🛠️ 기타 / 범용",        []),
]


def _categorize_command(cmd: dict) -> tuple[str, str]:
    """명령어 id + description 기반 카테고리 결정."""
    text = (
        cmd.get("id", "") + " "
        + cmd.get("name", "") + " "
        + (cmd.get("description") or "")
    ).lower()
    for cat_id, cat_label, kws in CMD_CATEGORIES:
        for kw in kws:
            if kw in text:
                return cat_id, cat_label
    return "other", "🛠️ 기타 / 범용"


# v2.43.1 — TTL+mtime cache. The bare scan rglob's hundreds of plugin
# command .md files (308 on a power user's machine) and takes ~1.1 s.
# Invalidate when top-level command/plugin dirs change.
_COMMANDS_TTL_S = 60
_commands_cache: dict = {"key": None, "ts": 0.0, "value": None}
_commands_lock = Lock()


def _commands_fingerprint() -> tuple:
    parts: list[float] = []
    try:
        if COMMANDS_DIR.exists():
            parts.append(COMMANDS_DIR.stat().st_mtime)
            for p in COMMANDS_DIR.iterdir():
                try:
                    parts.append(p.stat().st_mtime)
                except Exception:
                    continue
    except Exception:
        pass
    try:
        markets = PLUGINS_DIR / "marketplaces"
        if markets.exists():
            parts.append(markets.stat().st_mtime)
            for m in markets.iterdir():
                try:
                    parts.append(m.stat().st_mtime)
                except Exception:
                    continue
    except Exception:
        pass
    return tuple(round(x, 3) for x in parts)


def list_commands(force_refresh: bool = False) -> list:
    """Cached wrapper. Pass ``force_refresh=True`` (or hit the endpoint with
    ``?refresh=1``) to bypass the cache."""
    fp = _commands_fingerprint()
    now = time.time()
    if not force_refresh:
        with _commands_lock:
            if (_commands_cache["key"] == fp
                    and _commands_cache["value"] is not None
                    and (now - _commands_cache["ts"]) < _COMMANDS_TTL_S):
                return _commands_cache["value"]
    value = _list_commands_uncached()
    with _commands_lock:
        _commands_cache["key"] = fp
        _commands_cache["ts"] = now
        _commands_cache["value"] = value
    return value


def _list_commands_uncached() -> list:
    out: list = []
    for name, description, content in _BUILTIN_COMMANDS:
        out.append({
            "id": name,
            "name": name,
            "description": description,
            "scope": "builtin",
            "path": "",
            "content": content,
            "doc": "https://developers.openai.com/codex/cli/slash-commands#built-in-slash-commands",
        })
    # user global commands
    if COMMANDS_DIR.exists():
        for p in sorted(COMMANDS_DIR.rglob("*.md")):
            raw = _safe_read(p)
            meta = _parse_frontmatter(raw)
            rel = p.relative_to(COMMANDS_DIR)
            cid = str(rel).replace("/", ":").replace(".md", "")
            out.append({
                "id": cid,
                "name": meta.get("name", cid),
                "description": meta.get("description", "") or meta.get("argument-hint", ""),
                "scope": "user",
                "path": str(p),
                "content": _strip_frontmatter(raw)[:4000],
            })
    # plugin commands (scan plugin marketplaces, but skip .bak)
    if PLUGINS_DIR.exists():
        for plugin_md in PLUGINS_DIR.rglob("commands/*.md"):
            try:
                if ".bak" in str(plugin_md):
                    continue
                raw = _safe_read(plugin_md, 4000)
                meta = _parse_frontmatter(raw)
                cid = plugin_md.stem
                out.append({
                    "id": f"plugin:{cid}",
                    "name": meta.get("name", cid),
                    "description": meta.get("description", ""),
                    "scope": "plugin",
                    "path": str(plugin_md),
                    "content": _strip_frontmatter(raw)[:2000],
                })
            except Exception:
                continue
    # 카테고리 + 번역 주입 (ko/en/zh 모두)
    tr_cache = _load_translation_cache()
    for c in out:
        cat_id, cat_label = _categorize_command(c)
        c["category"] = cat_id
        c["categoryLabel"] = cat_label
        # legacy: descriptionKo 유지
        c["descriptionKo"] = tr_cache.get(_cache_key("cmd", c["id"], "ko"), "")
        c["descriptionEn"] = tr_cache.get(_cache_key("cmd", c["id"], "en"), "")
        c["descriptionZh"] = tr_cache.get(_cache_key("cmd", c["id"], "zh"), "")
    return out


def _cache_key(kind: str, item_id: str, lang: str = "ko") -> str:
    """번역 캐시 키 규칙.

    - ko (기본): cmd 는 prefix 없이 id 만, 나머지는 `{kind}:{id}` (legacy 호환)
    - 기타 언어: `{lang}:{kind}:{id}`
    """
    if lang == "ko":
        return f"{kind}:{item_id}" if kind != "cmd" else item_id
    return f"{lang}:{kind}:{item_id}"


# ───────── 번역 배치 (cmd/skill/plugin/agent 공용) ─────────

def _collect_translate_items(kind: str) -> list:
    """kind 에 따라 [{id, desc}, ...] 수집. 순환 회피를 위해 late import."""
    items: list = []
    if kind == "cmd":
        for c in list_commands():
            d = c.get("description") or ""
            if d:
                items.append({"id": c["id"], "desc": d[:320]})
    elif kind == "skill":
        from .skills import list_skills
        for s in list_skills():
            d = s.get("description") or ""
            if d:
                items.append({"id": s["id"], "desc": d[:320]})
    elif kind == "plugin":
        from .plugins import api_plugins_browse
        for p in api_plugins_browse().get("plugins", []):
            d = p.get("description") or ""
            if d:
                items.append({"id": p["id"], "desc": d[:320]})
    elif kind == "agent":
        from .agents import list_agents
        for a in list_agents().get("agents", []):
            d = a.get("description") or ""
            if d:
                items.append({"id": a["id"], "desc": d[:320]})
    return items


_LANG_PROMPT = {
    "ko": {
        "label": "한국어",
        "instructions": "- 기술용어(Codex CLI, PR, CLI 등)는 그대로 유지.\n"
                        "- 20~70자 정도, 핵심 동사 포함 (\"~한다\" 체).\n"
                        "- 한국어 요약이 불가능하면 원문 기술 용어 나열.",
    },
    "en": {
        "label": "English",
        "instructions": "- Keep technical terms (Codex CLI, PR, CLI, etc.) as-is.\n"
                        "- One concise sentence, 10-20 words, present tense.\n"
                        "- If the input is already English, lightly polish and return.",
    },
    "zh": {
        "label": "简体中文",
        "instructions": "- 保留技术术语（Codex CLI、PR、CLI 等）。\n"
                        "- 简洁一句话（20-40 字），使用动词短语。\n"
                        "- 若输入已是中文，轻度润色后返回。",
    },
}


def api_translate_batch(body: dict) -> dict:
    """범용 번역 배치.

    body:
      kind        : 'cmd' | 'skill' | 'plugin' | 'agent'
      targetLang  : 'ko' | 'en' | 'zh'  (기본 'ko', legacy 호환)
      limit       : 5~60, 기본 50

    캐시에 없는 항목만 Codex CLI 로 번역.
    """
    from .auth import api_auth_status

    codex_bin = shutil.which("codex")
    if not codex_bin:
        return {"error": "codex CLI 설치 필요"}
    if not api_auth_status().get("connected"):
        return {"error": "Codex 계정 연결 필요"}

    body = body or {}
    kind = body.get("kind") if isinstance(body, dict) else "cmd"
    if kind not in ("cmd", "skill", "plugin", "agent"):
        return {"error": "unknown kind"}
    target_lang = (body.get("targetLang") or body.get("lang") or "ko").lower()
    if target_lang not in _LANG_PROMPT:
        return {"error": f"unknown targetLang: {target_lang}"}
    limit = min(60, max(5, int(body.get("limit") or 50)))

    cache = _load_translation_cache()
    all_items = _collect_translate_items(kind)
    pending = [
        x for x in all_items
        if not cache.get(_cache_key(kind, x["id"], target_lang))
    ]
    if not pending:
        return {"translated": 0, "requested": 0, "remaining": 0,
                "total": len(all_items), "done": True,
                "targetLang": target_lang}

    batch = pending[:limit]
    kind_label = {"cmd": "slash command", "skill": "skill",
                  "plugin": "plugin", "agent": "agent"}[kind]
    lang_cfg = _LANG_PROMPT[target_lang]

    prompt = f"""Translate each Codex CLI {kind_label} description below into **concise {lang_cfg['label']} (one line)**.
{lang_cfg['instructions']}

입력/Input:
{json.dumps(batch, ensure_ascii=False, indent=2)}

JSON 만 출력 / Output JSON only:
{{"translations": {{"<id>": "<translation>", ...}}}}
"""
    try:
        from .codex_exec import run_codex_exec
        proc, parsed_exec = run_codex_exec(
            codex_bin, prompt, ephemeral=True, timeout=300,
        )
    except Exception as e:
        return {"error": f"Codex CLI 실행 실패: {e}"}
    if proc.returncode != 0:
        return {"error": f"Codex CLI 오류: {(proc.stderr or '')[:400]}"}

    response_text = (parsed_exec.get("output") or proc.stdout or "").strip()
    m = re.search(r'\{[\s\S]*"translations"[\s\S]*\}', response_text)
    if not m:
        return {"error": "번역 JSON 없음", "error_key": "err_translate_no_json", "raw": response_text[:1500]}
    try:
        parsed = json.loads(m.group(0))
        tr = parsed.get("translations", {})
    except Exception as e:
        return {"error": f"JSON 파싱 실패: {e}", "raw": response_text[:1500]}

    added = 0
    for item_id, val in tr.items():
        if isinstance(val, str) and val.strip():
            cache[_cache_key(kind, item_id, target_lang)] = val.strip()
            added += 1
    _save_translation_cache(cache)

    remaining = max(0, len(pending) - added)
    return {
        "translated": added, "requested": len(batch),
        "remaining": remaining, "total": len(all_items),
        "done": remaining == 0, "targetLang": target_lang,
    }


def api_commands_translate(body: dict) -> dict:
    """하위 호환 shim — kind=cmd 로 강제."""
    b = dict(body or {})
    b["kind"] = "cmd"
    return api_translate_batch(b)
