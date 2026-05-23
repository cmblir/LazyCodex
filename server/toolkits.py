"""Official Codex toolkit status helpers.

The Guide Hub now points to OpenAI Codex documentation, config.toml schema,
slash commands, skills, and OpenAI Docs MCP. Older third-party installer
endpoints remain as compatibility shims so stale frontend bundles or browser
tabs fail closed instead of installing unverified assets.
"""
from __future__ import annotations

import shutil
from typing import Any

from .cli_tools import _which


def api_toolkit_status(_q: dict | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "gitAvailable": bool(_which("git")),
        "codexAvailable": bool(_which("codex")),
        "toolkits": [
            {
                "id": "openai-codex-config",
                "title": "OpenAI Codex config.toml",
                "doc": "https://developers.openai.com/codex/config-reference",
            },
            {
                "id": "openai-docs-mcp",
                "title": "OpenAI Docs MCP",
                "doc": "https://developers.openai.com/learn/docs-mcp",
                "command": "codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp",
            },
            {
                "id": "openai-codex-slash-commands",
                "title": "Codex slash commands",
                "doc": "https://developers.openai.com/codex/cli/slash-commands",
            },
        ],
        "legacyInstallersDisabled": True,
        "pluginCommandAvailable": bool(shutil.which("codex") or _which("codex")),
    }


def _disabled_install_endpoint(_body: dict | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "This installer has been removed. Use Guide Hub official Codex resources or the Codex CLI /plugins flow.",
        "doc": "https://developers.openai.com/codex/plugins",
    }


def api_toolkit_ecc_install(_body: dict | None = None) -> dict[str, Any]:
    return _disabled_install_endpoint(_body)


def api_toolkit_ecc_uninstall(_body: dict | None = None) -> dict[str, Any]:
    return _disabled_install_endpoint(_body)


def api_toolkit_ecc_install_plugin(_body: dict | None = None) -> dict[str, Any]:
    return _disabled_install_endpoint(_body)


def api_toolkit_ecc_uninstall_plugin(_body: dict | None = None) -> dict[str, Any]:
    return _disabled_install_endpoint(_body)


def api_toolkit_ccb_install(_body: dict | None = None) -> dict[str, Any]:
    return _disabled_install_endpoint(_body)


def api_toolkit_ccb_uninstall(_body: dict | None = None) -> dict[str, Any]:
    return _disabled_install_endpoint(_body)


def api_toolkit_ccb_open(_body: dict | None = None) -> dict[str, Any]:
    return _disabled_install_endpoint(_body)
