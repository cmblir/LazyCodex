"""Codex CLI 스킬 (`~/.codex/skills/*`) + 플러그인 마켓플레이스 스킬.

- list_skills: 사용자 스킬 + 플러그인 스킬 + 번역 주입
- get_skill / put_skill: 단건 조회/편집 (플러그인 스킬은 read-only)
- _scan_plugin_skills / _resolve_skill_path: 플러그인 두 레이아웃 지원
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from threading import Lock
from typing import Optional

from .codex_md import get_settings
from .config import PLUGINS_DIR, SKILLS_DIR
from .plugins import discover_plugin_roots
from .translations import _load_translation_cache
from .utils import _parse_frontmatter, _safe_read, _safe_write, _strip_frontmatter


def _skill_record(skill_md: Path, sid: str, scope: str, source: str, plugin_key: str = "", read_only: bool = False) -> dict:
    raw = _safe_read(skill_md)
    meta = _parse_frontmatter(raw)
    root = skill_md.parent
    return {
        "id": sid,
        "name": meta.get("name", root.name),
        "path": str(root),
        "description": meta.get("description", ""),
        "source": source,
        "scope": scope,
        "pluginKey": plugin_key,
        "pluginEnabled": None if scope != "plugin" else False,
        "readOnly": read_only,
        "files": [f.name for f in root.iterdir() if f.is_file()],
        "content": _strip_frontmatter(raw)[:8000],
    }


def _scan_system_skills() -> list:
    out: list = []
    system_dir = SKILLS_DIR / ".system"
    if not system_dir.exists():
        return out
    for sd in sorted(system_dir.iterdir()):
        skill_md = sd / "SKILL.md"
        if sd.is_dir() and skill_md.exists():
            out.append(_skill_record(skill_md, f".system:{sd.name}", "system", "Codex system", read_only=True))
    return out


def _scan_plugin_skills() -> list:
    """활성·비활성 모든 마켓플레이스 플러그인의 스킬 수집."""
    out: list = []
    for plugin in discover_plugin_roots():
        root = Path(plugin.get("installPath", ""))
        skills_dir = root / "skills"
        if not skills_dir.exists():
            continue
        for sd in sorted(skills_dir.iterdir()):
            skill_md = sd / "SKILL.md"
            if not sd.is_dir() or not skill_md.exists():
                continue
            sid = f"{plugin['marketplace']}:{plugin['name']}:{sd.name}"
            rec = _skill_record(skill_md, sid, "plugin", f"{plugin['marketplace']}/{plugin['name']}", plugin["id"], read_only=True)
            rec["pluginEnabled"] = bool(plugin.get("enabled"))
            out.append(rec)
    if out:
        return out

    if not PLUGINS_DIR.exists():
        return out
    markets_dir = PLUGINS_DIR / "marketplaces"
    if not markets_dir.exists():
        return out
    seen: set[str] = set()
    for market in sorted(markets_dir.iterdir()):
        if not market.is_dir() or market.name.endswith(".bak"):
            continue
        # Layout A: <market>/plugins/<plugin>/skills/<id>/SKILL.md
        plugins_root = market / "plugins"
        if plugins_root.exists():
            for plugin_dir in sorted(plugins_root.iterdir()):
                if not plugin_dir.is_dir():
                    continue
                skills_dir = plugin_dir / "skills"
                if not skills_dir.exists():
                    continue
                for sd in sorted(skills_dir.iterdir()):
                    if not sd.is_dir():
                        continue
                    skill_md = sd / "SKILL.md"
                    if not skill_md.exists():
                        continue
                    if str(sd) in seen:
                        continue
                    seen.add(str(sd))
                    raw = _safe_read(skill_md)
                    meta = _parse_frontmatter(raw)
                    sid = f"{market.name}:{plugin_dir.name}:{sd.name}"
                    out.append({
                        "id": sid,
                        "name": meta.get("name", sd.name),
                        "path": str(sd),
                        "description": meta.get("description", ""),
                        "source": f"{market.name}/{plugin_dir.name}",
                        "scope": "plugin",
                        "pluginKey": f"{plugin_dir.name}@{market.name}",
                        "files": [f.name for f in sd.iterdir() if f.is_file()],
                        "content": _strip_frontmatter(raw)[:8000],
                    })
        # Layout B: <market>/skills/<id>/SKILL.md  (ecc 스타일)
        direct = market / "skills"
        if direct.exists():
            for sd in sorted(direct.iterdir()):
                if not sd.is_dir():
                    continue
                skill_md = sd / "SKILL.md"
                if not skill_md.exists():
                    continue
                if str(sd) in seen:
                    continue
                seen.add(str(sd))
                raw = _safe_read(skill_md)
                meta = _parse_frontmatter(raw)
                sid = f"{market.name}:{sd.name}"
                out.append({
                    "id": sid,
                    "name": meta.get("name", sd.name),
                    "path": str(sd),
                    "description": meta.get("description", ""),
                    "source": f"{market.name}",
                    "scope": "plugin",
                    "pluginKey": f"{market.name}@{market.name}",
                    "files": [f.name for f in sd.iterdir() if f.is_file()],
                    "content": _strip_frontmatter(raw)[:8000],
                })
    return out


# v2.43.1 — TTL+mtime cache. The bare scan walks 485 SKILL.md files across
# user + every installed plugin marketplace and takes ~800 ms on a power
# user's machine. Invalidate on the newest top-level mtime so a freshly
# edited skill shows up immediately.
_SKILLS_TTL_S = 60
_skills_cache: dict = {"key": None, "ts": 0.0, "value": None}
_skills_lock = Lock()


def _skills_fingerprint() -> tuple:
    """Cheap fingerprint — only stat the top-level dirs, not every SKILL.md.
    A new/edited skill always lands inside one of these, so its parent's
    mtime bumps too on filesystem-level change."""
    parts: list[float] = []
    try:
        if SKILLS_DIR.exists():
            parts.append(SKILLS_DIR.stat().st_mtime)
            for p in SKILLS_DIR.iterdir():
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


def list_skills(force_refresh: bool = False) -> list:
    """Cached wrapper. Pass ``force_refresh=True`` (or hit the endpoint with
    ``?refresh=1``) to bypass the cache."""
    fp = _skills_fingerprint()
    now = time.time()
    if not force_refresh:
        with _skills_lock:
            if (_skills_cache["key"] == fp
                    and _skills_cache["value"] is not None
                    and (now - _skills_cache["ts"]) < _SKILLS_TTL_S):
                return _skills_cache["value"]
    value = _list_skills_uncached()
    with _skills_lock:
        _skills_cache["key"] = fp
        _skills_cache["ts"] = now
        _skills_cache["value"] = value
    return value


def _list_skills_uncached() -> list:
    out: list = []
    if SKILLS_DIR.exists():
        try:
            entries = sorted(SKILLS_DIR.iterdir())
        except Exception:
            entries = []
        for p in entries:
            try:
                ok = p.is_dir() or p.is_symlink()
            except Exception:
                ok = False
            if not ok:
                continue
            if p.name == ".system":
                continue
            skill_md = p / "SKILL.md"
            if not skill_md.exists():
                continue
            meta: dict = {}
            content = ""
            try:
                raw = _safe_read(skill_md)
                meta = _parse_frontmatter(raw)
                content = _strip_frontmatter(raw)
            except Exception:
                pass
            try:
                files = [f.name for f in p.iterdir() if f.is_file()]
            except Exception:
                files = []
            out.append({
                "id": p.name,
                "name": meta.get("name", p.name),
                "path": str(p),
                "description": meta.get("description", ""),
                "source": "user",
                "scope": "user",
                "files": files,
                "content": content[:8000],
            })

    out.extend(_scan_system_skills())

    # 플러그인 스킬 — 활성 여부 주입
    plugin_skills = _scan_plugin_skills()
    settings = get_settings()
    enabled_map = (settings.get("enabledPlugins") or {}) if isinstance(settings, dict) else {}
    for ps in plugin_skills:
        key = ps.get("pluginKey", "")
        if key in enabled_map:
            ps["pluginEnabled"] = bool(enabled_map.get(key))
        else:
            ps["pluginEnabled"] = bool(ps.get("pluginEnabled"))
    out.extend(plugin_skills)

    # 번역 주입 (ko/en/zh)
    cache = _load_translation_cache()
    for s in out:
        sid = s["id"]
        s["descriptionKo"] = cache.get(f"skill:{sid}", "")
        s["descriptionEn"] = cache.get(f"en:skill:{sid}", "")
        s["descriptionZh"] = cache.get(f"zh:skill:{sid}", "")
    return out


def _resolve_skill_path(skill_id: str) -> tuple[Optional[Path], str]:
    """skill_id → (실제 SKILL.md 경로, scope). scope ∈ {'user','plugin',''}."""
    if skill_id.startswith(".system:"):
        sid = skill_id.split(":", 1)[1]
        if not re.match(r"^[a-zA-Z0-9_.-]+$", sid or ""):
            return None, ""
        p = SKILLS_DIR / ".system" / sid / "SKILL.md"
        return (p if p.exists() else None), "system"
    if ":" in skill_id:
        parts = skill_id.split(":")
        if not all(re.match(r"^[a-zA-Z0-9_.-]+$", x or "") for x in parts):
            return None, ""
        if len(parts) == 3:
            market, plugin, sd = parts
            for root in discover_plugin_roots():
                if root.get("marketplace") == market and root.get("name") == plugin:
                    p = Path(root.get("installPath", "")) / "skills" / sd / "SKILL.md"
                    if p.exists():
                        return p, "plugin"
        markets_dir = PLUGINS_DIR / "marketplaces"
        if len(parts) == 3:
            market, plugin, sd = parts
            p = markets_dir / market / "plugins" / plugin / "skills" / sd / "SKILL.md"
            return (p if p.exists() else None), "plugin"
        if len(parts) == 2:
            market, sd = parts
            p = markets_dir / market / "skills" / sd / "SKILL.md"
            return (p if p.exists() else None), "plugin"
        return None, ""
    if not re.match(r"^[a-zA-Z0-9_-]+$", skill_id or ""):
        return None, ""
    p = SKILLS_DIR / skill_id / "SKILL.md"
    return (p if p.exists() else None), "user"


def get_skill(skill_id: str) -> dict:
    p, scope = _resolve_skill_path(skill_id)
    if not p:
        return {"error": "not found"}
    raw = _safe_read(p)
    meta = _parse_frontmatter(raw)
    return {
        "id": skill_id,
        "name": meta.get("name", skill_id),
        "description": meta.get("description", ""),
        "raw": raw,
        "content": _strip_frontmatter(raw),
        "scope": scope,
        "readOnly": scope in ("plugin", "system"),
        "path": str(p),
    }


def put_skill(skill_id: str, body: dict) -> dict:
    if ":" in (skill_id or ""):
        from .errors import err
        return err("skill_plugin_readonly")
    if not re.match(r"^[a-zA-Z0-9_-]+$", skill_id or ""):
        return {"ok": False, "error": "invalid skill id"}
    raw = body.get("raw", "") if isinstance(body, dict) else ""
    if not isinstance(raw, str):
        return {"ok": False, "error": "raw must be string"}
    p = SKILLS_DIR / skill_id / "SKILL.md"
    ok = _safe_write(p, raw)
    return {"ok": ok}
