"""Interview engine — phase loop: prompt -> validate -> normalize -> persist."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

from rakkib.normalize import apply_normalize, eval_when, resolve_numeric_aliases
from rakkib.schema import FieldDef, QuestionSchema, load_all_schemas
from rakkib.state import State

console = Console()


def run_interview(state: State, questions_dir: Path | str = "questions") -> State:
    """Drive Phases 1-6 using embedded AgentSchema blocks.

    Resume is automatic: load state, find first phase with unset required keys,
    start there. If ``confirmed: true``, ask once whether to start over.
    """
    schemas = load_all_schemas(questions_dir)

    if state.is_confirmed():
        overwrite = Confirm.ask(
            "An existing confirmed state was found. Start over?",
            default=False,
        )
        if overwrite:
            state = State({})

    resume = state.resume_phase()
    for schema in schemas:
        if schema.phase < resume:
            continue
        _run_phase(schema, state)
        state.save()

    return state


def _run_phase(schema: QuestionSchema, state: State) -> None:
    """Execute a single phase's field list against the current state."""
    console.print(f"[bold blue]Phase {schema.phase}[/bold blue]")
    for field in schema.fields:
        _run_field(field, state, schema)
    _enforce_rules(schema, state)


def _run_field(
    field: FieldDef, state: State, schema: QuestionSchema | None = None
) -> None:
    """Process one field: detect, derive, prompt, validate, normalize, record."""
    # 1. Skip if `when` condition is false
    if field.when and not eval_when(field.when, state):
        return

    # 2. Handle derived fields
    if field.type == "derived":
        _handle_derived(field, state)
        return

    # 3. Handle secret group
    if field.type == "secret_group":
        _handle_secret_group(field, state)
        return

    # 4. Handle summary
    if field.type == "summary":
        _handle_summary(field, state)
        return

    # 5. Handle repeat fields
    if field.repeat_for:
        _handle_repeat(field, state, schema)
        return

    # 6. Prompt user based on type
    value: Any = None
    if field.type == "text":
        value = _prompt_text(field, state)
    elif field.type == "confirm":
        value = _prompt_confirm(field, state)
    elif field.type == "single_select":
        value = _prompt_single_select(field, state)
    elif field.type == "multi_select":
        value = _prompt_multi_select(field, state)
    else:
        console.print(f"[yellow]Unknown field type: {field.type}[/yellow]")
        return

    # 7. Handle value_if_true
    if field.value_if_true is not None:
        if value is True:
            _record_dict(field.value_if_true, state)
        return

    # 8. Record values
    _record_field_value(field, value, state)


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------


def _handle_derived(field: FieldDef, state: State) -> None:
    """Handle derived field types."""
    # Detect from host command
    if field.detect:
        result = _run_detect(field, state)
        if isinstance(result, dict):
            for k, v in result.items():
                state.set(k, v)
        elif result is not None:
            _record_field_value(field, result, state)
        return

    # Derive from template
    if field.template:
        template = field.template
        derive_keys = field.derive_from
        if isinstance(derive_keys, str):
            derive_keys = [derive_keys]
        for key in derive_keys or []:
            val = state.get(key, "")
            template = template.replace(f"{{{{{key}}}}}", str(val))
        _record_field_value(field, template, state)
        return

    # Derive from value
    if field.value is not None:
        value = field.value
        if isinstance(value, dict):
            # Check if it's a state-keyed dict (keys match records)
            if field.records and all(r in value for r in field.records):
                rendered = _render_template_dict(value, state)
                for k, v in rendered.items():
                    state.set(k, v)
                return
            # Otherwise it's a platform-keyed dict or has a default key
            platform = state.get("platform")
            if platform and platform in value:
                value = value[platform]
            elif "default" in value:
                value = value["default"]

        _record_field_value(field, value, state)
        return

    # derived_value
    if field.derived_value:
        _record_dict(field.derived_value, state)
        return


def _run_detect(field: FieldDef, state: State) -> Any:
    """Run detection command and normalize result."""
    detect = field.detect
    command = None

    if isinstance(detect, dict):
        if "command" in detect:
            command = detect["command"]
        else:
            platform = state.get("platform")
            if platform == "linux" and "linux" in detect:
                command = detect["linux"]
            elif platform == "mac" and "mac" in detect:
                command = detect["mac"]

    if not command:
        return None

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=False
        )
        output = result.stdout.strip()
    except Exception:
        output = ""

    # Check detect-level normalize first
    normalize = detect.get("normalize") if isinstance(detect, dict) else None
    if normalize and isinstance(normalize, dict):
        if output in normalize:
            val = normalize[output]
            if isinstance(val, dict):
                return val  # Caller records each key
            return val
        if "default" in normalize:
            val = normalize["default"]
            if isinstance(val, dict):
                return val
            return val

    # Apply field-level normalize
    if field.normalize:
        return apply_normalize(output, field.normalize)

    return output


def _render_template_dict(value: dict[str, Any], state: State) -> dict[str, Any]:
    """Render {{key}} placeholders in a dict of template strings."""
    rendered: dict[str, Any] = {}
    for k, v in value.items():
        if isinstance(v, str):
            for key in _extract_template_keys(v):
                val = state.get(key, "")
                v = v.replace(f"{{{{{key}}}}}", str(val))
        rendered[k] = v
    return rendered


def _extract_template_keys(template: str) -> list[str]:
    return re.findall(r"\{\{([^{}]+)\}\}", template)


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


def _prompt_text(field: FieldDef, state: State) -> str:
    """Prompt for text input with validation."""
    default = _get_default(field, state)
    prompt = field.prompt

    while True:
        if default is not None and default != "":
            answer = Prompt.ask(prompt, default=str(default))
        else:
            answer = Prompt.ask(prompt)

        # Empty answer with default: use default
        if answer == "" and default is not None:
            answer = str(default)

        if _validate(answer, field):
            return answer

        # Validation failed — loop


def _prompt_confirm(field: FieldDef, state: State) -> Any:
    """Prompt for confirmation or yes/no mapped to arbitrary values."""
    prompt = field.prompt
    default = field.default

    if field.accepted_inputs:
        values = set(field.accepted_inputs.values())
        if values <= {True, False}:
            # Standard boolean confirm
            bool_default = default if isinstance(default, bool) else None
            return Confirm.ask(prompt, default=bool_default)
        else:
            # Non-boolean mapping (e.g., generate/manual)
            choices = ", ".join(field.accepted_inputs.keys())
            while True:
                raw = Prompt.ask(f"{prompt} ({choices})", default="")
                raw_lower = raw.lower().strip()
                if raw_lower in field.accepted_inputs:
                    return field.accepted_inputs[raw_lower]
                if raw == "" and default is not None:
                    return default
                console.print(f"[red]Invalid input. Please enter one of: {choices}[/red]")
    else:
        bool_default = default if isinstance(default, bool) else None
        return Confirm.ask(prompt, default=bool_default)


def _prompt_single_select(field: FieldDef, state: State) -> str:
    """Prompt for single select."""
    prompt = field.prompt
    values = field.canonical_values

    while True:
        answer = Prompt.ask(prompt)
        answer_stripped = answer.strip()
        answer_lower = answer_stripped.lower()

        # Check aliases
        for canonical, aliases in field.aliases.items():
            if answer_lower in [a.lower() for a in aliases]:
                return canonical

        if answer_lower in [v.lower() for v in values]:
            return answer_lower

        console.print(f"[red]Invalid choice. Valid options: {', '.join(values)}[/red]")


def _prompt_multi_select(field: FieldDef, state: State) -> list[str]:
    """Prompt for multi-select."""
    prompt = field.prompt
    selection_mode = getattr(field, "selection_mode", "") or ""
    default = field.default if field.default is not None else []
    if not isinstance(default, list):
        default = []

    canonical = field.canonical_values
    aliases = getattr(field, "numeric_aliases", {}) or {}

    while True:
        answer = Prompt.ask(prompt, default="")

        if answer.strip() == "":
            if selection_mode == "deselect_from_default":
                return list(default)
            return []

        parts = resolve_numeric_aliases(answer, aliases)

        valid: list[str] = []
        invalid: list[str] = []
        for p in parts:
            p_lower = p.lower()
            matched = None
            for c in canonical:
                if c.lower() == p_lower:
                    matched = c
                    break
            if matched:
                valid.append(matched)
            else:
                invalid.append(p)

        if invalid:
            console.print(
                f"[red]Invalid choices: {', '.join(invalid)}. Valid: {', '.join(canonical)}[/red]"
            )
            continue

        if selection_mode == "deselect_from_default":
            result = [d for d in default if d not in valid]
        else:  # add_to_empty
            result = list(dict.fromkeys(valid))  # preserve order, dedupe

        return result


# ---------------------------------------------------------------------------
# Special field types
# ---------------------------------------------------------------------------


def _handle_secret_group(field: FieldDef, state: State) -> None:
    """Handle secret group entries."""
    for entry in field.entries:
        key = entry.get("key", "")
        when = entry.get("when", "always")

        if when != "always" and not eval_when(when, state):
            continue

        prompt = f"Enter value for {key}:"
        while True:
            value = Prompt.ask(prompt)
            if value.strip() != "":
                state.set(f"secrets.values.{key}", value)
                break
            console.print("[red]Value cannot be empty.[/red]")


def _handle_summary(field: FieldDef, state: State) -> None:
    """Display a formatted summary of selected state fields."""
    console.print("\n[bold]Deployment Summary[/bold]")
    for key in field.summary_fields:
        value = state.get(key)
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value) if value else "None"
        else:
            value_str = str(value) if value is not None else "None"
        console.print(f"  {label}: {value_str}")
    console.print()


def _handle_repeat(
    field: FieldDef, state: State, schema: QuestionSchema | None
) -> None:
    """Handle repeat_for fields (e.g., subdomains)."""
    repeat_for = field.repeat_for

    if repeat_for == "selected_service_slugs":
        foundation = state.get("foundation_services", []) or []
        selected = state.get("selected_services", []) or []
        slugs = foundation + selected
    else:
        console.print(f"[yellow]Unknown repeat_for: {repeat_for}[/yellow]")
        return

    # Build default subdomain map from service catalog
    defaults: dict[str, str] = {}
    if schema and schema.service_catalog:
        for section in ("foundation_bundle", "optional_services"):
            for item in schema.service_catalog.get(section, []):
                slug = item.get("slug", "")
                defaults[slug] = item.get("default_subdomain", slug)

    customize = state.get("customize_subdomains", False)
    if customize is None:
        customize = False

    for slug in slugs:
        default = defaults.get(slug, slug)
        if customize:
            prompt = (
                field.prompt_template.replace("<service>", slug)
                .replace("<default>", default)
            )
            while True:
                answer = Prompt.ask(prompt, default=default)
                if answer == "":
                    answer = default
                if _validate(answer, field):
                    state.set(f"subdomains.{slug}", answer)
                    break
        else:
            state.set(f"subdomains.{slug}", default)


# ---------------------------------------------------------------------------
# Rules enforcement
# ---------------------------------------------------------------------------


def _enforce_rules(schema: QuestionSchema, state: State) -> None:
    """Enforce phase-level rules after fields have run."""
    for rule in schema.rules:
        if not isinstance(rule, dict):
            continue

        if_selected = rule.get("if_selected")
        selected_services = state.get("selected_services", []) or []

        if if_selected and if_selected in selected_services:
            require_confirm = rule.get("require_confirm")
            if require_confirm == "transfer_public_risk":
                confirmed = Confirm.ask(
                    "[yellow]Warning:[/yellow] transfer.sh will be deployed as a public "
                    "unauthenticated upload endpoint. Anyone who can reach the URL can upload files. "
                    "Continue?",
                    default=False,
                )
                if not confirmed:
                    state.set(
                        "selected_services",
                        [s for s in selected_services if s != "transfer"],
                    )

            requires = rule.get("requires")
            if requires and isinstance(requires, dict):
                foundation = state.get("foundation_services", []) or []
                for req_key, req_values in requires.items():
                    if req_key == "foundation_services":
                        for req_val in req_values:
                            if req_val not in foundation:
                                console.print(
                                    f"[yellow]Hermes dashboard exposure requires Authentik protection. "
                                    f"Re-selecting {req_val}.[/yellow]"
                                )
                                foundation = foundation + [req_val]
                        state.set("foundation_services", foundation)


# ---------------------------------------------------------------------------
# Defaults & validation
# ---------------------------------------------------------------------------


def _get_default(field: FieldDef, state: State) -> Any:
    """Compute the default value for a prompt field."""
    if field.default_from_state:
        return state.get(field.default_from_state)

    if field.default_from_host:
        host_default = field.default_from_host
        if isinstance(host_default, dict):
            platform = state.get("platform")
            if platform == "linux":
                sudo_user = os.environ.get("SUDO_USER")
                if "sudo_linux" in host_default and sudo_user:
                    cmd = host_default["sudo_linux"]
                    if cmd == "SUDO_USER":
                        return sudo_user
                if "linux" in host_default:
                    cmd = host_default["linux"]
                    if cmd == "SUDO_USER":
                        return os.environ.get("SUDO_USER", "")
                    try:
                        result = subprocess.run(
                            cmd, shell=True, capture_output=True, text=True
                        )
                        return result.stdout.strip()
                    except Exception:
                        return ""
            elif platform == "mac" and "mac" in host_default:
                cmd = host_default["mac"]
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True
                    )
                    return result.stdout.strip()
                except Exception:
                    return ""
        else:
            try:
                result = subprocess.run(
                    str(host_default), shell=True, capture_output=True, text=True
                )
                return result.stdout.strip()
            except Exception:
                return ""

    return field.default


def _validate(answer: str, field: FieldDef) -> bool:
    """Validate an answer according to the field's validate spec."""
    validate_spec = field.validate
    if not validate_spec:
        return True

    if isinstance(validate_spec, dict):
        if validate_spec.get("non_empty"):
            if not answer or not answer.strip():
                msg = validate_spec.get("message", "Value cannot be empty.")
                console.print(f"[red]{msg}[/red]")
                return False

        pattern = validate_spec.get("pattern")
        if pattern:
            if not re.match(pattern, answer):
                msg = validate_spec.get("message", "Invalid format.")
                console.print(f"[red]{msg}[/red]")
                return False

        return True

    if isinstance(validate_spec, str):
        if not re.match(validate_spec, answer):
            console.print("[red]Invalid format.[/red]")
            return False
        return True

    return True


# ---------------------------------------------------------------------------
# Recording helpers
# ---------------------------------------------------------------------------


def _record_field_value(field: FieldDef, value: Any, state: State) -> None:
    """Record a field's result into state.

    If ``records`` is empty, falls back to recording under the field ``id``
    so that downstream ``when`` clauses can reference it.
    """
    if field.records:
        for record_key in field.records:
            if field.derived_value and record_key in field.derived_value:
                state.set(record_key, field.derived_value[record_key])
            else:
                state.set(record_key, value)
    else:
        state.set(field.id, value)


def _record_dict(value_dict: dict[str, Any], state: State) -> None:
    """Record a flat dict of key-value pairs into state."""
    for key, value in value_dict.items():
        state.set(key, value)
