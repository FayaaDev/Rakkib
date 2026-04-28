"""Step 7 — Verify.

Run the final smoke tests for the deployed server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rakkib.state import State
from rakkib.steps import STEP_MODULES, VerificationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_verifications(state: State) -> list[VerificationResult]:
    """Import and run verify() from all other step modules.

    Reads from the cache written by cli._run_steps when available to avoid
    re-running each step's verify() three times per pull.
    """
    cache: dict[str, dict] = state.get("_step_verify_cache") or {}
    results: list[VerificationResult] = []

    for step_name, module_path in STEP_MODULES:
        if step_name in cache:
            cached = cache[step_name]
            results.append(VerificationResult(ok=cached["ok"], step=cached["step"], message=cached["message"]))
            continue

        try:
            module = __import__(module_path, fromlist=["verify"])
            verify_fn = getattr(module, "verify", None)
            if verify_fn is None:
                results.append(
                    VerificationResult.failure(
                        step_name,
                        f"Module {module_path} does not export verify()",
                    )
                )
                continue
            result = verify_fn(state)
            results.append(result)
        except ImportError:
            results.append(
                VerificationResult.failure(
                    step_name,
                    f"Step module {module_path} not found",
                )
            )
        except Exception as exc:
            results.append(
                VerificationResult.failure(
                    step_name,
                    f"verify() raised {type(exc).__name__}: {exc}",
                )
            )

    return results


def _print_summary(results: list[VerificationResult]) -> None:
    """Print a plain-text summary of verification results."""
    print("")
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for r in results:
        status = "PASS" if r.ok else "FAIL"
        icon = "✓" if r.ok else "✗"
        print(f"{icon}  [{status}]  Step {r.step:<12}  {r.message}")
        if not r.ok and r.log_path:
            print(f"      Log: {r.log_path}")

    failures = [r for r in results if not r.ok]
    print("-" * 60)
    print(f"Total: {len(results)} checks, {len(failures)} failures")
    print("")

    if failures:
        print("ACTION REQUIRED")
        print("-" * 60)
        print(
            "Some verification checks failed. Review the failures above, "
            "check the relevant logs, and re-run `rakkib pull` to retry."
        )
        print("")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run(state: State) -> None:
    results = _collect_verifications(state)
    failures = [r for r in results if not r.ok]

    if failures:
        _print_summary(results)
    else:
        print("All verification checks passed.")


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify(state: State) -> VerificationResult:
    results = _collect_verifications(state)
    failures = [r for r in results if not r.ok]

    if not failures:
        return VerificationResult.success("verify", "All sub-verifications passed")

    messages = [f"{r.step}: {r.message}" for r in failures]
    return VerificationResult.failure(
        "verify",
        f"{len(failures)} verification(s) failed: " + "; ".join(messages),
        state_slice={"failed_steps": [r.step for r in failures]},
    )
