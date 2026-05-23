"""Codex Docs Hub — official OpenAI Codex docs index.

This is a small static catalogue used by the local dashboard. Keep URLs on
``developers.openai.com/codex`` unless an item intentionally points to the
OpenAI API docs.
"""
from __future__ import annotations

_CODEX = "https://developers.openai.com/codex"
_API = "https://developers.openai.com/api/docs"

CATALOG: dict[str, list[dict]] = {
    "using-codex": [
        {"url": f"{_CODEX}/cli", "title": "Codex CLI", "summary": "Run Codex locally from a terminal; read, edit, and run code in the selected directory.", "relatedTab": "sessions"},
        {"url": f"{_CODEX}/ide", "title": "IDE Extension", "summary": "Use Codex side by side in VS Code-compatible editors and JetBrains IDEs.", "relatedTab": "ideStatus"},
        {"url": f"{_CODEX}/cloud", "title": "Codex Web", "summary": "Delegate tasks to Codex cloud environments and apply diffs locally.", "relatedTab": None},
        {"url": f"{_CODEX}/use-cases", "title": "Use cases", "summary": "Official workflow examples for engineering, quality, automation, and knowledge work.", "relatedTab": "codexHarness"},
    ],
    "configuration": [
        {"url": f"{_CODEX}/config-basic", "title": "Config basics", "summary": "Configuration layers, precedence, user/project config.toml, profiles, and common options.", "relatedTab": "codexHarness"},
        {"url": f"{_CODEX}/config-advanced", "title": "Advanced config", "summary": "One-off overrides, sandbox combinations, shell environment policy, MCP, and OTel.", "relatedTab": "codexHarness"},
        {"url": f"{_CODEX}/config-reference", "title": "Config reference", "summary": "Reference for official config.toml keys and profile-scoped options.", "relatedTab": "codexHarness"},
        {"url": f"{_CODEX}/sample-config", "title": "Sample config", "summary": "Official sample config.toml patterns.", "relatedTab": "codexHarness"},
        {"url": f"{_CODEX}/rules", "title": "Rules", "summary": "Command/tool rules and permission control.", "relatedTab": "permissions"},
        {"url": f"{_CODEX}/hooks", "title": "Hooks", "summary": "PreToolUse, PostToolUse, Stop, and other automation hooks.", "relatedTab": "hooks"},
        {"url": f"{_CODEX}/agents-md", "title": "AGENTS.md", "summary": "Project instructions and durable context for Codex.", "relatedTab": "codexmd"},
        {"url": f"{_CODEX}/mcp", "title": "MCP", "summary": "Model Context Protocol servers and external tool/context connections.", "relatedTab": "mcp"},
    ],
    "extensions": [
        {"url": f"{_CODEX}/plugins", "title": "Plugins", "summary": "Installable bundles of skills, agents, and commands.", "relatedTab": "plugins"},
        {"url": f"{_CODEX}/skills", "title": "Skills", "summary": "Save repeatable workflows as SKILL.md instructions.", "relatedTab": "skills"},
        {"url": f"{_CODEX}/subagents", "title": "Subagents", "summary": "Parallelize complex tasks with configured agent roles.", "relatedTab": "agents"},
        {"url": f"{_CODEX}/slash-commands", "title": "Slash commands", "summary": "CLI and IDE slash commands.", "relatedTab": "commands"},
    ],
    "automation": [
        {"url": f"{_CODEX}/non-interactive", "title": "Non-interactive mode", "summary": "Script Codex for repeatable automation.", "relatedTab": "agentSdkScaffold"},
        {"url": f"{_CODEX}/sdk", "title": "Codex SDK", "summary": "Build automation around Codex programmatically.", "relatedTab": "agentSdkScaffold"},
        {"url": f"{_CODEX}/github-action", "title": "GitHub Action", "summary": "Run Codex from GitHub workflows.", "relatedTab": None},
        {"url": f"{_CODEX}/mcp-server", "title": "Codex MCP Server", "summary": "Expose Codex through MCP.", "relatedTab": "mcp"},
    ],
    "openai-api": [
        {"url": f"{_API}/guides/tools", "title": "OpenAI tools", "summary": "OpenAI API tool-use concepts used by local playground tabs.", "relatedTab": "serverTools"},
        {"url": f"{_API}/guides/function-calling", "title": "Function calling", "summary": "Structured tool calls and tool results.", "relatedTab": "toolUseLab"},
        {"url": f"{_API}/guides/batch", "title": "Batch API", "summary": "Batch request processing.", "relatedTab": "batchJobs"},
        {"url": f"{_API}/api-reference/files", "title": "Files API", "summary": "Upload and manage files for OpenAI API workflows.", "relatedTab": "apiFiles"},
        {"url": f"{_API}/guides/embeddings", "title": "Embeddings", "summary": "OpenAI embeddings guide.", "relatedTab": "embeddingLab"},
    ],
}

CATEGORY_LABELS = {
    "using-codex": "Using Codex",
    "configuration": "Configuration",
    "extensions": "Plugins · Skills · Subagents",
    "automation": "Automation",
    "openai-api": "OpenAI API playground support",
}


def api_codex_docs_list(_q: dict | None = None) -> dict:
    return {
        "categories": [
            {"id": cid, "label": CATEGORY_LABELS.get(cid, cid), "items": items}
            for cid, items in CATALOG.items()
        ],
    }


def api_codex_docs_search(query: dict) -> dict:
    q = (query.get("q", [""])[0] if isinstance(query, dict) else "").strip().lower()
    if not q:
        return api_codex_docs_list(None)
    out = []
    for cid, items in CATALOG.items():
        hits = [
            it for it in items
            if q in it["title"].lower() or q in it["summary"].lower() or q in it["url"].lower()
        ]
        if hits:
            out.append({"id": cid, "label": CATEGORY_LABELS.get(cid, cid), "items": hits})
    return {"categories": out, "query": q}
