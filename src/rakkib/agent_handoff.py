"""Agent handoff — launch opencode/claude/codex with a narrow prompt.

On any verify() failure, the binary asks "launch agent to diagnose? (Y/n)"
and invokes the available agent with:
- failed step name
- log tail
- relevant state keys
- specific question files for that step
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal

AgentName = Literal["opencode", "claude", "codex"]


def find_agent(preferred: AgentName | None = None) -> AgentName | None:
    """Return the first available agent CLI on PATH."""
    candidates: list[AgentName] = ["opencode", "claude", "codex"]
    if preferred:
        candidates = [preferred] + [c for c in candidates if c != preferred]
    for agent in candidates:
        if shutil.which(agent):
            return agent
    return None


def handoff(
    step: str,
    log_tail: str,
    state_slice: dict,
    question_files: list[Path],
    agent: AgentName | None = None,
) -> None:
    """Launch an agent with a narrow diagnostic prompt."""
    chosen = agent or find_agent()
    if not chosen:
        raise RuntimeError("No supported agent found on PATH: opencode, claude, codex")

    prompt = _build_prompt(step, log_tail, state_slice, question_files)
    _launch(chosen, prompt)


def _build_prompt(
    step: str,
    log_tail: str,
    state_slice: dict,
    question_files: list[Path],
) -> str:
    """Construct a narrow diagnostic prompt for the agent."""
    files_block = "\n".join(str(p) for p in question_files)
    return (
        f"Rakkib step '{step}' failed verification.\n\n"
        f"Relevant question files:\n{files_block}\n\n"
        f"State context:\n{state_slice}\n\n"
        f"Last log lines:\n{log_tail}\n\n"
        "Diagnose the failure and suggest a fix. Do not re-run the full installer."
    )


def _launch(agent: AgentName, prompt: str) -> None:
    """Run the agent CLI with the given prompt."""
    if agent == "opencode":
        subprocess.run(["opencode", ".", "--prompt", prompt])
    elif agent == "claude":
        subprocess.run(["claude", prompt])
    elif agent == "codex":
        subprocess.run(["codex", prompt])
    else:
        raise ValueError(f"Unsupported agent: {agent}")
