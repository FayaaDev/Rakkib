"""Agent handoff — launch opencode/claude/codex with a narrow prompt.

On any verify() failure, the binary asks "launch agent to diagnose? (Y/n)"
and invokes the available agent with:
- failed step name
- failure message
- log tail
- relevant state keys (secrets redacted)
- specific question / step files for that step

The agent receives a narrow diagnostic prompt, not AGENT_PROTOCOL.md whole.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import deque
from pathlib import Path
from typing import Any, Literal

import yaml
from rich.console import Console
from rich.prompt import Confirm

from rakkib.state import State

AgentName = Literal["opencode", "claude", "codex"]

console = Console()

# ---------------------------------------------------------------------------
# Agent discovery
# ---------------------------------------------------------------------------


def find_agent(preferred: str | None = None) -> AgentName | None:
    """Return the first available agent CLI on PATH.

    *preferred* may be an agent name or ``"auto"`` / ``"none"``.
    """
    candidates: list[AgentName] = ["opencode", "claude", "codex"]

    if preferred and preferred not in ("auto", "none"):
        if preferred in candidates:
            candidates = [preferred] + [c for c in candidates if c != preferred]
        else:
            return None

    for agent in candidates:
        if shutil.which(agent):
            return agent
    return None


# ---------------------------------------------------------------------------
# Log tail
# ---------------------------------------------------------------------------


def read_log_tail(log_path: Path | str, lines: int = 50) -> str:
    """Return the last *lines* of a log file."""
    path = Path(log_path)
    if not path.exists():
        return f"(log file not found: {path})"
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            # Efficient tail for large files using a deque
            return "".join(deque(fh, maxlen=lines))
    except Exception as exc:
        return f"(could not read log: {exc})"


# ---------------------------------------------------------------------------
# Step → log path mapping
# ---------------------------------------------------------------------------


def log_paths_for_step(step: str, state: State) -> list[Path]:
    """Return canonical log file path(s) for a given step name."""
    data_root = Path(state.get("data_root", "/srv"))

    mapping: dict[str, list[Path]] = {
        "layout": [data_root / "logs" / "layout.log"],
        "caddy": [data_root / "logs" / "caddy.log"],
        "postgres": [data_root / "logs" / "postgres.log"],
        "cron": [data_root / "logs" / "cron.log"],
        "cloudflare": [data_root / "logs" / "cloudflare.log"],
        "verify": [],
    }

    if step == "services":
        # Collect per-service logs for all selected services
        svc_ids: list[str] = []
        svc_ids.extend(state.get("foundation_services", []) or [])
        svc_ids.extend(state.get("selected_services", []) or [])
        return [data_root / "logs" / f"step60-{sid}.log" for sid in svc_ids]

    return mapping.get(step, [])


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

_SECRET_SUBSTRINGS = ("secret", "password", "pass", "key", "token", "credential")


def _is_secret_key(key: str) -> bool:
    lower = key.lower()
    return any(sub in lower for sub in _SECRET_SUBSTRINGS)


def redact_state(data: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy with secret values replaced by ``***``."""
    if not isinstance(data, dict):
        return data

    result: dict[str, Any] = {}
    for key, value in data.items():
        if key == "secrets" and isinstance(value, dict):
            # Redact the entire secrets subtree, preserving mode hint
            result[key] = {
                "mode": value.get("mode", "unknown"),
                "values": "***REDACTED***",
            }
        elif _is_secret_key(key):
            result[key] = "***"
        elif isinstance(value, dict):
            result[key] = redact_state(value)
        elif isinstance(value, list):
            result[key] = [
                redact_state(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# Step → context file mapping
# ---------------------------------------------------------------------------

_STEP_CONTEXT_FILES: dict[str, list[str]] = {
    "layout": ["steps/10-layout.md"],
    "caddy": ["steps/30-caddy.md", "questions/02-identity.md"],
    "postgres": ["steps/50-postgres.md", "questions/05-secrets.md"],
    "services": ["steps/60-services.md", "questions/03-services.md", "registry.yaml"],
    "cron": ["steps/80-cron-jobs.md"],
    "cloudflare": ["steps/40-cloudflare.md", "questions/04-cloudflare.md"],
    "verify": ["steps/90-verify.md"],
}


def question_files_for_step(step: str, repo_dir: Path) -> list[tuple[str, str]]:
    """Return (filename, content) tuples for the files relevant to *step*.

    Files that do not exist are silently skipped.
    """
    rel_paths = _STEP_CONTEXT_FILES.get(step, [])
    results: list[tuple[str, str]] = []
    for rel in rel_paths:
        path = repo_dir / rel
        if path.exists():
            try:
                results.append((rel, path.read_text(encoding="utf-8")))
            except Exception:
                pass
    return results


# ---------------------------------------------------------------------------
# State slice for a step
# ---------------------------------------------------------------------------

_STEP_STATE_KEYS: dict[str, list[str]] = {
    "layout": ["data_root", "platform", "admin_user"],
    "caddy": ["data_root", "docker_net", "domain", "subdomain"],
    "postgres": ["data_root"],
    "services": ["data_root", "foundation_services", "selected_services"],
    "cron": ["data_root", "backup_dir", "platform", "selected_services", "admin_user"],
    "cloudflare": ["data_root", "cloudflare", "tunnel_uuid", "cloudflared_metrics_port"],
    "verify": ["data_root"],
}


def build_state_slice(step: str, state: State) -> dict[str, Any]:
    """Extract relevant state keys for *step* and redact secrets."""
    keys = _STEP_STATE_KEYS.get(step, ["data_root"])
    slice_: dict[str, Any] = {}
    for key in keys:
        if state.has(key):
            # Use dot-notated keys directly in the slice for clarity
            slice_[key] = state.get(key)
    # Also include failed_steps if present (from Step 90 aggregator)
    if step == "verify" and state.has("failed_steps"):
        slice_["failed_steps"] = state.get("failed_steps")
    return redact_state(slice_)


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_prompt(
    step: str,
    message: str,
    log_tail: str,
    state_slice: dict[str, Any],
    file_contents: list[tuple[str, str]],
) -> str:
    """Construct a narrow diagnostic prompt for the agent."""
    files_block = "\n\n".join(
        f"--- {name} ---\n{content}" for name, content in file_contents
    )

    state_yaml = yaml.safe_dump(state_slice, sort_keys=False, allow_unicode=True)

    parts = [
        f"Rakkib step '{step}' failed verification.",
        "",
        f"Failure message: {message}",
        "",
        "Relevant state context (secrets redacted):",
        "```yaml",
        state_yaml.rstrip(),
        "```",
        "",
        "Last log lines:",
        "```",
        log_tail.rstrip() or "(no log output)",
        "```",
    ]

    if files_block:
        parts.extend([
            "",
            "Relevant documentation:",
            files_block,
        ])

    parts.extend([
        "",
        "Diagnose the failure and suggest a fix. Do not re-run the full installer. "
        "If you need to run a command to inspect the system, tell the user what to run. "
        "Keep your response focused on this single failure.",
    ])

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Agent launcher
# ---------------------------------------------------------------------------


def _launch(agent: AgentName, prompt: str, repo_dir: Path | None = None) -> int:
    """Launch *agent* with *prompt* and return its exit code.

    Prompts are passed via stdin to avoid shell argument length limits.
    """
    cwd = str(repo_dir) if repo_dir else "."

    if agent == "opencode":
        result = subprocess.run(
            ["opencode", ".", "--prompt", "-"],
            input=prompt,
            text=True,
            cwd=cwd,
        )
    elif agent == "claude":
        # Claude Code one-shot mode varies by version; try common patterns.
        # Prefer ``claude -p -`` (project mode with stdin prompt) if available.
        result = subprocess.run(
            ["claude", "-p", "-"],
            input=prompt,
            text=True,
            cwd=cwd,
        )
    elif agent == "codex":
        result = subprocess.run(
            ["codex", "-"],
            input=prompt,
            text=True,
            cwd=cwd,
        )
    else:
        raise ValueError(f"Unsupported agent: {agent}")

    return result.returncode


# ---------------------------------------------------------------------------
# Public handoff entrypoint
# ---------------------------------------------------------------------------


def handoff(
    step: str,
    message: str,
    log_path: Path | None,
    state: State,
    repo_dir: Path,
    agent: str | None = None,
    print_prompt: bool = False,
    no_agent: bool = False,
) -> bool:
    """Offer to launch an agent to diagnose a step failure.

    Returns ``True`` if an agent was launched (or prompt printed), ``False``
    if the user declined or no agent was available.
    """
    if no_agent:
        console.print("[dim]--no-agent set; skipping agent handoff.[/dim]")
        return False

    chosen = find_agent(agent) if agent not in (None, "auto", "none") else find_agent()

    # Resolve log tail(s)
    log_paths = [log_path] if log_path else log_paths_for_step(step, state)
    tails: list[str] = []
    for lp in log_paths:
        tail = read_log_tail(lp, lines=50)
        if tail and not tail.startswith("(log file not found"):
            tails.append(f"--- {lp.name} ---\n{tail}")
    log_tail = "\n\n".join(tails) if tails else "(no logs available)"

    state_slice = build_state_slice(step, state)
    file_contents = question_files_for_step(step, repo_dir)

    prompt = _build_prompt(step, message, log_tail, state_slice, file_contents)

    if print_prompt:
        console.print("[bold cyan]Agent prompt:[/bold cyan]")
        console.print(prompt)
        return True

    if not chosen:
        console.print(
            "[yellow]No supported agent found on PATH (opencode, claude, codex).[/yellow]"
        )
        console.print(
            "[dim]You can re-run with --print-prompt to see the diagnostic prompt, "
            "or install an agent and try again.[/dim]"
        )
        return False

    launch = Confirm.ask(
        f"Launch [bold]{chosen}[/bold] to diagnose the failure? (Y/n)",
        default=True,
    )
    if not launch:
        console.print("[dim]Agent handoff skipped.[/dim]")
        return False

    console.print(f"[dim]Launching {chosen} with narrow diagnostic prompt…[/dim]")
    exit_code = _launch(chosen, prompt, repo_dir=repo_dir)
    if exit_code != 0:
        console.print(f"[yellow]{chosen} exited with code {exit_code}.[/yellow]")
    return True
