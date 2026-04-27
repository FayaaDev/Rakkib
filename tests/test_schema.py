"""Tests for schema parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from rakkib.schema import FieldDef, QuestionSchema, load_all_schemas

QUESTIONS_DIR = Path(__file__).resolve().parent.parent / "questions"


def test_load_all_schemas_finds_all_six():
    schemas = load_all_schemas(QUESTIONS_DIR)
    phases = [s.phase for s in schemas]
    assert phases == [1, 2, 3, 4, 5, 6]


def test_phase_1_platform_field():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "01-platform.md")
    assert schema.phase == 1
    assert schema.schema_version == 1

    field_map = {f.id: f for f in schema.fields}

    # Derived host field: arch
    arch = field_map["arch"]
    assert arch.type == "derived"
    assert arch.source == "host"
    assert arch.detect["command"] == "uname -m"
    assert arch.detect["normalize"]["x86_64"] == "amd64"
    assert arch.records == ["arch"]

    # Platform single_select
    platform = field_map["platform"]
    assert platform.type == "single_select"
    assert platform.prompt == "What platform are you installing on?"
    assert platform.canonical_values == ["linux", "mac"]
    assert platform.normalize == "lowercase"
    assert platform.aliases["mac"] == ["mac", "macos", "osx", "darwin"]
    assert platform.records == ["platform"]

    # Docker confirm
    docker = field_map["docker_installed"]
    assert docker.type == "confirm"
    assert docker.accepted_inputs["y"] is True
    assert docker.accepted_inputs["n"] is False

    # Host gateway derived
    gw = field_map["host_gateway"]
    assert gw.type == "derived"
    assert gw.value["linux"] == "172.18.0.1"
    assert gw.value["mac"] == "host.docker.internal"


def test_phase_2_identity_fields():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "02-identity.md")
    assert schema.phase == 2

    field_map = {f.id: f for f in schema.fields}

    server_name = field_map["server_name"]
    assert server_name.type == "text"
    assert server_name.validate["pattern"] == r"^[a-z0-9-]+$"
    assert server_name.validate["message"] == "Use lowercase letters, numbers, and hyphens only."

    domain = field_map["domain"]
    assert domain.type == "text"
    assert domain.validate["pattern"] == r"^(?!https?://).+\..+$"

    admin_user = field_map["admin_user"]
    assert admin_user.default_from_host is not None
    assert admin_user.default_from_host["linux"] == "id -un"

    lan_ip = field_map["lan_ip"]
    assert lan_ip.type == "derived"
    assert lan_ip.source == "host"
    assert lan_ip.detect["linux"] == "hostname -I"
    assert lan_ip.normalize == "first_non_loopback_ipv4"

    data_root = field_map["data_root"]
    assert data_root.derive_from == "platform"
    assert data_root.value["linux"] == "/srv"

    backup_dir = field_map["backup_dir"]
    assert backup_dir.template == "{{data_root}}/backups"
    assert backup_dir.derive_from == "data_root"


def test_phase_3_service_catalog_and_rules():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "03-services.md")
    assert schema.phase == 3

    assert "foundation_bundle" in schema.service_catalog
    assert len(schema.service_catalog["foundation_bundle"]) == 5
    assert schema.service_catalog["foundation_bundle"][0]["slug"] == "nocodb"

    assert len(schema.rules) == 2
    assert schema.rules[0]["if_selected"] == "transfer"

    field_map = {f.id: f for f in schema.fields}
    foundation = field_map["foundation_services"]
    assert foundation.type == "multi_select"
    assert foundation.selection_mode == "deselect_from_default"
    assert foundation.numeric_aliases["1"] == "nocodb"

    optional = field_map["optional_services"]
    assert optional.type == "multi_select"
    assert optional.selection_mode == "add_to_empty"
    assert optional.records == ["selected_services"]

    subdomain = field_map["service_subdomain"]
    assert subdomain.type == "text"
    assert subdomain.repeat_for == "selected_service_slugs"


def test_phase_4_cloudflare_execution_paths():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "04-cloudflare.md")
    assert schema.phase == 4

    field_map = {f.id: f for f in schema.fields}

    tunnel_strategy = field_map["tunnel_strategy"]
    assert tunnel_strategy.type == "single_select"
    assert tunnel_strategy.canonical_values == ["new", "existing"]
    assert tunnel_strategy.aliases["existing"] == ["existing", "reuse"]

    headless = field_map["headless"]
    assert headless.type == "confirm"
    assert headless.when == "cloudflare.tunnel_strategy == new"
    assert headless.derived_value == {"cloudflare.auth_method": "browser_login"}
    assert headless.records == ["cloudflare.headless", "cloudflare.auth_method"]

    advanced = field_map["advanced_api_token"]
    assert advanced.type == "confirm"
    assert advanced.when == "cloudflare.tunnel_strategy == new and accept_browser_login == false"
    assert advanced.value_if_true == {"cloudflare.auth_method": "api_token"}

    existing_auth = field_map["existing_tunnel_auth"]
    assert existing_auth.type == "derived"
    assert existing_auth.when == "cloudflare.tunnel_strategy == existing"
    assert existing_auth.value == {"cloudflare.auth_method": "existing_tunnel", "cloudflare.headless": None}

    tunnel_name = field_map["tunnel_name"]
    assert tunnel_name.default_from_state == "server_name"

    tunnel_uuid = field_map["tunnel_uuid"]
    assert tunnel_uuid.when == "cloudflare.tunnel_strategy == existing and knows_tunnel_uuid == true"
    assert tunnel_uuid.validate["pattern"] == r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

    creds = field_map["tunnel_credential_paths"]
    assert creds.when == "cloudflare.tunnel_uuid is not null"
    assert creds.derive_from == ["data_root", "cloudflare.tunnel_uuid"]


def test_phase_5_secrets_and_execution_generated():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "05-secrets.md")
    assert schema.phase == 5

    assert len(schema.execution_generated_only) == 3
    assert schema.execution_generated_only[0]["key"] == "NOCODB_OIDC_CLIENT_ID"

    field_map = {f.id: f for f in schema.fields}
    secrets_mode = field_map["secrets_mode"]
    assert secrets_mode.type == "confirm"
    assert secrets_mode.accepted_inputs["y"] == "generate"
    assert secrets_mode.accepted_inputs["n"] == "manual"
    assert secrets_mode.records == ["secrets.mode"]

    manual = field_map["manual_secret_values"]
    assert manual.type == "secret_group"
    assert manual.when == "secrets.mode == manual"
    assert len(manual.entries) > 0
    assert manual.entries[0]["key"] == "POSTGRES_PASSWORD"

    n8n = field_map["n8n_mode"]
    assert n8n.type == "single_select"
    assert n8n.when == "n8n in selected_services"
    assert n8n.aliases["migrate"] == ["migrate", "restore", "restoring"]


def test_phase_6_summary_and_confirm():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "06-confirm.md")
    assert schema.phase == 6

    field_map = {f.id: f for f in schema.fields}

    summary = field_map["deployment_summary"]
    assert summary.type == "summary"
    assert "server_name" in summary.summary_fields

    confirmed = field_map["confirmed"]
    assert confirmed.type == "confirm"
    assert confirmed.records == ["confirmed"]


def test_question_schema_from_text():
    text = """
## AgentSchema
```yaml
schema_version: 1
phase: 99
fields:
  - id: test
    type: text
    prompt: Hello
```
"""
    schema = QuestionSchema.from_text(text)
    assert schema.phase == 99
    assert len(schema.fields) == 1
    assert schema.fields[0].id == "test"


def test_question_schema_missing_block_raises():
    with pytest.raises(ValueError, match="No AgentSchema block found"):
        QuestionSchema.from_text("# Just markdown\nNo schema here.")
