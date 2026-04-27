"""Schema parsing — extract AgentSchema YAML from questions/*.md files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

QUESTIONS_DIR = Path("questions")


@dataclass
class FieldDef:
    """A single field definition from an AgentSchema block."""

    id: str
    type: str
    prompt: str = ""
    prompt_template: str = ""
    when: str | None = None
    default: Any = None
    default_from_state: str | None = None
    default_from_host: Any = None
    canonical_values: list[str] = field(default_factory=list)
    numeric_aliases: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, list[str]] = field(default_factory=dict)
    accepted_inputs: dict[str, Any] = field(default_factory=dict)
    validate: dict[str, Any] | str | None = None
    detect: dict[str, Any] = field(default_factory=dict)
    normalize: str | dict[str, Any] | None = None
    derive_from: str | list[str] | None = None
    value: Any = None
    derived_value: dict[str, Any] = field(default_factory=dict)
    value_if_true: Any = None
    records: list[str] = field(default_factory=list)
    repeat_for: str | None = None
    summary_fields: list[str] = field(default_factory=list)
    entries: list[dict[str, Any]] = field(default_factory=list)
    source: str | None = None
    template: str | None = None
    selection_mode: str | None = None
    required: bool = True


@dataclass
class QuestionSchema:
    """Parsed AgentSchema from a single question file."""

    schema_version: int
    phase: int
    reads_state: list[str] = field(default_factory=list)
    writes_state: list[str] = field(default_factory=list)
    fields: list[FieldDef] = field(default_factory=list)
    service_catalog: dict[str, Any] = field(default_factory=dict)
    rules: list[dict[str, Any]] = field(default_factory=list)
    execution_generated_only: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path | str) -> "QuestionSchema":
        """Parse a questions/*.md file and extract its AgentSchema YAML block."""
        text = Path(path).read_text()
        return cls.from_text(text)

    @classmethod
    def from_text(cls, text: str) -> "QuestionSchema":
        """Parse AgentSchema YAML from markdown text."""
        match = re.search(
            r"## AgentSchema\s+```yaml\n(.*?)```",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            raise ValueError("No AgentSchema block found")
        raw = yaml.safe_load(match.group(1))
        if not isinstance(raw, dict):
            raise ValueError("AgentSchema block is not a YAML mapping")

        known_field_keys = {f.name for f in FieldDef.__dataclass_fields__.values()}
        fields = []
        for f in raw.get("fields", []):
            if not isinstance(f, dict):
                raise ValueError("Each field must be a YAML mapping")
            filtered = {k: v for k, v in f.items() if k in known_field_keys}
            fields.append(FieldDef(**filtered))

        return cls(
            schema_version=raw.get("schema_version", 1),
            phase=raw.get("phase", 0),
            reads_state=raw.get("reads_state", []),
            writes_state=raw.get("writes_state", []),
            fields=fields,
            service_catalog=raw.get("service_catalog", {}),
            rules=raw.get("rules", []),
            execution_generated_only=raw.get("execution_generated_only", []),
        )


def load_all_schemas(directory: Path | str = QUESTIONS_DIR) -> list[QuestionSchema]:
    """Load and return all question schemas sorted by phase."""
    directory = Path(directory)
    schemas = []
    for path in sorted(directory.glob("*.md")):
        try:
            schemas.append(QuestionSchema.from_file(path))
        except ValueError:
            continue  # skip files without AgentSchema
    schemas.sort(key=lambda s: s.phase)
    return schemas
