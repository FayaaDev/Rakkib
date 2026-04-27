# Step 10 — Layout

Create the target directory structure under `{{DATA_ROOT}}`.

## Actions

1. On Linux, create the managed `/srv` layout with the allowlisted helper when available: `sudo -n rakkib privileged ensure-layout --state .fss-state.yaml`. This creates `{{DATA_ROOT}}`, `{{DATA_ROOT}}/docker`, `{{DATA_ROOT}}/data`, `{{DATA_ROOT}}/apps/static`, `{{DATA_ROOT}}/backups`, and `{{DATA_ROOT}}/MDs` without running the full agent as root. If `sudo -n` fails because authorization expired, stop and ask the user to run `rakkib auth sudo` in a terminal.
2. On Mac, create these directories if they do not already exist:
   `{{DATA_ROOT}}/docker`, `{{DATA_ROOT}}/data`, `{{DATA_ROOT}}/apps/static`, `{{DATA_ROOT}}/backups`, and `{{DATA_ROOT}}/MDs`.
3. Create per-service directories only for required and selected services.
4. Ensure the admin user owns the created paths.
5. Create a placeholder root-site directory only if the user wants a static root site later.

## Verify

- `ls -ld {{DATA_ROOT}} {{DATA_ROOT}}/docker {{DATA_ROOT}}/data {{DATA_ROOT}}/backups {{DATA_ROOT}}/MDs`
- `test -w {{DATA_ROOT}}/docker`
