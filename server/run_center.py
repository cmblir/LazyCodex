"""Run Center — unified catalog + executor for local/plugin runnable items.

Run Center wires detected plugin skills and commands into the existing
`execute_with_assignee` pipeline so a single dashboard click can run the item.

Surfaces three things over HTTP:
- `GET  /api/run/catalog`            — all runnable items (filterable by source).
- `POST /api/run/execute`            — run an item with a goal, return result.
- `GET  /api/run/history`            — recent runs (per-user SQLite).
- `GET  /api/run/favorites`          — favorite item IDs.
- `POST /api/run/favorite/toggle`    — toggle a favorite.

The executor is **NOT** a session spawn — it is a one-shot prompt execution
through `execute_with_assignee`, same as a workflow `session` node. The result
comes back as JSON. For long-running flows users are pointed at the workflow
templates (Quick Actions in Phase 3 do that hand-off).
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from .config import _env_path
from .db import _db
from .logger import log
from .utils import _safe_read

# ── Storage ──────────────────────────────────────────────────────────────────

RUN_CENTER_FAV_PATH = _env_path(
    "CODEX_DASHBOARD_RUN_FAVORITES",
    Path.home() / ".codex-dashboard-run-favorites.json",
)


def _ensure_history_table() -> None:
    """Create the `run_history` table if missing. Idempotent."""
    try:
        with _db() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS run_history (
              id TEXT PRIMARY KEY,
              source TEXT,
              item_id TEXT,
              item_name TEXT,
              goal TEXT,
              assignee TEXT,
              status TEXT,
              output TEXT,
              error TEXT,
              tokens_in INTEGER DEFAULT 0,
              tokens_out INTEGER DEFAULT 0,
              cost_usd REAL DEFAULT 0.0,
              duration_ms INTEGER DEFAULT 0,
              ts INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_runhist_ts ON run_history(ts DESC);
            CREATE INDEX IF NOT EXISTS idx_runhist_item ON run_history(source, item_id);
            """)
    except Exception as e:
        log.warning("run_history table init failed: %s", e)


_ensure_history_table()


# ── Catalog: plugin skills + plugin commands ────────────────────────────────

# Older LazyCodex versions installed a third-party Codex plugin marketplace.
# Keep scanning those package names for backward compatibility, but surface them
# as generic plugin catalog entries rather than a branded dependency.
_LEGACY_PLUGIN_SLUG = "everything-" + "codex-" + "code"
_PLUGIN_CATALOG_IDS = ("ecc@ecc", f"{_LEGACY_PLUGIN_SLUG}@{_LEGACY_PLUGIN_SLUG}")
_PLUGIN_CATALOG_NAMES = ("ecc", _LEGACY_PLUGIN_SLUG)
_INSTALLED_PLUGINS_PATH = Path.home() / ".codex" / "plugins" / "installed_plugins.json"


def _plugin_catalog_roots() -> list[Path]:
    """Return every install path that looks like a plugin catalog, deduped by recency.

    Resolution order:
      1. installed_plugins.json — authoritative when the user clicked install
         from Guide & Tools.
      2. ~/.codex/plugins/cache/<pkg>/<pkg>/<version>/ — older installs that
         haven't updated the json yet.
      3. ~/.codex/plugins/marketplaces/<pkg>/ — when only the marketplace is
         registered (skills/commands are still readable as a fallback).
    """
    seen: set[str] = set()
    roots: list[Path] = []

    # 1. installed_plugins.json
    try:
        if _INSTALLED_PLUGINS_PATH.exists():
            data = json.loads(_safe_read(_INSTALLED_PLUGINS_PATH) or "{}")
            for pid, entries in (data.get("plugins") or {}).items():
                if pid not in _PLUGIN_CATALOG_IDS:
                    continue
                for ent in entries or []:
                    p = ent.get("installPath")
                    if not p:
                        continue
                    pp = Path(p)
                    if (pp / "skills").exists() and str(pp) not in seen:
                        roots.append(pp); seen.add(str(pp))
    except Exception as e:
        log.warning("installed_plugins.json read failed: %s", e)

    # 2. cache glob
    cache_base = Path.home() / ".codex" / "plugins" / "cache"
    for pkg in _PLUGIN_CATALOG_NAMES:
        outer = cache_base / pkg / pkg
        if outer.exists():
            for ver in sorted(outer.iterdir(), reverse=True):
                if ver.is_dir() and (ver / "skills").exists() and str(ver) not in seen:
                    roots.append(ver); seen.add(str(ver))

    # 3. marketplace
    mp_base = Path.home() / ".codex" / "plugins" / "marketplaces"
    for pkg in _PLUGIN_CATALOG_NAMES:
        mp = mp_base / pkg
        if mp.exists() and (mp / "skills").exists() and str(mp) not in seen:
            roots.append(mp); seen.add(str(mp))

    return roots


def _plugin_catalog_root() -> Optional[Path]:
    """Backwards-compat wrapper — returns the first detected plugin catalog root."""
    rs = _plugin_catalog_roots()
    return rs[0] if rs else None


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) from a markdown document."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    block = m.group(1)
    fm: dict = {}
    for line in block.splitlines():
        kv = re.match(r"^(\w[\w-]*):\s*(.*)$", line.strip())
        if kv:
            v = kv.group(2).strip().strip('"').strip("'")
            fm[kv.group(1)] = v
    return fm, text[m.end():]


def _categorize_skill(name: str, description: str) -> str:
    """Best-effort tag a skill into a coarse category for filter chips."""
    low = (name + " " + description).lower()
    if any(k in low for k in ("frontend", "react", "ui", "css", "tailwind", "next", "nuxt", "vue", "svelte")):
        return "frontend"
    if any(k in low for k in ("backend", "api", "server", "rest", "django", "spring", "laravel", "nestjs", "fastapi")):
        return "backend"
    if any(k in low for k in ("test", "tdd", "pytest", "jest", "junit", "kotest", "kotlinstest", "playwright", "e2e")):
        return "testing"
    if any(k in low for k in ("review", "lint", "code-review", "quality")):
        return "review"
    if any(k in low for k in ("security", "owasp", "vuln", "auth", "secret", "csrf", "xss")):
        return "security"
    if any(k in low for k in ("deploy", "docker", "k8s", "ci/cd", "ops", "kubernetes")):
        return "ops"
    if any(k in low for k in ("ai", "llm", "codex", "agent", "embed", "prompt", "rag")):
        return "ai"
    if any(k in low for k in ("data", "sql", "database", "etl", "analytics", "postgres", "clickhouse", "mongo")):
        return "data"
    if any(k in low for k in ("ml", "pytorch", "tensorflow", "training", "model")):
        return "ml"
    if any(k in low for k in ("mobile", "android", "ios", "flutter", "swift", "kotlin")):
        return "mobile"
    return "general"


def _list_plugin_skills(root: Path) -> list[dict]:
    """Read every SKILL.md under <root>/skills/<name>/SKILL.md."""
    out = []
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return out
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        sf = child / "SKILL.md"
        if not sf.exists():
            continue
        try:
            text = _safe_read(sf, limit=4_000)
            fm, _ = _parse_frontmatter(text)
        except Exception:
            continue
        name = fm.get("name") or child.name
        desc = fm.get("description") or ""
        out.append({
            "id":          f"plugin:skill:{child.name}",
            "source":      "plugin",
            "kind":        "skill",
            "name":        name,
            "description": desc,
            "category":    _categorize_skill(name, desc),
            "invocation":  f"Use the `{name}` skill",
            "tools":       fm.get("tools", ""),
            "path":        str(sf),
        })
    return out


def _list_plugin_commands(root: Path) -> list[dict]:
    """Read every commands/*.md."""
    out = []
    cdir = root / "commands"
    if not cdir.exists():
        return out
    for fp in sorted(cdir.glob("*.md")):
        try:
            text = _safe_read(fp, limit=4_000)
            fm, _ = _parse_frontmatter(text)
        except Exception:
            continue
        cname = fm.get("name") or fp.stem
        desc = fm.get("description") or ""
        out.append({
            "id":          f"plugin:cmd:{cname}",
            "source":      "plugin",
            "kind":        "command",
            "name":        f"/{cname}",
            "description": desc,
            "category":    _categorize_skill(cname, desc),
            "invocation":  f"Run the slash command /{cname}",
            "path":        str(fp),
        })
    return out


_CATALOG_CACHE: dict = {"ts": 0, "items": [], "debug": {}}
_CATALOG_TTL_S = 30


def _build_catalog() -> tuple[list[dict], dict]:
    """Combine all sources. Returns (items, debug_info).

    Debug info captures every plugin catalog root that was scanned plus how many
    skills / commands each contributed for UI diagnostics.
    """
    items: list[dict] = []
    debug: dict = {"plugin_roots": [], "plugin_skill_total": 0, "plugin_cmd_total": 0}
    seen_ids: set[str] = set()

    for root in _plugin_catalog_roots():
        skills = _list_plugin_skills(root)
        commands = _list_plugin_commands(root)
        added_s = 0
        added_c = 0
        for it in skills:
            if it["id"] in seen_ids:
                continue
            items.append(it); seen_ids.add(it["id"]); added_s += 1
        for it in commands:
            if it["id"] in seen_ids:
                continue
            items.append(it); seen_ids.add(it["id"]); added_c += 1
        debug["plugin_roots"].append({
            "path": str(root), "skills": added_s, "commands": added_c,
        })
        debug["plugin_skill_total"] += added_s
        debug["plugin_cmd_total"]   += added_c

    return items, debug


def _get_catalog(force: bool = False) -> tuple[list[dict], dict]:
    now = time.time()
    if (not force) and now - _CATALOG_CACHE["ts"] < _CATALOG_TTL_S and _CATALOG_CACHE["items"]:
        return _CATALOG_CACHE["items"], _CATALOG_CACHE.get("debug", {})
    items, debug = _build_catalog()
    _CATALOG_CACHE["ts"]    = now
    _CATALOG_CACHE["items"] = items
    _CATALOG_CACHE["debug"] = debug
    return items, debug


# ── Favorites ───────────────────────────────────────────────────────────────

def _load_favorites() -> set[str]:
    if not RUN_CENTER_FAV_PATH.exists():
        return set()
    try:
        data = json.loads(_safe_read(RUN_CENTER_FAV_PATH) or "{}")
        ids = data.get("ids") or []
        return {x for x in ids if isinstance(x, str)}
    except Exception:
        return set()


def _save_favorites(ids: set[str]) -> bool:
    try:
        from .utils import _safe_write
        return _safe_write(RUN_CENTER_FAV_PATH, json.dumps({"ids": sorted(ids)}, ensure_ascii=False, indent=2))
    except Exception as e:
        log.error("favorites save failed: %s", e)
        return False


# ── Public APIs ─────────────────────────────────────────────────────────────

def api_run_catalog(query: dict | None = None) -> dict:
    """GET /api/run/catalog?source=plugin&kind=skill|command&q=...&refresh=1"""
    q = query or {}
    src    = (q.get("source", [""])[0] if isinstance(q.get("source"), list) else q.get("source", "")).strip()
    kind   = (q.get("kind",   [""])[0] if isinstance(q.get("kind"),   list) else q.get("kind",   "")).strip()
    needle = (q.get("q",      [""])[0] if isinstance(q.get("q"),      list) else q.get("q",      "")).strip().lower()
    refresh_raw = q.get("refresh", [""])[0] if isinstance(q.get("refresh"), list) else q.get("refresh", "")
    force = str(refresh_raw).lower() in ("1", "true", "yes")

    items, debug = _get_catalog(force=force)
    if src:
        items = [it for it in items if it.get("source") == src]
    if kind:
        items = [it for it in items if it.get("kind") == kind]
    if needle:
        def _match(it):
            return (
                needle in (it.get("name", "")     or "").lower()
                or needle in (it.get("description", "") or "").lower()
                or needle in (it.get("category", "") or "").lower()
            )
        items = [it for it in items if _match(it)]

    favs = _load_favorites()
    counts: dict[str, int] = {}
    for it in items:
        counts[it["source"]] = counts.get(it["source"], 0) + 1
    out_items = []
    for it in items:
        out = dict(it)
        out["favorite"] = it["id"] in favs
        # Strip the verbose `path` from the wire payload — the UI doesn't need it.
        out.pop("path", None)
        out_items.append(out)

    return {
        "ok": True,
        "items": out_items,
        "counts": counts,
        "total": len(out_items),
        "plugin_installed": bool(_plugin_catalog_roots()),
        "debug": debug,
    }


def api_run_favorite_toggle(body: dict) -> dict:
    """POST /api/run/favorite/toggle  body: {id}"""
    if not isinstance(body, dict):
        return {"ok": False, "error": "bad body"}
    item_id = (body.get("id") or "").strip()
    if not item_id:
        return {"ok": False, "error": "id required"}
    favs = _load_favorites()
    if item_id in favs:
        favs.discard(item_id)
        toggled = False
    else:
        favs.add(item_id)
        toggled = True
    if not _save_favorites(favs):
        return {"ok": False, "error": "save failed"}
    return {"ok": True, "favorite": toggled, "count": len(favs)}


def api_run_history(query: dict | None = None) -> dict:
    """GET /api/run/history?limit=50&item=plugin:cmd:foo"""
    q = query or {}
    limit_raw = q.get("limit")
    limit = int((limit_raw[0] if isinstance(limit_raw, list) else limit_raw) or 50)
    limit = max(1, min(limit, 200))
    item_raw = q.get("item")
    item_id = (item_raw[0] if isinstance(item_raw, list) else (item_raw or "")) or ""

    rows: list[dict] = []
    try:
        with _db() as c:
            sql = "SELECT * FROM run_history"
            args: list = []
            if item_id:
                sql += " WHERE source = ? AND item_id = ?"
                src, _, rid = item_id.partition(":")
                rid = rid.replace("skill:", "").replace("cmd:", "")
                args.extend([src, rid])
            sql += " ORDER BY ts DESC LIMIT ?"
            args.append(limit)
            for r in c.execute(sql, args).fetchall():
                rows.append({
                    "id":         r["id"],
                    "source":     r["source"],
                    "itemId":     r["item_id"],
                    "itemName":   r["item_name"],
                    "goal":       (r["goal"] or "")[:200],
                    "assignee":   r["assignee"],
                    "status":     r["status"],
                    "tokensIn":   r["tokens_in"] or 0,
                    "tokensOut":  r["tokens_out"] or 0,
                    "costUsd":    r["cost_usd"] or 0.0,
                    "durationMs": r["duration_ms"] or 0,
                    "ts":         r["ts"],
                })
    except sqlite3.OperationalError as e:
        log.warning("run_history query failed: %s", e)
    return {"ok": True, "rows": rows, "count": len(rows)}


def api_run_history_get(query: dict | None = None) -> dict:
    """GET /api/run/history/get?id=<run_id> — one row including output/error bodies."""
    q = query or {}
    rid = q.get("id")
    rid = rid[0] if isinstance(rid, list) else rid
    if not rid:
        return {"ok": False, "error": "id required"}
    try:
        with _db() as c:
            r = c.execute("SELECT * FROM run_history WHERE id = ?", (rid,)).fetchone()
            if not r:
                return {"ok": False, "error": "not found"}
            return {"ok": True, "run": {k: r[k] for k in r.keys()}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _build_prompt(item: dict, goal: str) -> tuple[str, str]:
    """Compose (system_prompt, user_prompt) from an item + the user's goal."""
    invocation = (item.get("invocation") or "").strip()
    name = item.get("name", "")
    desc = item.get("description", "")
    src = item.get("source", "")

    system_parts = [f"You are LazyCodex Run Center invoking the `{name}` {item.get('kind', 'task')} ({src.upper()})."]
    if desc:
        system_parts.append(f"Item description: {desc}")
    if invocation:
        system_parts.append(invocation)
    system_parts.append(
        "Reply concisely. If the task expects code or a file, output it inside a single fenced block."
    )
    system_prompt = "\n\n".join(system_parts)
    user_prompt = goal.strip() or "(no goal supplied)"
    return system_prompt, user_prompt


def _record_history(rec: dict) -> None:
    try:
        with _db() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO run_history
                (id, source, item_id, item_name, goal, assignee, status, output, error,
                 tokens_in, tokens_out, cost_usd, duration_ms, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec["id"], rec["source"], rec["item_id"], rec["item_name"],
                    rec["goal"], rec["assignee"], rec["status"],
                    (rec.get("output") or "")[:200_000],
                    (rec.get("error")  or "")[:8_000],
                    int(rec.get("tokens_in")  or 0),
                    int(rec.get("tokens_out") or 0),
                    float(rec.get("cost_usd")  or 0.0),
                    int(rec.get("duration_ms") or 0),
                    int(rec.get("ts") or time.time() * 1000),
                ),
            )
    except Exception as e:
        log.warning("run history insert failed: %s", e)


def api_run_execute(body: dict) -> dict:
    """POST /api/run/execute  body: {itemId, goal, assignee?, cwd?, timeoutSeconds?}

    One-shot execution. For long-running multi-stage flows use the Workflow Quick
    Actions in the Workflows tab — this endpoint is intentionally synchronous and
    bounded.
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "bad body"}
    item_id = (body.get("itemId") or "").strip()
    goal    = (body.get("goal") or "").strip()
    if not item_id:
        return {"ok": False, "error": "itemId required"}
    if not goal:
        return {"ok": False, "error": "goal required"}

    items, _ = _get_catalog()
    item = next((it for it in items if it["id"] == item_id), None)
    if not item:
        return {"ok": False, "error": f"item not found: {item_id}"}

    assignee = (body.get("assignee") or "codex:gpt-5-codex").strip()
    cwd      = (body.get("cwd") or "").strip()
    timeout  = max(15, min(int(body.get("timeoutSeconds") or 180), 1800))

    system_prompt, user_prompt = _build_prompt(item, goal)
    run_id = f"run-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
    t0 = time.time()

    try:
        from .ai_providers import execute_with_assignee
        resp = execute_with_assignee(
            assignee, user_prompt,
            system_prompt=system_prompt,
            cwd=cwd or "",
            timeout=timeout,
            extra=None,
            fallback=True,
        )
    except Exception as e:
        log.exception("run execute failed")
        rec = {
            "id": run_id, "source": item["source"],
            "item_id": item["id"], "item_name": item["name"],
            "goal": goal, "assignee": assignee,
            "status": "err", "output": "", "error": f"executor crashed: {e}",
            "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
            "duration_ms": int((time.time() - t0) * 1000),
            "ts": int(time.time() * 1000),
        }
        _record_history(rec)
        return {"ok": False, "error": rec["error"], "runId": run_id}

    duration_ms = resp.duration_ms or int((time.time() - t0) * 1000)
    rec = {
        "id": run_id, "source": item["source"],
        "item_id": item["id"], "item_name": item["name"],
        "goal": goal, "assignee": assignee,
        "status": resp.status,
        "output": resp.output, "error": resp.error or "",
        "tokens_in": resp.tokens_in, "tokens_out": resp.tokens_out,
        "cost_usd": resp.cost_usd or 0.0,
        "duration_ms": duration_ms,
        "ts": int(time.time() * 1000),
    }
    _record_history(rec)

    return {
        "ok":          resp.status == "ok",
        "runId":       run_id,
        "status":      resp.status,
        "output":      resp.output,
        "error":       resp.error or "",
        "provider":    resp.provider,
        "model":       resp.model,
        "tokensIn":    resp.tokens_in,
        "tokensOut":   resp.tokens_out,
        "costUsd":     resp.cost_usd or 0.0,
        "durationMs":  duration_ms,
        "item": {
            "id":       item["id"],
            "name":     item["name"],
            "source":   item["source"],
            "category": item.get("category", ""),
        },
    }


def api_run_to_workflow(body: dict) -> dict:
    """POST /api/run/to-workflow  body: {itemId}
    For catalog items, scaffold a minimal one-node workflow.
    """
    if not isinstance(body, dict):
        return {"ok": False, "error": "bad body"}
    item_id = (body.get("itemId") or "").strip()
    items, _ = _get_catalog()
    item = next((it for it in items if it["id"] == item_id), None)
    if not item:
        return {"ok": False, "error": f"item not found: {item_id}"}

    # No template → emit a draft workflow (caller saves via /api/workflows/save).
    nid_start = "n-rcstart"
    nid_session = "n-rcrun"
    nid_out = "n-rcout"
    invocation = (item.get("invocation") or item.get("description") or "").strip()
    draft = {
        "name":        f"Run · {item.get('name', item_id)}",
        "description": f"Generated from Run Center · {item.get('source', '').upper()} · {item.get('description', '')[:140]}",
        "nodes": [
            {"id": nid_start,   "type": "start",   "x": 80,  "y": 200, "title": "Start", "data": {}},
            {"id": nid_session, "type": "session", "x": 320, "y": 200, "title": item.get("name", "Run"),
             "data": {
                 "subject":     item.get("name", "Run Center item"),
                 "description": invocation or item.get("description", ""),
                 "assignee":    "codex:gpt-5-codex",
                 "inputsMode":  "concat",
             }},
            {"id": nid_out,     "type": "output",  "x": 560, "y": 200, "title": "Output", "data": {"exportTo": ""}},
        ],
        "edges": [
            {"id": "e1", "from": nid_start,   "to": nid_session, "fromPort": "out", "toPort": "in"},
            {"id": "e2", "from": nid_session, "to": nid_out,     "fromPort": "out", "toPort": "in"},
        ],
        "viewport": {"panX": 0.0, "panY": 0.0, "zoom": 1.0},
        "repeat":   {"enabled": False, "maxIterations": 1, "intervalSeconds": 0,
                     "scheduleEnabled": False, "scheduleStart": "", "scheduleEnd": "",
                     "feedbackNote": "", "feedbackNodeId": ""},
        "notify":   {"slack": "", "discord": ""},
        "policy":   {"tokenBudgetTotal": 0, "onBudgetExceeded": "stop", "fallbackProvider": ""},
    }
    return {"ok": True, "kind": "draft", "draft": draft, "item": item["name"]}
