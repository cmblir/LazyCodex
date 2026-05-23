"""플러그인 / 마켓플레이스 관리.

- api_plugins_browse : 설치된 모든 마켓플레이스의 plugins 목록 + 상태
- api_plugin_toggle  : settings.json 의 enabledPlugins 토글
- list_plugins_api   : installed_plugins.json 기반 설치 리스트
- list_marketplaces  : known_marketplaces.json 기반 (읽기)
- api_marketplace_list/add/remove : settings.extraKnownMarketplaces 편집
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from .codex_md import get_settings, put_settings
from .config import CODEX_CONFIG_TOML, INSTALLED_PLUGINS_JSON, KNOWN_MARKETPLACES_JSON, PLUGINS_DIR
from .translations import _load_translation_cache
from .utils import _safe_read


def _config_plugin_enabled() -> dict[str, bool]:
    if not CODEX_CONFIG_TOML.exists():
        return {}
    try:
        data = tomllib.loads(_safe_read(CODEX_CONFIG_TOML))
    except Exception:
        return {}
    plugins = data.get("plugins", {}) if isinstance(data, dict) else {}
    out: dict[str, bool] = {}
    if isinstance(plugins, dict):
        for pid, meta in plugins.items():
            if isinstance(meta, dict):
                out[str(pid)] = bool(meta.get("enabled", True))
    return out


def _plugin_counts(root: Path) -> dict:
    skills_dir = root / "skills"
    commands_dir = root / "commands"
    agents_dir = root / "agents"
    hooks_dir = root / "hooks"
    return {
        "agents": len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0,
        "skills": sum(1 for x in skills_dir.iterdir() if x.is_dir() and (x / "SKILL.md").exists()) if skills_dir.exists() else 0,
        "commands": len(list(commands_dir.glob("*.md"))) if commands_dir.exists() else 0,
        "hooks": len(list(hooks_dir.iterdir())) if hooks_dir.exists() else 0,
    }


def _read_plugin_json(root: Path) -> dict:
    for candidate in (root / ".codex-plugin" / "plugin.json", root / "codex-plugin.json", root / "plugin.json"):
        if candidate.exists():
            try:
                return json.loads(_safe_read(candidate))
            except Exception:
                return {}
    return {}


def discover_plugin_roots() -> list[dict]:
    """Return concrete plugin roots Codex can load.

    Current Codex installs bundled/runtime plugins under
    ``~/.codex/plugins/cache/<market>/<plugin>/<version>`` and records enabled
    state in ``config.toml``. Older marketplace checkouts are still supported.
    """
    settings = get_settings()
    legacy_enabled = settings.get("enabledPlugins", {}) if isinstance(settings, dict) else {}
    config_enabled = _config_plugin_enabled()
    out: list[dict] = []
    seen: set[str] = set()

    cache_dir = PLUGINS_DIR / "cache"
    if cache_dir.exists():
        for pj in sorted(cache_dir.glob("*/*/*/.codex-plugin/plugin.json")):
            root = pj.parent.parent
            plugin = root.parent.name
            market = root.parent.parent.name
            plugin_id = f"{plugin}@{market}"
            if plugin_id in seen:
                continue
            seen.add(plugin_id)
            meta = _read_plugin_json(root)
            iface = meta.get("interface") if isinstance(meta.get("interface"), dict) else {}
            out.append({
                "id": plugin_id,
                "name": meta.get("name") or plugin,
                "marketplace": market,
                "description": meta.get("description") or iface.get("shortDescription", ""),
                "author": (meta.get("author") or {}).get("name") if isinstance(meta.get("author"), dict) else meta.get("author", ""),
                "tags": meta.get("keywords", []) if isinstance(meta.get("keywords"), list) else [],
                "version": meta.get("version") or root.name,
                "installed": True,
                "enabled": bool(config_enabled.get(plugin_id, legacy_enabled.get(plugin_id, True))),
                "installPath": str(root),
                "source": "cache",
                "counts": _plugin_counts(root),
            })

    markets_dir = PLUGINS_DIR / "marketplaces"
    if markets_dir.exists():
        for market in sorted(markets_dir.iterdir()):
            if not market.is_dir() or market.name.endswith(".bak"):
                continue
            plugins_root = market / "plugins"
            if not plugins_root.exists():
                continue
            for plugin_dir in sorted(plugins_root.iterdir()):
                if not plugin_dir.is_dir():
                    continue
                plugin_id = f"{plugin_dir.name}@{market.name}"
                if plugin_id in seen:
                    continue
                seen.add(plugin_id)
                meta = _read_plugin_json(plugin_dir)
                out.append({
                    "id": plugin_id,
                    "name": meta.get("name") or plugin_dir.name,
                    "marketplace": market.name,
                    "description": meta.get("description", ""),
                    "author": (meta.get("author") or {}).get("name") if isinstance(meta.get("author"), dict) else meta.get("author", ""),
                    "tags": meta.get("keywords", []) if isinstance(meta.get("keywords"), list) else [],
                    "version": meta.get("version", ""),
                    "installed": plugin_id in config_enabled or bool(legacy_enabled.get(plugin_id)),
                    "enabled": bool(config_enabled.get(plugin_id, legacy_enabled.get(plugin_id, False))),
                    "installPath": str(plugin_dir),
                    "source": "marketplace",
                    "counts": _plugin_counts(plugin_dir),
                })
    return out


def api_plugins_browse() -> dict:
    """설치된 마켓플레이스의 모든 plugins 리스트 + 설치/활성 상태."""
    roots = discover_plugin_roots()
    if roots:
        cache = _load_translation_cache()
        for p in roots:
            pid = p["id"]
            p["descriptionKo"] = cache.get(f"plugin:{pid}", "")
            p["descriptionEn"] = cache.get(f"en:plugin:{pid}", "")
            p["descriptionZh"] = cache.get(f"zh:plugin:{pid}", "")
        return {
            "plugins": roots,
            "marketplaces": len({p.get("marketplace", "") for p in roots if p.get("marketplace")}),
        }

    markets_dir = PLUGINS_DIR / "marketplaces"
    if not markets_dir.exists():
        return {"plugins": []}
    settings = get_settings()
    enabled = settings.get("enabledPlugins", {}) if isinstance(settings, dict) else {}

    installed_json: dict = {}
    if INSTALLED_PLUGINS_JSON.exists():
        try:
            installed_json = json.loads(_safe_read(INSTALLED_PLUGINS_JSON))
        except Exception:
            installed_json = {}
    installed_plugins_map = installed_json.get("plugins", {}) if isinstance(installed_json, dict) else {}

    out: list = []
    for market in sorted(markets_dir.iterdir()):
        if not market.is_dir() or market.name.endswith(".bak"):
            continue
        plugins_root = market / "plugins"
        if not plugins_root.exists():
            continue
        # marketplace.json 읽기 시도
        mp_meta: dict = {}
        for candidate in ("marketplace.json", ".codex-plugin/marketplace.json"):
            f = market / candidate
            if f.exists():
                try:
                    mp_meta = json.loads(_safe_read(f))
                    break
                except Exception:
                    pass

        mp_plugins: dict = {}
        if isinstance(mp_meta, dict):
            for p in mp_meta.get("plugins", []) or []:
                if isinstance(p, dict) and p.get("name"):
                    mp_plugins[p["name"]] = p

        for plugin_dir in sorted(plugins_root.iterdir()):
            if not plugin_dir.is_dir():
                continue
            name = plugin_dir.name
            mp_entry = mp_plugins.get(name, {})
            desc = mp_entry.get("description", "")
            if not desc:
                pj = plugin_dir / "codex-plugin.json"
                if pj.exists():
                    try:
                        pjd = json.loads(_safe_read(pj))
                        desc = pjd.get("description", "")
                    except Exception:
                        pass
            composite_id = f"{name}@{market.name}"
            is_installed = composite_id in installed_plugins_map
            is_enabled = bool(enabled.get(composite_id, False))
            agents_n = len(list((plugin_dir / "agents").glob("*.md"))) if (plugin_dir / "agents").exists() else 0
            skills_n = sum(1 for x in (plugin_dir / "skills").iterdir() if x.is_dir()) if (plugin_dir / "skills").exists() else 0
            commands_n = len(list((plugin_dir / "commands").glob("*.md"))) if (plugin_dir / "commands").exists() else 0
            hooks_n = len(list((plugin_dir / "hooks").iterdir())) if (plugin_dir / "hooks").exists() else 0
            out.append({
                "id": composite_id,
                "name": name,
                "marketplace": market.name,
                "description": desc,
                "author": (mp_entry.get("author") or {}).get("name")
                    if isinstance(mp_entry.get("author"), dict) else mp_entry.get("author", ""),
                "tags": mp_entry.get("tags", []) if isinstance(mp_entry.get("tags"), list) else [],
                "version": mp_entry.get("version", ""),
                "installed": is_installed,
                "enabled": is_enabled,
                "counts": {"agents": agents_n, "skills": skills_n, "commands": commands_n, "hooks": hooks_n},
            })
    cache = _load_translation_cache()
    for p in out:
        pid = p["id"]
        p["descriptionKo"] = cache.get(f"plugin:{pid}", "")
        p["descriptionEn"] = cache.get(f"en:plugin:{pid}", "")
        p["descriptionZh"] = cache.get(f"zh:plugin:{pid}", "")
    return {
        "plugins": out,
        "marketplaces": len({m.name for m in markets_dir.iterdir() if m.is_dir() and not m.name.endswith('.bak')}),
    }


def api_plugin_toggle(body: dict) -> dict:
    """settings.json 의 enabledPlugins 토글."""
    plugin_id = (body or {}).get("id")
    enable = bool((body or {}).get("enable", True))
    if not plugin_id:
        return {"ok": False, "error": "id required"}
    s = get_settings()
    if not isinstance(s, dict):
        s = {}
    ep = s.get("enabledPlugins")
    if not isinstance(ep, dict):
        ep = {}
        s["enabledPlugins"] = ep
    ep[plugin_id] = bool(enable)
    return put_settings(s)


def list_plugins_api() -> list:
    discovered = discover_plugin_roots()
    if discovered:
        return [{
            "id": p["id"],
            "name": p["name"],
            "marketplace": p["marketplace"],
            "version": p.get("version", ""),
            "scope": "user",
            "enabled": bool(p.get("enabled")),
            "installPath": p.get("installPath", ""),
            "installedAt": "",
            "lastUpdated": "",
        } for p in discovered]
    if not INSTALLED_PLUGINS_JSON.exists():
        return []
    try:
        data = json.loads(_safe_read(INSTALLED_PLUGINS_JSON))
    except Exception:
        return []
    plugins_raw = data.get("plugins", {}) if isinstance(data, dict) else {}
    settings = get_settings()
    enabled_map = settings.get("enabledPlugins", {}) if isinstance(settings, dict) else {}
    out: list = []
    if not isinstance(plugins_raw, dict):
        return out
    for plugin_id, installs in plugins_raw.items():
        if not isinstance(installs, list) or not installs:
            continue
        latest = installs[-1] if isinstance(installs[-1], dict) else {}
        name = plugin_id.split("@")[0] if "@" in plugin_id else plugin_id
        marketplace = plugin_id.split("@")[1] if "@" in plugin_id else "unknown"
        out.append({
            "id": plugin_id, "name": name, "marketplace": marketplace,
            "version": latest.get("version", ""), "scope": latest.get("scope", "user"),
            "enabled": bool(enabled_map.get(plugin_id, False)),
            "installPath": latest.get("installPath", ""),
            "installedAt": latest.get("installedAt", ""),
            "lastUpdated": latest.get("lastUpdated", ""),
        })
    return out


def list_marketplaces() -> list:
    if not KNOWN_MARKETPLACES_JSON.exists():
        return []
    try:
        data = json.loads(_safe_read(KNOWN_MARKETPLACES_JSON))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    out: list = []
    for name, meta in data.items():
        if not isinstance(meta, dict):
            continue
        source = meta.get("source") or {}
        out.append({
            "id": name,
            "name": name,
            "type": source.get("source", ""),
            "repo": source.get("repo", ""),
            "installLocation": meta.get("installLocation", ""),
            "lastUpdated": meta.get("lastUpdated", ""),
        })
    return out


def api_marketplace_list() -> dict:
    """known_marketplaces.json + settings.extraKnownMarketplaces."""
    km: dict = {}
    if KNOWN_MARKETPLACES_JSON.exists():
        try:
            km = json.loads(_safe_read(KNOWN_MARKETPLACES_JSON))
        except Exception:
            km = {}
    s = get_settings()
    extra = (s.get("extraKnownMarketplaces") if isinstance(s, dict) else None) or {}
    out: list = []
    for name, meta in {**km, **extra}.items():
        src = (meta or {}).get("source") or {}
        out.append({
            "id": name,
            "name": name,
            "type": src.get("source", ""),
            "repo": src.get("repo") or src.get("url") or "",
            "installLocation": meta.get("installLocation", ""),
            "lastUpdated": meta.get("lastUpdated", ""),
            "inSettingsExtra": name in extra,
        })
    return {"marketplaces": out}


def api_marketplace_add(body: dict) -> dict:
    """settings.json 의 extraKnownMarketplaces 에 추가. body: {name, url}"""
    if not isinstance(body, dict):
        return {"ok": False, "error": "bad body"}
    name = (body.get("name") or "").strip()
    url = (body.get("url") or "").strip()
    if not re.match(r"^[a-zA-Z0-9_.-]+$", name):
        return {"ok": False, "error": "이름은 영숫자/-/_/. 만 허용", "error_key": "err_marketplace_name_invalid"}
    if not url.startswith("http"):
        return {"ok": False, "error": "git URL 필요", "error_key": "err_marketplace_url_required"}
    s = get_settings()
    if not isinstance(s, dict):
        s = {}
    extra = s.get("extraKnownMarketplaces") or {}
    extra[name] = {"source": {"source": "git", "url": url}}
    s["extraKnownMarketplaces"] = extra
    return put_settings(s)


def api_marketplace_remove(body: dict) -> dict:
    name = (body or {}).get("name") if isinstance(body, dict) else None
    if not name:
        return {"ok": False, "error": "name required"}
    s = get_settings()
    extra = s.get("extraKnownMarketplaces") if isinstance(s, dict) else None
    if not isinstance(extra, dict) or name not in extra:
        return {"ok": False, "error": "등록된 마켓플레이스가 아닙니다", "error_key": "err_marketplace_not_found"}
    del extra[name]
    s["extraKnownMarketplaces"] = extra
    return put_settings(s)
