"""Codex CLI config.toml harness helpers.

OpenAI Codex CLI now uses ``~/.codex/config.toml`` for most runtime
configuration. This module keeps LazyCodex' setup UI aligned with that file
without depending on non-stdlib TOML writers.
"""
from __future__ import annotations

import json
import re
import tomllib
from typing import Any

from .config import CODEX_HOME, ROOT
from .utils import _safe_read, _safe_write


CONFIG_TOML = CODEX_HOME / "config.toml"
SCHEMA_URL = "https://developers.openai.com/codex/config-schema.json"
DOCS_URL = "https://developers.openai.com/codex/config-reference"
_BARE_TOML_KEY = re.compile(r"^[A-Za-z0-9_-]+$")

OFFICIAL_SURFACES: list[dict[str, Any]] = [
    {"area": "Build", "name": "Subagents", "tab": "agents", "status": "official", "doc": "https://developers.openai.com/codex/subagents", "basis": "Configured agent roles and parallel delegation."},
    {"area": "Build", "name": "Skills", "tab": "skills", "status": "official", "doc": "https://developers.openai.com/codex/skills", "basis": "Reusable SKILL.md instructions for repeated work."},
    {"area": "Build", "name": "Slash commands", "tab": "commands", "status": "official", "doc": "https://developers.openai.com/codex/cli/slash-commands", "basis": "CLI/IDE slash command surface."},
    {"area": "Build", "name": "Codex CLI exec / non-interactive", "tab": "commands", "status": "official", "doc": "https://developers.openai.com/codex/cli", "basis": "Scripted Codex automation through official CLI surfaces."},
    {"area": "Config", "name": "config.toml layers", "tab": "codexHarness", "status": "official", "doc": "https://developers.openai.com/codex/config-basic", "basis": "User/project/system config precedence and profiles."},
    {"area": "Config", "name": "Rules / permissions", "tab": "permissions", "status": "official", "doc": "https://developers.openai.com/codex/rules", "basis": "Rules, permission profiles, and sandbox approval behavior."},
    {"area": "Config", "name": "Hooks", "tab": "hooks", "status": "official", "doc": "https://developers.openai.com/codex/hooks", "basis": "PreToolUse/PostToolUse/Stop and related hook events."},
    {"area": "Config", "name": "AGENTS.md", "tab": "codexmd", "status": "official", "doc": "https://developers.openai.com/codex/agents-md", "basis": "Durable project instructions."},
    {"area": "Config", "name": "MCP", "tab": "mcp", "status": "official", "doc": "https://developers.openai.com/codex/mcp", "basis": "External tools/context through Model Context Protocol."},
    {"area": "Config", "name": "Plugins / marketplaces", "tab": "plugins", "status": "official", "doc": "https://developers.openai.com/codex/plugins", "basis": "Installable bundles of skills, agents, and commands."},
    {"area": "Legacy", "name": "settings.json / output styles / statusline", "tab": "settings", "status": "legacy", "doc": "https://developers.openai.com/codex/config-basic", "basis": "Kept only for LazyCodex or older plugin compatibility; current official runtime config centers on config.toml."},
    {"area": "Local", "name": "LazyCodex DAG workflows / Run Center", "tab": "workflows", "status": "local", "doc": "https://developers.openai.com/codex/use-cases", "basis": "Local dashboard automation, not an OpenAI Codex built-in feature."},
]


HARNESS_CATALOG: list[dict[str, Any]] = [
    {
        "category": "features",
        "title": "기능 플래그 · Slash command",
        "keys": [
            ["features.goals", "/goal 활성화"],
            ["features.memories", "/memories 활성화"],
            ["features.multi_agent", "/agent 및 subagent collaboration tools"],
            ["features.apps", "/apps connector surface"],
            ["features.hooks", "/hooks 및 lifecycle hooks"],
            ["features.plugin_hooks", "plugin 제공 hooks opt-in"],
            ["features.fast_mode", "/fast 및 service tier 선택"],
            ["features.personality", "/personality"],
            ["features.undo", "turn 단위 undo snapshot"],
            ["features.codex_git_commit", "Codex generated git commit attribution"],
            ["features.apply_patch_freeform", "freeform apply_patch input"],
            ["features.apply_patch_streaming_events", "apply_patch streaming events"],
            ["features.auth_elicitation", "auth 관련 elicitation"],
            ["features.child_agents_md", "하위 AGENTS.md 로드"],
            ["features.enable_request_compression", "streaming request zstd compression"],
            ["features.network_proxy", "sandboxed network proxy"],
            ["features.prevent_idle_sleep", "turn 실행 중 sleep 방지"],
            ["features.request_permissions_tool", "request_permissions tool"],
            ["features.tool_search", "tool search"],
            ["features.tool_suggest", "tool suggestion"],
            ["features.shell_tool", "기본 shell tool"],
            ["features.shell_snapshot", "반복 shell snapshot"],
            ["features.unified_exec", "PTY 기반 unified exec"],
            ["features.skill_mcp_dependency_install", "skill MCP dependency install prompt"],
        ],
    },
    {
        "category": "runtime",
        "title": "모델 · 추론",
        "keys": [
            ["model", "기본 모델 ID"],
            ["review_model", "/review 전용 모델 override"],
            ["model_provider", "model_providers 중 사용할 provider"],
            ["oss_provider", "--oss 기본 local provider"],
            ["model_reasoning_effort", "none/minimal/low/medium/high/xhigh"],
            ["plan_mode_reasoning_effort", "Plan mode 전용 reasoning effort"],
            ["model_reasoning_summary", "none/auto/concise/detailed"],
            ["model_verbosity", "low/medium/high"],
            ["model_supports_reasoning_summaries", "reasoning metadata 강제 전송 여부"],
            ["model_context_window", "컨텍스트 창 토큰 수 override"],
            ["model_auto_compact_token_limit", "자동 compact 트리거 토큰 수"],
            ["service_tier", "priority/flex 등 서비스 티어 요청"],
        ],
    },
    {
        "category": "safety",
        "title": "승인 · 샌드박스",
        "keys": [
            ["approval_policy", "untrusted/on-request/never 또는 granular"],
            ["sandbox_mode", "read-only/workspace-write/danger-full-access"],
            ["allow_login_shell", "shell tool login shell 허용 여부"],
            ["sandbox_workspace_write.network_access", "workspace-write 네트워크 허용"],
            ["sandbox_workspace_write.writable_roots", "추가 쓰기 허용 경로"],
            ["sandbox_workspace_write.exclude_tmpdir_env_var", "$TMPDIR writable 제외"],
            ["sandbox_workspace_write.exclude_slash_tmp", "/tmp writable 제외"],
            ["approvals_reviewer", "user/auto_review"],
            ["auto_review.policy", "자동 승인 리뷰어 정책"],
            ["default_permissions", "기본 permissions profile"],
            ["projects.<path>.trust_level", "project-local .codex layer trust"],
            ["permissions", "이름 있는 권한 profile"],
            ["permissions.<name>.filesystem", "glob/path 별 read/write/none 정책"],
            ["permissions.<name>.network", "도메인/포트 단위 네트워크 정책"],
        ],
    },
    {
        "category": "context",
        "title": "목표 · 지시 · 컨텍스트",
        "keys": [
            ["features.goals", "/goal slash command 활성화"],
            ["instructions", "시스템 지시"],
            ["developer_instructions", "developer role 지시"],
            ["model_instructions_file", "모델 지시 파일 경로"],
            ["compact_prompt", "히스토리 compact 프롬프트"],
            ["project_doc_fallback_filenames", "AGENTS.md 대체 파일명"],
            ["project_doc_max_bytes", "프로젝트 문서 최대 주입 bytes"],
            ["project_root_markers", "프로젝트 루트 탐지 marker"],
            ["include_apps_instructions", "apps instructions 주입 여부"],
            ["include_environment_context", "environment_context 주입 여부"],
            ["include_permissions_instructions", "permissions instructions 주입 여부"],
            ["include_collaboration_mode_instructions", "collaboration mode 주입 여부"],
            ["profiles.<name>", "작업 모드별 config 묶음"],
            ["experimental_compact_prompt_file", "compact prompt 파일 분리"],
            ["model_catalog_json", "startup 시 모델 catalog override"],
        ],
    },
    {
        "category": "tools",
        "title": "도구 · MCP · 앱",
        "keys": [
            ["mcp_servers", "MCP 서버 정의"],
            ["mcp_servers.openaiDeveloperDocs.url", "OpenAI Docs MCP streamable HTTP server"],
            ["mcp_oauth_credentials_store", "MCP OAuth 저장 방식"],
            ["mcp_oauth_callback_port", "MCP OAuth callback 고정 포트"],
            ["mcp_oauth_callback_url", "MCP OAuth redirect URI override"],
            ["web_search", "disabled/cached/live"],
            ["tools.web_search", "검색 context/domain/location 세부 설정"],
            ["tools.view_image", "local image attachment tool"],
            ["apps._default.enabled", "앱/커넥터 기본 활성화"],
            ["apps._default.default_tools_approval_mode", "앱 도구 기본 승인 모드"],
            ["apps.<name>.default_tools_enabled", "앱별 도구 기본 활성화"],
            ["apps.<name>.tools.<tool>.approval_mode", "앱 도구별 승인 모드"],
            ["tool_suggest", "설치 제안 도구 카탈로그"],
            ["tool_suggest.discoverables", "추가 discoverable connector/plugin"],
            ["tool_suggest.disabled_tools", "특정 tool suggestion 비활성화"],
            ["shell_environment_policy", "shell 환경변수 상속/제외/강제 설정"],
            ["web_search", "공식 top-level web search mode"],
            ["features.apps", "Apps/connectors feature gate"],
        ],
    },
    {
        "category": "agents",
        "title": "서브 에이전트 · 스킬",
        "keys": [
            ["agents.max_threads", "동시 agent thread 제한"],
            ["agents.max_depth", "spawn nesting depth 제한"],
            ["agents.job_max_runtime_seconds", "agent job 최대 실행 시간"],
            ["agents.interrupt_message", "agent interrupt message 기록 여부"],
            ["agents.<role>.description", "역할 설명"],
            ["agents.<role>.config_file", "역할별 config layer"],
            ["skills.include_instructions", "skills instructions 주입"],
            ["skills.bundled.enabled", "번들 skill 활성화"],
            ["skills.config", "개별 skill enable/disable"],
            ["plugins.<plugin>.mcp_servers.<server>.enabled", "plugin 제공 MCP 서버 override"],
            ["plugins.<plugin>.mcp_servers.<server>.default_tools_approval_mode", "plugin MCP tool 승인 모드"],
        ],
    },
    {
        "category": "terminal",
        "title": "터미널 · 알림 · 기록",
        "keys": [
            ["tui.alternate_screen", "auto/always/never"],
            ["tui.animations", "TUI 애니메이션"],
            ["tui.notifications", "TUI terminal notification"],
            ["tui.notification_method", "auto/osc9/bel"],
            ["tui.notification_condition", "unfocused/always"],
            ["tui.raw_output_mode", "copy-friendly raw output"],
            ["tui.show_tooltips", "welcome tooltip 표시"],
            ["tui.status_line", "footer status line 항목"],
            ["tui.terminal_title", "terminal title 항목"],
            ["tui.keymap", "키맵 override"],
            ["tui.theme", "syntax highlighting theme"],
            ["tui.vim_mode_default", "composer Vim normal mode 기본값"],
            ["disable_paste_burst", "burst paste 감지 비활성화"],
            ["notify", "완료 알림 외부 명령"],
            ["history.persistence", "save-all/none"],
            ["history.max_bytes", "history.jsonl 최대 크기"],
            ["tool_output_token_limit", "tool output 저장 토큰 예산"],
            ["file_opener", "파일 citation opener"],
            ["background_terminal_max_timeout", "background terminal poll timeout"],
            ["log_dir", "Codex log directory"],
            ["sqlite_home", "Codex SQLite state directory"],
            ["otel.environment", "OpenTelemetry environment label"],
            ["otel.exporter", "otel exporter 선택"],
            ["otel.trace_exporter", "otel trace exporter 선택"],
            ["otel.metrics_exporter", "otel metrics exporter 선택"],
            ["check_for_update_on_startup", "시작 시 업데이트 체크"],
            ["feedback.enabled", "/feedback 활성화 여부"],
            ["hide_agent_reasoning", "reasoning event 숨김"],
            ["show_raw_agent_reasoning", "raw reasoning 표시"],
            ["notice", "warning/migration notice acknowledgement"],
        ],
    },
    {
        "category": "providers",
        "title": "Provider · 인증 · 엔터프라이즈",
        "keys": [
            ["model_providers", "OpenAI 호환 provider 추가"],
            ["openai_base_url", "built-in openai base URL override"],
            ["chatgpt_base_url", "ChatGPT base URL override"],
            ["cli_auth_credentials_store", "file/keyring/auto/ephemeral"],
            ["forced_login_method", "로그인 방식 제한"],
            ["forced_chatgpt_workspace_id", "workspace 제한"],
            ["analytics.enabled", "analytics 활성화 여부"],
            ["marketplaces", "plugin marketplace entries"],
            ["profile", "기본 profile 선택"],
            ["projects.<path>.trust_level", "프로젝트 trust level"],
            ["zsh_path", "patched zsh absolute path"],
        ],
    },
]


HARNESS_PRESETS: list[dict[str, Any]] = [
    {
        "id": "gpt55-coding-agent",
        "title": "GPT-5.5 코딩 에이전트",
        "desc": "OpenAI 최신 모델 가이드 기준: gpt-5.5, reasoning medium, verbosity medium을 기본값으로 둡니다.",
        "patch": {
            "model": "gpt-5.5",
            "review_model": "gpt-5.5",
            "model_reasoning_effort": "medium",
            "plan_mode_reasoning_effort": "high",
            "model_verbosity": "medium",
            "web_search": "cached",
        },
    },
    {
        "id": "trusted-current-project",
        "title": "현재 프로젝트 trust",
        "desc": "현재 repo의 project-local .codex/config.toml, hooks, rules 로드를 명시적으로 허용합니다.",
        "patch": {
            "projects": {
                str(ROOT): {"trust_level": "trusted"},
            },
        },
    },
    {
        "id": "openai-docs-mcp",
        "title": "OpenAI Docs MCP",
        "desc": "OpenAI 공식 문서 MCP 서버를 streamable HTTP로 등록하고 tool approval을 prompt로 둡니다.",
        "patch": {
            "mcp_servers": {
                "openaiDeveloperDocs": {
                    "url": "https://developers.openai.com/mcp",
                    "required": False,
                    "default_tools_approval_mode": "prompt",
                }
            },
            "mcp_oauth_credentials_store": "auto",
        },
    },
    {
        "id": "config-schema-diagnostics",
        "title": "Config schema 진단",
        "desc": "config.toml 편집/진단에 필요한 로그, 히스토리, schema reference 친화 설정을 켭니다.",
        "patch": {
            "log_dir": str(CODEX_HOME / "log"),
            "history": {"persistence": "save-all", "max_bytes": 52428800},
            "tool_output_token_limit": 12000,
            "tui": {"raw_output_mode": True, "show_tooltips": False},
        },
    },
    {
        "id": "safe-local",
        "title": "안전한 로컬 기본값",
        "desc": "읽기 중심, 필요 시 승인. 처음 세팅이나 낯선 repo에 적합.",
        "patch": {
            "approval_policy": {
                "granular": {
                    "mcp_elicitations": True,
                    "rules": True,
                    "sandbox_approval": True,
                    "request_permissions": False,
                    "skill_approval": False,
                }
            },
            "sandbox_mode": "read-only",
            "approvals_reviewer": "user",
            "model_reasoning_effort": "medium",
            "model_reasoning_summary": "auto",
            "web_search": "cached",
            "history": {"persistence": "save-all", "max_bytes": 10485760},
        },
    },
    {
        "id": "workspace-builder",
        "title": "워크스페이스 빌더",
        "desc": "프로젝트 내부 쓰기는 허용하고 네트워크/외부 경로는 명시적으로 관리.",
        "patch": {
            "approval_policy": "on-request",
            "sandbox_mode": "workspace-write",
            "model_reasoning_effort": "high",
            "model_verbosity": "medium",
            "sandbox_workspace_write": {
                "network_access": False,
                "writable_roots": [],
                "exclude_tmpdir_env_var": False,
                "exclude_slash_tmp": False,
            },
        },
    },
    {
        "id": "controlled-autonomy",
        "title": "통제된 자율 실행",
        "desc": "workspace-write 기반으로 자동 리뷰어와 granular approval 을 결합합니다.",
        "patch": {
            "sandbox_mode": "workspace-write",
            "approvals_reviewer": "auto_review",
            "approval_policy": {
                "granular": {
                    "mcp_elicitations": True,
                    "rules": True,
                    "sandbox_approval": True,
                    "request_permissions": True,
                    "skill_approval": False,
                }
            },
            "auto_review": {
                "policy": (
                    "Approve low-risk reads and project-local writes. Deny secrets, "
                    "credential exfiltration, destructive git operations, and network access "
                    "that is not necessary for the task."
                )
            },
            "sandbox_workspace_write": {"network_access": False, "writable_roots": []},
        },
    },
    {
        "id": "goal-harness",
        "title": "목표 중심 하네스",
        "desc": "goal/작업 품질을 안정화하는 지시·계획·compact 설정.",
        "patch": {
            "developer_instructions": (
                "Before acting, restate the user's goal, identify constraints, "
                "and keep the work scoped to the current repository."
            ),
            "plan_mode_reasoning_effort": "high",
            "compact_prompt": (
                "Preserve the user's goal, active plan, decisions made, files changed, "
                "tests run, and unresolved risks."
            ),
            "project_doc_fallback_filenames": ["AGENTS.md", "README.md"],
            "project_doc_max_bytes": 32768,
        },
    },
    {
        "id": "goal-command",
        "title": "/goal 명령 활성화",
        "desc": "Codex CLI의 실험적 /goal slash command를 켭니다. 새 세션에서 /goal <목표>로 사용할 수 있습니다.",
        "patch": {
            "features": {"goals": True},
        },
    },
    {
        "id": "feature-memories",
        "title": "/memories 활성화",
        "desc": "Codex Memories 기능을 켜고 기본 생성/주입 설정을 준비합니다.",
        "patch": {
            "features": {"memories": True},
            "memories": {"use_memories": True, "generate_memories": True},
        },
    },
    {
        "id": "feature-apps",
        "title": "/apps 활성화",
        "desc": "ChatGPT Apps/connectors 표면을 켜되 destructive/open-world 도구는 기본 차단합니다.",
        "patch": {
            "features": {"apps": True},
            "apps": {"_default": {"enabled": True, "destructive_enabled": False, "open_world_enabled": False}},
        },
    },
    {
        "id": "feature-hooks",
        "title": "/hooks 활성화",
        "desc": "Lifecycle hooks 표면을 명시적으로 켭니다.",
        "patch": {"features": {"hooks": True}},
    },
    {
        "id": "feature-plugin-hooks",
        "title": "Plugin hooks 활성화",
        "desc": "설치된 플러그인이 제공하는 lifecycle hook 사용을 허용합니다.",
        "patch": {"features": {"plugin_hooks": True}},
    },
    {
        "id": "feature-multi-agent",
        "title": "Multi-agent 활성화",
        "desc": "spawn_agent/send_input/wait_agent 등 subagent collaboration tools를 켭니다.",
        "patch": {"features": {"multi_agent": True}, "agents": {"max_threads": 6, "max_depth": 2}},
    },
    {
        "id": "feature-fast-mode",
        "title": "/fast 활성화",
        "desc": "모델 카탈로그가 제공하는 Fast tier 선택 표면을 켭니다.",
        "patch": {"features": {"fast_mode": True}},
    },
    {
        "id": "feature-personality",
        "title": "/personality 활성화",
        "desc": "세션 중 응답 스타일을 전환하는 personality controls를 켭니다.",
        "patch": {"features": {"personality": True}},
    },
    {
        "id": "feature-undo",
        "title": "Undo 활성화",
        "desc": "turn 단위 되돌리기 snapshot 기능을 켭니다.",
        "patch": {"features": {"undo": True}},
    },
    {
        "id": "feature-git-commit",
        "title": "Codex git commit 활성화",
        "desc": "Codex-generated git commit 기능과 기본 attribution을 켭니다.",
        "patch": {"features": {"codex_git_commit": True}},
    },
    {
        "id": "feature-shell-runtime",
        "title": "Shell runtime 안정화",
        "desc": "shell tool, shell snapshot, unified exec, request compression, idle sleep 방지를 명시적으로 켭니다.",
        "patch": {
            "features": {
                "shell_tool": True,
                "shell_snapshot": True,
                "unified_exec": True,
                "enable_request_compression": True,
                "skill_mcp_dependency_install": True,
                "prevent_idle_sleep": True,
            }
        },
    },
    {
        "id": "patch-workbench",
        "title": "Patch 워크벤치",
        "desc": "apply_patch freeform 입력과 streaming event를 켜서 코드 수정 하네스를 명확히 엽니다.",
        "patch": {
            "features": {
                "apply_patch_freeform": True,
                "apply_patch_streaming_events": True,
            },
        },
    },
    {
        "id": "auth-permission-flow",
        "title": "Auth/권한 요청 플로우",
        "desc": "인증 elicitation과 request_permissions tool을 켜고 granular approval에서 요청 경로를 허용합니다.",
        "patch": {
            "features": {
                "auth_elicitation": True,
                "request_permissions_tool": True,
            },
            "approval_policy": {
                "granular": {
                    "mcp_elicitations": True,
                    "rules": True,
                    "sandbox_approval": True,
                    "request_permissions": True,
                    "skill_approval": False,
                }
            },
        },
    },
    {
        "id": "tool-discovery-pack",
        "title": "Tool discovery 팩",
        "desc": "tool_search/tool_suggest 표면을 켜고 설치 제안 카탈로그를 config에서 관리할 준비를 합니다.",
        "patch": {
            "features": {
                "tool_search": True,
                "tool_suggest": True,
            },
            "tool_suggest": {
                "disabled_tools": [],
            },
        },
    },
    {
        "id": "child-agents-md-pack",
        "title": "하위 AGENTS.md 로드",
        "desc": "repo 하위 디렉터리별 AGENTS.md를 읽도록 켜고 협업 모드 instructions 주입을 유지합니다.",
        "patch": {
            "features": {"child_agents_md": True},
            "include_collaboration_mode_instructions": True,
        },
    },
    {
        "id": "context-injection-pack",
        "title": "Context injection 팩",
        "desc": "환경, 권한, 협업 모드, 앱 지시와 프로젝트 문서 fallback을 한 번에 정리합니다.",
        "patch": {
            "include_environment_context": True,
            "include_permissions_instructions": True,
            "include_collaboration_mode_instructions": True,
            "include_apps_instructions": True,
            "project_doc_fallback_filenames": ["AGENTS.md", "README.md", "CONTRIBUTING.md"],
            "project_doc_max_bytes": 65536,
            "project_root_markers": [".git", ".hg", ".sl", "pyproject.toml", "package.json"],
        },
    },
    {
        "id": "feature-network-proxy-limited",
        "title": "제한형 네트워크 프록시",
        "desc": "sandboxed networking을 켜되 OpenAI/GitHub/PyPI 계열 도메인만 allow 합니다.",
        "patch": {
            "features": {
                "network_proxy": {
                    "enabled": True,
                    "allow_local_binding": False,
                    "allow_upstream_proxy": True,
                    "domains": {
                        "api.openai.com": "allow",
                        "auth.openai.com": "allow",
                        "developers.openai.com": "allow",
                        "platform.openai.com": "allow",
                        "github.com": "allow",
                        "**.githubusercontent.com": "allow",
                        "pypi.org": "allow",
                        "files.pythonhosted.org": "allow",
                    },
                }
            }
        },
    },
    {
        "id": "feature-web-search-cached",
        "title": "Cached web search",
        "desc": "최신 공식 권장인 top-level web_search 값을 cached로 설정합니다.",
        "patch": {"web_search": "cached"},
    },
    {
        "id": "feature-web-search-research",
        "title": "공식 문서 리서치 검색",
        "desc": "live web search와 tools.web_search 객체 설정을 공식 OpenAI 도메인 중심으로 제한합니다.",
        "patch": {
            "web_search": "live",
            "tools": {
                "web_search": {
                    "context_size": "high",
                    "allowed_domains": ["developers.openai.com", "platform.openai.com"],
                },
                "view_image": True,
            },
        },
    },
    {
        "id": "feature-image-tool",
        "title": "이미지 보기 도구",
        "desc": "로컬 이미지 attachment/view_image 도구를 명시적으로 켭니다.",
        "patch": {"tools": {"view_image": True}},
    },
    {
        "id": "feature-pack-safe",
        "title": "안전한 기능 팩",
        "desc": "목표, 메모리, 에이전트, 훅, Fast/personality, shell runtime을 안전한 기본값으로 켭니다.",
        "patch": {
            "features": {
                "goals": True,
                "memories": True,
                "multi_agent": True,
                "hooks": True,
                "fast_mode": True,
                "personality": True,
                "shell_tool": True,
                "shell_snapshot": True,
                "unified_exec": True,
                "enable_request_compression": True,
                "skill_mcp_dependency_install": True,
                "prevent_idle_sleep": True,
                "apply_patch_freeform": True,
                "apply_patch_streaming_events": True,
                "child_agents_md": True,
            },
            "web_search": "cached",
            "memories": {"use_memories": True, "generate_memories": True},
            "agents": {"max_threads": 6, "max_depth": 2},
            "include_environment_context": True,
            "include_permissions_instructions": True,
            "include_collaboration_mode_instructions": True,
        },
    },
    {
        "id": "feature-pack-experimental",
        "title": "실험 기능 팩",
        "desc": "Apps, plugin hooks, undo, Codex git commit까지 포함해 실험 표면을 확장합니다.",
        "patch": {
            "features": {
                "apps": True,
                "plugin_hooks": True,
                "undo": True,
                "codex_git_commit": True,
            },
            "apps": {"_default": {"enabled": True, "destructive_enabled": False, "open_world_enabled": False}},
        },
    },
    {
        "id": "memory-privacy-safe",
        "title": "메모리 privacy-safe",
        "desc": "외부 컨텍스트(MCP/web/tool search)를 사용한 thread는 memory 생성 대상에서 제외합니다.",
        "patch": {
            "features": {"memories": True},
            "memories": {
                "use_memories": True,
                "generate_memories": True,
                "disable_on_external_context": True,
                "max_rollout_age_days": 30,
                "max_rollouts_per_startup": 16,
                "min_rate_limit_remaining_percent": 25,
            },
        },
    },
    {
        "id": "shell-env-hardened",
        "title": "Shell 환경변수 하드닝",
        "desc": "login shell을 끄고 subprocess 환경변수 상속을 core로 제한하며 secret 계열 glob을 제외합니다.",
        "patch": {
            "allow_login_shell": False,
            "shell_environment_policy": {
                "inherit": "core",
                "ignore_default_excludes": False,
                "exclude": ["*TOKEN*", "*SECRET*", "*KEY*", "AWS_*", "AZURE_*", "GITHUB_TOKEN"],
            },
        },
    },
    {
        "id": "tui-operator",
        "title": "TUI 운영자 모드",
        "desc": "터미널 스크롤백과 알림, raw output, tooltip 설정을 작업자 친화적으로 맞춥니다.",
        "patch": {
            "tui": {
                "alternate_screen": "never",
                "animations": False,
                "notifications": ["agent-turn-complete", "approval-requested"],
                "notification_method": "auto",
                "notification_condition": "unfocused",
                "raw_output_mode": True,
                "show_tooltips": False,
            }
        },
    },
    {
        "id": "tool-output-budget",
        "title": "Tool output 예산",
        "desc": "긴 로그가 history/context를 밀어내지 않도록 tool output 저장량과 background poll window를 제한합니다.",
        "patch": {
            "tool_output_token_limit": 12000,
            "background_terminal_max_timeout": 300000,
            "history": {"persistence": "save-all", "max_bytes": 52428800},
        },
    },
    {
        "id": "review-harness",
        "title": "/review 하네스",
        "desc": "/review 전용 모델과 reasoning summary를 명시해 리뷰 품질을 안정화합니다.",
        "patch": {
            "review_model": "gpt-5.5",
            "model_reasoning_summary": "auto",
            "model_verbosity": "medium",
        },
    },
    {
        "id": "apps-prompt-tools",
        "title": "Apps prompt 승인",
        "desc": "Apps/connectors를 켜되 도구별 기본 동작은 prompt 승인으로 묶습니다.",
        "patch": {
            "features": {"apps": True},
            "apps": {
                "_default": {
                    "enabled": True,
                    "destructive_enabled": False,
                    "open_world_enabled": False,
                    "default_tools_enabled": True,
                    "default_tools_approval_mode": "prompt",
                }
            },
        },
    },
    {
        "id": "mcp-strict-tools",
        "title": "MCP 엄격 승인 기본값",
        "desc": "MCP OAuth는 auto/file-safe로 두고, MCP tool approval은 서버별 prompt 설정을 쓰도록 유도합니다.",
        "patch": {
            "mcp_oauth_credentials_store": "auto",
            "mcp_oauth_callback_port": 1455,
            "approval_policy": {
                "granular": {
                    "mcp_elicitations": True,
                    "rules": True,
                    "sandbox_approval": True,
                    "request_permissions": False,
                    "skill_approval": False,
                }
            },
        },
    },
    {
        "id": "local-oss-ollama",
        "title": "--oss Ollama 기본값",
        "desc": "codex --oss 실행 시 기본 local provider를 Ollama로 지정합니다.",
        "patch": {"oss_provider": "ollama"},
    },
    {
        "id": "profiles-pack",
        "title": "작업별 프로파일 팩",
        "desc": "깊은 리뷰, 빠른 수정, 오프라인 안전 모드를 --profile 로 전환합니다.",
        "patch": {
            "profiles": {
                "deep-review": {
                    "model_reasoning_effort": "xhigh",
                    "model_reasoning_summary": "detailed",
                    "approval_policy": "on-request",
                    "sandbox_mode": "read-only",
                },
                "quick-fix": {
                    "model_reasoning_effort": "medium",
                    "model_verbosity": "low",
                    "approval_policy": "on-request",
                    "sandbox_mode": "workspace-write",
                },
                "offline-safe": {
                    "web_search": "disabled",
                    "approval_policy": "untrusted",
                    "sandbox_mode": "read-only",
                    "history": {"persistence": "none"},
                },
            }
        },
    },
    {
        "id": "profile-default-deep",
        "title": "기본 Deep review profile",
        "desc": "deep-review profile을 만들고 기본 profile로 지정해 긴 리뷰/검증 작업에 바로 진입합니다.",
        "patch": {
            "profile": "deep-review",
            "profiles": {
                "deep-review": {
                    "model_reasoning_effort": "xhigh",
                    "model_reasoning_summary": "detailed",
                    "model_verbosity": "medium",
                    "approval_policy": "on-request",
                    "sandbox_mode": "read-only",
                    "web_search": "cached",
                }
            },
        },
    },
    {
        "id": "agent-fleet",
        "title": "서브 에이전트 하네스",
        "desc": "병렬 agent thread, 역할 config, skill 주입을 켜는 작업 분담형 프리셋.",
        "patch": {
            "agents": {
                "max_threads": 6,
                "max_depth": 2,
                "job_max_runtime_seconds": 1800,
                "reviewer": {
                    "description": "Review code changes for bugs, regressions, and missing tests.",
                    "nickname_candidates": ["reviewer", "qa"],
                },
                "researcher": {
                    "description": "Find primary-source technical context and summarize tradeoffs.",
                    "nickname_candidates": ["researcher", "docs"],
                },
            },
            "skills": {"include_instructions": True, "bundled": {"enabled": True}},
            "features": {"multi_agent": True},
        },
    },
    {
        "id": "permission-profile",
        "title": "권한 프로파일 골격",
        "desc": "반복 실행용 filesystem/network permission profile 을 config 에 둡니다.",
        "patch": {
            "default_permissions": "workspace-lite",
            "permissions": {
                "workspace-lite": {
                    "filesystem": {
                        ".": "write",
                        ".git": "read",
                        ".env": "none",
                        "**/*.pem": "none",
                        "**/*secret*": "none",
                    },
                    "network": {"enabled": False},
                }
            },
        },
    },
    {
        "id": "connected-tools",
        "title": "연결 도구 하네스",
        "desc": "MCP OAuth, web search, app connector 도구를 명시적으로 관리.",
        "patch": {
            "web_search": "cached",
            "mcp_oauth_credentials_store": "auto",
            "mcp_oauth_callback_port": 1455,
            "tools": {"view_image": True},
            "apps": {
                "_default": {
                    "enabled": True,
                    "destructive_enabled": False,
                    "open_world_enabled": False,
                    "default_tools_enabled": True,
                    "default_tools_approval_mode": "prompt",
                }
            },
        },
    },
    {
        "id": "telemetry-audit",
        "title": "운영 감사 하네스",
        "desc": "history, 알림, OTel 라벨을 켜서 반복 작업의 흔적을 남깁니다.",
        "patch": {
            "history": {"persistence": "save-all", "max_bytes": 52428800},
            "notify": ["terminal-notifier", "-title", "Codex", "-message", "Task complete"],
            "otel": {"environment": "local", "exporter": "none", "log_user_prompt": False},
        },
    },
    {
        "id": "privacy-quiet-pack",
        "title": "프라이버시 quiet 팩",
        "desc": "analytics/feedback/OTel 전송과 raw reasoning 표시를 꺼서 로컬 작업 기록만 남깁니다.",
        "patch": {
            "analytics": {"enabled": False},
            "feedback": {"enabled": False},
            "hide_agent_reasoning": True,
            "show_raw_agent_reasoning": False,
            "otel": {
                "exporter": "none",
                "trace_exporter": "none",
                "metrics_exporter": "none",
                "log_user_prompt": False,
            },
        },
    },
    {
        "id": "citation-opener-vscode",
        "title": "파일 citation opener: VS Code",
        "desc": "Codex가 표시하는 파일 citation을 VS Code에서 열도록 file_opener를 설정합니다.",
        "patch": {"file_opener": "vscode"},
    },
    {
        "id": "auth-storage-auto",
        "title": "인증 저장소 auto",
        "desc": "CLI/MCP OAuth credential 저장 방식을 플랫폼에 맞게 자동 선택합니다.",
        "patch": {
            "cli_auth_credentials_store": "auto",
            "mcp_oauth_credentials_store": "auto",
        },
    },
    {
        "id": "azure-provider-template",
        "title": "Azure OpenAI provider 템플릿",
        "desc": "Azure OpenAI Responses API provider 골격을 추가합니다. URL의 YOUR_PROJECT_NAME은 실제 리소스명으로 바꿔야 합니다.",
        "patch": {
            "model_provider": "azure",
            "model_providers": {
                "azure": {
                    "name": "Azure",
                    "base_url": "https://YOUR_PROJECT_NAME.openai.azure.com/openai",
                    "env_key": "AZURE_OPENAI_API_KEY",
                    "query_params": {"api-version": "2025-04-01-preview"},
                    "wire_api": "responses",
                    "request_max_retries": 4,
                    "stream_max_retries": 10,
                    "stream_idle_timeout_ms": 300000,
                }
            },
        },
    },
    {
        "id": "quiet-terminal",
        "title": "조용한 터미널",
        "desc": "스크롤백을 보존하고 기록/알림/업데이트 소음을 줄입니다.",
        "patch": {
            "tui": {"alternate_screen": "never", "animations": False},
            "notify": ["terminal-notifier", "-title", "Codex", "-message", "Task complete"],
            "check_for_update_on_startup": False,
            "analytics": {"enabled": False},
        },
    },
]

HARNESS_FEATURE_FLAGS: list[dict[str, Any]] = [
    {
        "key": "features.goals",
        "label": "/goal",
        "maturity": "experimental",
        "default": False,
        "presetId": "goal-command",
        "command": "/goal Finish the migration and keep tests green",
        "doc": "https://developers.openai.com/codex/cli/slash-commands#set-an-experimental-goal-with-goal",
        "desc": "장기 작업 목표를 active thread에 붙입니다.",
    },
    {
        "key": "features.memories",
        "label": "/memories",
        "maturity": "stable",
        "default": False,
        "presetId": "feature-memories",
        "command": "/memories",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "메모리 주입/생성을 세션에서 관리합니다.",
    },
    {
        "key": "features.multi_agent",
        "label": "Subagents",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-multi-agent",
        "command": "/agent",
        "doc": "https://developers.openai.com/codex/subagents",
        "desc": "spawn_agent 등 병렬 에이전트 협업 도구를 켭니다.",
    },
    {
        "key": "features.apps",
        "label": "/apps",
        "maturity": "experimental",
        "default": False,
        "presetId": "feature-apps",
        "command": "/apps",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "Apps/connectors를 프롬프트에 붙이는 표면입니다.",
    },
    {
        "key": "features.hooks",
        "label": "/hooks",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-hooks",
        "command": "/hooks",
        "doc": "https://developers.openai.com/codex/hooks",
        "desc": "lifecycle hooks를 로드하고 세션에서 점검합니다.",
    },
    {
        "key": "features.plugin_hooks",
        "label": "Plugin hooks",
        "maturity": "under-development",
        "default": False,
        "presetId": "feature-plugin-hooks",
        "command": "/hooks",
        "doc": "https://developers.openai.com/codex/hooks",
        "desc": "플러그인이 제공하는 hook까지 opt-in합니다.",
    },
    {
        "key": "features.fast_mode",
        "label": "/fast",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-fast-mode",
        "command": "/fast",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "Fast service tier 전환 표면을 켭니다.",
    },
    {
        "key": "features.personality",
        "label": "/personality",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-personality",
        "command": "/personality",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "응답 스타일을 세션 중 전환합니다.",
    },
    {
        "key": "features.undo",
        "label": "Undo",
        "maturity": "stable",
        "default": False,
        "presetId": "feature-undo",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "turn 단위 git snapshot 기반 undo를 켭니다.",
    },
    {
        "key": "features.codex_git_commit",
        "label": "Codex git commit",
        "maturity": "experimental",
        "default": False,
        "presetId": "feature-git-commit",
        "command": "/diff",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "Codex generated commit과 attribution trailer를 켭니다.",
    },
    {
        "key": "features.apply_patch_freeform",
        "label": "Apply patch freeform",
        "maturity": "stable",
        "default": True,
        "presetId": "patch-workbench",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "apply_patch tool의 freeform 입력 표면을 명시적으로 켭니다.",
    },
    {
        "key": "features.apply_patch_streaming_events",
        "label": "Patch streaming",
        "maturity": "stable",
        "default": True,
        "presetId": "patch-workbench",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "patch 적용 이벤트를 streaming 상태로 추적합니다.",
    },
    {
        "key": "features.auth_elicitation",
        "label": "Auth elicitation",
        "maturity": "experimental",
        "default": False,
        "presetId": "auth-permission-flow",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "인증이 필요한 도구가 사용자 입력을 요청할 수 있게 합니다.",
    },
    {
        "key": "features.request_permissions_tool",
        "label": "Request permissions",
        "maturity": "experimental",
        "default": False,
        "presetId": "auth-permission-flow",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "세션 중 권한 상승 요청 tool 표면을 켭니다.",
    },
    {
        "key": "features.child_agents_md",
        "label": "Child AGENTS.md",
        "maturity": "experimental",
        "default": False,
        "presetId": "child-agents-md-pack",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/agents-md",
        "desc": "하위 디렉터리별 AGENTS.md를 로드하는 표면입니다.",
    },
    {
        "key": "features.tool_search",
        "label": "Tool search",
        "maturity": "experimental",
        "default": False,
        "presetId": "tool-discovery-pack",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "사용 가능한 도구를 검색하는 표면을 엽니다.",
    },
    {
        "key": "features.tool_suggest",
        "label": "Tool suggest",
        "maturity": "experimental",
        "default": False,
        "presetId": "tool-discovery-pack",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "작업에 맞는 connector/plugin/tool 설치 제안을 켭니다.",
    },
    {
        "key": "features.shell_tool",
        "label": "Shell tool",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-shell-runtime",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "기본 shell command 실행 도구입니다.",
    },
    {
        "key": "features.enable_request_compression",
        "label": "Request compression",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-shell-runtime",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "지원되는 streaming request body를 zstd로 압축합니다.",
    },
    {
        "key": "features.prevent_idle_sleep",
        "label": "Prevent idle sleep",
        "maturity": "experimental",
        "default": False,
        "presetId": "feature-shell-runtime",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "turn이 실행 중일 때 머신 sleep을 방지합니다.",
    },
    {
        "key": "features.network_proxy.enabled",
        "label": "Network proxy",
        "maturity": "experimental",
        "default": False,
        "presetId": "feature-network-proxy-limited",
        "command": "codex -c 'features.network_proxy.enabled=true'",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "sandboxed networking을 도메인 정책과 함께 엽니다.",
    },
    {
        "key": "features.shell_snapshot",
        "label": "Shell snapshot",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-shell-runtime",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "반복 command 실행을 빠르게 하기 위해 shell 환경을 snapshot합니다.",
    },
    {
        "key": "features.unified_exec",
        "label": "Unified exec",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-shell-runtime",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-basic#supported-features",
        "desc": "PTY 기반 unified exec tool을 명시적으로 사용합니다.",
    },
    {
        "key": "features.skill_mcp_dependency_install",
        "label": "Skill MCP deps",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-shell-runtime",
        "command": "/skills",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "스킬이 요구하는 MCP dependency 설치 prompt를 허용합니다.",
    },
    {
        "key": "web_search",
        "label": "Web search cached",
        "maturity": "stable",
        "default": "cached",
        "presetId": "feature-web-search-cached",
        "command": "codex --search",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "legacy feature flag 대신 top-level web_search = cached를 사용합니다.",
    },
    {
        "key": "tools.view_image",
        "label": "View image",
        "maturity": "stable",
        "default": True,
        "presetId": "feature-image-tool",
        "command": "/status",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "로컬 이미지 attachment tool을 명시적으로 관리합니다.",
    },
]


HARNESS_CONTROLS: list[dict[str, Any]] = [
    {
        "area": "Model",
        "key": "model",
        "label": "기본 모델",
        "presetId": "gpt55-coding-agent",
        "doc": "https://developers.openai.com/api/docs/guides/latest-model",
        "desc": "GPT-5.5를 Codex 기본 모델로 지정하고 review_model도 맞춥니다.",
    },
    {
        "area": "Model",
        "key": "model_reasoning_effort",
        "label": "Reasoning effort",
        "presetId": "gpt55-coding-agent",
        "doc": "https://developers.openai.com/api/docs/guides/latest-model",
        "desc": "GPT-5.5 권장 balanced 시작점인 medium을 기본으로 사용합니다.",
    },
    {
        "area": "Project",
        "key": f"projects.{ROOT}.trust_level",
        "label": "현재 프로젝트 trust",
        "presetId": "trusted-current-project",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "trusted 프로젝트에서만 project-local .codex/config.toml, hooks, rules 레이어가 로드됩니다.",
    },
    {
        "area": "MCP",
        "key": "mcp_servers.openaiDeveloperDocs.url",
        "label": "OpenAI Docs MCP",
        "presetId": "openai-docs-mcp",
        "doc": "https://developers.openai.com/learn/docs-mcp",
        "desc": "OpenAI 공식 문서 MCP 서버를 Codex CLI/IDE extension 공용 config에 등록합니다.",
    },
    {
        "area": "Diagnostics",
        "key": "log_dir",
        "label": "Config/CLI 로그",
        "presetId": "config-schema-diagnostics",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "config.toml 진단, history 보존, raw output을 함께 켜서 문제 재현을 쉽게 합니다.",
    },
    {
        "area": "Context",
        "key": "include_environment_context",
        "label": "환경 컨텍스트 주입",
        "presetId": "context-injection-pack",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "현재 환경 정보를 모델 컨텍스트에 포함해 세션 상태 오해를 줄입니다.",
    },
    {
        "area": "Context",
        "key": "include_permissions_instructions",
        "label": "권한 지시 주입",
        "presetId": "context-injection-pack",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "sandbox/approval 권한 설명을 모델 컨텍스트에 포함합니다.",
    },
    {
        "area": "Context",
        "key": "include_collaboration_mode_instructions",
        "label": "협업 모드 지시 주입",
        "presetId": "context-injection-pack",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "Plan/Default 같은 collaboration mode 지시를 세션에 주입합니다.",
    },
    {
        "area": "Context",
        "key": "include_apps_instructions",
        "label": "Apps 지시 주입",
        "presetId": "context-injection-pack",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "Apps/connectors 관련 instructions를 컨텍스트에 포함할지 관리합니다.",
    },
    {
        "area": "Security",
        "key": "allow_login_shell",
        "label": "Login shell 차단",
        "presetId": "shell-env-hardened",
        "doc": "https://developers.openai.com/codex/config-advanced#shell-environment-policy",
        "desc": "shell tool이 login shell semantics를 쓰지 못하게 하고 secret 계열 환경변수 상속을 줄입니다.",
    },
    {
        "area": "Security",
        "key": "default_permissions",
        "label": "권한 프로파일",
        "presetId": "permission-profile",
        "doc": "https://developers.openai.com/codex/config-advanced#named-permission-profiles",
        "desc": "반복 실행용 filesystem/network permission profile을 config에 고정합니다.",
    },
    {
        "area": "Network",
        "key": "features.network_proxy",
        "label": "제한형 sandbox network",
        "presetId": "feature-network-proxy-limited",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "전역 network_access 대신 도메인 allowlist 기반 sandboxed networking을 사용합니다.",
    },
    {
        "area": "Research",
        "key": "tools.web_search",
        "label": "검색 도구 세부 설정",
        "presetId": "feature-web-search-research",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "context_size, allowed_domains, location을 설정할 수 있는 object form을 씁니다.",
    },
    {
        "area": "Tools",
        "key": "tools.view_image",
        "label": "이미지 attachment",
        "presetId": "feature-image-tool",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "스크린샷/이미지 기반 작업에서 view_image tool을 명시적으로 켭니다.",
    },
    {
        "area": "Tools",
        "key": "features.tool_search",
        "label": "Tool search",
        "presetId": "tool-discovery-pack",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "사용 가능한 도구 탐색 표면을 켜고 tool_suggest 설정과 같이 관리합니다.",
    },
    {
        "area": "Tools",
        "key": "tool_suggest.disabled_tools",
        "label": "Tool suggestion 제어",
        "presetId": "tool-discovery-pack",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "설치/사용 제안에서 제외할 도구를 config로 관리합니다.",
    },
    {
        "area": "MCP",
        "key": "mcp_servers.<id>.default_tools_approval_mode",
        "label": "MCP tool 승인 모드",
        "presetId": "mcp-strict-tools",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "MCP OAuth와 elicitation은 허용하되 tool approval은 서버별 prompt/allowlist로 관리합니다.",
    },
    {
        "area": "Apps",
        "key": "apps._default.default_tools_approval_mode",
        "label": "Apps prompt 승인",
        "presetId": "apps-prompt-tools",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "connector tool 기본값을 prompt 승인으로 두고 destructive/open-world는 닫습니다.",
    },
    {
        "area": "Memory",
        "key": "memories.disable_on_external_context",
        "label": "외부 컨텍스트 memory 제외",
        "presetId": "memory-privacy-safe",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "MCP/web/tool search가 섞인 thread를 memory generation 입력에서 제외합니다.",
    },
    {
        "area": "Patch",
        "key": "features.apply_patch_freeform",
        "label": "Apply patch 입력",
        "presetId": "patch-workbench",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "코드 수정 워크플로우에서 apply_patch freeform과 streaming event를 명시적으로 관리합니다.",
    },
    {
        "area": "Permissions",
        "key": "features.request_permissions_tool",
        "label": "권한 요청 tool",
        "presetId": "auth-permission-flow",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "세션 중 필요한 권한을 요청하는 tool 표면과 granular approval을 같이 켭니다.",
    },
    {
        "area": "Review",
        "key": "review_model",
        "label": "/review 모델",
        "presetId": "review-harness",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "/review 전용 모델과 reasoning summary 정책을 분리합니다.",
    },
    {
        "area": "TUI",
        "key": "tui.notifications",
        "label": "TUI 알림/스크롤백",
        "presetId": "tui-operator",
        "doc": "https://developers.openai.com/codex/config-advanced#tui-options",
        "desc": "agent 완료/approval 알림과 raw output, alternate screen 정책을 작업용으로 맞춥니다.",
    },
    {
        "area": "History",
        "key": "tool_output_token_limit",
        "label": "Tool output 예산",
        "presetId": "tool-output-budget",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "긴 command output이 history/context를 과도하게 차지하지 않도록 제한합니다.",
    },
    {
        "area": "Local",
        "key": "oss_provider",
        "label": "--oss provider",
        "presetId": "local-oss-ollama",
        "doc": "https://developers.openai.com/codex/config-advanced#oss-mode-local-providers",
        "desc": "codex --oss 실행 시 Ollama 또는 LM Studio 기본값을 config에 둡니다.",
    },
    {
        "area": "Profile",
        "key": "profile",
        "label": "기본 profile",
        "presetId": "profile-default-deep",
        "doc": "https://developers.openai.com/codex/config-basic#use-a-profile",
        "desc": "profile을 기본 선택값으로 지정하고 작업별 profile 묶음을 config에 둡니다.",
    },
    {
        "area": "UX",
        "key": "file_opener",
        "label": "파일 citation opener",
        "presetId": "citation-opener-vscode",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "Codex가 출력하는 파일 경로 citation을 익숙한 에디터에서 열도록 연결합니다.",
    },
    {
        "area": "Auth",
        "key": "cli_auth_credentials_store",
        "label": "인증 저장소",
        "presetId": "auth-storage-auto",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "CLI와 MCP OAuth credential 저장 방식을 auto로 맞춥니다.",
    },
    {
        "area": "Privacy",
        "key": "feedback.enabled",
        "label": "Feedback/telemetry quiet",
        "presetId": "privacy-quiet-pack",
        "doc": "https://developers.openai.com/codex/config-reference",
        "desc": "feedback, analytics, OTel exporter와 raw reasoning 노출을 끕니다.",
    },
    {
        "area": "Provider",
        "key": "model_providers.azure",
        "label": "Azure provider 골격",
        "presetId": "azure-provider-template",
        "doc": "https://developers.openai.com/codex/config-advanced#model-providers",
        "desc": "OpenAI 호환 provider 설정을 config에 추가합니다. 적용 후 placeholder URL을 실제 값으로 바꿔야 합니다.",
    },
]


HARNESS_TECHNIQUES: list[dict[str, Any]] = [
    {
        "title": "설정 레이어를 분리합니다",
        "why": "사용자 기본값은 ~/.codex/config.toml, repo 정책은 .codex/config.toml, 임시 실험은 --profile 또는 -c 로 분리하면 전역 설정 오염이 줄어듭니다.",
        "keys": ["profiles", "project_root_markers", "model", "model_provider"],
        "docs": "https://developers.openai.com/codex/config-basic",
        "snippet": "codex --profile deep-review\ncodex -c 'sandbox_mode=\"read-only\"'",
    },
    {
        "title": "프로젝트 trust 를 명시합니다",
        "why": "Codex는 trusted 프로젝트에서만 project-local .codex/config.toml, hooks, rules 레이어를 로드합니다. 반복 작업 repo는 trust 상태를 config에 남겨두는 편이 예측 가능합니다.",
        "keys": ["projects.<path>.trust_level", ".codex/config.toml", "hooks", "rules"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": f"[projects.\"{str(ROOT)}\"]\ntrust_level = \"trusted\"",
    },
    {
        "title": "공식 문서는 MCP로 붙입니다",
        "why": "OpenAI Docs MCP를 등록하면 Codex가 OpenAI API, Codex, Apps SDK 관련 최신 공식 문서를 도구로 검색하고 읽을 수 있습니다.",
        "keys": ["mcp_servers.openaiDeveloperDocs.url", "mcp_servers.<id>.default_tools_approval_mode", "/mcp"],
        "docs": "https://developers.openai.com/learn/docs-mcp",
        "snippet": "[mcp_servers.openaiDeveloperDocs]\nurl = \"https://developers.openai.com/mcp\"\ndefault_tools_approval_mode = \"prompt\"",
    },
    {
        "title": "승인 정책을 문자열이 아니라 플로우로 봅니다",
        "why": "approval_policy, sandbox_mode, approvals_reviewer, permissions 를 한 묶음으로 맞춰야 자동화와 안전도가 같이 올라갑니다.",
        "keys": ["approval_policy", "approvals_reviewer", "sandbox_mode", "default_permissions"],
        "docs": "https://developers.openai.com/codex/concepts/sandboxing",
        "snippet": "approval_policy = { granular = { sandbox_approval = true, rules = true, mcp_elicitations = true } }",
    },
    {
        "title": "goal 을 config layer 로 고정합니다",
        "why": "반복되는 작업 목표, 리뷰 기준, compact 기준은 developer_instructions 와 compact_prompt 로 런타임에 계속 유지시키는 편이 안정적입니다.",
        "keys": ["features.goals", "developer_instructions", "compact_prompt", "plan_mode_reasoning_effort"],
        "docs": "https://developers.openai.com/codex/cli/slash-commands#set-an-experimental-goal-with-goal",
        "snippet": "[features]\ngoals = true\n\n# Then in Codex CLI:\n/goal Finish the migration and keep tests green.",
    },
    {
        "title": "컨텍스트 주입량을 예산화합니다",
        "why": "AGENTS.md, fallback docs, environment context, permission instructions 는 강력하지만 길어질수록 비용과 noise 가 늘어납니다.",
        "keys": ["project_doc_max_bytes", "project_doc_fallback_filenames", "include_environment_context"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": "project_doc_max_bytes = 32768\nproject_doc_fallback_filenames = [\"AGENTS.md\", \"README.md\"]",
    },
    {
        "title": "하위 AGENTS.md 와 context flags 를 같이 봅니다",
        "why": "대형 repo에서는 child_agents_md, project_root_markers, include_* flags가 실제 모델이 받는 지시의 경계를 결정합니다.",
        "keys": ["features.child_agents_md", "include_collaboration_mode_instructions", "include_apps_instructions", "project_root_markers"],
        "docs": "https://developers.openai.com/codex/agents-md",
        "snippet": "[features]\nchild_agents_md = true\n\ninclude_permissions_instructions = true",
    },
    {
        "title": "도구 표면을 최소 권한으로 엽니다",
        "why": "MCP, app connector, web search, computer use 는 작업 범위를 넓히므로 destructive/open_world/network 를 명시적으로 꺼두고 필요한 tool 만 켭니다.",
        "keys": ["mcp_servers", "apps._default", "web_search", "tools"],
        "docs": "https://developers.openai.com/codex/mcp",
        "snippet": "[apps._default]\nenabled = true\ndestructive_enabled = false\nopen_world_enabled = false",
    },
    {
        "title": "Tool discovery 는 자동 설치가 아니라 제안 표면입니다",
        "why": "tool_search/tool_suggest 는 사용할 수 있는 도구를 찾는 보조 표면이므로, disabled_tools 와 approval mode를 같이 관리해야 합니다.",
        "keys": ["features.tool_search", "features.tool_suggest", "tool_suggest.disabled_tools", "apps._default.default_tools_approval_mode"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": "[features]\ntool_search = true\ntool_suggest = true\n\n[tool_suggest]\ndisabled_tools = []",
    },
    {
        "title": "반복 작업은 skill 과 subagent 로 승격합니다",
        "why": "자주 쓰는 리뷰/리서치/마이그레이션 흐름은 prompts 보다 agent role 과 skill 로 두면 재사용성과 품질 검증이 좋아집니다.",
        "keys": ["agents", "skills", "plugins"],
        "docs": "https://developers.openai.com/codex/skills",
        "snippet": "[agents.reviewer]\ndescription = \"Review changes for bugs, regressions, and missing tests.\"",
    },
    {
        "title": "패치 적용 경로를 별도 하네스로 둡니다",
        "why": "코드 변경 작업은 apply_patch 기능, 파일 citation opener, /review 모델을 함께 묶으면 수정-검토 루프가 짧아집니다.",
        "keys": ["features.apply_patch_freeform", "features.apply_patch_streaming_events", "file_opener", "review_model"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": "[features]\napply_patch_freeform = true\napply_patch_streaming_events = true\n\nfile_opener = \"vscode\"",
    },
    {
        "title": "쉘 환경과 네트워크를 별도 정책으로 관리합니다",
        "why": "환경변수 상속, secret 차단, workspace-write 네트워크 허용 여부는 sandbox 와 별도 축이라 명시적으로 보는 것이 안전합니다.",
        "keys": ["shell_environment_policy", "allow_login_shell", "sandbox_workspace_write.network_access", "permissions"],
        "docs": "https://developers.openai.com/codex/config-advanced",
        "snippet": "allow_login_shell = false\n\n[shell_environment_policy]\ninherit = \"core\"\nexclude = [\"*TOKEN*\", \"*SECRET*\"]",
    },
    {
        "title": "sandbox network 는 domain allowlist 로 엽니다",
        "why": "workspace-write network_access=true 보다 features.network_proxy 의 domains 정책이 반복 작업에서 검토하기 쉽습니다.",
        "keys": ["features.network_proxy.enabled", "features.network_proxy.domains", "permissions.<name>.network.domains"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": "[features.network_proxy]\nenabled = true\n\n[features.network_proxy.domains]\n\"api.openai.com\" = \"allow\"",
    },
    {
        "title": "검색은 mode 와 tool 옵션을 분리합니다",
        "why": "web_search 는 cached/live/disabled 를 고르고, tools.web_search 는 context size와 allowed domains를 좁히는 세부 하네스입니다.",
        "keys": ["web_search", "tools.web_search.context_size", "tools.web_search.allowed_domains"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": "web_search = \"live\"\n\n[tools.web_search]\ncontext_size = \"high\"\nallowed_domains = [\"developers.openai.com\"]",
    },
    {
        "title": "MCP와 Apps 도구 승인 모드를 기본값으로 묶습니다",
        "why": "서버/앱별 tool allowlist와 approval_mode를 config에 두면 연결 도구가 늘어도 실행 경계가 유지됩니다.",
        "keys": ["mcp_servers.<id>.enabled_tools", "mcp_servers.<id>.default_tools_approval_mode", "apps._default.default_tools_approval_mode"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": "[apps._default]\ndefault_tools_approval_mode = \"prompt\"\ndestructive_enabled = false\nopen_world_enabled = false",
    },
    {
        "title": "검증 루프를 hooks 로 붙입니다",
        "why": "PreToolUse/PostToolUse/Stop hook 은 command policy, lint/test, 알림을 자동화하는 지점입니다. 다만 한 레이어에 hooks.json 과 inline hooks 를 섞지 않는 편이 좋습니다.",
        "keys": ["hooks.PreToolUse", "hooks.PostToolUse", "hooks.Stop"],
        "docs": "https://developers.openai.com/codex/hooks",
        "snippet": "[[hooks.PostToolUse]]\nmatcher = \"^Bash$\"",
    },
    {
        "title": "관측 가능성을 남깁니다",
        "why": "history, notify, OTel 설정은 긴 작업과 반복 자동화에서 무엇이 실행됐는지 추적하는 기본 하네스입니다.",
        "keys": ["history", "notify", "otel", "tool_output_token_limit", "hide_agent_reasoning"],
        "docs": "https://developers.openai.com/codex/config-reference",
        "snippet": "tool_output_token_limit = 12000\n\n[history]\npersistence = \"save-all\"\nmax_bytes = 52428800",
    },
]


HARNESS_PLAYBOOKS: list[dict[str, Any]] = [
    {
        "name": "공식 Codex 최신 기본값",
        "steps": ["gpt-5.5 모델/리뷰 모델 설정", "OpenAI Docs MCP 등록", "현재 프로젝트 trust 명시", "config schema 진단/히스토리 보존"],
        "presetIds": ["gpt55-coding-agent", "openai-docs-mcp", "trusted-current-project", "config-schema-diagnostics"],
    },
    {
        "name": "낯선 repo 첫 진입",
        "steps": ["safe-local 적용", "AGENTS.md/README fallback 확인", "web_search=cached 유지", "write 작업 전 workspace-builder 로 전환"],
        "presetIds": ["safe-local", "goal-command", "goal-harness"],
    },
    {
        "name": "긴 리팩터링",
        "steps": ["goal-harness 로 목표/compact 고정", "context-injection-pack 으로 지시 주입 정리", "workspace-builder 적용", "agent-fleet 로 reviewer/researcher 분리", "patch-workbench 로 수정 루프 강화", "tool-output-budget 으로 로그 예산 제한"],
        "presetIds": ["goal-command", "goal-harness", "context-injection-pack", "workspace-builder", "agent-fleet", "patch-workbench", "tool-output-budget", "telemetry-audit"],
    },
    {
        "name": "반복 운영 자동화",
        "steps": ["permission-profile 로 filesystem/network 경계 설정", "connected-tools 로 MCP/app connector 표면 제한", "shell-env-hardened 로 secret 상속 축소", "hooks 에 검증 command 연결"],
        "presetIds": ["permission-profile", "connected-tools", "shell-env-hardened"],
    },
    {
        "name": "문서 리서치 작업",
        "steps": ["live web search 를 공식 도메인으로 제한", "tool discovery 로 필요한 connector/tool 후보 확인", "view_image tool 활성화", "network proxy 는 필요한 도메인만 allow"],
        "presetIds": ["feature-web-search-research", "tool-discovery-pack", "feature-image-tool", "feature-network-proxy-limited"],
    },
    {
        "name": "프라이버시 우선 메모리",
        "steps": ["memories 기능 활성화", "외부 컨텍스트 사용 thread는 memory 생성 제외", "history는 보존하되 tool output 예산 제한"],
        "presetIds": ["memory-privacy-safe", "tool-output-budget"],
    },
    {
        "name": "무승인/CI 스타일 실행",
        "steps": ["profile 로 sandbox/read-only 분리", "approval never 는 위험 조합 진단 확인 후 사용", "history/otel 로 실행 흔적 보존"],
        "presetIds": ["profiles-pack", "telemetry-audit"],
    },
    {
        "name": "IDE 같은 코드 수정 루프",
        "steps": ["apply_patch event 표면 활성화", "file citation opener 연결", "/review 모델 분리", "권한 요청 tool은 prompt 기반으로 유지"],
        "presetIds": ["patch-workbench", "citation-opener-vscode", "review-harness", "auth-permission-flow"],
    },
    {
        "name": "조용한 로컬 프라이버시 모드",
        "steps": ["analytics/feedback/OTel exporter 끄기", "memory 외부 컨텍스트 제외", "secret 환경변수 상속 줄이기", "cached search만 사용"],
        "presetIds": ["privacy-quiet-pack", "memory-privacy-safe", "shell-env-hardened", "feature-web-search-cached"],
    },
]


def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{_toml_key(str(k))} = {_toml_value(val)}" for k, val in sorted(v.items())) + " }"
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if v is None:
        return '""'
    return json.dumps(str(v), ensure_ascii=False)


def _toml_key(k: str) -> str:
    return k if _BARE_TOML_KEY.match(k) else json.dumps(k, ensure_ascii=False)


def _toml_table(path: list[str]) -> str:
    return ".".join(_toml_key(p) for p in path)


def _flatten_tables(path: list[str], data: dict[str, Any], out: list[tuple[list[str], dict[str, Any]]]) -> None:
    scalars: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            _flatten_tables([*path, k], v, out)
        else:
            scalars[k] = v
    if path and scalars:
        out.append((path, scalars))


def _to_toml(data: dict[str, Any]) -> str:
    top = {k: v for k, v in data.items() if not isinstance(v, dict)}
    tables: list[tuple[list[str], dict[str, Any]]] = []
    for k, v in data.items():
        if isinstance(v, dict):
            _flatten_tables([k], v, tables)
    lines: list[str] = [
        "# Managed by LazyCodex. Comments from the previous file are not preserved when applying presets.",
    ]
    for k in sorted(top):
        lines.append(f"{_toml_key(k)} = {_toml_value(top[k])}")
    for table, values in tables:
        lines.append("")
        lines.append(f"[{_toml_table(table)}]")
        for k in sorted(values):
            lines.append(f"{_toml_key(k)} = {_toml_value(values[k])}")
    return "\n".join(lines).rstrip() + "\n"


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_config() -> tuple[str, dict[str, Any], str]:
    raw = _safe_read(CONFIG_TOML) if CONFIG_TOML.exists() else ""
    if not raw.strip():
        return raw, {}, ""
    try:
        return raw, tomllib.loads(raw), ""
    except Exception as e:
        return raw, {}, str(e)


def _flatten_keys(data: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if not isinstance(data, dict):
        return keys
    for k, v in data.items():
        path = f"{prefix}.{k}" if prefix else str(k)
        keys.add(path)
        if isinstance(v, dict):
            keys |= _flatten_keys(v, path)
    return keys


def _nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _feature_flags(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in HARNESS_FEATURE_FLAGS:
        key = item["key"]
        configured = _nested(parsed, key, None) if "." in key else parsed.get(key)
        if configured is None:
            effective = item.get("default")
            source = "default"
        else:
            effective = configured
            source = "config"
        out.append({**item, "configured": configured, "effective": effective, "source": source})
    return out


def _harness_controls(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in HARNESS_CONTROLS:
        key = item["key"]
        if "<" in key:
            configured = None
        else:
            configured = _nested(parsed, key, None) if "." in key else parsed.get(key)
        out.append({**item, "configured": configured, "active": configured is not None})
    return out


def _harness_stats(parsed: dict[str, Any]) -> dict[str, int]:
    controls = _harness_controls(parsed)
    return {
        "catalogKeys": sum(len(group.get("keys") or []) for group in HARNESS_CATALOG),
        "presetCount": len(HARNESS_PRESETS),
        "featureFlagCount": len(HARNESS_FEATURE_FLAGS),
        "controlCount": len(HARNESS_CONTROLS),
        "configuredControls": sum(1 for item in controls if item.get("active")),
        "playbookCount": len(HARNESS_PLAYBOOKS),
        "techniqueCount": len(HARNESS_TECHNIQUES),
    }


def _analyze_config(parsed: dict[str, Any]) -> dict[str, Any]:
    flat = _flatten_keys(parsed)
    groups = {
        "모델": ["model", "model_provider", "model_reasoning_effort", "model_reasoning_summary", "model_verbosity"],
        "안전": ["approval_policy", "sandbox_mode", "sandbox_workspace_write", "approvals_reviewer", "default_permissions", "permissions", "allow_login_shell", "shell_environment_policy"],
        "기능": ["features", "web_search", "apps", "memories", "tools"],
        "목표": ["features.goals", "developer_instructions", "instructions", "compact_prompt", "project_doc_fallback_filenames", "project_doc_max_bytes", "review_model"],
        "도구": ["mcp_servers", "apps", "web_search", "tools", "shell_environment_policy"],
        "에이전트": ["agents", "skills", "plugins", "marketplaces"],
        "운영": ["history", "notify", "otel", "tui", "check_for_update_on_startup", "tool_output_token_limit", "feedback"],
        "프로파일": ["profile", "profiles"],
    }
    coverage = []
    for name, wanted in groups.items():
        matched = [k for k in wanted if k in flat or any(x.startswith(k + ".") for x in flat)]
        coverage.append({"name": name, "count": len(matched), "total": len(wanted), "keys": matched})

    approval = parsed.get("approval_policy")
    sandbox = parsed.get("sandbox_mode")
    web_search = parsed.get("web_search")
    app_default = _nested(parsed, "apps._default", {}) or {}
    risks: list[dict[str, str]] = []
    if approval == "never" and sandbox == "danger-full-access":
        risks.append({"level": "danger", "title": "무승인 + 전체 접근", "detail": "approval_policy=never 와 danger-full-access 조합은 신뢰한 로컬 repo 에서만 사용하세요."})
    if sandbox == "workspace-write" and _nested(parsed, "sandbox_workspace_write.network_access") is True:
        risks.append({"level": "warn", "title": "workspace-write 네트워크 허용", "detail": "쓰기 가능한 sandbox 에서 네트워크가 열려 있습니다. 필요한 도메인/작업인지 확인하세요."})
    if web_search == "live" and sandbox in ("workspace-write", "danger-full-access"):
        risks.append({"level": "warn", "title": "live web search + 실행 권한", "detail": "live 검색 결과는 최신이지만 임의 웹 컨텐츠입니다. 도구 실행과 결합될 때 주의가 필요합니다."})
    if app_default.get("destructive_enabled") is True:
        risks.append({"level": "warn", "title": "앱 destructive 도구 허용", "detail": "connector/app 도구의 destructive hint 를 기본 허용 중입니다."})
    if app_default.get("open_world_enabled") is True:
        risks.append({"level": "warn", "title": "앱 open-world 도구 허용", "detail": "외부 세계와 상호작용하는 app 도구가 기본 허용될 수 있습니다."})
    if _nested(parsed, "features.network_proxy.domains.*") == "allow":
        risks.append({"level": "warn", "title": "network_proxy 전체 도메인 허용", "detail": "features.network_proxy.domains 에 '*' allow가 설정되어 있습니다. 가능하면 필요한 도메인만 열어두세요."})
    if _nested(parsed, "shell_environment_policy.ignore_default_excludes") is True:
        risks.append({"level": "warn", "title": "secret 환경변수 기본 제외 비활성", "detail": "KEY/SECRET/TOKEN 계열 기본 제외를 무시하고 있습니다."})
    if parsed.get("show_raw_agent_reasoning") is True:
        risks.append({"level": "warn", "title": "raw reasoning 표시", "detail": "raw reasoning content가 화면/로그에 노출될 수 있습니다. 필요한 워크플로우에서만 사용하세요."})
    if not risks:
        risks.append({"level": "ok", "title": "명백한 고위험 조합 없음", "detail": "현재 파싱된 user config 에서 danger 조합은 감지되지 않았습니다."})

    profile_names = sorted((parsed.get("profiles") or {}).keys()) if isinstance(parsed.get("profiles"), dict) else []
    commands = [
        "codex --profile deep-review" if "deep-review" in profile_names else "codex --profile <name>",
        "codex -c 'sandbox_mode=\"read-only\"' -c 'web_search=\"disabled\"'",
        "codex --search",
        "codex --no-alt-screen",
        "codex -c 'features.network_proxy.enabled=true'",
        "codex -c 'features.goals=true' -c 'features.tool_search=true'",
        "codex -c 'features.apply_patch_streaming_events=true'",
        "codex -c 'tools.web_search={ context_size=\"high\", allowed_domains=[\"developers.openai.com\"] }'",
    ]
    return {
        "flatKeys": sorted(flat),
        "coverage": coverage,
        "risks": risks,
        "profileNames": profile_names,
        "commands": commands,
    }


def api_codex_harness_config(q: dict | None = None) -> dict:
    raw, parsed, error = _read_config()
    return {
        "ok": not bool(error),
        "path": str(CONFIG_TOML),
        "exists": CONFIG_TOML.exists(),
        "raw": raw,
        "parsed": parsed,
        "parseError": error,
        "catalog": HARNESS_CATALOG,
        "presets": HARNESS_PRESETS,
        "techniques": HARNESS_TECHNIQUES,
        "playbooks": HARNESS_PLAYBOOKS,
        "featureFlags": _feature_flags(parsed),
        "controls": _harness_controls(parsed),
        "stats": _harness_stats(parsed),
        "officialSurfaces": OFFICIAL_SURFACES,
        "analysis": _analyze_config(parsed),
        "schemaUrl": SCHEMA_URL,
        "docsUrl": DOCS_URL,
    }


def api_codex_harness_save(body: dict) -> dict:
    raw = body.get("raw", "") if isinstance(body, dict) else ""
    if not isinstance(raw, str):
        return {"ok": False, "error": "raw must be string"}
    try:
        tomllib.loads(raw) if raw.strip() else {}
    except Exception as e:
        return {"ok": False, "error": f"TOML parse error: {e}"}
    return {"ok": bool(_safe_write(CONFIG_TOML, raw))}


def api_codex_harness_apply(body: dict) -> dict:
    pid = (body or {}).get("presetId") if isinstance(body, dict) else ""
    preset = next((p for p in HARNESS_PRESETS if p["id"] == pid), None)
    if not preset:
        return {"ok": False, "error": f"unknown preset: {pid}"}
    raw, parsed, error = _read_config()
    if error:
        return {"ok": False, "error": "config.toml parse error; fix raw file before applying presets", "detail": error}
    merged = _deep_merge(parsed, preset["patch"])
    text = _to_toml(merged)
    ok = _safe_write(CONFIG_TOML, text)
    return {"ok": bool(ok), "raw": text, "path": str(CONFIG_TOML)}
