# Question File 05 — Secrets

**Phase 5 of 6. No writes outside the repo occur during this phase.**

## AgentSchema

```yaml
schema_version: 1
phase: 5
reads_state:
  - foundation_services
  - selected_services
writes_state:
  - secrets.mode
  - secrets.n8n_mode
  - secrets.values
fields:
  - id: secrets_mode
    type: confirm
    prompt: Do you want the agent to generate all required passwords and keys automatically? [y/N]
    accepted_inputs:
      y: generate
      n: manual
      "yes": generate
      "no": manual
    records:
      - secrets.mode
  - id: manual_secret_values
    type: secret_group
    when: secrets.mode == manual
    records:
      - secrets.values
    entries:
      - key: POSTGRES_PASSWORD
        when: always
      - key: NOCODB_DB_PASS
        when: nocodb in foundation_services
      - key: NOCODB_ADMIN_PASS
        when: nocodb in foundation_services
      - key: N8N_DB_PASS
        when: n8n in selected_services
      - key: N8N_ENCRYPTION_KEY
        when: n8n in selected_services
      - key: IMMICH_DB_PASSWORD
        when: immich in selected_services
  - id: n8n_mode
    type: single_select
    when: n8n in selected_services
    prompt: Is this a fresh n8n install, or are you restoring/migrating an existing n8n instance? (fresh/migrate)
    canonical_values: [fresh, migrate]
    aliases:
      fresh: [fresh]
      migrate: [migrate, restore, restoring]
    records:
      - secrets.n8n_mode
  - id: migrate_n8n_encryption_key
    type: text
    when: n8n in selected_services and secrets.n8n_mode == migrate and secrets.values.N8N_ENCRYPTION_KEY is null
    prompt: What is the existing N8N_ENCRYPTION_KEY for this n8n instance?
    validate:
      non_empty: true
    records:
      - secrets.values.N8N_ENCRYPTION_KEY
execution_generated_only:
  - key: IMMICH_VERSION
    when: immich in selected_services
    reason: Defaults to `release` during Immich rendering; not prompted during the interview.
```

---

## Instructions for the Agent

Ask the questions below in order. Record all results into `.fss-state.yaml` under `secrets:`.

Secrets can be generated later during execution, but the strategy must be decided now. If the user wants to supply values manually, record them exactly. Remind the user that `.fss-state.yaml` is gitignored.

---

## Questions to Ask

### Q1 — Secret Strategy

Ask: "Do you want the agent to generate all required passwords and keys automatically? [y/N]"

Accepted answers: `y` or `n`.

If the answer is `y`, record `mode: generate` and skip to the service-specific preservation questions below.

If the answer is `n`, record `mode: manual` and ask for the following values:

- `POSTGRES_PASSWORD`
- `NOCODB_DB_PASS` if `nocodb` is in `foundation_services`
- `NOCODB_ADMIN_PASS` if `nocodb` is in `foundation_services`

If `n8n` is selected, also ask for:
- `N8N_DB_PASS`
- `N8N_ENCRYPTION_KEY`

If `immich` is selected, also ask for:
- `IMMICH_DB_PASSWORD`

Record each value under `secrets.values`.

### Q2 — Existing n8n Key Preservation

Only ask this if `n8n` is selected.

Ask: "Is this a fresh n8n install, or are you restoring/migrating an existing n8n instance? (fresh/migrate)"

Accepted answers:
- `fresh`
- `migrate`
- `restore` -> `migrate`
- `restoring` -> `migrate`

If `migrate` and `N8N_ENCRYPTION_KEY` is not already recorded, ask for the existing key and record it.

Warn clearly: `N8N_ENCRYPTION_KEY` must not change after first use.

---

## Record in .fss-state.yaml

```yaml
secrets:
  mode: generate
  n8n_mode: fresh
  values:
    POSTGRES_PASSWORD: null
    NOCODB_DB_PASS: null
    NOCODB_ADMIN_PASS: null
    N8N_DB_PASS: null
    N8N_ENCRYPTION_KEY: null
    IMMICH_DB_PASSWORD: null
    IMMICH_VERSION: null
```

For generated mode, values may stay `null` until execution time.

During rendering, every key under `secrets.values` maps directly to the placeholder of the same name. Example: `secrets.values.POSTGRES_PASSWORD` -> `{{POSTGRES_PASSWORD}}`.
