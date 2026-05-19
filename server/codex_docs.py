"""Codex Docs Hub — docs.anthropic.com 주요 페이지 색인 + 로컬 검색.

정적 카탈로그. URL 은 2026-04 시점 기준. Anthropic 이 경로를 바꾸면
이 파일의 `CATALOG` 만 갱신하면 된다.

검색은 클라이언트/서버 단순 substring 필터로 충분 — 전역 검색엔진 없음.
"""
from __future__ import annotations

_BASE_DOCS = "https://docs.anthropic.com/en/docs"
_BASE_API = "https://docs.anthropic.com/en/api"

CATALOG: dict[str, list[dict]] = {
    "codex-code": [
        {"url": f"{_BASE_DOCS}/codex-code/overview", "title": "Codex CLI 개요", "summary": "CLI 설치 · 기본 사용 · 프로젝트 초기화.", "relatedTab": "onboarding"},
        {"url": f"{_BASE_DOCS}/codex-code/sub-agents", "title": "Sub-agents", "summary": "프로젝트별 서브에이전트 정의 · 역할 프리셋.", "relatedTab": "projectAgents"},
        {"url": f"{_BASE_DOCS}/codex-code/skills", "title": "Skills", "summary": "재사용 가능한 스킬 생성 · 호출 규칙.", "relatedTab": "skills"},
        {"url": f"{_BASE_DOCS}/codex-code/hooks-guide", "title": "Hooks", "summary": "이벤트 훅 (PreToolUse / PostToolUse / Stop …).", "relatedTab": "hooks"},
        {"url": f"{_BASE_DOCS}/codex-code/mcp", "title": "MCP", "summary": "Model Context Protocol 커넥터 설정.", "relatedTab": "mcp"},
        {"url": f"{_BASE_DOCS}/codex-code/plugins", "title": "Plugins", "summary": "플러그인 마켓플레이스 · 설치 · 활성화.", "relatedTab": "plugins"},
        {"url": f"{_BASE_DOCS}/codex-code/output-styles", "title": "Output Styles", "summary": "답변 톤/포맷 커스터마이즈.", "relatedTab": "outputStyles"},
        {"url": f"{_BASE_DOCS}/codex-code/statusline", "title": "Status Line", "summary": "하단 상태라인 · 컨텍스트 표시.", "relatedTab": "statusline"},
        {"url": f"{_BASE_DOCS}/codex-code/slash-commands", "title": "Slash Commands", "summary": "`/` 명령 구조 · 커스텀 명령 등록.", "relatedTab": "commands"},
        {"url": f"{_BASE_DOCS}/codex-code/memory", "title": "Memory", "summary": "AGENTS.md 로 프로젝트 지식 고정.", "relatedTab": "codexmd"},
        {"url": f"{_BASE_DOCS}/codex-code/interactive-mode", "title": "Interactive Mode", "summary": "세션 단축키 · 컨텍스트 관리.", "relatedTab": "sessions"},
        {"url": f"{_BASE_DOCS}/codex-code/iam", "title": "IAM · Permissions", "summary": "allow / deny 규칙 · 권한 정책.", "relatedTab": "permissions"},
        {"url": f"{_BASE_DOCS}/codex-code/settings", "title": "Settings", "summary": "`~/.codex/settings.json` 전체 레퍼런스.", "relatedTab": "settings"},
        {"url": f"{_BASE_DOCS}/codex-code/troubleshooting", "title": "Troubleshooting", "summary": "흔한 오류 · 복구 절차.", "relatedTab": None},
    ],
    "codex-api": [
        {"url": f"{_BASE_API}/messages", "title": "Messages API", "summary": "핵심 엔드포인트 · content block 구조.", "relatedTab": "aiProviders"},
        {"url": f"{_BASE_DOCS}/build-with-codex/prompt-caching", "title": "Prompt Caching", "summary": "cache_control 로 반복 프롬프트 비용 절감.", "relatedTab": "promptCache"},
        {"url": f"{_BASE_DOCS}/build-with-codex/extended-thinking", "title": "Extended Thinking", "summary": "thinking block · budget_tokens.", "relatedTab": "thinkingLab"},
        {"url": f"{_BASE_DOCS}/build-with-codex/tool-use", "title": "Tool Use", "summary": "tool_use / tool_result 라운드 트립.", "relatedTab": "toolUseLab"},
        {"url": f"{_BASE_DOCS}/build-with-codex/message-batches", "title": "Message Batches", "summary": "대용량 프롬프트 병렬 제출.", "relatedTab": "batchJobs"},
        {"url": f"{_BASE_DOCS}/build-with-codex/files", "title": "Files API", "summary": "파일 업로드 + document reference.", "relatedTab": "apiFiles"},
        {"url": f"{_BASE_DOCS}/build-with-codex/vision", "title": "Vision", "summary": "이미지 / PDF 입력 처리.", "relatedTab": "visionLab"},
        {"url": f"{_BASE_DOCS}/build-with-codex/citations", "title": "Citations", "summary": "문서 인용 응답 모드.", "relatedTab": "citationsLab"},
        {"url": f"{_BASE_DOCS}/agents-and-tools/tool-use/web-search-tool", "title": "Web Search Tool", "summary": "Anthropic 서버 측 hosted 검색 도구.", "relatedTab": "serverTools"},
        {"url": f"{_BASE_DOCS}/agents-and-tools/tool-use/code-execution-tool", "title": "Code Execution Tool", "summary": "Anthropic 호스팅 Python sandbox.", "relatedTab": "serverTools"},
        {"url": f"{_BASE_DOCS}/build-with-codex/embeddings", "title": "Embeddings", "summary": "Voyage AI 기반 임베딩 API.", "relatedTab": "aiProviders"},
    ],
    "agent-sdk": [
        {"url": f"{_BASE_DOCS}/codex-code/sdk/sdk-overview", "title": "Agent SDK Overview", "summary": "Python / TypeScript SDK 진입점.", "relatedTab": None},
        {"url": f"{_BASE_DOCS}/codex-code/sdk/sdk-python", "title": "Python SDK", "summary": "codex-agent-sdk (Python) · uv 권장.", "relatedTab": None},
        {"url": f"{_BASE_DOCS}/codex-code/sdk/sdk-typescript", "title": "TypeScript SDK", "summary": "codex-agent-sdk (TS) · bun/npm.", "relatedTab": None},
    ],
    "models": [
        {"url": f"{_BASE_DOCS}/about-codex/models", "title": "Models", "summary": "Opus / Sonnet / Haiku 세대별 비교.", "relatedTab": "modelBench"},
        {"url": f"{_BASE_DOCS}/about-codex/model-deprecations", "title": "Model Deprecations", "summary": "구 모델 은퇴 일정.", "relatedTab": None},
        {"url": "https://www.anthropic.com/pricing", "title": "Pricing", "summary": "공식 요금표 (per-million-tokens).", "relatedTab": "usage"},
    ],
    "policy-and-account": [
        {"url": "https://codex.ai/settings/organization", "title": "Team / Organization", "summary": "워크스페이스 · 멤버 · 결제 관리.", "relatedTab": "team"},
        {"url": f"{_BASE_DOCS}/resources/glossary", "title": "Glossary", "summary": "공식 용어 정의.", "relatedTab": None},
    ],
}

CATEGORY_LABELS = {
    "codex-code": "Codex CLI",
    "codex-api": "Codex API",
    "agent-sdk": "Agent SDK",
    "models": "Models & Pricing",
    "policy-and-account": "Account & Policy",
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
