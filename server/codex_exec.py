"""Codex CLI non-interactive execution helpers.

Codex CLI 0.131+ uses `codex exec --json` for machine-readable output. The
older `codex -p ... --output-format json` path no longer exists, so all server
side Codex calls should go through this module.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_codex_exec_cmd(
    codex_bin: str,
    prompt: str,
    *,
    model: str = "",
    cwd: str = "",
    system_prompt: str = "",
    append_system_prompt: str = "",
    resume_session_id: str = "",
    ephemeral: bool = False,
    json_output: bool = True,
) -> list[str]:
    """Build a Codex CLI command compatible with current `codex exec`.

    `system_prompt` and `append_system_prompt` map to config overrides because
    current `codex exec` does not expose the old `--system-prompt` flags.
    """
    base = [codex_bin, "exec"]
    if resume_session_id:
        base.append("resume")

    if json_output:
        base.append("--json")
    base += ["--color", "never", "--skip-git-repo-check"]
    if ephemeral:
        base.append("--ephemeral")
    if model:
        base += ["--model", model]
    if cwd:
        base += ["-C", str(Path(cwd).expanduser())]

    developer_bits = [x.strip() for x in (system_prompt, append_system_prompt) if x and x.strip()]
    if developer_bits:
        base += ["-c", "developer_instructions=" + _toml_string("\n\n".join(developer_bits))]

    if resume_session_id:
        base += [resume_session_id, prompt]
    else:
        base.append(prompt)
    return base


def parse_codex_exec_jsonl(stdout: str) -> dict[str, Any]:
    """Parse `codex exec --json` JSONL and return final text + metadata."""
    events: list[dict[str, Any]] = []
    output = ""
    thread_id = ""
    error = ""
    usage: dict[str, Any] = {}
    for raw_line in (stdout or "").splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        events.append(obj)
        typ = obj.get("type")
        if typ == "thread.started":
            thread_id = str(obj.get("thread_id") or obj.get("threadId") or thread_id)
        elif typ == "error":
            msg = obj.get("message") or obj.get("error")
            if isinstance(msg, str):
                try:
                    nested = json.loads(msg)
                    if isinstance(nested, dict):
                        nested_error = nested.get("error") or {}
                        if isinstance(nested_error, dict):
                            msg = str(nested_error.get("message") or msg)
                except Exception:
                    pass
                error = msg
        elif typ == "item.completed":
            item = obj.get("item") or {}
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str):
                    output = text
        elif typ in ("agent_message", "message"):
            text = obj.get("text") or obj.get("content")
            if isinstance(text, str):
                output = text
        elif typ == "turn.completed":
            maybe_usage = obj.get("usage")
            if isinstance(maybe_usage, dict):
                usage = maybe_usage
        elif typ == "turn.failed":
            err = obj.get("error") or {}
            if isinstance(err, dict):
                msg = err.get("message")
                if isinstance(msg, str):
                    try:
                        nested = json.loads(msg)
                        if isinstance(nested, dict):
                            nested_error = nested.get("error") or {}
                            if isinstance(nested_error, dict):
                                msg = str(nested_error.get("message") or msg)
                    except Exception:
                        pass
                    error = msg

    if not output:
        # Fallback for unexpected future formats: keep non-control text only.
        noise = {"Reading additional input from stdin..."}
        output = "\n".join(
            line for line in (stdout or "").splitlines()
            if line.strip()
            and not line.lstrip().startswith("{")
            and line.strip() not in noise
        ).strip()

    return {
        "output": output,
        "error": error,
        "threadId": thread_id,
        "usage": usage,
        "events": events[-100:],
    }


def run_codex_exec(
    codex_bin: str,
    prompt: str,
    *,
    model: str = "",
    cwd: str = "",
    system_prompt: str = "",
    append_system_prompt: str = "",
    resume_session_id: str = "",
    ephemeral: bool = False,
    timeout: int = 300,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    cmd = build_codex_exec_cmd(
        codex_bin,
        prompt,
        model=model,
        cwd=cwd,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        resume_session_id=resume_session_id,
        ephemeral=ephemeral,
    )
    proc = subprocess.run(
        cmd,
        cwd=cwd or None,
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    return proc, parse_codex_exec_jsonl(proc.stdout or "")
