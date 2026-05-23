"""인증 / 계정 정보 — Codex CLI 연동 상태, 플랜, 로그인/로그아웃.

~/.codex.json 의 oauthAccount 또는 ~/.codex/auth.json 을 읽어 UI 에 노출하고,
`codex auth login` / `logout` 을 감싸 로컬 훅을 제공한다.
"""
from __future__ import annotations

import base64
import json
import platform
import shutil
import subprocess

from .config import CODEX_AUTH_JSON, CODEX_JSON
from .translations import _load_dash_config, _save_dash_config
from .utils import _safe_read


CODEX_PLANS = [
    {"id": "free",        "label": "무료 (Free)",          "note": "rate limit 있음"},
    {"id": "pro",         "label": "Codex Pro",          "note": "$20/월"},
    {"id": "max_5x",      "label": "Codex Max (5×)",      "note": "$100/월"},
    {"id": "max_20x",     "label": "Codex Max (20×)",     "note": "$200/월"},
    {"id": "team",        "label": "Codex Team",          "note": "팀 워크스페이스"},
    {"id": "enterprise",  "label": "Codex Enterprise",    "note": "엔터프라이즈"},
    {"id": "api_only",    "label": "API 키 전용",          "note": "종량제"},
]


def _read_legacy_codex_json() -> dict:
    if not CODEX_JSON.exists():
        return {}
    try:
        data = json.loads(_safe_read(CODEX_JSON, 500000))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _decode_jwt_payload(token: str) -> dict:
    if not token or token.count(".") < 2:
        return {}
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_codex_auth_json() -> dict:
    """Read modern Codex CLI auth state without exposing token values."""
    if not CODEX_AUTH_JSON.exists():
        return {}
    try:
        data = json.loads(_safe_read(CODEX_AUTH_JSON, 500000))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    tokens = data.get("tokens") if isinstance(data.get("tokens"), dict) else {}
    id_payload = _decode_jwt_payload(tokens.get("id_token") or "")
    return {
        "authMode": data.get("auth_mode") or "",
        "accountId": tokens.get("account_id") or id_payload.get("sub") or "",
        "email": id_payload.get("email") or "",
        "displayName": id_payload.get("name") or id_payload.get("nickname") or "",
        "emailVerified": bool(id_payload.get("email_verified", False)),
        "lastRefresh": data.get("last_refresh") or "",
        "hasAccessToken": bool(tokens.get("access_token")),
        "hasRefreshToken": bool(tokens.get("refresh_token")),
    }


def _auth_file_mtime() -> float:
    mtimes = []
    for p in (CODEX_JSON, CODEX_AUTH_JSON):
        try:
            if p.exists():
                mtimes.append(p.stat().st_mtime)
        except Exception:
            pass
    return max(mtimes) if mtimes else 0.0


def api_team_info() -> dict:
    """조직/워크스페이스/팀 정보 (codex.ai team 기능용)."""
    data = _read_legacy_codex_json()
    oauth = data.get("oauthAccount") or {}
    modern = _read_codex_auth_json()
    if not oauth and not modern:
        return {"connected": False}
    cfg = _load_dash_config()
    claimed = cfg.get("claimedPlan") or ""
    return {
        "connected": bool(oauth or modern),
        "displayName": oauth.get("displayName", "") or modern.get("displayName", ""),
        "email": oauth.get("emailAddress", "") or modern.get("email", ""),
        "organizationUuid": oauth.get("organizationUuid", ""),
        "organizationName": oauth.get("organizationName", ""),
        "organizationRole": oauth.get("organizationRole", ""),
        "workspaceRole": oauth.get("workspaceRole"),
        "accountUuid": oauth.get("accountUuid", "") or modern.get("accountId", ""),
        "billingType": oauth.get("billingType", "") or modern.get("authMode", ""),
        "hasExtraUsageEnabled": bool(oauth.get("hasExtraUsageEnabled", False)),
        "claimedPlan": claimed,
        "note": "상세 멤버 리스트/사용량은 codex.ai/settings/organization 에서 관리됩니다. 로컬에는 조직 식별자만 저장됨.",
    }


_AUTH_STATUS_CACHE: dict = {"data": None, "ts": 0.0, "codex_json_mtime": 0.0}
# QQ136 — server-side cache for /api/auth/status. The endpoint runs
# `codex --version` AND `codex auth status` subprocess calls (~450ms
# combined). Auth state is stable except when the user re-runs
# `codex auth login`, which mutates ~/.codex.json's mtime — so the
# memo invalidates automatically when that file changes. 30s TTL
# otherwise.
_AUTH_STATUS_TTL_S = 30.0


def api_auth_status() -> dict:
    """Codex auth files에서 연결 상태 반환 + codex CLI 설치 여부.

    QQ136 — Memoised for up to 30s; auto-invalidates when ~/.codex.json
    mtime changes (covers `codex auth login` / refresh).
    """
    import time as _time
    cur_mtime = _auth_file_mtime()
    cached = _AUTH_STATUS_CACHE.get("data")
    if (
        cached is not None
        and (_time.time() - _AUTH_STATUS_CACHE.get("ts", 0)) < _AUTH_STATUS_TTL_S
        and _AUTH_STATUS_CACHE.get("codex_json_mtime") == cur_mtime
    ):
        return cached

    cli_path = shutil.which("codex") or ""
    cli_version = ""
    if cli_path:
        try:
            cli_version = subprocess.check_output(
                [cli_path, "--version"], text=True, timeout=5,
            ).strip()
        except Exception:
            cli_version = ""

    data = _read_legacy_codex_json()
    modern_auth = _read_codex_auth_json()
    if not data and not modern_auth:
        return {
            "connected": False,
            "reason": "~/.codex/auth.json 또는 ~/.codex.json 이 없습니다 — Codex CLI에 로그인하세요.",
            "cliInstalled": bool(cli_path),
            "cliPath": cli_path,
            "cliVersion": cli_version,
        }

    oauth = data.get("oauthAccount") or {}
    if not oauth and not modern_auth:
        return {
            "connected": False, "reason": "OAuth 계정 없음 — `codex auth login` 실행 필요.",
            "cliInstalled": bool(cli_path), "cliPath": cli_path, "cliVersion": cli_version,
        }

    billing = oauth.get("billingType") or modern_auth.get("authMode", "")
    # 로컬에는 세부 플랜(Pro/Max/Team)이 저장되지 않음.
    # 사용자가 대시보드에서 직접 선택한 값이 있으면 우선.
    cfg = _load_dash_config()
    claimed_plan_id = cfg.get("claimedPlan") or ""
    claimed_plan = next((p for p in CODEX_PLANS if p["id"] == claimed_plan_id), None)

    if claimed_plan:
        plan_label = claimed_plan["label"]
    elif billing == "stripe_subscription":
        plan_label = "Codex 구독 활성 (세부 플랜 미지정)"
    elif billing == "api_key":
        plan_label = "API 키"
    else:
        plan_label = "무료 / 미확인"

    # Older Codex CLIs exposed `codex auth status`; newer ones do not. Treat
    # this subprocess as best-effort only and rely on auth.json as canonical.
    cli_auth: dict = {}
    if cli_path:
        try:
            raw = subprocess.check_output(
                [cli_path, "auth", "status"], text=True, timeout=5, stderr=subprocess.DEVNULL,
            ).strip()
            cli_auth = json.loads(raw) if raw.startswith("{") else {}
        except Exception:
            cli_auth = {}

    # CLI auth status 에 subscriptionType 이 있으면 plan label 덮어쓰기
    sub_type = cli_auth.get("subscriptionType", "")
    if sub_type and not claimed_plan:
        sub_map = {"free": "Free", "pro": "Pro", "max": "Max", "team": "Team", "enterprise": "Enterprise"}
        plan_label = f"Codex {sub_map.get(sub_type, sub_type)}"

    projects_count = len(data.get("projects", {}) or {})
    result = {
        "connected": True,
        "email": cli_auth.get("email") or oauth.get("emailAddress", "") or modern_auth.get("email", ""),
        "displayName": oauth.get("displayName", "") or modern_auth.get("displayName", ""),
        "accountUuid": oauth.get("accountUuid", "") or modern_auth.get("accountId", ""),
        "organizationUuid": cli_auth.get("orgId") or oauth.get("organizationUuid", ""),
        "organizationName": cli_auth.get("orgName") or "",
        "organizationRole": oauth.get("organizationRole", ""),
        "workspaceRole": oauth.get("workspaceRole", ""),
        "billingType": billing,
        "subscriptionType": sub_type,
        "planLabel": plan_label,
        "claimedPlanId": claimed_plan_id,
        "planNote": claimed_plan["note"] if claimed_plan else "플랜은 로컬에 저장되지 않습니다. 직접 선택하세요.",
        "availablePlans": CODEX_PLANS,
        "hasExtraUsageEnabled": bool(oauth.get("hasExtraUsageEnabled", False)),
        "subscriptionCreatedAt": oauth.get("subscriptionCreatedAt", ""),
        "accountCreatedAt": oauth.get("accountCreatedAt", ""),
        "userID": data.get("userID", ""),
        "firstTokenDate": data.get("codexCodeFirstTokenDate", ""),
        "projectsKnown": projects_count,
        "cliInstalled": bool(cli_path),
        "cliPath": cli_path,
        "cliVersion": cli_version,
        "authFile": str(CODEX_AUTH_JSON if modern_auth else CODEX_JSON),
        "authMode": modern_auth.get("authMode", ""),
        "authLastRefresh": modern_auth.get("lastRefresh", ""),
    }
    _AUTH_STATUS_CACHE["data"] = result
    _AUTH_STATUS_CACHE["ts"] = _time.time()
    _AUTH_STATUS_CACHE["codex_json_mtime"] = cur_mtime
    return result


def api_set_claimed_plan(body: dict) -> dict:
    pid = (body or {}).get("planId") if isinstance(body, dict) else ""
    if pid and not any(p["id"] == pid for p in CODEX_PLANS):
        return {"ok": False, "error": f"unknown plan id: {pid}"}
    cfg = _load_dash_config()
    if pid:
        cfg["claimedPlan"] = pid
    else:
        cfg.pop("claimedPlan", None)
    _save_dash_config(cfg)
    return {"ok": True, "planId": pid or ""}


def api_auth_login(body: dict) -> dict:
    """터미널에서 `codex auth login` 을 실행. 인터랙티브 명령이므로 터미널 앱을 열어준다."""
    cli = shutil.which("codex")
    if not cli:
        return {"ok": False, "error": "Codex CLI 가 설치되어 있지 않습니다. 먼저 설치하세요."}
    # macOS: AppleScript 로 기본 터미널에서 `codex auth login` 실행
    if platform.system() == "Darwin":
        script = f'''
        tell application "Terminal"
            activate
            do script "{cli} auth login"
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], timeout=5, capture_output=True)
            return {"ok": True, "method": "terminal", "message": "터미널에서 로그인 창이 열렸습니다. 브라우저 인증 완료 후 돌아오세요."}
        except Exception as e:
            return {"ok": False, "error": f"터미널 실행 실패: {e}"}
    # Linux / fallback
    try:
        subprocess.Popen([cli, "auth", "login"], start_new_session=True)
        return {"ok": True, "method": "background", "message": "codex auth login 이 실행되었습니다. 완료 후 새로고침하세요."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_auth_logout(body: dict) -> dict:
    """로그아웃 — `codex auth logout` 실행."""
    cli = shutil.which("codex")
    if not cli:
        return {"ok": False, "error": "Codex CLI 미설치"}
    try:
        r = subprocess.run([cli, "auth", "logout"], capture_output=True, text=True, timeout=10)
        return {"ok": True, "message": "로그아웃 되었습니다.", "output": r.stdout.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}
