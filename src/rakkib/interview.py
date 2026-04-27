"""Interview engine — phase loop: prompt -> validate -> normalize -> persist."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from questionary import Choice
from rich.console import Console

from rakkib.normalize import apply_normalize, eval_when, resolve_numeric_aliases
from rakkib.schema import FieldDef, QuestionSchema, load_all_schemas
from rakkib.state import State
from rakkib.tui import prompt_checkbox, prompt_confirm, prompt_password, prompt_select, prompt_text

console = Console()


def run_interview(state: State, questions_dir: Path | str = "questions") -> State:
    """Drive Phases 1-6 using embedded AgentSchema blocks.

    Resume is automatic: load state, find first phase with unset required keys,
    start there. If ``confirmed: true``, ask once whether to start over.
    """
    schemas = load_all_schemas(questions_dir)

    if state.is_confirmed():
        overwrite = prompt_confirm(
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

    if schema.service_catalog:
        _handle_service_catalog(schema, state)
        _enforce_rules(schema, state)
        state.save()
        return

    for field in schema.fields:
        _run_field(field, state, schema)
    _enforce_rules(schema, state)


def _run_field(
    field: FieldDef, state: State, schema: QuestionSchema | None = None
) -> None:
    """Process one field: detect, derive, prompt, validate, normalize, record."""
    if field.when and not eval_when(field.when, state):
        return

    if field.type == "derived":
        _handle_derived(field, state)
        return

    if field.type == "secret_group":
        _handle_secret_group(field, state)
        return

    if field.type == "summary":
        _handle_summary(field, state)
        return

    if field.repeat_for:
        _handle_repeat(field, state, schema)
        return

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

    if field.value_if_true is not None:
        if value is True:
            _record_dict(field.value_if_true, state)
        return

    _record_field_value(field, value, state)


# ---------------------------------------------------------------------------
# Service catalog (Phase 3 combined checkbox)
# ---------------------------------------------------------------------------


def _handle_service_catalog(schema: QuestionSchema, state: State) -> None:
    """Present the service catalog as a single grouped checkbox, then
    record foundation_services, selected_services, host_addons, and subdomains.

    Uses questionary.checkbox with sectioned Choices so the user sees
    Foundation (pre-checked), Optional (unchecked), and Host Addons (unchecked)
    in one prompt.
    """
    catalog = schema.service_catalog or {}

    foundation_items = catalog.get("foundation_bundle", [])
    optional_items = catalog.get("optional_services", [])
    host_items = catalog.get("host_addons", [])

    choices: list[Choice] = []

    if foundation_items:
        choices.append(Choice(title="━━ Foundation Bundle ━━", value="__header_foundation__", disabled=True))
        for item in foundation_items:
            slug = item["slug"]
            label = item.get("label", slug)
            choices.append(Choice(title=f"  {label}", value=slug, checked=True))

    if optional_items:
        choices.append(Choice(title="━━ Optional Services ━━", value="__header_optional__", disabled=True))
        for item in optional_items:
            slug = item["slug"]
            label = item.get("label", slug)
            choices.append(Choice(title=f"  {label}", value=slug, checked=False))

    if host_items:
        choices.append(Choice(title="━━ Host Addons ━━", value="__header_host__", disabled=True))
        for item in host_items:
            slug = item["slug"]
            label = item.get("label", slug)
            choices.append(Choice(title=f"  {label}", value=slug, checked=False))

    console.print("\n[bold]=== Service Selection ===[/bold]\n")

    selected = prompt_checkbox("Select services to install:", choices=choices)

    foundation_defaults = [item["slug"] for item in foundation_items]
    foundation_selected = [s for s in selected if s in foundation_defaults]
    optional_selected = [s for s in selected if s in {item["slug"] for item in optional_items}]
    host_selected = [s for s in selected if s in {item["slug"] for item in host_items}]

    state.set("foundation_services", foundation_selected)
    state.set("selected_services", optional_selected)
    state.set("host_addons", host_selected)

    _build_subdomain_defaults(foundation_items + optional_items, state)

    customize = prompt_confirm(
        "Do you want to customize any subdomains?",
        default=False,
    )
    state.set("customize_subdomains", customize)

    if customize:
        _customize_subdomains(foundation_items + optional_items, state)


def _build_subdomain_defaults(items: list[dict[str, Any]], state: State) -> None:
    """Set default subdomains for all selected services."""
    for item in items:
        slug = item["slug"]
        default_sub = item.get("default_subdomain", slug)
        state.set(f"subdomains.{slug}", default_sub)
        state.set(f"{slug.upper().replace('-', '_')}_SUBDOMAIN", default_sub)


def _customize_subdomains(items: list[dict[str, Any]], state: State) -> None:
    """Prompt the user to customize subdomain for each service."""
    for item in items:
        slug = item["slug"]
        default_sub = item.get("default_subdomain", slug)
        answer = prompt_text(f"Subdomain for {slug}? [{default_sub}] ", default=default_sub)
        if answer and answer.strip():
            state.set(f"subdomains.{slug}", answer.strip())
            state.set(f"{slug.upper().replace('-', '_')}_SUBDOMAIN", answer.strip())


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------


def _handle_derived(field: FieldDef, state: State) -> None:
    """Handle derived field types."""
    if field.detect:
        result = _run_detect(field, state)
        if isinstance(result, dict):
            for k, v in result.items():
                state.set(k, v)
        elif result is not None:
            _record_field_value(field, result, state)
        return

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

    if field.value is not None:
        value = field.value
        if isinstance(value, dict):
            if field.records and all(r in value for r in field.records):
                rendered = _render_template_dict(value, state)
                for k, v in rendered.items():
                    state.set(k, v)
                return
            platform = state.get("platform")
            if platform and platform in value:
                value = value[platform]
            elif "default" in value:
                value = value["default"]

        _record_field_value(field, value, state)
        return

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

    normalize = detect.get("normalize") if isinstance(detect, dict) else None
    if normalize and isinstance(normalize, dict):
        if output in normalize:
            val = normalize[output]
            if isinstance(val, dict):
                return val
            return val
        if "default" in normalize:
            val = normalize["default"]
            if isinstance(val, dict):
                return val
            return val

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
# Prompt wrappers (questionary-based)
# ---------------------------------------------------------------------------


def _prompt_text(field: FieldDef, state: State) -> str:
    """Prompt for text input with validation."""
    default = _get_default(field, state)
    prompt = field.prompt

    while True:
        default_str = str(default) if default is not None and default != "" else None
        answer = prompt_text(prompt, default=default_str)

        if answer == "" and default is not None:
            answer = str(default)

        if _validate(answer, field):
            return answer


def _prompt_confirm(field: FieldDef, state: State) -> Any:
    """Prompt for confirmation or yes/no mapped to arbitrary values.

    For boolean confirms (y/n → True/False), uses questionary.confirm.
    For non-boolean mappings (y/n → generate/manual), uses questionary.select.
    """
    prompt = field.prompt
    default = field.default

    if field.accepted_inputs:
        values = set(field.accepted_inputs.values())
        if values <= {True, False}:
            bool_default = default if isinstance(default, bool) else False
            return prompt_confirm(prompt, default=bool_default)
        else:
            choices = [str(k) for k in field.accepted_inputs.keys()]
            values_map = {str(k): v for k, v in field.accepted_inputs.items()}
            while True:
                result = prompt_select(prompt, choices=choices)
                if result is None:
                    if default is not None:
                        return default
                    continue
                matched = values_map.get(result.lower())
                if matched is not None:
                    return matched
                console.print(f"[red]Invalid choice. Valid options: {', '.join(choices)}[/red]")
    else:
        bool_default = default if isinstance(default, bool) else False
        return prompt_confirm(prompt, default=bool_default)


def _prompt_single_select(field: FieldDef, state: State) -> str:
    """Prompt for single select using questionary.select."""
    prompt = field.prompt
    values = field.canonical_values

    choices = []
    for canonical in values:
        aliases = field.aliases.get(canonical, [])
        if aliases and len(aliases) > 1:
            title = f"{canonical} ({', '.join(aliases)})"
        elif aliases:
            title = f"{canonical} ({aliases[0]})"
        else:
            title = canonical
        choices.append(Choice(title=title, value=canonical))

    result = prompt_select(prompt, choices=choices)
    if result is not None:
        return result

    while True:
        fallback = prompt_text(prompt)
        if not fallback:
            continue
        fallback_lower = fallback.strip().lower()
        for canonical, aliases in field.aliases.items():
            if fallback_lower in [a.lower() for a in aliases]:
                return canonical
        if fallback_lower in [v.lower() for v in values]:
            return fallback_lower
        console.print(f"[red]Invalid choice. Valid options: {', '.join(values)}[/red]")


def _prompt_multi_select(field: FieldDef, state: State) -> list[str]:
    """Prompt for multi-select using questionary.checkbox."""
    prompt = field.prompt
    selection_mode = getattr(field, "selection_mode", "") or ""
    default = field.default if field.default is not None else []
    if not isinstance(default, list):
        default = []

    canonical = field.canonical_values

    choices = []
    for item in canonical:
        is_checked = item in default
        choices.append(Choice(title=item, value=item, checked=is_checked))

    selected = prompt_checkbox(prompt, choices=choices)

    if not selected:
        if selection_mode == "deselect_from_default":
            return list(default)
        return []

    if selection_mode == "deselect_from_default":
        return [d for d in default if d not in selected]
    else:
        return list(dict.fromkeys(selected))


# ---------------------------------------------------------------------------
# Special field types
# ---------------------------------------------------------------------------


def _handle_secret_group(field: FieldDef, state: State) -> None:
    """Handle secret group entries — uses password (hidden) input."""
    for entry in field.entries:
        key = entry.get("key", "")
        when = entry.get("when", "always")

        if when != "always" and not eval_when(when, state):
            continue

        while True:
            value = prompt_password(f"Enter value for {key}:")
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
                answer = prompt_text(prompt, default=default)
                if answer == "":
                    answer = default
                if _validate(answer, field):
                    state.set(f"subdomains.{slug}", answer)
                    state.set(f"{slug.upper().replace('-', '_')}_SUBDOMAIN", answer)
                    break
        else:
            state.set(f"subdomains.{slug}", default)
            state.set(f"{slug.upper().replace('-', '_')}_SUBDOMAIN", default)


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
                confirmed = prompt_confirm(
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