# Question File 05 — Secrets

**Phase 5 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the questions below in order. Record all results into `.fss-state.yaml` under `secrets:`.

Secrets can be generated later during execution, but the strategy must be decided now. If the user wants to supply values manually, record them exactly. Remind the user that `.fss-state.yaml` is gitignored.

---

## Questions to Ask

### Q1 — Secret Strategy

Ask: "Do you want the agent to generate all required passwords and keys automatically? (y/n)"

Accepted answers: `y` or `n`.

If the answer is `y`, record `mode: generate` and skip to the service-specific preservation questions below.

If the answer is `n`, record `mode: manual` and ask for the following values:

- `POSTGRES_PASSWORD`
- `NOCODB_DB_PASS`
- `NOCODB_ADMIN_PASS`

If `n8n` is selected, also ask for:
- `N8N_DB_PASS`
- `N8N_ENCRYPTION_KEY`

Record each value under `secrets.values`.

### Q2 — Existing n8n Key Preservation

Only ask this if `n8n` is selected.

Ask: "Is this a fresh n8n install, or are you restoring/migrating an existing n8n instance? (fresh/migrate)"

Accepted answers:
- `fresh`
- `migrate`

If `migrate` and `N8N_ENCRYPTION_KEY` is not already recorded, ask for the existing key and record it.

Warn clearly: `N8N_ENCRYPTION_KEY` must not change after first use.

---

## Record in .fss-state.yaml

```yaml
secrets:
  mode: generate              # or: manual
  n8n_mode: fresh             # only if n8n selected
  values:
    POSTGRES_PASSWORD: null
    NOCODB_DB_PASS: null
    NOCODB_ADMIN_PASS: null
    N8N_DB_PASS: null
    N8N_ENCRYPTION_KEY: null
```

For generated mode, values may stay `null` until execution time.
