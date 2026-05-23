"""가이드 & 온보딩 — 공식 Codex 리소스 카탈로그 + 대시보드 체크리스트.

- /api/guide/toolkit     : OpenAI Codex 공식 문서/설정 리소스 카탈로그 (정적)
- /api/guide/onboarding  : 사용자 ~/.codex 상태를 자동 감지해 체크리스트 진행률 계산

모든 데이터는 stdlib 만으로 생성되며 외부 호출/파일 쓰기 없음 (읽기 전용).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import (
    AGENTS_DIR, CODEX_HOME, AGENTS_MD, COMMANDS_DIR,
    INSTALLED_PLUGINS_JSON, PLUGINS_DIR, SETTINGS_JSON, SKILLS_DIR,
)
from .utils import _safe_read


# ───────── 공식 Codex 리소스 카탈로그 (정적) ─────────
#
# 공식 문서 URL·권장 설정·관련 명령을 한 화면에 모아 대시보드에서
# 그대로 복사·적용하도록 돕는다. 서드파티 번들은 플러그인 탭에서만 다룬다.

_TOOLKIT_SOURCES: list[dict[str, Any]] = [
    {
        "id": "openai-codex-config",
        "title": "OpenAI Codex config.toml",
        "subtitle": "~/.codex/config.toml 로 모델, 승인, 샌드박스, MCP, 앱, 메모리, TUI를 제어",
        "author": "OpenAI",
        "repo": "https://developers.openai.com/codex/config-reference",
        "stars": "Official",
        "license": "Docs",
        "highlights": [
            "user-level ~/.codex/config.toml 과 project-local .codex/config.toml 레이어",
            "approval_policy, sandbox_mode, permissions, projects.<path>.trust_level",
            "mcp_servers, apps, tools.web_search, memories, agents, skills.config",
            "VS Code/Cursor TOML 진단용 #:schema https://developers.openai.com/codex/config-schema.json",
        ],
        "install": [
            {
                "label": "설정 진단",
                "code": "/debug-config",
            },
            {
                "label": "현재 세션 상태 확인",
                "code": "/status",
            },
            {
                "label": "schema 주석",
                "code": "#:schema https://developers.openai.com/codex/config-schema.json",
            },
        ],
        "categories": [
            {
                "name": "핵심 키",
                "items": [
                    "model", "review_model", "model_reasoning_effort",
                    "approval_policy", "sandbox_mode", "default_permissions",
                    "projects.<path>.trust_level", "web_search",
                ],
            },
            {
                "name": "도구/컨텍스트",
                "items": [
                    "mcp_servers.<id>.url", "apps._default.enabled",
                    "tools.web_search.allowed_domains", "tools.view_image",
                    "developer_instructions", "compact_prompt",
                ],
            },
            {
                "name": "운영",
                "items": [
                    "history.persistence", "tool_output_token_limit",
                    "tui.raw_output_mode", "tui.status_line",
                    "analytics.enabled", "feedback.enabled",
                ],
            },
        ],
    },
    {
        "id": "openai-codex-goal-mode",
        "title": "Goal mode",
        "subtitle": "/goal 로 긴 작업의 완료 기준과 진행 목표를 Codex가 계속 추적",
        "author": "OpenAI",
        "repo": "https://developers.openai.com/codex/prompting#goal-mode",
        "stars": "Official",
        "license": "Docs",
        "highlights": [
            "/goal 이 보이지 않으면 [features] goals = true 또는 codex features enable goals",
            "Goal text가 시작 프롬프트이자 완료 기준으로 동작",
            "어려운 목표는 /plan 으로 다듬은 뒤 /goal 로 고정",
            "pause/resume/clear 로 장시간 작업을 제어",
        ],
        "install": [
            {
                "label": "config.toml feature gate",
                "code": "[features]\ngoals = true",
            },
            {
                "label": "CLI helper",
                "code": "codex features enable goals",
            },
            {
                "label": "Goal 시작",
                "code": "/goal Migrate the codebase and keep all smoke tests passing.",
            },
        ],
        "categories": [
            {
                "name": "좋은 goal 조건",
                "items": [
                    "구체적 산출물", "검증 방법", "허용된 부작용",
                    "중단 조건", "테스트/스크린샷/문서 기준",
                ],
            },
            {
                "name": "같이 쓰기 좋은 명령",
                "items": [
                    "/plan", "/status", "/compact", "/review", "/debug-config",
                ],
            },
        ],
    },
    {
        "id": "openai-codex-slash-commands",
        "title": "Built-in slash commands",
        "subtitle": "Codex CLI 공식 내장 명령: /skills, /plugins, /agent, /mcp, /status 등",
        "author": "OpenAI",
        "repo": "https://developers.openai.com/codex/cli/slash-commands#built-in-slash-commands",
        "stars": "Official",
        "license": "Docs",
        "highlights": [
            "/skills 는 스킬 탐색/선택, /plugins 는 플러그인 탐색/관리",
            "/agent 는 spawned subagent thread 전환",
            "/mcp 는 연결된 Model Context Protocol 도구 상태 확인",
            "/debug-config 는 config layer와 requirements 진단",
        ],
        "install": [
            {
                "label": "명령 목록",
                "code": "/help",
            },
            {
                "label": "스킬 사용",
                "code": "/skills",
            },
            {
                "label": "플러그인 관리",
                "code": "/plugins",
            },
        ],
        "categories": [
            {
                "name": "세션 제어",
                "items": [
                    "/clear", "/compact", "/resume", "/new", "/fork", "/side",
                ],
            },
            {
                "name": "검증/설정",
                "items": [
                    "/status", "/diff", "/review", "/debug-config", "/permissions", "/model",
                ],
            },
        ],
    },
    {
        "id": "openai-codex-skills",
        "title": "Skills",
        "subtitle": "반복 작업을 SKILL.md 로 표준화하고 /skills 에서 선택",
        "author": "OpenAI",
        "repo": "https://developers.openai.com/codex/skills",
        "stars": "Official",
        "license": "Docs",
        "highlights": [
            "SKILL.md 는 작업별 절차, 제약, 검증 루틴을 담는 재사용 단위",
            "skills.config 로 특정 스킬 경로 enable/disable 가능",
            "MCP dependency install prompt는 features.skill_mcp_dependency_install 로 관리",
            "스킬은 명령 자동 실행이 아니라 Codex 행동 지침을 보강하는 표면",
        ],
        "install": [
            {
                "label": "스킬 탐색",
                "code": "/skills",
            },
            {
                "label": "config.toml 예시",
                "code": "[features]\nskill_mcp_dependency_install = true",
            },
        ],
        "categories": [
            {
                "name": "좋은 스킬 구성",
                "items": [
                    "언제 사용할지", "입력/출력 형식", "검증 명령", "금지 동작", "관련 파일/스크립트",
                ],
            },
            {
                "name": "연결 키",
                "items": [
                    "skills.config", "features.skill_mcp_dependency_install", "/skills", "plugins.<plugin>.*",
                ],
            },
        ],
    },
    {
        "id": "openai-docs-mcp",
        "title": "OpenAI Docs MCP",
        "subtitle": "Codex에서 developers.openai.com/platform.openai.com 공식 문서를 바로 검색",
        "author": "OpenAI",
        "repo": "https://developers.openai.com/learn/docs-mcp",
        "stars": "Official",
        "license": "Docs",
        "highlights": [
            "공식 Docs MCP streamable HTTP URL: https://developers.openai.com/mcp",
            "Codex CLI와 IDE extension 설정을 공유",
            "AGENTS.md에 공식 문서 우선 검색 지시를 함께 두면 안정적",
            "OpenAI API, Codex, Apps SDK, Agents SDK 질문에 적합",
        ],
        "install": [
            {
                "label": "Codex CLI",
                "code": "codex mcp add openaiDeveloperDocs --url https://developers.openai.com/mcp",
            },
            {
                "label": "config.toml",
                "code": "[mcp_servers.openaiDeveloperDocs]\nurl = \"https://developers.openai.com/mcp\"\nrequired = false\ndefault_tools_approval_mode = \"prompt\"",
            },
            {
                "label": "확인",
                "code": "/mcp",
            },
        ],
        "categories": [
            {
                "name": "권장 사용",
                "items": [
                    "OpenAI 관련 질문 전 공식 문서 확인", "config key 검증",
                    "API request/response schema 확인", "최신 모델/도구 변화 확인",
                ],
            },
            {
                "name": "관련 config",
                "items": [
                    "mcp_servers.<id>.url", "mcp_servers.<id>.required",
                    "mcp_servers.<id>.default_tools_approval_mode",
                    "mcp_oauth_credentials_store",
                ],
            },
        ],
    },
    {
        "id": "openai-gpt55-coding",
        "title": "GPT-5.5 for coding agents",
        "subtitle": "복잡한 코드 작업, 도구 사용, 장시간 agent workflow에 맞춘 최신 OpenAI 모델 가이드",
        "author": "OpenAI",
        "repo": "https://developers.openai.com/api/docs/guides/latest-model",
        "stars": "Official",
        "license": "Docs",
        "highlights": [
            "GPT-5.5는 coding agents, tool-heavy workflows, long-context retrieval에 적합",
            "reasoning effort 기본값은 medium, high/xhigh는 품질 이득이 검증될 때만 사용",
            "outcome-first prompt: 결과, 성공 기준, 허용 부작용, 증거 규칙을 명확히",
            "tool search, hosted tools, compaction, prompt caching을 함께 고려",
        ],
        "install": [
            {
                "label": "Codex 모델 설정",
                "code": "model = \"gpt-5.5\"\nmodel_reasoning_effort = \"medium\"\nmodel_verbosity = \"medium\"",
            },
            {
                "label": "깊은 리뷰 profile",
                "code": "[profiles.deep-review]\nmodel = \"gpt-5.5\"\nmodel_reasoning_effort = \"high\"\nweb_search = \"cached\"",
            },
        ],
        "categories": [
            {
                "name": "튜닝 축",
                "items": [
                    "model", "model_reasoning_effort", "model_verbosity",
                    "developer_instructions", "compact_prompt", "tools.web_search",
                ],
            },
            {
                "name": "검증 기준",
                "items": [
                    "테스트 통과", "작업 범위 준수", "도구 선택 정확도", "토큰/지연 비용", "최종 답변 명료도",
                ],
            },
        ],
    },
]


# ───────── 베스트 프랙티스 (정적) ─────────

_BEST_PRACTICES: list[dict[str, Any]] = [
    {
        "id": "workflow-rpers",
        "title": "Research → Plan → Execute → Review → Ship",
        "desc": "모든 주요 작업은 이 5단계로. 각 단계마다 슬래시 명령어를 붙이면 품질이 올라간다.",
        "steps": [
            {"label": "Research", "tip": "레포 탐색, /mcp, OpenAI Docs MCP로 맥락 먼저. 코드 쓰기 전 WHY 정리."},
            {"label": "Plan",     "tip": "/plan 또는 Plan Mode. 파일별 변경안 · 리스크 · 롤백 플랜까지."},
            {"label": "Execute",  "tip": "작은 변경 단위로 구현하고 필요한 경우 /goal 로 완료 기준을 고정."},
            {"label": "Review",   "tip": "/diff + /review. 테스트/타입체크/스모크 결과를 함께 남깁니다."},
            {"label": "Ship",     "tip": "/status 로 권한/모델/컨텍스트 확인 후 커밋 또는 handoff."},
        ],
    },
    {
        "id": "token-optimization",
        "title": "토큰 · 컨텍스트 최적화",
        "desc": "Codex CLI 에서 비용·지연·품질 모두 개선하는 핵심 스위치 5개.",
        "steps": [
            {"label": "모델 기준",  "tip": "기본은 gpt-5.5 + reasoning medium. 빠른 작업은 low, 깊은 리뷰만 high/xhigh로 올립니다."},
            {"label": "Verbosity",  "tip": "긴 설명이 필요 없으면 model_verbosity=low 또는 medium. 답변 길이와 reasoning effort는 분리합니다."},
            {"label": "Compact 기준",  "tip": "/compact 힌트에는 완료한 일, 남은 리스크, 다음 목표, 변경 파일, 검증 결과를 남깁니다."},
            {"label": "MCP 10개 이하", "tip": "활성 MCP 서버는 10개 이하 — 매 턴마다 도구 디스크립션 비용."},
            {"label": "Session 분리",  "tip": "새 태스크는 /new 또는 새 세션. 이어갈 때만 /resume 사용."},
        ],
    },
    {
        "id": "planning-habits",
        "title": "Plan Mode · 컨텍스트 습관",
        "desc": "Boris Cherny(Codex CLI 창시자)가 반복 강조하는 운용 팁.",
        "steps": [
            {"label": "Plan 먼저",        "tip": "모든 비자명한 작업은 Plan Mode 로. 코드 생성 전 사용자 승인을 받는다."},
            {"label": "컨텍스트 감시",    "tip": "/status 로 토큰/권한/모델을 확인하고, 길어지면 /compact 또는 /clear."},
            {"label": "Prototype > PRD",  "tip": "길게 쓴 스펙보다 20~30개의 작은 프로토타입이 빠른 수렴을 준다."},
            {"label": "작은 PR",           "tip": "PR 사이즈 median 118 lines. 커지면 쪼개라 — 리뷰 품질 & 롤백 용이."},
            {"label": "Squash Merge",     "tip": "히스토리 선형 유지. rebase 보다 squash 가 충돌 복구에 유리."},
        ],
    },
    {
        "id": "security",
        "title": "보안 · 안전 기본값",
        "desc": "로컬/개인 사용에서도 꼭 켜두면 좋은 안전 스위치.",
        "steps": [
            {"label": "권한 프로파일",    "tip": "default_permissions 와 permissions.<name> 으로 filesystem/network 경계를 고정."},
            {"label": "Sandbox",    "tip": "낯선 repo는 read-only, 프로젝트 작업은 workspace-write + on-request."},
            {"label": "MCP 승인",     "tip": "mcp_servers.<id>.default_tools_approval_mode=prompt 로 tool 실행을 확인."},
            {"label": "프로젝트 trust",     "tip": "projects.<path>.trust_level 로 project-local .codex/ 레이어 로드를 명시."},
        ],
    },
]


# ───────── 슬래시 명령어 치트시트 ─────────

_CHEATSHEET_COMMANDS: list[dict[str, Any]] = [
    {"cmd": "/help",     "desc": "Codex CLI 사용법과 명령어 전체 목록"},
    {"cmd": "/clear",    "desc": "현재 세션 컨텍스트 초기화 — 새 주제 시작 시"},
    {"cmd": "/compact",  "desc": "대화를 요약해 컨텍스트 압축 (힌트 프롬프트 동반 권장)"},
    {"cmd": "/copy",     "desc": "마지막 완료 응답 복사"},
    {"cmd": "/diff",     "desc": "현재 working tree diff 확인"},
    {"cmd": "/resume",   "desc": "저장된 이전 세션 재개"},
    {"cmd": "/plan",     "desc": "Plan Mode 진입 — 코드 변경 전 승인 단계"},
    {"cmd": "/goal",     "desc": "긴 작업의 persistent objective 설정/조회/일시정지/재개"},
    {"cmd": "/fast",     "desc": "모델 카탈로그가 제공할 때 Fast service tier 토글"},
    {"cmd": "/init",     "desc": "현재 레포용 AGENTS.md 를 자동 초기화"},
    {"cmd": "/review",   "desc": "현재 변경분 코드리뷰"},
    {"cmd": "/debug-config", "desc": "config layer와 requirements 진단"},
    {"cmd": "/status",   "desc": "모델, 권한, writable roots, 토큰/컨텍스트 상태 확인"},
    {"cmd": "/logout",   "desc": "현재 계정 로그아웃"},
    {"cmd": "/model",    "desc": "활성 모델과 reasoning effort 변경"},
    {"cmd": "/memories", "desc": "메모리 주입/생성 설정"},
    {"cmd": "/agent",    "desc": "spawned subagent thread 전환"},
    {"cmd": "/skills",   "desc": "스킬 탐색과 선택"},
    {"cmd": "/hooks",    "desc": "lifecycle hook 보기/관리"},
    {"cmd": "/mcp",      "desc": "MCP 서버 목록 + 연결 상태"},
    {"cmd": "/plugins",  "desc": "설치/탐색 가능한 플러그인 관리"},
    {"cmd": "/apps",     "desc": "ChatGPT Apps/connectors 탐색"},
    {"cmd": "/statusline", "desc": "상태라인 커스터마이즈"},
    {"cmd": "/theme",    "desc": "터미널 syntax theme 설정"},
]

_CHEATSHEET_KEYS: list[dict[str, str]] = [
    {"key": "Shift+Tab",  "desc": "Plan Mode ↔ 실행 모드 토글"},
    {"key": "Ctrl+C",     "desc": "현재 응답/도구 실행 중단"},
    {"key": "Ctrl+D",     "desc": "Codex CLI 종료"},
    {"key": "Ctrl+R",     "desc": "출력 스타일 · 토큰 디테일 토글"},
    {"key": "Ctrl+L",     "desc": "터미널 화면 클리어 (세션 유지)"},
    {"key": "Esc Esc",    "desc": "마지막 메시지 편집 (더블 Esc)"},
    {"key": "!<command>", "desc": "프롬프트 앞에 ! — 사용자 측에서 셸 실행 후 출력 공유"},
    {"key": "↑ / ↓",      "desc": "이전/다음 프롬프트 히스토리 이동"},
    {"key": "Tab",        "desc": "파일/경로 자동완성"},
]


# ───────── 온보딩 상태 진단 ─────────

def _count_dir(p: Path, pattern: str = "*") -> int:
    if not p.exists():
        return 0
    try:
        return sum(1 for _ in p.glob(pattern))
    except Exception:
        return 0


def _installed_plugins_count() -> int:
    if not INSTALLED_PLUGINS_JSON.exists():
        return 0
    try:
        data = json.loads(_safe_read(INSTALLED_PLUGINS_JSON) or "{}")
    except Exception:
        return 0
    # installed_plugins.json 스키마: {"<marketplace>": {"<plugin>": {...}}}
    total = 0
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, dict):
                total += len(v)
    return total


def _settings_has_permissions() -> bool:
    if not SETTINGS_JSON.exists():
        return False
    try:
        data = json.loads(_safe_read(SETTINGS_JSON) or "{}")
    except Exception:
        return False
    perms = data.get("permissions") if isinstance(data, dict) else None
    if not isinstance(perms, dict):
        return False
    return bool(perms.get("allow") or perms.get("deny"))


def _settings_has_hooks() -> bool:
    if not SETTINGS_JSON.exists():
        return False
    try:
        data = json.loads(_safe_read(SETTINGS_JSON) or "{}")
    except Exception:
        return False
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return False
    # 하나라도 이벤트에 훅이 걸려 있으면 True
    for v in hooks.values():
        if v:
            return True
    return False


def _codex_md_substantial() -> bool:
    """AGENTS.md 가 100자 이상 내용을 담고 있으면 "작성된" 것으로 간주."""
    if not AGENTS_MD.exists():
        return False
    try:
        text = _safe_read(AGENTS_MD) or ""
    except Exception:
        return False
    return len(text.strip()) >= 100


def _mcp_count() -> int:
    """user/project MCP 연결 수를 합산."""
    try:
        from .mcp import list_connectors
        conns = list_connectors()
        return len(conns.get("local", [])) + len(conns.get("project", []))
    except Exception:
        return 0


def api_guide_toolkit() -> dict[str, Any]:
    """외부 툴/가이드 카탈로그 + 베스트 프랙티스 + 치트시트."""
    return {
        "toolkits": _TOOLKIT_SOURCES,
        "bestPractices": _BEST_PRACTICES,
        "cheatsheet": {
            "commands": _CHEATSHEET_COMMANDS,
            "keys": _CHEATSHEET_KEYS,
        },
    }


def api_guide_onboarding() -> dict[str, Any]:
    """현재 ~/.codex 상태를 감지해 체크리스트를 채워서 반환.

    각 단계:
      id · title · desc · done · hint · navigate (관련 탭 id)
    """
    skills_n   = _count_dir(SKILLS_DIR)
    agents_n   = _count_dir(AGENTS_DIR, "*.md")
    commands_n = _count_dir(COMMANDS_DIR, "*.md")
    plugins_n  = _installed_plugins_count()
    mcp_n      = _mcp_count()

    steps = [
        {
            "id": "cli-installed",
            "title": "Codex CLI CLI 설치",
            "desc": "`~/.codex` 디렉토리가 존재해야 모든 기능이 동작합니다.",
            "done": CODEX_HOME.exists(),
            "hint": "공식 설치 문서 기준으로 Codex CLI 를 설치하세요.",
            "navigate": "system",
            "doc": "https://developers.openai.com/codex/overview",
        },
        {
            "id": "codex-md",
            "title": "전역 AGENTS.md 작성",
            "desc": "모든 세션에 로드되는 개인/팀 규약. 100자 이상 작성을 권장합니다.",
            "done": _codex_md_substantial(),
            "hint": "AGENTS.md 탭에서 편집 · `/init` 으로 자동 생성 가능.",
            "navigate": "codexmd",
            "doc": "https://developers.openai.com/codex/agents-md",
        },
        {
            "id": "permissions",
            "title": "권한(permissions) 설정",
            "desc": "allow / deny 규칙으로 위험한 명령을 차단합니다.",
            "done": _settings_has_permissions(),
            "hint": "권한 탭에서 추천 프로파일 클릭 — rm -rf /, curl | sh 등 기본 차단.",
            "navigate": "permissions",
            "doc": "https://developers.openai.com/codex/rules",
        },
        {
            "id": "hooks",
            "title": "훅(hooks) 하나 이상 설정",
            "desc": "SessionStart/Stop · PreToolUse 훅으로 자동화 · 안전장치를 추가합니다.",
            "done": _settings_has_hooks(),
            "hint": "훅 탭 · PreToolUse 에 시크릿 감지 스크립트 추천.",
            "navigate": "hooks",
            "doc": "https://developers.openai.com/codex/hooks",
        },
        {
            "id": "skills",
            "title": "스킬 1개 이상 보유",
            "desc": "스킬은 Codex가 작업 문맥에서 재사용하는 지식/워크플로 모듈입니다.",
            "done": skills_n >= 1,
            "detail": f"{skills_n} 개 감지",
            "hint": "반복 작업은 SKILL.md 기반 스킬로 표준화하세요.",
            "navigate": "skills",
            "doc": "https://developers.openai.com/codex/skills",
        },
        {
            "id": "agents",
            "title": "서브에이전트 1개 이상",
            "desc": "특정 작업에 특화된 전담 에이전트를 만들어 두면 품질이 급상승.",
            "done": agents_n >= 1,
            "detail": f"{agents_n} 개 감지",
            "hint": "에이전트 탭 · planner / code-reviewer 먼저 만들어보세요.",
            "navigate": "agents",
            "doc": "https://developers.openai.com/codex/subagents",
        },
        {
            "id": "commands",
            "title": "커스텀 슬래시 명령어",
            "desc": "자주 쓰는 프롬프트를 /command 로 축약 — 반복 작업 자동화.",
            "done": commands_n >= 1,
            "detail": f"{commands_n} 개 감지",
            "hint": "슬래시 명령어 탭에서 /tdd, /plan, /code-review 등 추가.",
            "navigate": "commands",
            "doc": "https://developers.openai.com/codex/cli/slash-commands",
        },
        {
            "id": "mcp",
            "title": "MCP 커넥터 1개 이상",
            "desc": "GitHub / Context7 / Playwright 등 외부 시스템 연결.",
            "done": mcp_n >= 1,
            "detail": f"{mcp_n} 개 감지",
            "hint": "MCP 탭에서 원클릭 설치 · 처음엔 context7 + github 조합 추천.",
            "navigate": "mcp",
            "doc": "https://developers.openai.com/codex/mcp",
        },
        {
            "id": "plugins",
            "title": "플러그인 또는 마켓플레이스 추가",
            "desc": "Codex 플러그인/마켓플레이스로 skills, agents, commands 묶음을 관리.",
            "done": plugins_n >= 1,
            "detail": f"{plugins_n} 개 설치",
            "hint": "플러그인 탭에서 설치 상태를 확인하고 /plugins 로 Codex CLI에서도 검증하세요.",
            "navigate": "plugins",
            "doc": "https://developers.openai.com/codex/plugins",
        },
        {
            "id": "output-style",
            "title": "출력 스타일 선택",
            "desc": "답변 톤/포맷을 프로젝트 성격에 맞게 고정.",
            "done": _count_dir(CODEX_HOME / "output-styles", "*") >= 1,
            "hint": "출력 스타일 탭에서 커스텀 스타일을 만들거나 기본값 확인.",
            "navigate": "outputStyles",
            "doc": "https://developers.openai.com/codex/config-reference",
        },
    ]

    done_count = sum(1 for s in steps if s.get("done"))
    total = len(steps)
    pct = round(done_count / total * 100) if total else 0

    return {
        "steps": steps,
        "progress": {"done": done_count, "total": total, "percent": pct},
        "tips": [
            "모든 항목 체크 후엔 'AI 종합 평가' 탭에서 0~100 점수를 받아보세요.",
            "가이드 허브 → 유용한 툴 탭에서 한 번에 설치 가능한 팩을 찾을 수 있습니다.",
        ],
    }
