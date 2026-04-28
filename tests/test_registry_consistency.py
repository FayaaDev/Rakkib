"""Consistency checks for registry-declared templates and hooks."""

from __future__ import annotations

from rakkib.hooks.services import POST_RENDER_HOOKS, POST_START_HOOKS, PRE_START_HOOKS
from rakkib.steps import data_dir, load_service_registry


def test_registry_templates_and_hooks_resolve():
    registry = load_service_registry()
    repo = data_dir()

    for svc in registry["services"]:
        caddy = svc.get("caddy") or {}
        for template_name in (caddy.get("template"), caddy.get("public_template")):
            if template_name:
                assert (repo / "templates" / "caddy" / "routes" / template_name).exists()

        for extra in svc.get("extra_templates", []):
            assert (repo / extra["src"]).exists()

        blueprint = (svc.get("authentik") or {}).get("blueprint")
        if blueprint:
            assert (repo / blueprint).exists()

        hooks = svc.get("hooks") or {}
        for hook_name in hooks.get("post_render", []):
            assert hook_name in POST_RENDER_HOOKS
        for hook_name in hooks.get("pre_start", []):
            assert hook_name in PRE_START_HOOKS
        for hook_name in hooks.get("post_start", []):
            assert hook_name in POST_START_HOOKS


def test_registry_postgres_contracts_are_complete():
    registry = load_service_registry()

    for svc in registry["services"]:
        postgres = svc.get("postgres") or {}
        if not postgres:
            continue

        password_key = postgres.get("password_key")
        assert password_key, f"{svc['id']} postgres config must declare password_key"

        declared_secret_keys = set(svc.get("env_keys", []) or [])
        declared_secret_keys.update((svc.get("secrets") or {}).keys())
        for condition in svc.get("conditional_secrets", []):
            declared_secret_keys.update((condition.get("keys") or {}).keys())

        assert password_key in declared_secret_keys, (
            f"{svc['id']} postgres password_key '{password_key}' must be declared in env_keys, "
            "secrets, or conditional_secrets"
        )

        pre_start_hooks = (svc.get("hooks") or {}).get("pre_start", [])
        assert "service_postgres_login_preflight" in pre_start_hooks, (
            f"{svc['id']} declares postgres and must use service_postgres_login_preflight"
        )
